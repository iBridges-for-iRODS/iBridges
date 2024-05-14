"""A class to handle iRODS and local (Win, linux) paths."""
from __future__ import annotations

from pathlib import PurePosixPath
from typing import Union

import irods


class IrodsPath():
    """Extending the posix path functionalities with iRODS functionalities."""

    _current_working_path = ""

    def __init__(self, session, *args):
        """Initialize IrodsPath object similar to the Path object.

        It does take an extra argument in session.

        Parameters
        ----------
        session:
            Session that is used for the ipath.
        args:
            Specification of the path. For example: "x/z" or "x", "z".

        """
        self.session = session
        assert hasattr(session, "irods_session")
        # We don't want recursive IrodsPaths, so we take the
        # path outside of the IrodsPath object.
        args = [a._path if isinstance(a, IrodsPath) else a
                for a in args]
        self._path = PurePosixPath(*args)
        super().__init__()

    def absolute_path(self) -> str:
        """Return the path if the absolute irods path."""
        # absolute path
        if len(self._path.parts) == 0:
            return self.session.home
        if self._path.parts[0] == "~" or self._path.parts[0] == ".":
            begin, end = self.session.home, self._path.parts[1:]
        elif self._path.parts[0] == "/":
            begin, end = "/", self._path.parts[1:]
        else:
            begin, end = self.session.home, self._path.parts
        return str(PurePosixPath(begin, *end))


    def __str__(self) -> str:
        """Get the absolute path if converting to string."""
        return self.absolute_path()

    def __repr__(self) -> str:
        """Representation of the IrodsPath object in line with a Path object."""
        return f"IrodsPath({', '.join(self._path.parts)})"

    def __truediv__(self, other) -> IrodsPath:
        """Ensure that we can append just like the Path object."""
        return self.__class__(self.session, self._path, other)

    def __getattribute__(self, attr):
        """Make the IrodsPath transparent so that some Path functionality is available."""
        if attr in ["name", "parts"]:
            return self._path.__getattribute__(attr)
        return super().__getattribute__(attr)

    def joinpath(self, *args):
        """Concanate another path to this one.

        Returns
        -------
            The concatenated path.

        """
        return IrodsPath(self.session, self._path, *args)

    @property
    def parent(self):
        """Return the parent directory of the current directory.

        Returns
        -------
            The parent just above the current directory

        """
        return IrodsPath(self.session, self._path.parent)

    def remove(self):
        """Remove the data behind an iRODS path.

        Raises
        ------
        PermissionError:
            If the user has insufficient permission to remove the data.

        """
        try:
            if self.collection_exists():
                coll = self.session.irods_session.collections.get(str(self))
                coll.remove()
            elif self.dataobject_exists():
                obj = self.session.irods_session.data_objects.get(str(self))
                obj.unlink()
        except irods.exception.CUT_ACTION_PROCESSED_ERR as exc:
            raise PermissionError(
                f"While removing {self}: iRODS server forbids action.") from exc

    @staticmethod
    def create_collection(session,
                          coll_path: Union[IrodsPath, str]) -> irods.collection.iRODSCollection:
        """Create a collection and all collections in its path.

        Parameters
        ----------
        session:
            Session for which the collection is created.
        coll_path:
            Irods path to the collection to be created.

        Raises
        ------
        PermissionError:
            If the collection cannot be created due to insufficient permissions.

        Returns
        -------
        collection:
            The newly created collection.

        """
        try:
            return session.irods_session.collections.create(str(coll_path))
        except irods.exception.CUT_ACTION_PROCESSED_ERR as exc:
            raise PermissionError(
                "While creating collection '{coll_path}': iRODS server forbids action.") from exc

    def rename(self, new_name: Union[str, IrodsPath]) -> IrodsPath:
        """Change the name or the path of a data object or collection.
        New collections on the path will be created.
        
        Parameters
        ----------
        new_name: str or IrodsPath
            new name or a new full path
        """

        if not self.exists():
            raise ValueError(f'str{self} does not exist.')

        # Build new path
        if str(new_name).startswith('/'+self.session.zone):
            new_path = IrodsPath(self.session, new_name)
        else:
            new_path = self.parent.joinpath(new_name)

        try:
            # Make sure new path exists on iRODS server
            if not new_path.parent.exists():
                self.create_collection(self.session, new_path.parent)

            if self.dataobject_exists():
                self.session.irods_session.data_objects.move(str(self), str(new_path))
            else:
                self.session.irods_session.collections.move(str(self), str(new_path))
            return new_path

        except irods.exception.SAME_SRC_DEST_PATHS_ERR as err:
            raise ValueError(f'Path {new_path} already exists.') from err
        except irods.exception.SYS_CROSS_ZONE_MV_NOT_SUPPORTED as err:
            raise ValueError(
                    f'Path {new_path} needs to start with /{self.session.zone}/home') from err
        except irods.exception.CAT_NO_ACCESS_PERMISSION as err:
            raise PermissionError(f'Not allowed to move data to {new_path}') from err


    def collection_exists(self) -> bool:
        """Check if the path points to an iRODS collection."""
        return self.session.irods_session.collections.exists(str(self))

    def dataobject_exists(self) -> bool:
        """Check if the path points to an iRODS data object."""
        return self.session.irods_session.data_objects.exists(str(self))

    def exists(self) -> bool:
        """Check if the path already exists on the iRODS server."""
        return self.dataobject_exists() or self.collection_exists()

    def walk(self, depth: int):
        """Walk on a collection.

        Parameters
        ----------
        depth : int
            Stops after depth many iterations, even if the tree is deeper.

        """
        raise NotImplementedError("Walk method not implemented yet.")

    def relative_to(self, other: IrodsPath) -> PurePosixPath:
        """Calculate the relative path compared to our path."""
        return PurePosixPath(self.absolute_path()).relative_to(PurePosixPath(other.absolute_path()))
