"""Set and modify permissions."""

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
        """Create a table of all currently set permissions with ordered types."""
        # Explicit ordering: admin -> group -> user
        order = {
            "rodsadmin": 0,
            "rodsgroup": 1,
            "rodsuser": 2,
        }

        names, zones, permissions = ["name"], ["zone"], ["permission"]
        for perm in sorted(self, key=lambda p: (order.get(p.user_type, 99), p.user_name)):
            names.append(_format_name(perm))
            zones.append(perm.user_zone)
            permissions.append(perm.access_name)

        return _create_table(names, zones, permissions)

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


def _create_table(*cols):
    col_width = []
    for col in cols:
        col_width.append(max(*(len(x) for x in col)) + 3)
    table_str = ""
    for i_row in range(len(cols[0])):
        row_str = ""
        for cur_col_width, col in zip(col_width, cols):
            row_str += f"{col[i_row]:<{cur_col_width}}"
        row_str += "\n"
        if i_row == 0:
            row_str += (sum(col_width)-3)*"-" + "\n"
        table_str += row_str
    return table_str

def _format_name(perm):
    if perm.user_type == "rodsadmin":
        prefix = "admin"
    elif perm.user_type == "rodsgroup":
        prefix = "group"
    else:
        prefix = "user"
    return f"({prefix}) {perm.user_name}"
