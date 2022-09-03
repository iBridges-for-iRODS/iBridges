"""IrodsConnector base

"""
import base64
import hashlib
import json
import logging
import os
import pathlib
import random
import shutil
import ssl
import string

import irods
import irods.rule
import irods.ticket

# Keywords
ALL_KW = irods.keywords.ALL_KW
FORCE_FLAG_KW = irods.keywords.FORCE_FLAG_KW
REG_CHKSUM_KW = irods.keywords.REG_CHKSUM_KW
RESC_NAME_KW = irods.keywords.RESC_NAME_KW
VERIFY_CHKSUM_KW = irods.keywords.VERIFY_CHKSUM_KW
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
RED = '\x1b[1;31m'
DEFAULT = '\x1b[0m'
YEL = '\x1b[1;33m'
BLUE = '\x1b[1;34m'
# Misc
BUFF_SIZE = 2**30
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

    def __init__(self, ienv=None, password=None):
        """iRODS authentication with Python client.

        Parameters
        ----------
        ienv : dict
            iRODS environment.
        password : str
            Plain text password.

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
        self._ienv = None
        self._password = None
        self._permissions = None
        self._resources = None
        self._session = None
        if ienv is not None:
            self.ienv = ienv
        if password is not None:
            self.password = password
        self.default_resc = None
        if 'irods_default_resource' in self.ienv:
            self.default_resc = self.ienv['irods_default_resource']
        # FIXME move iBridges parameters to iBridges configuration
        self.davrods = None
        if 'davrods_server' in self.ienv:
            self.davrods = self.ienv['davrods_server'].strip('/')

    def _get_ienv(self):
        """iRODS environment getter method.

        Returns
        -------
        dict
            iRODS environmnent dictionary obtained but JSON file.

        """
        if self._ienv is None:
            if 'IRODS_ENVIRONMENT_FILE' in os.environ:
                env_file = os.environ['IRODS_ENVIRONMENT_FILE']
            else:
                env_file = pathlib.Path(
                    '~/.irods/irods_environment.json').expanduser()
            with open(env_file, encoding='utf-8') as envfd:
                self._ienv = json.load(envfd)
        return self._ienv

    def _set_ienv(self, env_dict):
        """iRODS environment setter method.

        Pararmeters
        -----------
        env_dict : dict
            iRODS environment.

        """
        self._ienv = env_dict

    def _del_ienv(self):
        """iRODS environment deleter method.

        """
        self._ienv = None

    ienv = property(
        _get_ienv, _set_ienv, _del_ienv, 'iRODS environment dictionary')

    def _get_password(self):
        """iRODS password getter method.

        Returns
        -------
        str
            iRODS password pre-set or decoded from iRODS authentication
            file.

        """
        if self._password in (None, ''):
            if 'IRODS_AUTHENTICATION_FILE' in os.environ:
                auth_file = os.environ['IRODS_AUTHENTICATION_FILE']
            else:
                auth_file = pathlib.Path('~/.irods/.irodsA').expanduser()
            if os.path.exists(auth_file):
                with open(auth_file, encoding='utf-8') as authfd:
                    encoded = authfd.read()
                self._password = irods.password_obfuscation.decode(encoded)
        return self._password

    def _set_password(self, password):
        """iRODS password setter method.

        Pararmeters
        -----------
        password : str
            Unencrypted iRODS password.

        """
        if password not in (None, ''):
            if 'IRODS_AUTHENTICATION_FILE' in os.environ:
                auth_file = os.environ['IRODS_AUTHENTICATION_FILE']
            else:
                auth_file = pathlib.Path('~/.irods/.irodsA').expanduser()
            encoded = irods.password_obfuscation.encode(password)
            with open(auth_file, 'w', encoding='utf-8') as authfd:
                authfd.write(encoded)
            self._password = password

    def _del_password(self):
        """iRODS password deleter method.

        """
        self._password = None

    password = property(
        _get_password, _set_password, _del_password, 'iRODS password')

    def _get_permissions(self):
        """iRODS permissions mapping getter method.

        Returns
        -------
        dict
            Correct permissions mapping for the current server version.

        """
        if self._permissions is None:
            self._permissions = {
                'null': 'none',
                'read_object': 'read',
                'modify_object': 'write',
                'own': 'own',
            }
            if self.session.server_version < (4, 3, 0):
                self._permissions.update(
                    {'read object': 'read', 'modify object': 'write'})
        return self._permissions

    permissions = property(
        _get_permissions, None, None, 'iRODS permissions mapping')

    def _get_resources(self):
        """iRODS resources metadata getter method.

        Returns
        -------
        dict
            Name, parent, status, context, and free_space of all
            resources.

        NOTE: free_space of a resource is the free_space annotated, if
              so annotated, otherwise it is the sum of the free_space of
              all its children.

        """
        if self._resources is None:
            query = self.session.query(
                RESC_NAME, RESC_PARENT, RESC_STATUS, RESC_CONTEXT)
            resc_list, resc_dict = [], {}
            for item in query.get_results():
                name, parent, status, context = item.values()
                free_space = 0
                if parent is None:
                    free_space = self.get_free_space(name)
                metadata = {
                    'parent': parent,
                    'status': status,
                    'context': context,
                    'free_space': free_space,
                }
                resc_list.append((name, metadata))
            resc_dict.update(
                sorted(resc_list, key=lambda item: str.casefold(item[0])))
            self._resources = resc_dict
            # Check for inclusion of default resource.
            resc_names = []
            for name, metadata in self.resources.items():
                context = metadata['context']
                if context is not None:
                    for kvp in context.split(';'):
                        if 'write' in kvp:
                            _, val = kvp.split('=')
                            if float(val) == 0.0:
                                continue
                status = metadata['status']
                if status is not None:
                    if 'down' in status:
                        continue
                if metadata['parent'] is None and metadata['free_space'] > 0:
                    resc_names.append(name)
            if self.default_resc not in resc_names:
                print('    -=WARNING=-    '*4)
                print(f'The default resource ({self.default_resc}) not found in available resources!')
                print('Check "irods_default_resource" and "force_unknown_free_space" settings.')
                print('    -=WARNING=-    '*4)
        return self._resources

    resources = property(
        _get_resources, None, None, 'iRODS resource metadata')

    def _get_session(self):
        """iRODS session getter method.

        Returns
        -------
        iRODSSession
            iRODS connection based on given environment and password.

        """
        if self._session is None:
            options = self.ienv.copy()
            if self.password is not None:
                options['password'] = self.password
            try:
                self._session = irods.session.iRODSSession(**options)
            except irods.connection.PlainTextPAMPasswordError:
                try:
                    ssl_context = ssl.create_default_context(
                        purpose=ssl.Purpose.SERVER_AUTH,
                        cafile=None, capath=None, cadata=None)
                    ssl_settings = {
                        'client_server_negotiation':
                            'request_server_negotiation',
                        'client_server_policy': 'CS_NEG_REQUIRE',
                        'encryption_algorithm': 'AES-256-CBC',
                        'encryption_key_size': 32,
                        'encryption_num_hash_rounds': 16,
                        'encryption_salt_size': 8,
                        'ssl_context': ssl_context,
                    }
                    options.update(ssl_settings)
                    self._session = irods.session.iRODSSession(**options)
                except Exception as sslerror:
                    raise sslerror
            except Exception as autherror:
                logging.info('AUTHENTICATION ERROR', exc_info=True)
                print(f'{RED}AUTHENTICATION ERROR: {autherror!r}{DEFAULT}')
                raise autherror
            print('Welcome to iRODS:')
            print(f'iRODS Zone: {self._session.zone}')
            print(f'You are: {self._session.username}')
            print(f'Default resource: {self.default_resc}')
            print('You have access to: \n')
            home_path = f'/{self._session.zone}/home'
            colls = self.get_collection(home_path).subcollections
            print('\n'.join([coll.path for coll in colls]))
            logging.info(
                'IRODS LOGIN SUCCESS: %s, %s, %s', self._session.username,
                self._session.zone, self._session.host)
        return self._session

    session = property(_get_session, None, None, 'iRODSSession')

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

    def get_permissions(self, path='', obj=None):
        """Discover ACLs for an iRODS collection expressed as a `path`
        or an `obj`ect.

        Parameters
        ----------
        path : str
            Logical iRODS path of a collection or data object.
        obj : iRODSCollection, iRODSDataObject
            Instance of an iRODS collection or data object.

        Returns
        -------
        list
            iRODS ACL instances.

        """
        if isinstance(path, str) and path:
            try:
                return self.session.permissions.get(
                    self.session.collections.get(path))
            except irods.exception.CollectionDoesNotExist:
                return self.session.permissions.get(
                    self.session.data_objects.get(path))
            finally:
                logging.info('GET PERMISSIONS', exc_info=True)
        if self.is_dataobject_or_collection(obj):
            return self.session.permissions.get(obj)
        print('WARNING -- `obj` must be or `path` must resolve into, a collection or data object')
        return []

    def set_permissions(self, perm, path, user, zone, recursive=False):
        """Set permissions (ACL) for an iRODS collection or data object.

        Parameters
        ----------
        perm : str
            Name of permission string: own, read, write, or null.
        path : str
            Name of iRODS logical path.
        user : str
            Name of user.
        zone : str
            Name of user's zone.
        recursive : bool
            Apply ACL to all children of `path`.

        """
        acl = irods.access.iRODSAccess(perm, path, user, zone)
        try:
            if self.session.collections.exists(path):
                self.session.permissions.set(acl, recursive=recursive)
        except irods.exception.CAT_INVALID_USER as ciu:
            print(f'{RED}ACL ERROR: user unknown{DEFAULT}')
            raise ciu
        except irods.exception.CAT_INVALID_ARGUMENT as cia:
            print(f'{RED}ACL ERROR: permission {perm} or path {path} not known{DEFAULT}')
            logging.info(
                'ACL ERROR: permission %s or path %s not known',
                perm, path, exc_info=True)
            raise cia

    def ensure_coll(self, coll_name):
        """Optimally create a collection with `coll_name` if one does
        not exist.

        Parameters
        ----------
        coll_name : str
            Name of the collection to check/create.

        Returns
        -------
        iRODSCollection
            Existing or new iRODS collection.

        Raises:
            irods.exception.CAT_NO_ACCESS_PERMISSION

        """
        try:
            if self.session.collections.exists(coll_name):
                return self.session.collections.get(coll_name)
            return self.session.collections.create(coll_name)
        except irods.exception.CAT_NO_ACCESS_PERMISSION as cnap:
            logging.info('ENSURE COLLECTION', exc_info=True)
            raise cnap

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

    def list_resources(self):
        """Discover all writable root resources available in the current
        system producing 2 lists, one with resource names and another
        the value of the free_space annotation.  A value of 0 indicates
        no free space annotated.

        Returns
        -------
        tuple
            Discovered names of writable root resources: (names,
            free_space).

        """
        resc_names, free_spaces = [], []
        for name, metadata in self.resources.items():
            context = metadata['context']
            if context is not None:
                for kvp in context.split(';'):
                    if 'write' in kvp:
                        _, val = kvp.split('=')
                        if float(val) == 0.0:
                            continue
            status = metadata['status']
            if status is not None:
                if 'down' in status:
                    continue
            if metadata['parent'] is None:
                resc_names.append(name)
                free_spaces.append(metadata['free_space'])
        return resc_names, free_spaces

    def get_resource(self, resc_name):
        '''Instantiate an iRODS resource.

        Prameters
        ---------
        resc_name : str
            Name of the iRODS resource.

        Returns
        -------
        iRODSResource
            Instance of the resource with `resc_name`.

        Raises:
            irods.exception.ResourceDoesNotExist

        '''
        try:
            return self.session.resources.get(resc_name)
        except irods.exception.ResourceDoesNotExist as rdne:
            print(f'Resource with name {resc_name} not found')
            raise rdne

    def resource_space(self, resc_name):
        """Find the available space left on a resource in bytes.

        Parameters
        ----------
        resc_name : str
            Name of an iRODS resource.

        Returns
        -------
        int
            Number of bytes in `resc_name`.

        Throws: ResourceDoesNotExist if resource not known
                FreeSpaceNotSet if 'free_space' not set

        """
        space = self.resources[resc_name]['free_space']
        if space == -1:
            logging.info(
                'RESOURCE ERROR: Resource %s does not exist (typo?).',
                resc_name, exc_info=True)
            raise irods.exception.ResourceDoesNotExist(
                f'RESOURCE ERROR: Resource {resc_name} does not exist (typo?).')
        if space == 0:
            logging.info(
                'RESOURCE ERROR: Resource "free_space" is not set for %s.',
                resc_name, exc_info=True)
            raise FreeSpaceNotSet(
                'RESOURCE ERROR: Resource "free_space" is not set for {rescname}.')
        return space

    def get_free_space(self, resc_name):
        """Determine free space in a resource hierarchy.

        If the specified resource name has the free space annotated,
        then report that.  If not, search for any resources in the tree
        that have the free space annotated and report the sum all those
        values.

        Parameters
        ----------
        resc_name : str
            Name of monolithic resource or the top of a resource tree.

        Returns
        -------
        int
            Number of bytes free in the resource hierarchy.

        The return can have one of two possible values if not the actual
        free space:

            -1 if the resource does not exists (typo or otherwise)
             0 if the no free space has been annotated in the specified
               resource tree

        """
        try:
            resc = self.session.resources.get(resc_name)
        except irods.exception.ResourceDoesNotExist:
            print(f'Resource with name {resc_name} not found')
            return -1
        if resc.free_space is not None:
            return int(resc.free_space)
        children = get_resource_children(resc)
        return sum([int(child.free_space) for child in children if child.free_space is not None])

    def dataobject_exists(self, path):
        """Check if an iRODS data object exists.

        Parameters
        ----------
        path : str
            Name of an iRODS data object.

        Returns
        -------
        bool
            Existence of the data object with `path`.

        """
        return self.session.data_objects.exists(path)

    def collection_exists(self, path):
        """Check if an iRODS collection exists.

        Parameters
        ----------
        path : str
            Name of an iRODS collection.

        Returns
        -------
        bool
            Existance of the collection with `path`.

        """
        return self.session.collections.exists(path)

    def get_dataobject(self, path):
        """Instantiate an iRODS data object.

        Parameters
        ----------
        path : str
            Name of an iRODS data object.

        Returns
        -------
        iRODSDataObject
            Instance of the data object with `path`.

        """
        if self.dataobject_exists(path):
            return self.session.data_objects.get(path)
        raise irods.exception.DataObjectDoesNotExist(path)

    def get_collection(self, path):
        """Instantiate an iRODS collection.

        Parameters
        ----------
        path : str
            Name of an iRODS collection.

        Returns
        -------
        iRODSCollection
            Instance of the collection with `path`.

        """
        if self.collection_exists(path):
            return self.session.collections.get(path)
        raise irods.exception.CollectionDoesNotExist(path)

    def irods_put(self, local_path, irods_path, **options):
        """Upload `local_path` to `irods_path` following iRODS
        `options`.

        Parameters
        ----------
        local_path : str
            Path of local file or directory/folder.
        irods_path : str
            Path of iRODS data object or collection.
        options : dict
            iRODS transfer options.

        """
        self.session.data_objects.put(local_path, irods_path, **options)

    def irods_get(self, irods_path, local_path, **options):
        """Download `irods_path` to `local_path` following iRODS
        `options`.

        Parameters
        ----------
        irods_path : str
            Path of iRODS data object or collection.
        local_path : str
            Path of local file or directory/folder.
        options : dict
            iRODS transfer options.

        """
        self.session.data_objects.get(irods_path, local_path, **options)

    @staticmethod
    def is_dataobject(obj):
        """Check if `obj` is an iRODS data object.

        Parameters
        ----------
        obj : iRODS object instance
            iRODS instance to check.

        Returns
        -------
        bool
            If `obj` is an iRODS data object.

        """
        return isinstance(obj, irods.data_object.iRODSDataObject)

    @staticmethod
    def is_collection(obj):
        """Check if `obj` is an iRODS collection.

        Parameters
        ----------
        obj : iRODS object instance
            iRODS instance to check.

        Returns
        -------
        bool
            If `obj` is an iRODS collection.

        """
        return isinstance(obj, irods.collection.iRODSCollection)

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

    def upload_data(self, src_path, dst_coll, resc_name, size, buff=BUFF_SIZE, force=False, diffs=None):
        """Upload data from the local `src_path` to the iRODS
        `dst_coll`.

        When `src_path` is a folder/directory, upload its contents
        recursively to the iRODS collection `dst_coll`.  If `src_path`
        is the path to a file, upload the file.

        Parameters
        ----------
        src_path : str
            Absolute path to local file or folder.
        dst_coll : iRODSCollection
            The iRODS collection to where the data will be uploaded.
        resc_name : str
            Name of the top-level iRODS resource.
        size : int
            Size of data to be uploaded in bytes.
        buff : int
            Buffer size on resource that should remain after upload in
            bytes.
        force : bool
            Ignore storage capacity on resource associated with
            `resc_name`.
        diffs : list
            Output of diff functions.

        Throws:
        ResourceDoesNotExist
        ValueError (if resource too small or buffer is too small)

        """
        logging.info(
            'iRODS UPLOAD: %s-->%s %s', src_path, dst_coll.path,
            resc_name)
        # Handle both POSIX and non-POSIX paths.
        src_path = pathlib.Path(src_path)
        if src_path.is_file() or src_path.is_dir():
            if self.is_collection(dst_coll):
                dst_path = pathlib.Path(dst_coll.path).joinpath(
                    src_path.name)
            else:
                raise irods.exception.CollectionDoesNotExist(dst_coll)
        else:
            raise FileNotFoundError(
                'ERROR iRODS upload: not a valid source path')
        options = {
            ALL_KW: '',
            FORCE_FLAG_KW: '',
            'num_threads': NUM_THREADS,
            REG_CHKSUM_KW: '',
            VERIFY_CHKSUM_KW: '',
        }
        if resc_name in [None, '']:
            resc_name = self.default_resc
        options[RESC_NAME_KW] = resc_name
        if diffs is None:
            if src_path.is_file():
                diff, only_fs, _, _ = self.diffObjFile(
                    str(dst_path), str(src_path), scope='checksum')
            else:
                diff, only_fs, _, _ = self.diffIrodsLocalfs(
                    dst_coll, str(src_path))
        else:
            diff, only_fs, _, _ = diffs
        if not force:
            space = self.resource_space(resc_name)
            if size > (space - buff):
                logging.info(
                    'ERROR iRODS upload: Not enough free space on resource.',
                    exc_info=True)
                raise NotEnoughFreeSpace(
                    'ERROR iRODS upload: Not enough free space on resource.')
        try:
            # Data object
            if src_path.is_file() and len(diff + only_fs) > 0:
                logging.info(
                    'IRODS UPLOADING file %s to %s', src_path, dst_path)
                self.irods_put(str(src_path), str(dst_path), **options)
            # Collection
            else:
                logging.info('IRODS UPLOAD started:')
                for irods_path, local_path in diff:
                    # Upload files to distinct data objects.
                    _ = self.ensure_coll(str(irods_dirname(irods_path)))
                    logging.info(
                        'REPLACE: %s with %s', irods_path, local_path)
                    self.irods_put(str(local_path), str(irods_path),
                        **options)
                # Variable `only_fs` can contain files and folders.
                for rel_path in only_fs:
                    # Create subcollections and upload.
                    rel_path = pathlib.Path(rel_path)
                    local_path = src_path.joinpath(rel_path)
                    if len(rel_path.parts) > 1:
                        new_path = dst_path.joinpath(rel_path.parent)
                    else:
                        new_path = dst_path
                    _ = self.ensure_coll(str(new_path))
                    logging.info('UPLOAD: %s to %s', local_path, new_path)
                    irods_path = new_path.joinpath(rel_path.name)
                    logging.info('CREATE %s', irods_path)
                    self.irods_put(str(local_path), str(irods_path), **options)
        except Exception as error:
            logging.info('UPLOAD ERROR', exc_info=True)
            raise error

    def download_data(self, src_obj, dst_path, size, buff=BUFF_SIZE, force=False, diffs=None):
        """Dowload data from an iRODS `src_obj` to the local `dst_path`.

        When `src_obj` is a collection, download its contents
        recursively to the local folder/directory `dst_path`.  If
        `src_obj` is a data object, download it to a file in the local
        folder/director.

        Parameters
        ----------
        src_obj : iRODSCollection, iRODSDataObject
            The iRODS collection or data object from where the data will
            be downloaded.
        dst_path : str
            Absolute path to local folder/directory.
        size : int
            Size of data to be uploaded in bytes.
        buff : int
            Buffer size on local storage that should remain after
            download in bytes.
        force : bool
            Ignore storage capacity on the storage system of `dst_path`.
        diffs : list
            Output of diff functions.

        """
        logging.info('iRODS DOWNLOAD: %s-->%s', src_obj.path, dst_path)
        options = {
            FORCE_FLAG_KW: '',
            REG_CHKSUM_KW: '',
        }
        # Handle both POSIX and non-POSIX paths.
        if self.is_dataobject_or_collection(src_obj):
            src_path = pathlib.Path(src_obj.path)
        else:
            raise FileNotFoundError(
                'ERROR iRODS download: not a valid source path'
            )
        dst_path = pathlib.Path(dst_path)
        if not dst_path.is_dir():
            logging.info(
                'DOWNLOAD ERROR: destination path does not exist or is not directory',
                exc_info=True)
            raise FileNotFoundError(
                'ERROR iRODS download: destination path does not exist or is not directory')
        if not os.access(dst_path, os.W_OK):
            logging.info(
                'DOWNLOAD ERROR: No rights to write to destination.',
                exc_info=True)
            raise PermissionError(
                'ERROR iRODS download: No rights to write to destination.')
        # Only download if not present or difference in files.
        if diffs is None:
            dst_path = dst_path.joinpath(src_path.name)
            if self.is_dataobject(src_obj):
                diff, _, only_irods, _ = self.diffObjFile(
                    str(src_path), str(dst_path), scope="checksum")
            else:
                if not dst_path.is_dir():
                    os.mkdir(dst_path)
                diff, _, only_irods, _ = self.diffIrodsLocalfs(
                    src_obj, str(dst_path), scope="checksum")
        else:
            diff, _, only_irods, _ = diffs
        # Check space on destination.
        if not force:
            space = shutil.disk_usage(dst_path).free
            if size > (space - buff):
                logging.info(
                    'ERROR iRODS download: Not enough space on local disk.',
                    exc_info=True)
                raise NotEnoughFreeSpace(
                    'ERROR iRODS download: Not enough space on local disk.')
        try:
            # Data object
            if self.is_dataobject(src_obj) and len(diff + only_irods) > 0:
                logging.info(
                    'IRODS DOWNLOADING object: %s to %s',
                    src_path, dst_path)
                self.irods_get(
                    str(src_path), str(dst_path.joinpath(src_path.name)),
                    **options)
            # Collection
            else:
                logging.info("IRODS DOWNLOAD started:")
                for irods_path, local_path in diff:
                    # Download data objects to distinct files.
                    logging.info(
                        'REPLACE: %s with %s', local_path, irods_path)
                    self.irods_get(str(irods_path), str(local_path), **options)
                # Variable `only_irods` can contain data objects and
                # collections.
                for rel_path in only_irods:
                    # Create subdirectories and download.
                    rel_path = pathlib.Path(rel_path)
                    irods_path = src_path.joinpath(rel_path)
                    local_path = dst_path.joinpath(
                        src_path.name).joinpath(rel_path)
                    if not local_path.parent.is_dir():
                        local_path.parent.mkdir()
                    logging.info(
                        'INFO: Downloading %s to %s', irods_path,
                        local_path)
                    self.irods_get(str(irods_path), str(local_path), **options)
        except Exception as error:
            logging.info('DOWNLOAD ERROR', exc_info=True)
            raise error

    def diffObjFile(self, objPath, fsPath, scope="size"):
        """
        Compares and iRODS object to a file system file.
        returns ([diff], [only_irods], [only_fs], [same])
        """
        if os.path.isdir(fsPath) and not os.path.isfile(fsPath):
            raise IsADirectoryError("IRODS FS DIFF: file is a directory.")
        if self.session.collections.exists(objPath):
            raise IsADirectoryError("IRODS FS DIFF: object exists already as collection. "+objPath)

        if not os.path.isfile(fsPath) and self.session.data_objects.exists(objPath):
            return ([], [], [objPath], [])

        elif not self.session.data_objects.exists(objPath) and os.path.isfile(fsPath):
            return ([], [fsPath], [], [])

        #both, file and object exist
        obj = self.session.data_objects.get(objPath)
        if scope == "size":
            objSize = obj.size
            fSize = os.path.getsize(fsPath)
            if objSize != fSize:
                return ([(objPath, fsPath)], [], [], [])
            else:
                return ([], [], [], [(objPath, fsPath)])
        elif scope == "checksum":
            objCheck = obj.checksum
            if objCheck == None:
                try:
                    obj.chksum()
                    objCheck = obj.checksum
                except:
                    logging.info('No checksum for '+obj.path)
                    return([(objPath, fsPath)], [], [], [])
            if objCheck.startswith("sha2"):
                sha2Obj = base64.b64decode(objCheck.split('sha2:')[1])
                with open(fsPath, "rb") as f:
                    stream = f.read()
                    sha2 = hashlib.sha256(stream).digest()
                print(sha2Obj != sha2)
                if sha2Obj != sha2:
                    return([(objPath, fsPath)], [], [], [])
                else:
                    return ([], [], [], [(objPath, fsPath)])
            elif objCheck:
                #md5
                with open(fsPath, "rb") as f:
                    stream = f.read()
                    md5 = hashlib.md5(stream).hexdigest()
                if objCheck != md5:
                    return([(objPath, fsPath)], [], [], [])
                else:
                    return ([], [], [], [(objPath, fsPath)])


    def diffIrodsLocalfs(self, coll, dirPath, scope="size"):
        '''
        Compares and iRODS tree to a directory and lists files that are not in sync.
        Syncing scope can be 'size' or 'checksum'
        Returns: zip([dataObjects][files]) where ther is a difference
        collection: iRODS collection
        '''

        listDir = []
        if not dirPath == None:
            if not os.access(dirPath, os.R_OK):
                raise PermissionError("IRODS FS DIFF: No rights to write to destination.")
            if not os.path.isdir(dirPath):
                raise IsADirectoryError("IRODS FS DIFF: directory is a file.")
            for root, dirs, files in os.walk(dirPath, topdown=False):
                for name in files:
                    listDir.append(os.path.join(root.split(dirPath)[1], name).strip(os.sep))

        listColl = []
        if not coll == None:
            for root, subcolls, obj in coll.walk():
                for o in obj:
                    listColl.append(os.path.join(root.path.split(coll.path)[1], o.name).strip('/'))

        diff = []
        same = []
        for locPartialPath in set(listDir).intersection(listColl):
            iPartialPath = locPartialPath.replace(os.sep, "/")
            if scope == "size":
                objSize = self.session.data_objects.get(coll.path + '/' + iPartialPath).size
                fSize = os.path.getsize(os.path.join(dirPath, iPartialPath))
                if objSize != fSize:
                    diff.append((coll.path + '/' + iPartialPath, os.path.join(dirPath, locPartialPath)))
                else:
                    same.append((coll.path + '/' + iPartialPath, os.path.join(dirPath, locPartialPath)))
            elif scope == "checksum":
                objCheck = self.session.data_objects.get(coll.path + '/' + iPartialPath).checksum
                if objCheck == None:
                    try:
                        self.session.data_objects.get(coll.path + '/' + iPartialPath).chksum()
                        objCheck = self.session.data_objects.get(
                                    coll.path + '/' + iPartialPath).checksum
                    except:
                        logging.info('No checksum for '+coll.path + '/' + iPartialPath)
                        diff.append((coll.path + '/' + iPartialPath, 
                                        os.path.join(dirPath, locPartialPath)))
                        continue
                if objCheck.startswith("sha2"):
                    sha2Obj = base64.b64decode(objCheck.split('sha2:')[1])
                    with open(os.path.join(dirPath, locPartialPath), "rb") as f:
                        stream = f.read()
                        sha2 = hashlib.sha256(stream).digest()
                    if sha2Obj != sha2:
                        diff.append((coll.path + '/' + iPartialPath, os.path.join(dirPath, locPartialPath)))
                    else:
                        same.append((coll.path + '/' + iPartialPath, os.path.join(dirPath, locPartialPath)))
                elif objCheck:
                    #md5
                    with open(os.path.join(dirPath, locPartialPath), "rb") as f:
                        stream = f.read()
                        md5 = hashlib.md5(stream).hexdigest();
                    if objCheck != md5:
                        diff.append((coll.path + '/' + iPartialPath, os.path.join(dirPath, locPartialPath)))
                    else:
                        same.append((coll.path + '/' + iPartialPath, os.path.join(dirPath, locPartialPath)))
            else: #same paths, no scope
                diff.append((coll.path + '/' + iPartialPath, os.path.join(dirPath, locPartialPath)))

        #adding files that are not on iRODS, only present on local FS
        #adding files that are not on local FS, only present in iRODS
        #adding files that are stored on both devices with the same checksum/size
        irodsOnly = list(set(listColl).difference(listDir))
        for i in range(0, len(irodsOnly)):
            irodsOnly[i] = irodsOnly[i].replace(os.sep, "/")
        return (diff, list(set(listDir).difference(listColl)), irodsOnly, same)

    def addMetadata(self, items, key, value, units = None):
        """
        Adds metadata to all items
        items: list of iRODS data objects or iRODS collections
        key: string
        value: string
        units: (optional) string 

        Throws:
            CATALOG_ALREADY_HAS_ITEM_BY_THAT_NAME
        """
        for item in items:
            try:
                item.metadata.add(key.upper(), value, units)
            except irods.exception.CATALOG_ALREADY_HAS_ITEM_BY_THAT_NAME:
                print(RED+"INFO ADD META: Metadata already present"+DEFAULT)
            except irods.exception.CAT_NO_ACCESS_PERMISSION as cnap:
                raise cnap("ERROR UPDATE META: no permissions")

    def updateMetadata(self, items, key, value, units = None):
        """
        Updates a metadata entry to all items
        items: list of iRODS data objects or iRODS collections
        key: string
        value: string
        units: (optional) string

        Throws: CAT_NO_ACCESS_PERMISSION
        """
        try:
            for item in items:
                if key in item.metadata.keys():
                    meta = item.metadata.get_all(key)
                    valuesUnits = [(m.value, m.units) for m in meta]
                    if (value, units) not in valuesUnits:
                        #remove all iCAT entries with that key
                        for m in meta:
                            item.metadata.remove(m)
                        #add key, value, units
                        self.addMetadata(items, key, value, units)

                else:
                    self.addMetadata(items, key, value, units)
        except irods.exception.CAT_NO_ACCESS_PERMISSION as cnap:
            raise cnap("ERROR UPDATE META: no permissions "+item.path)

    def deleteMetadata(self, items, key, value, units):
        """
        Deletes a metadata entry of all items
        items: list of iRODS data objects or iRODS collections
        key: string
        value: string
        units: (optional) string

        Throws:
            CAT_SUCCESS_BUT_WITH_NO_INFO: metadata did not exist
        """
        for item in items:
            try:
                item.metadata.remove(key, value, units)
            except irods.exception.CAT_SUCCESS_BUT_WITH_NO_INFO:
                print(RED+"INFO DELETE META: Metadata never existed"+DEFAULT)
            except irods.exception.CAT_NO_ACCESS_PERMISSION as cnap:
                raise cnap("ERROR UPDATE META: no permissions "+item.path)



    def deleteData(self, item):
        """
        Delete a data object or a collection recursively.
        item: iRODS data object or collection
        """

        if self.session.collections.exists(item.path):
            logging.info("IRODS DELETE: "+item.path)
            try:
                item.remove(recurse = True, force = True)
            except irods.exceptionCAT_NO_ACCESS_PERMISSION as cnap:
                raise cnap("ERROR IRODS DELETE: no permissions")
        elif self.session.data_objects.exists(item.path):
            logging.info("IRODS DELETE: "+item.path)
            try:
                item.unlink(force = True)
            except irods.exception.CAT_NO_ACCESS_PERMISSION as cnap:
                raise irods.exception("ERROR IRODS DELETE: no permissions "+item.path)


    def executeRule(self, ruleFile, params, output='ruleExecOut'):
        """
        Executes and interactive rule. Returns stdout and stderr.
        params: Depending on rule,
                dictionary of variables for rule, will overwrite the default settings.
        params format example:
        params = {  # extra quotes for string literals
            '*obj': '"/zone/home/user"',
            '*name': '"attr_name"',
            '*value': '"attr_value"'
        }
        """
        try:
            rule = irods.rule.Rule(self.session, ruleFile, params=params, output=output)
            out = rule.execute()
        except Exception as e:
            logging.info('RULE EXECUTION ERROR', exc_info=True)
            return [], [repr(e)]

        stdout = []
        stderr = []
        if len(out.MsParam_PI) > 0:
            try:
                stdout = [o.decode() 
                    for o in (out.MsParam_PI[0].inOutStruct.stdoutBuf.buf.strip(b'\x00')).split(b'\n')]
                stderr = [o.decode() 
                    for o in (out.MsParam_PI[0].inOutStruct.stderrBuf.buf.strip(b'\x00')).split(b'\n')]
            except AttributeError:
                logging.info('RULE EXECUTION ERROR: '+str(stdout+stderr), exc_info=True)
                return stdout, stderr
        
        return stdout, stderr


    def getSize(self, itemPaths):
        '''
        Compute the size of the iRods dataobject or collection
        Returns: size in bytes.
        itemPaths: list of irods paths pointing to collection or object
        '''
        size = 0
        for path in itemPaths:
            #remove possible leftovers of windows fs separators
            path = path.replace("\\", "/")
            if self.session.data_objects.exists(path):
                size = size + self.session.data_objects.get(path).size

            elif self.session.collections.exists(path):
                coll = self.session.collections.get(path)
                walk = [coll]
                while walk:
                    try:
                        coll = walk.pop()
                        walk.extend(coll.subcollections)
                        for obj in coll.data_objects:
                            size = size + obj.size
                    except:
                        logging.info('DATA SIZE', exc_info=True)
                        raise
        return size


    def createTicket(self, path, expiryString=""):
        ticket = irods.ticket.Ticket(self.session, 
                        ''.join(random.choice(string.ascii_letters) for _ in range(20)))
        ticket.issue("read", path)
        logging.info('CREATE TICKET: '+ticket.ticket+': '+path)
        #returns False when no expiry date is set
        return ticket.ticket, False


def get_resource_children(resc):
    """Get all the children for the resource named `resc_name`.

    Parameters
    ----------
    resc : instance
        iRODS resource instance.

    Returns
    -------
    list
        Instances of child resources.

    """
    children = []
    for child in resc.children:
        children.extend(get_resource_children(child))
    return resc.children + children


def irods_dirname(path):
    """Find path less the final element for an iRODS path.

    Parameters
    ----------
    path : str
        An iRODS path, relative or absolute.

    Returns
    -------
    str
        iRODS path less the element after the final '/'

    """
    return pathlib.Path(path).parent
