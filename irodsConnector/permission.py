""" permission operations
"""
import logging
import irods.access
import irods.collection
import irods.exception
import irodsConnector.session
import irodsConnector.keywords as kw
from irodsConnector.utils import IrodsUtils


class Permission(object):
    """Irods permission operations """
    _permissions = None

    def permissions(self, ses_man: irodsConnector.session.Session) -> dict:
        """iRODS permissions mapping.

        Parameters
        ----------
        ses_man : irods session
            instance of the Session class
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
            if ses_man.session.server_version < (4, 3, 0):
                self._permissions.update(
                    {'read object': 'read', 'modify object': 'write'})
        return self._permissions

    def get_permissions(self, ses_man: irodsConnector.session.Session, path: str = '', obj: irods.collection = None) \
            -> list:
        """Discover ACLs for an iRODS collection expressed as a `path`
        or an `obj`ect.

        Parameters
        ----------
        ses_man : irods session
            instance of the Session class
        path : str
            Logical iRODS path of a collection or data object.
        obj : iRODSCollection, iRODSDataObject
            Instance of an iRODS collection or data object.

        Returns
        -------
        list
            iRODS ACL instances.

        """
        logging.info('GET PERMISSIONS')
        if isinstance(path, str) and path:
            try:
                return ses_man.session.permissions.get(
                    ses_man.session.collections.get(path))
            except irods.exception.CollectionDoesNotExist:
                return ses_man.session.permissions.get(
                    ses_man.session.data_objects.get(path))
        if IrodsUtils.is_dataobject_or_collection(obj):
            return ses_man.session.permissions.get(obj)
        print('WARNING -- `obj` must be or `path` must resolve into, a collection or data object')
        return []

    def set_permissions(self, ses_man: irodsConnector.session.Session, perm: str, path: str, user: str = '', 
                        zone: str = '', recursive: bool = False, admin: bool = False):
        """Set permissions (ACL) for an iRODS collection or data object.

        Parameters
        ----------
        ses_man : irodsConnector.session
            instance of the Session class
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
        admin : bool
            If a 'rodsadmin' apply ACL for another user.

        """
        acl = irods.access.iRODSAccess(perm, path, user, zone)
        try:
            if IrodsUtils.dataobject_exists(ses_man.session, path) or \
                    IrodsUtils.collection_exists(ses_man.session, path):
                ses_man.session.permissions.set(acl, recursive=recursive, admin=admin)
        except irods.exception.CAT_INVALID_USER as ciu:
            print(f'{kw.RED}ACL ERROR: user unknown{kw.DEFAULT}')
            raise ciu
        except irods.exception.CAT_INVALID_ARGUMENT as cia:
            print(f'{kw.RED}ACL ERROR: permission {perm} or path {path} not known{kw.DEFAULT}')
            logging.info(
                'ACL ERROR: permission %s or path %s not known',
                perm, path, exc_info=True)
            raise cia
