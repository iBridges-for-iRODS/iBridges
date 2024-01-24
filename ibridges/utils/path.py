"""
A classes to handle iRODS and local (Win, linux) paths.
"""
from __future__ import annotations

import irods


class IrodsPath():
    """Extending the posix path functionalities with iRODS functionalities."""

    _current_working_path = ""

    def __init__(self, session, *args):
        self.session = session
        self._raw_paths = []
        for arg in args:
            if isinstance(arg, str):
                self._raw_paths.extend(arg.split("/"))
            elif isinstance(arg, IrodsPath):
                self._raw_paths.extend(arg._raw_paths)
        if len(args) == 0:
            self._raw_paths = ["."]
        super().__init__()

    def absolute_path(self) -> str:
        """
        Return the path if the path starts with '/zone/home', otherwise 
        concatenate the '/zone/home' prefix to the current path.
        """
        # absolute path
        if self._raw_paths[0] == "":
            return "/" + "/".join(self._raw_paths[1:])
        if self._raw_paths[0] == "~":
            begin, end = self.session.home(), self._raw_paths[1:]
        elif self._raw_paths[0] == ".":
            begin, end = self.session.cwd(), self._raw_paths[1:]
        else:
            begin, end = self.session.cwd(), self._raw_paths
        if len(end) > 0:
            return begin + "/" + "/".join(end)
        return begin

    def __str__(self) -> str:
        return self.absolute_path()

    def __repr__(self) -> str:
        return f"IrodsPath({', '.join(self._raw_paths)})"

    def __truediv__(self, other) -> IrodsPath:
        return self.__class__(self.session, *self._raw_paths, other)

    @property
    def name(self) -> str:
        return self._raw_paths[-1]

    def remove(self):
        """Removes the data behind an iRODS path
        """
        try:
            if self.collection_exists():
                coll = self.session.irods_session.collections.get(str(self))
                coll.remove()
            elif self.dataobject_exists():
                obj = self.session.irods_session.data_objects.get(str(self))
                obj.unlink()
        except irods.exception.CUT_ACTION_PROCESSED_ERR:
            raise(irods.exception.CUT_ACTION_PROCESSED_ERR('iRODS server forbids action.'))

    @staticmethod
    def create_collection(session,  coll_path: str) -> irods.collection.iRODSCollection:
        """Create a collection and all collections in its path. Return he collection. If the
        collection already exists, return ir.

        Return
        ------
        irods.collection.iRODSCollection
            The 
        """
        try:
            return session.irods_session.collections.create(str(coll_path))
        except irods.exception.CUT_ACTION_PROCESSED_ERR:
            raise(irods.exception.CUT_ACTION_PROCESSED_ERR('iRODS server forbids action.'))

    def rename(self):
        """
        Rename the collection or data object
        """

    def collection_exists(self) -> bool:
        """
        Check if the path points to an iRODS collection
        """
        return self.session.irods_session.collections.exists(str(self))

    def dataobject_exists(self) -> bool:
        """
        Check if the path points to an iRODS data object
        """
        return self.session.irods_session.data_objects.exists(str(self))

    def exists(self) -> bool:
        """
        Check if the path already exists on the iRODS server
        """
        return self.dataobject_exists() or self.collection_exists()

    def walk(self, depth: int):
        """
        Walk on a collection.

        Parameters
        ----------
        depth : int
            Stops after depth many iterations, even if the tree is deeper.
        """
