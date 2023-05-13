""" permission operations
"""
import logging
import irods.access
import irods.collection
import irods.exception

from . import keywords as kw
from . import dataOperations
from . import session


class Permission(object):
    """Irods permission operations """
    _permissions = None

    def __init__(self, data_man: dataOperations.DataOperation, sess_man: session.Session):
        """ iRODS data operations initialization

            Parameters
            ----------
            data_man: dataOperations.DataOperation
                instance of the Dataoperation class
            sess_man : session.Session
                instance of the Session class

        """
        self.data_man = data_man
        self.sess_man = sess_man

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
            if self.sess_man.server_version < (4, 3, 0):
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
        if isinstance(path, str) and path:
            try:
                return self.sess_man.irods_session.permissions.get(
                    self.sess_man.irods_session.collections.get(path))
            except irods.exception.CollectionDoesNotExist:
                return self.sess_man.irods_session.permissions.get(
                    self.sess_man.irods_session.data_objects.get(path))
        if dataOperations.DataOperation.is_dataobject_or_collection(obj):
            return self.sess_man.irods_session.permissions.get(obj)
        logging.debug('`obj` must be or `path` must resolve into, a collection or data object')
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
            if self.data_man.dataobject_exists(path) or \
                    self.data_man.collection_exists(path):
                self.sess_man.irods_session.permissions.set(acl, recursive=recursive, admin=admin)
        except irods.exception.CAT_INVALID_USER as ciu:
            logging.error('%sACL: user unknown%s', kw.RED, kw.DEFAULT)
            raise ciu
        except irods.exception.CAT_INVALID_ARGUMENT as cia:
            logging.error(
                '%sACL: permission %s or path %s not known%s', kw.RED,
                perm, path, kw.DEFAULT, exc_info=True)
            raise cia
