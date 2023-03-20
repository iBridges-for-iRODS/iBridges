""" permission operations
"""
import logging
import irods.access
import irods.collection
import irods.exception
import irodsConnector.keywords as kw
from irodsConnector.dataOperations import DataOperation
from irodsConnector.session import Session


class Permission(object):
    """Irods permission operations """
    _permissions = None
    _data_man = None
    _ses_man = None

    def __init__(self, data_man: DataOperation, ses_man: Session):
        """ iRODS data operations initialization

            Parameters
            ----------
            data_man: irods Datamanager
                instance of the Dataoperation class
            ses_man : irods session
                instance of the Session class

        """
        self._data_man = data_man
        self._ses_man = ses_man

    @property
    def permissions(self) -> dict:
        """iRODS permissions mapping.

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
            if self._ses_man.server_version < (4, 3, 0):
                self._permissions.update(
                    {'read object': 'read', 'modify object': 'write'})
        return self._permissions

    def get_permissions(self, path: str = '', obj: irods.collection = None) \
            -> list:
        """Discover ACLs for an iRODS collection expressed as a `path`
        or an `obj`ect.

        Parameters
        ----------
        path: str
            Logical iRODS path of a collection or data object.
        obj: iRODSCollection, iRODSDataObject
            Instance of an iRODS collection or data object.

        Returns
        -------
        list
            iRODS ACL instances.

        """
        logging.info('GET PERMISSIONS')
        if isinstance(path, str) and path:
            try:
                return self._ses_man.session.permissions.get(
                    self._ses_man.session.collections.get(path))
            except irods.exception.CollectionDoesNotExist:
                return self._ses_man.session.permissions.get(
                    self._ses_man.session.data_objects.get(path))
        if DataOperation.is_dataobject_or_collection(obj):
            return self._ses_man.session.permissions.get(obj)
        print('WARNING -- `obj` must be or `path` must resolve into, a collection or data object')
        return []

    def set_permissions(self, perm: str, path: str, user: str = '',
                        zone: str = '', recursive: bool = False, admin: bool = False):
        """Set permissions (ACL) for an iRODS collection or data object.

        Parameters
        ----------
        perm: str
            Name of permission string: own, read, write, or null.
        path: str
            Name of iRODS logical path.
        user: str
            Name of user.
        zone: str
            Name of user's zone.
        recursive: bool
            Apply ACL to all children of `path`.
        admin: bool
            If a 'rodsadmin' apply ACL for another user.

        """
        acl = irods.access.iRODSAccess(perm, path, user, zone)
        try:
            if self._data_man.dataobject_exists(path) or \
                    self._data_man.collection_exists(path):
                self._ses_man.session.permissions.set(acl, recursive=recursive, admin=admin)
        except irods.exception.CAT_INVALID_USER as ciu:
            print(f'{kw.RED}ACL ERROR: user unknown{kw.DEFAULT}')
            raise ciu
        except irods.exception.CAT_INVALID_ARGUMENT as cia:
            print(f'{kw.RED}ACL ERROR: permission {perm} or path {path} not known{kw.DEFAULT}')
            logging.info(
                'ACL ERROR: permission %s or path %s not known',
                perm, path, exc_info=True)
            raise cia
