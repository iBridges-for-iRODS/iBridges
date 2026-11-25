"""Virtual file system that keeps track of future changes to local and remote systems."""
from collections import defaultdict
from pathlib import Path

from ibridges.path import IrodsPath
from ibridges.util import PathOperation, PathType, PathUpdate


class VirtualFileSystem():
    """Class that keeps track of the future state of the file/data system.

    During operations the status of files/directories will change. If a file gets created,
    then read, then modified, we know that those operations have to be performed in that
    particular order. That is what the VirtualFileSystem keeps track of: how each object
    in the file system gets mutated, read and deleted, so that the schedular can enforce
    the correct order between different operations, while maximizizing the concurrency.
    """

    def __init__(self):
        """Initialize the virtual file system without any files/directories present."""
        self.paths: dict[str, list[PathUpdate]] = {}
        self.last_mod: dict[str, int] = defaultdict(lambda: -1)

    def create_path(self, path: IrodsPath | Path,
                    path_type: PathType,
                    op_id: int,
                    overwrite: bool) -> int | None:
        """Create a new path on the virtual file system.

        Parameters
        ----------
        path:
            Path to create.
        path_type:
            Type of path to create (PathType.DIR or PathType.FILE).
        op_id:
            Id of the operation that creates the path.
        overwrite:
            Whether to overwrite the file/data object.

        Raises
        ------
        ValueError: if the path already exists
        ValueError: if the path_type is incompatible with the current path type

        Returns
        -------
        op_id:
            Id of the previous operation on the same path.

        """
        if self.exists(path):
            if not overwrite:
                raise ValueError(f"Path {path} already exists.")
            if self.path_type(path) != path_type:
                raise ValueError(f"Wrong path type for {path} (path_type)")
        self.paths[str(path)].append(PathUpdate(PathOperation.CREATE, path_type, op_id))
        self.last_mod[str(path)] = len(self.paths[str(path)]) - 1
        return self.paths[str(path)][-2].op_id

    def need_path(self, path: IrodsPath | Path,
                  path_type: PathType,
                  op_id: int) -> int | None:
        """Ensure that the path exist and put in a dependency.

        Parameters
        ----------
        path:
            Path that is required to exist.
        path_type:
            The type of path that it needs.
        op_id:
            ID of the operation that needs this path.

        Returns
        -------
            Operation id of the last mutation to the path.

        Raises
        ------
        ValueError
            When the path doesn't exist.
        ValueError
            When the path type is wrong.

        """
        if not self.exists(path):
            raise ValueError(f"Need path {path}, but path doesn't exist yet.")
        if self.path_type(path) != path_type:
            raise ValueError(f"Wrong path type for {path} (path_type)")
        self.paths[str(path)].append(PathUpdate(PathOperation.REQUIRE, path_type, op_id))
        if self.last_mod[str(path)] != -1:
            return self.paths[str(path)][self.last_mod[str(path)]].op_id
        return None

    def delete_path(self, path: IrodsPath | Path,
                    path_type: PathType,
                    op_id: int) -> int | None:
        """Add a delete path operation.

        Parameters
        ----------
        path
            Path that would be deleted.
        path_type
            Type of the path that would be deleted.
        op_id
            Id of the operation that will delete the path.

        Returns
        -------
            The ID of the operation that deleted the path.

        Raises
        ------
        ValueError
            If the path does not exist.
        ValueError
            If the path type is wrong.

        """
        if not self.exists(path):
            raise ValueError(f"Cannot delete {path}, because it does not exist.")
        if self.path_type(path) != path_type:
            raise ValueError(f"Wrong path type for {path} (path_type)")
        self.paths[str(path)].append(PathUpdate(PathOperation.DELETE, path_type, op_id))
        return self.paths[str(path)][-2].op_id

    def exists(self, path: Path | IrodsPath, allow_recurse: bool = True) -> bool:
        """Check whether a path exists already (virtually).

        Parameters
        ----------
        path
            Path to check whether it exists.
        allow_recurse
            Allow checking of whether the parent exists, by default True

        Returns
        -------
            Whether the path (virtually) exists.

        """
        if str(path) in self.paths:
            last_op, _, _ = self.paths[str(path)][-1]
            if last_op == PathOperation.DELETE:
                return False
            return True

        # Save a lot of time trying to find out which files exist by checking the
        # parent directory first.
        if allow_recurse:
            self.exists(path.parent, allow_recurse=False)
            # If the parent doesn't exist, then neither does the path itself
            if self.paths[str(path.parent)][0].operation == PathOperation.DELETE:
                self.paths[str(path)] = [PathUpdate(PathOperation.DELETE, PathType.MISSING, None)]
                return False
        exists = path.exists()
        if not exists:
            self.paths[str(path)] = [PathUpdate(PathOperation.DELETE, PathType.MISSING, None)]
            return False
        self.paths[str(path)] = [PathUpdate(PathOperation.CREATE,
                                            self.path_type(path), None)]
        return True

    def path_type(self, path: IrodsPath | Path):
        """Get the path type of a path from the vfs, or real system.

        Parameters
        ----------
        path
            Path to check the path type for.

        Returns
        -------
            The path type of the path if it exists, otherwise return PathType.MISSING

        """
        if str(path) in self.paths:
            return self.paths[str(path)][-1].path_type
        if isinstance(path, IrodsPath):
            if path.dataobject_exists():
                path_type = PathType.FILE
            elif path.collection_exists():
                path_type = PathType.DIR
            else:
                path_type = PathType.MISSING
            return path_type

        # Path is local
        if path.is_file():
            return PathType.FILE
        if path.is_dir():
            return PathType.DIR
        return PathType.MISSING

    def _print_all(self):
        for path, status in self.paths.items():
            print(f"{path}" + "  -> ".join(str(s) for s in status))
