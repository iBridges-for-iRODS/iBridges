""" permission operations """
from collections import defaultdict
from typing import Iterator

import irods.access
import irods.collection
import irods.exception
import irods.session


class Permissions():
    """Irods permissions operations"""

    def __init__(self, session, item) -> None:
        self.session = session
        self.item = item

    def __iter__(self) -> Iterator:
        for perm in self.session.irods_session.acls.get(self.item):
            yield perm

    def __str__(self) -> str:
        acl_dict = defaultdict(list)
        for perm in self:
            acl_dict[f'{perm.user_name}#{perm.user_zone}'].append(
                    f'{perm.access_name}\t{perm.user_type}')
        acl = ''
        for key, value in sorted(acl_dict.items()):
            v_str= '\n\t'.join(value)
            acl += f'{key}\n\t{v_str}\n'

        if isinstance(self.item, irods.collection.iRODSCollection):
            coll = self.session.irods_session.collections.get(self.item.path)
            acl += f"inheritance {coll.inheritance}\n"

        return acl

    @property
    def available_permissions(self) -> dict:
        """Get available permissions"""
        return self.session.irods_session.available_permissions

    def set(self, perm: str, user: str = '', zone: str = '',
            recursive: bool = False, admin: bool = False) -> None:
        """Set permissions (ACL) for an iRODS collection or data object."""
        acl = irods.access.iRODSAccess(perm, self.item.path, user, zone)
        self.session.irods_session.acls.set(acl, recursive=recursive, admin=admin)
