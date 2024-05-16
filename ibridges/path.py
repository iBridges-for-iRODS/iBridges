"""A class to handle iRODS and local (Win, linux) paths."""
from __future__ import annotations

from collections import defaultdict
from pathlib import PurePosixPath
from typing import Iterable, Optional, Union

import irods
from irods.models import DataObject

import ibridges.icat_columns as icat


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

    @property
    def collection(self) -> irods.collection.iRODSCollection:
        """Instantiate an iRODS collection.

        Parameters
        ----------
        session :
            Session to get the collection from.
        path : str
            Name of an iRODS collection.

        Raises
        ------
        ValueError:
            If the path points to a dataobject and not a collection.

        Returns
        -------
        iRODSCollection
            Instance of the collection with `path`.

        """
        if self.collection_exists():
            return self.session.irods_session.collections.get(str(self))
        if self.dataobject_exists():
            raise ValueError("Error retrieving collection, path is linked to a data object."
                            " Use get_dataobject instead to retrieve the data object.")
        raise irods.exception.CollectionDoesNotExist(str(self))

    @property
    def dataobject(self) -> irods.data_object.iRODSDataObject:
        """Instantiate an iRODS data object.

        Raises
        ------
        ValueError:
            If the path is pointing to a collection and not a data object.

        Returns
        -------
        iRODSDataObject
            Instance of the data object with `path`.

        """
        if self.dataobject_exists():
            return self.session.irods_session.data_objects.get(str(self))
        if self.collection_exists():
            raise ValueError("Error retrieving data object, path is linked to a collection."
                         " Use get_collection instead to retrieve the collection.")

        raise irods.exception.DataObjectDoesNotExist(str(IrodsPath))


    def walk(self, depth: Optional[int] = None) -> Iterable[IrodsPath]:
        """Walk on a collection.

        This iterates over all collections and data object for the path. If the
        path is pointing to a data object, it will simply yield this data object.

        Parameters
        ----------
        depth : int
            The maximum depth relative to the starting collection over which is walked.
            For example if depth equals 1, then it will iterate only over the subcollections
            and data objects directly under the starting collection.

        Returns
        -------
            Generator that generates all data objects and subcollections in the collection.

        """
        all_data_objects: dict[str, list[IrodsPath]] = defaultdict(list)
        for path, name, _, _ in _get_data_objects(self.session, self.collection):
            abs_path = IrodsPath(self.session, path).absolute_path()
            all_data_objects[abs_path].append(IrodsPath(self.session, path) / name)
        yield from _recursive_walk(self, depth, all_data_objects)
            # for path, name, _, _ in _get_data_objects(self.session, self.collection):
                # yield IrodsPath(self.session, path) / name

    def relative_to(self, other: IrodsPath) -> PurePosixPath:
        """Calculate the relative path compared to our path."""
        return PurePosixPath(self.absolute_path()).relative_to(PurePosixPath(other.absolute_path()))

    @property
    def size(self):
        """Collect the sizes of a data object or a collection.

        Returns
        -------
        int :
            Total size [bytes] of the iRODS object or all iRODS objects in the collection.

        """
        if not self.exists():
            raise ValueError(f"Path '{str(self)}' does not exist;"
                             " it is neither a collection nor a dataobject.")
        if self.dataobject_exists():
            return self.dataobject.size
        all_objs = _get_data_objects(self.session, self.collection)
        return sum(size for _, _, size, _ in all_objs)


def _recursive_walk(ipath, depth, data_objects):
    if depth is None:
        next_depth = None
    else:
        next_depth = depth - 1
    if not ipath.collection_exists():
        if ipath.dataobject_exists():
            yield ipath
    else:
        coll_ipaths = _get_subcoll_paths(ipath.session, ipath.collection)
        coll_ipaths = sorted(coll_ipaths, key=lambda x: str(coll_ipaths))
        for new_ipath in coll_ipaths:
            yield new_ipath
            if depth is None or depth > 1:
                yield from _recursive_walk(new_ipath, next_depth, data_objects)
        yield from data_objects[ipath.absolute_path()]


def _get_data_objects(session,
                      coll: irods.collection.iRODSCollection) -> list[tuple[str, str, int, str]]:
    """Retrieve all data objects in a collection and all its subcollections.

    Parameters
    ----------
    session:
        Session to get the data objects with.
    coll : irods.collection.iRODSCollection
        The collection to search for all data objects

    Returns
    -------
    list of all data objects
        [(collection path, name, size, checksum)]

    """
    # all objects in the collection
    objs = [(obj.collection.path, obj.name, obj.size, obj.checksum)
            for obj in coll.data_objects]

    # all objects in subcollections
    data_query = session.irods_session.query(icat.COLL_NAME, icat.DATA_NAME,
                                                  DataObject.size, DataObject.checksum)
    data_query = data_query.filter(icat.LIKE(icat.COLL_NAME, coll.path+"/%"))
    for res in data_query.get_results():
        path, name, size, checksum = res.values()
        objs.append((path, name, size, checksum))

    return objs


def _get_subcoll_paths(session,
                     coll: irods.collection.iRODSCollection) -> list:
    """Retrieve all sub collections in a sub tree starting at coll and returns their IrodsPaths."""
    coll_query = session.irods_session.query(icat.COLL_NAME)
    coll_query = coll_query.filter(icat.LIKE(icat.COLL_NAME, coll.path+"/%"))

    return [IrodsPath(session, p) for r in coll_query.get_results() for p in r.values()]
