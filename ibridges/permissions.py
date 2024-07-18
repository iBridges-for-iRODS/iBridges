"""Set and modify permissions."""

from collections import defaultdict
from typing import Iterator, Optional

import irods.access
import irods.collection
import irods.exception
import irods.session


class Permissions:
    """Irods permissions operations.

    This class allows the user retrieve the permissions as well as set them
    (if the iRODS server allows this).

    Parameters
    ----------
    session
        Session with the connection to the iRODS server.
    item
        Data object or collection to create or adjust the permissions for.

    """

    def __init__(self, session, item) -> None:
        """Initialize the permissions object."""
        self.session = session
        self.item = item

    def __iter__(self) -> Iterator:
        """Iterate over all ACLs."""
        yield from self.session.irods_session.acls.get(self.item)

    def __str__(self) -> str:
        """Create a string table of all currently set permissions."""
        acl_dict = defaultdict(list)
        for perm in self:
            acl_dict[f"{perm.user_name}#{perm.user_zone}"].append(
                f"{perm.access_name}\t{perm.user_type}"
            )
        acl = ""
        for key, value in sorted(acl_dict.items()):
            v_str = "\n\t".join(value)
            acl += f"{key}\n\t{v_str}\n"

        if isinstance(self.item, irods.collection.iRODSCollection):
            coll = self.session.irods_session.collections.get(self.item.path)
            acl += f"inheritance {coll.inheritance}\n"

        return acl

    @property
    def available_permissions(self) -> dict:
        """Get available permissions."""
        return self.session.irods_session.available_permissions.codes

    def set(
        self,
        perm: str,
        user: Optional[str] = None,
        zone: Optional[str] = None,
        recursive: bool = False,
        admin: bool = False,
    ) -> None:
        """Set permissions (ACL) for an iRODS collection or data object."""
        if user is None:
            user = self.session.username
        if zone is None:
            zone = self.session.zone
        # forbid that users can change their own ACLs,
        # does not apply to no/inherit, a setting  on collections which is independent of the user
        if (
            perm not in ["inherit", "noinherit"]
            and user == self.session.username
            and zone == self.session.zone
        ):
            raise ValueError(
                "Cannot set your own permissions, because you would lose "
                "access to the object/collection."
            )
        acl = irods.access.iRODSAccess(perm, self.item.path, user, zone)
        self.session.irods_session.acls.set(acl, recursive=recursive, admin=admin)
