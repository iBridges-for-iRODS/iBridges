""" permission operations """
import irods.access
import irods.collection
import irods.exception
import irods.session
from typing import Iterator, Union

class Permission():
    """Irods permission operations"""

    def __init__(self, session, item) -> None:
        self.session = session
        self.item = item

    def __iter__(self) -> Iterator:
        for m in self.session.irods_session.permissions.get(self.item):
            yield m

    def __repr__(self) -> str:
        acl_string = ""
        for m in self.session.irods_session.permissions.get(self.item):
            acl_string += f"{repr(m)}\n"

        if isinstance(self.item, irods.collection.iRODSCollection):
            coll = self.session.irods_session.collections.get(self.item.path)
            acl_string += f"<iRODSAccess inheritance {coll.inheritance} {self.item.path}>\n"

        return acl_string

    @property
    def available_permissions(self) -> dict:
        try:
            return self.session.irods_session.available_permissions
        except:
            permissions = {
                'null': 'none',
                'read_object': 'read',
                'modify_object': 'write',
                'own': 'own',
            }
            if self.session.server_version < (4, 3, 0):
                permissions.update({'read object': 'read', 'modify object': 'write'})
            return permissions

    def set(self, perm: str, user: str = '', zone: str = '', recursive: bool = False, admin: bool = False) -> None:
        """Set permissions (ACL) for an iRODS collection or data object."""
        acl = irods.access.iRODSAccess(perm, self.item.path, user, zone)
        self.session.irods_session.permissions.set(acl, recursive=recursive, admin=admin)
