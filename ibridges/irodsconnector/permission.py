""" permission operations
"""
import logging

import irods.access
import irods.collection
import irods.exception

from ibridges.irodsconnector import dataOperations
from ibridges.irodsconnector import session


class Permission(object):
    """Irods permission operations """
    _permissions = None

    def __init__(self, data_man: dataOperations.DataOperation, session: session.Session):
        """ iRODS data operations initialization

            Parameters
            ----------
            data_man: dataOperations.DataOperation
                instance of the Dataoperation class
            sess_man : session.Session
                instance of the Session class

        """
        self.session = session

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
            if self.session.server_version < (4, 3, 0):
                self._permissions.update(
                    {'read object': 'read', 'modify object': 'write'})
        return self._permissions

    def get_permissions(self, item: irods.collection | irods.data_object) -> list:
        """Discover ACLs for an iRODS collection expressed as a `path`
        or an `obj`ect.

        Parameters
        ----------
        item: irods.collection | irods.data_object

        Returns
        -------
        list
            iRODS ACL instances.

        """
        if dataOperations.DataOperation.is_dataobject_or_collection(obj):
            return self.session.irods_session.permissions.get(obj)
        logging.debug('Not a valid iRODS object or collection')
        return []

    def set_permissions(self, perm: str, item: irods.collection | irods.data_object,
                        user: str = '', zone: str = '', recursive: bool = False,
                        admin: bool = False):
        """Set permissions (ACL) for an iRODS collection or data object.

        Parameters
        ----------
        perm: str
            Name of permission string: own, read, write, or null.
        item: irods.data_object or irods.collection
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
            self.session.irods_session.permissions.set(acl, recursive=recursive, admin=admin)
        except irods.exception.CAT_INVALID_USER as error:
            logging.error('ACL: user unknown')
            raise error
        except irods.exception.CAT_INVALID_ARGUMENT as error:
            logging.error(
                'ACL: permission %s or path %s not known', perm, path,
                exc_info=True)
            raise error
