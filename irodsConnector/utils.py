""" irods utils
"""
from subprocess import call, PIPE
import logging
import irods.collection
import irods.data_object
import irods.exception
import irods.rule
import irods.session
import irodsConnector.keywords as kw


class IrodsUtils(object):
    """Irods calls which don't fit in one of the existing groups"""
    @staticmethod
    def icommands():
        """

        Returns
        -------
        bool
            Are the iCommands available?
        """
        return call(['which', 'iinit'], shell=True, stderr=PIPE) == 0

    @staticmethod
    def is_dataobject_or_collection(obj):
        """Check if `obj` is an iRODS data object or collection.

        Parameters
        ----------
        obj : iRODS object instance
            iRODS instance to check.

        Returns
        -------
        bool
            If `obj` is an iRODS data object or collection.

        """
        return isinstance(obj, (
            irods.data_object.iRODSDataObject,
            irods.collection.iRODSCollection))

    @staticmethod
    def dataobject_exists(session: irods.session, path: str):
        """Check if an iRODS data object exists.

        Parameters
        ----------
        session : irods session
        path : str
            Name of an iRODS data object.

        Returns
        -------
        bool
            Existence of the data object with `path`.

        """
        return session.data_objects.exists(path)

    @staticmethod
    def collection_exists(session: irods.session, path: str):
        """Check if an iRODS collection exists.

        Parameters
        ----------
        session : irods session 
        path : str
            Name of an iRODS collection.

        Returns
        -------
        bool
            Existance of the collection with `path`.

        """
        return session.collections.exists(path)

    def get_user_info(self, session: irods.session):
        """Query for user type and groups.

        Parameters
        ----------
        session : irods session

        Returns
        -------
        str
            iRODS user type name.
        list
            iRODS group names.

        """
        query = session.query(kw.USER_TYPE).filter(kw.LIKE(
            kw.USER_NAME, session.username))
        user_type = [
            list(result.values())[0] for result in query.get_results()
        ][0]
        query = session.query(kw.USER_GROUP_NAME).filter(kw.LIKE(
            kw.USER_NAME, session.username))
        user_groups = [
            list(result.values())[0] for result in query.get_results()
        ]
        return user_type, user_groups

    def search(self, session: irods.session, key_vals: dict = None):
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
        session : irods session
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
            data_query = session.query(
                kw.COLL_NAME, kw.DATA_NAME, kw.DATA_CHECKSUM)
            if 'object' in key_vals:
                if key_vals['object']:
                    data_query = data_query.filter(
                        kw.LIKE(kw.DATA_NAME, key_vals['object']))
            if 'checksum' in key_vals:
                if key_vals['checksum']:
                    data_query = data_query.filter(kw.LIKE(
                        kw.DATA_CHECKSUM, key_vals['checksum']))
        else:
            coll_query = session.query(kw.COLL_NAME)
            data_query = session.query(
                kw.COLL_NAME, kw.DATA_NAME, kw.DATA_CHECKSUM)

        if 'path' in key_vals and key_vals['path']:
            if coll_query:
                coll_query = coll_query.filter(kw.LIKE(
                    kw.COLL_NAME, key_vals['path']))
            data_query = data_query.filter(kw.LIKE(
                kw.COLL_NAME, key_vals['path']))
        for key in key_vals:
            if key not in ['checksum', 'path', 'object']:
                if data_query:
                    data_query.filter(kw.META_DATA_ATTR_NAME == key)
                if coll_query:
                    coll_query.filter(kw.META_COLL_ATTR_NAME == key)
                if key_vals[key]:
                    if data_query:
                        data_query.filter(
                            kw.META_DATA_ATTR_VALUE == key_vals[key])
                    if coll_query:
                        coll_query.filter(
                            kw.META_COLL_ATTR_VALUE == key_vals[key])
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

    def execute_rule(self, session: irods.session, rule_file: str, params: dict, output: str = 'ruleExecOut'):
        """Execute an iRODS rule.

        Parameters
        ----------
        session : irods session
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
                session, rule_file=rule_file, params=params, output=output,
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
