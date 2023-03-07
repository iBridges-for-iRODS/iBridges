"""IrodsConnector base

"""
import base64
import hashlib
import json
import logging
import os
import random
import shutil
import ssl
import string
import subprocess

import irods.access
import irods.collection
import irods.column
import irods.connection
import irods.data_object
import irods.exception
import irods.keywords
import irods.meta
import irods.models
import irods.password_obfuscation
import irods.rule
import irods.session
import irods.ticket

import utils

# Keywords
ALL_KW = irods.keywords.ALL_KW
FORCE_FLAG_KW = irods.keywords.FORCE_FLAG_KW
NUM_THREADS_KW = irods.keywords.NUM_THREADS_KW  # 'num_threads'
DEST_RESC_NAME_KW = irods.keywords.DEST_RESC_NAME_KW
RESC_NAME_KW = irods.keywords.RESC_NAME_KW
VERIFY_CHKSUM_KW = irods.keywords.VERIFY_CHKSUM_KW
REG_CHKSUM_KW = irods.keywords.REG_CHKSUM_KW
# Map model names to iquest attribute names
COLL_NAME = irods.models.Collection.name
DATA_NAME = irods.models.DataObject.name
DATA_CHECKSUM = irods.models.DataObject.checksum
META_COLL_ATTR_NAME = irods.models.CollectionMeta.name
META_COLL_ATTR_VALUE = irods.models.CollectionMeta.value
META_DATA_ATTR_NAME = irods.models.DataObjectMeta.name
META_DATA_ATTR_VALUE = irods.models.DataObjectMeta.value
RESC_NAME = irods.models.Resource.name
RESC_PARENT = irods.models.Resource.parent
RESC_STATUS = irods.models.Resource.status
RESC_CONTEXT = irods.models.Resource.context
USER_GROUP_NAME = irods.models.UserGroup.name
USER_NAME = irods.models.User.name
USER_TYPE = irods.models.User.type
# Query operators
LIKE = irods.column.Like
# ASCII colors
BLUE = '\x1b[1;34m'
DEFAULT = '\x1b[0m'
RED = '\x1b[1;31m'
YEL = '\x1b[1;33m'
# Misc
BUFF_SIZE = 10**9
MULTIPLIER = 1 / 10**9
NUM_THREADS = 4


class FreeSpaceNotSet(Exception):
    """Custom Exception for when free_space iRODS parameter missing.

    """


class NotEnoughFreeSpace(Exception):
    """Custom Exception for when the reported free_space is too low.

    """


class IrodsConnector():
    """Create a connection to an iRODS system.

    """
    _ienv = {}
    _password = ''
    _permissions = None
    _resources = None
    _session = None

    def __init__(self, irods_env_file='', password='', application_name=None):
        """iRODS authentication with Python client.

        Parameters
        ----------
        irods_env_file : str
            JSON document with iRODS connection parameters.
        password : str
            Plain text password.
        application_name : str
            Name of the application using this connector.

        The 'ienv' and 'password' properties can autoload from their
        respective caches, but can be overridden by the `ienv` and
        `password` arguments, respectively.  The iRODS environment file
        is expected in the standard location
        (~/.irods/irods_environment.json) or to be specified in the
        local environment with the IRODS_ENVIRONMENT_FILE variable, and
        the iRODS authentication file is expected in the standard
        location (~/.irods/.irodsA) or to be specified in the local
        environment with the IRODS_AUTHENTICATION_FILE variable.

        """
        self.__name__ = 'IrodsConnector'
        self.irods_env_file = irods_env_file
        if password:
            self.password = password
        self.application_name = application_name
        self.multiplier = MULTIPLIER

    @property
    def davrods(self):
        """DavRODS server URL.

        Returns
        -------
        str
            URL of the configured DavRODS server.

        """
        # FIXME move iBridges parameters to iBridges configuration
        return self.ienv.get('davrods_server', None)







    def get_user_info(self):
        """Query for user type and groups.

        Returns
        -------
        str
            iRODS user type name.
        list
            iRODS group names.

        """
        query = self.session.query(USER_TYPE).filter(LIKE(
            USER_NAME, self.session.username))
        user_type = [
            list(result.values())[0] for result in query.get_results()
        ][0]
        query = self.session.query(USER_GROUP_NAME).filter(LIKE(
            USER_NAME, self.session.username))
        user_groups = [
            list(result.values())[0] for result in query.get_results()
        ]
        return user_type, user_groups





    def search(self, key_vals=None):
        """Given a dictionary with metadata attribute names as keys and
        associated values, query for collections and data objects that
        fullfill the criteria.  The key 'checksum' will be mapped to
        DataObject.checksum, the key 'path' will be mapped to
        Collection.name and the key 'object' will be mapped to
        DataObject.name:

        {
            'checksum': '',
            'key1': 'val1',
            'key2': 'val2',
            'path': '',
            'object': '',
        }

        By Default, if `key_vals` is empty, all accessible collections
        and data objects will be returned.

        Parameters
        ----------
        key_vals : dict
            Attribute name mapping to values.

        Returns
        -------
        list: [[Collection name, Object name, checksum]]

        """
        coll_query = None
        data_query = None
        # data query
        if 'checksum' in key_vals or 'object' in key_vals:
            data_query = self.session.query(
                COLL_NAME, DATA_NAME, DATA_CHECKSUM)
            if 'object' in key_vals:
                if key_vals['object']:
                    data_query = data_query.filter(
                        LIKE(DATA_NAME, key_vals['object']))
            if 'checksum' in key_vals:
                if key_vals['checksum']:
                    data_query = data_query.filter(LIKE(
                        DATA_CHECKSUM, key_vals['checksum']))
        else:
            coll_query = self.session.query(COLL_NAME)
            data_query = self.session.query(
                COLL_NAME, DATA_NAME, DATA_CHECKSUM)

        if 'path' in key_vals and key_vals['path']:
            if coll_query:
                coll_query = coll_query.filter(LIKE(
                    COLL_NAME, key_vals['path']))
            data_query = data_query.filter(LIKE(
                COLL_NAME, key_vals['path']))
        for key in key_vals:
            if key not in ['checksum', 'path', 'object']:
                if data_query:
                    data_query.filter(META_DATA_ATTR_NAME == key)
                if coll_query:
                    coll_query.filter(META_COLL_ATTR_NAME == key)
                if key_vals[key]:
                    if data_query:
                        data_query.filter(
                            META_DATA_ATTR_VALUE == key_vals[key])
                    if coll_query:
                        coll_query.filter(
                            META_COLL_ATTR_VALUE == key_vals[key])
        results = [['', '', ''], ['', '', ''], ['', '', '']]
        coll_batch = [[]]
        data_batch = [[]]
        # Return only 100 results.
        if coll_query:
            num_colls = len(list(coll_query))
            results[0] = [f'Collections found: {num_colls}', '', '']
            coll_batch = list(coll_query.get_batches())
        if data_query:
            num_objs = len(list(data_query))
            results[1] = [f'Objects found: {num_objs}', '', '']
            data_batch = list(data_query.get_batches())
        for res in coll_batch[0][:50]:
            results.append([res[list(res.keys())[0]], '', ''])
        for res in data_batch[0][:50]:
            results.append([res[list(res.keys())[0]],
                            res[list(res.keys())[1]],
                            res[list(res.keys())[2]]])
        return results

    def execute_rule(self, rule_file, params, output='ruleExecOut'):
        """Execute an iRODS rule.

        Parameters
        ----------
        rule_file : str, file-like
            Name of the iRODS rule file, or a file-like object representing it.
        params : dict
            Rule arguments.
        output : str
            Rule output variable(s).

        Returns
        -------
        tuple
            (stdout, stderr)

        `params` format example:

        params = {  # extra quotes for string literals
            '*obj': '"/zone/home/user"',
            '*name': '"attr_name"',
            '*value': '"attr_value"'
        }

        """
        try:
            rule = irods.rule.Rule(
                self.session, rule_file=rule_file, params=params, output=output,
                instance_name='irods_rule_engine_plugin-irods_rule_language-instance')
            out = rule.execute()
        except irods.exception.NetworkException as netexc:
            logging.info('Lost connection to iRODS server.')
            return '', repr(netexc)
        except irods.exception.SYS_HEADER_READ_LEN_ERR as shrle:
            logging.info('iRODS server hiccuped.  Check the results and try again.')
            return '', repr(shrle)
        except Exception as error:
            logging.info('RULE EXECUTION ERROR', exc_info=True)
            return '', repr(error)
        stdout, stderr = '', ''
        if len(out.MsParam_PI) > 0:
            buffers = out.MsParam_PI[0].inOutStruct
            stdout = (buffers.stdoutBuf.buf or b'').decode()
            # Remove garbage after terminal newline.
            stdout = '\n'.join(stdout.split('\n')[:-1])
            stderr = (buffers.stderrBuf.buf or b'').decode()
        return stdout, stderr




