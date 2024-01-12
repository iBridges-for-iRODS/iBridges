""" permission operations """
from typing import Iterator
import irods.access
import irods.collection
import irods.exception
import irods.session
from collections import defaultdict

class Permission():
    """Irods permission operations"""

    def __init__(self, session, item) -> None:
        self.session = session
        self.item = item

    def __iter__(self) -> Iterator:
        for perm in self.session.irods_session.permissions.get(self.item):
            yield perm

    def __repr__(self) -> str:
        acl_dict = defaultdict(list)
        for p in self:
            acl_dict[f'{p.user_name}#{p.user_zone}\n'].append(
                    f'\t{p.access_name}\t{p.user_type}\n')
        acl = ''
        for key, value in sorted(acl_dict.items()):
            acl += key + ''.join(value)
            

        if isinstance(self.item, irods.collection.iRODSCollection):
            coll = self.session.irods_session.collections.get(self.item.path)
            acl += f"inheritance {coll.inheritance}\n"

        return acl

    @property
    def available_permissions(self) -> dict:
        """Get available permissions"""
        try:
            return self.session.irods_session.available_permissions
        except AttributeError:
            permissions = {
                'null': 'none',
                'read_object': 'read',
                'modify_object': 'write',
                'own': 'own',
            }
            if self.session.server_version < (4, 3, 0):
                permissions.update({'read object': 'read', 'modify object': 'write'})
            return permissions

    def set(self, perm: str, user: str = '', zone: str = '',
            recursive: bool = False, admin: bool = False) -> None:
        """Set permissions (ACL) for an iRODS collection or data object."""
        acl = irods.access.iRODSAccess(perm, self.item.path, user, zone)
        self.session.irods_session.permissions.set(acl, recursive=recursive, admin=admin)
