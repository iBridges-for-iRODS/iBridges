"""Basic operations used for parallel operation of the transfer manager."""

from __future__ import annotations

import warnings
from abc import ABC, abstractmethod
from collections import defaultdict
from enum import Enum, IntFlag
from inspect import signature
from pathlib import Path
from typing import NamedTuple, Optional, Union

import irods.collection
import irods.data_object
import irods.exception
import irods.keywords as kw
from irods.exception import CollectionDoesNotExist
from irods.manager.data_object_manager import MAXIMUM_SINGLE_THREADED_TRANSFER_SIZE
from tqdm.std import tqdm as tqdm_type

from ibridges.exception import (
    CollectionExistsError,
    DataObjectExistsError,
    FileTransferFailedError,
    NotACollectionError,
    ObjectTransferFailedError,
)
from ibridges.path import IrodsPath
from ibridges.session import Session
from ibridges.util import checksums_equal


class PathType(IntFlag):
    """Enum signifiying which type of path it is.

    For iRODS, FILE -> data object and DIR -> collection.
    """

    MISSING = 0
    FILE = 1
    DIR = 2


class PathOperation(Enum):
    """Type of operation or status of paths."""

    EXISTS = 1
    MISSING = 2
    CREATE = 3
    NEEDED = 4
    DELETE = 5


class PathUpdate(NamedTuple):
    """Tuple that contains information on the virtual mutation of a path."""

    operation: PathOperation
    path_type: PathType
    op_id: int


class SkipOperation(ValueError):  # noqa: N818
    """Signal that the operation has been skipped."""


def _transfer_needed(source: Union[IrodsPath, Path],
                     dest: Union[IrodsPath, Path],
                     overwrite: bool, on_error: str):
    if isinstance(source, IrodsPath):
        # Ensure that if the source is remote, the dest should be local.
        if not isinstance(dest, Path):
            raise ValueError("Internal error: source and destination should be local/remote.")
        ipath = source
        lpath = dest
    else:
        if not isinstance(dest, IrodsPath):
            raise ValueError("Internal error: source and destination should be local/remote.")
        ipath = dest
        lpath = source

    if not overwrite:
        if on_error == "fail":
            err_msg = (f"Cannot overwrite {source} -> {dest} unless overwrite==True. "
                       f"To ignore this error and skip the files use on_error=='warn'.")

            if isinstance(dest, IrodsPath):
                raise DataObjectExistsError(err_msg)
            raise FileExistsError(err_msg)
        if on_error == "warn":
            warnings.warn(f"Skipping file/data object {source} -> {dest} since "
                          f"both exist and overwrite == False.")
        return False
    if checksums_equal(ipath, lpath):
        return False
    return True


class VirtualFileSystem():
    """Class that keeps track of the future state of the file/data system."""

    def __init__(self):
        """Initialize the virtual file system without any files/directories present."""
        self.paths: dict[str, list[PathUpdate]] = {}
        self.last_mod: dict[str, int] = defaultdict(lambda: -1)

    def create_path(self, path: str | IrodsPath | Path,
                    path_type: PathType,
                    op_id: int) -> int | None:
        """Create a new path on the virtual file system.

        Parameters
        ----------
        path:
            Path to create.
        path_type:
            Type of path to create (PathType.DIR or PathType.FILE).
        op_id:
            Id of the operation that creates the path.

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
            raise ValueError(f"Path {path} already exists.")
        if self.path_type(path) & (PathType.FILE | PathType.DIR):
            raise ValueError(f"Wrong path type for {path} (path_type)")
        self.paths[str(path)].append(PathUpdate(PathOperation.CREATE, path_type, op_id))
        self.last_mod[str(path)] = len(self.paths[str(path)]) - 1
        return self.paths[str(path)][-2].op_id

    def need_path(self, path: str | IrodsPath | Path,
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
        if (self.path_type(path) & path_type) == 0:
            raise ValueError(f"Wrong path type for {path} (path_type)")
        self.paths[str(path)].append(PathUpdate(PathOperation.NEEDED, path_type, op_id))
        if self.last_mod[str(path)] != -1:
            return self.paths[str(path)][self.last_mod[str(path)]].op_id
        return None

    def delete_path(self, path: str | IrodsPath | Path,
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

    def exists(self, path: str | Path | IrodsPath, allow_recurse: bool = True) -> bool:
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
            if last_op in [PathOperation.MISSING, PathOperation.DELETE]:
                return False
            return True

        # Save a lot of time trying to find out which files exist by checking the
        # parent directory first.
        if allow_recurse:
            self.exists(path.parent, allow_recurse=False)
            # If the parent doesn't exist, then neither does the path itself
            if self.paths[str(path.parent)][0].operation == PathOperation.MISSING:
                self.paths[str(path)] = [PathUpdate(PathOperation.MISSING, None, None)]
                return False
        exists = path.exists()
        if not exists:
            self.paths[str(path)] = [PathUpdate(PathOperation.MISSING, None, None)]
            return False
        self.paths[str(path)] = [PathUpdate(PathOperation.EXISTS,
                                            self.path_type(path), None)]
        return True

    def path_type(self, path: str | IrodsPath | Path):
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


class BaseOperation(ABC):
    """Abstract basic operation class for data transfers."""

    @abstractmethod
    def add_to_vfs(self, vfs_local: VirtualFileSystem, vfs_remote: VirtualFileSystem,
                   op_id: int) -> int | None:
        """Virtually execute the operation and get the dependencies.

        Parameters
        ----------
        vfs_local
            Local virtual file system.
        vfs_remote
            iRODS virtual file system.
        op_id
            Id of the operation that is being added to the vfs.

        Returns
        -------
            Dependency for executing the current operation if there is any, otherwise None.

        """

    @abstractmethod
    def execute(self, session: Session, pbar, n_threads):
        """Execute the operation.

        Parameters
        ----------
        session
            Session to execute the operation with.
        pbar
            Progressbar that will be updated.
        n_threads
            Number of threads to use for the operation.

        """

    @property
    @abstractmethod
    def header(self) -> str:
        """Short description of the kind of operation."""


    @property
    @abstractmethod
    def body(self) -> str:
        """String representation of the actual operation."""

    @property
    @abstractmethod
    def size(self) -> int:
        """Size of the operation."""

    def threads(self, max_threads: int) -> int:
        """Get number of threads that will be used for the operation."""
        if self.size > MAXIMUM_SINGLE_THREADED_TRANSFER_SIZE:
            return max_threads
        return 1

class DownloadOperation(BaseOperation):
    """Operation to download data objects to a local file."""

    def __init__(self, ipath: IrodsPath, lpath: str | Path, overwrite: bool = False,
                 on_error: str = "fail",
                 resc_name: Optional[str] = "",
                 options: Optional[dict] = None):
        """Initialize the download operation.

        Parameters
        ----------
        ipath
            Remote path to data object that is being downloaded.
        lpath
            Local path where the data is being stored.
        overwrite
            Whether to overwrite the local file, by default False
        on_error
            What to do when an error is thrown, by default "fail"
        resc_name : str
            Optional resource name.
        options :
            Extra options to the python irodsclient get method.

        """
        self.ipath = ipath
        self.lpath = lpath
        self.overwrite = overwrite
        self.on_error = on_error
        self.resc_name = resc_name
        self.options = options

    def add_to_vfs(self, vfs_local, vfs_remote, op_id):
        if vfs_local.exists(self.lpath):
            if self.lpath.is_symlink():
                raise SkipOperation()
            if not _transfer_needed(
                    self.ipath, self.lpath, overwrite=self.overwrite, on_error=self.on_error):
                raise SkipOperation()
        deps = [
            vfs_remote.need_path(self.ipath, PathType.FILE, op_id),
            vfs_local.need_path(self.lpath.parent, PathType.DIR, op_id),
            vfs_local.create_path(self.lpath, PathType.FILE, op_id),
        ]
        return [d for d in deps if d is not None]

    def execute(self, session, pbar, n_threads):
        _obj_get(session, self.ipath, self.lpath, pbar=pbar, n_threads=n_threads,
                 resc_name=self.resc_name, options=self.options)

    @property
    def header(self):
        return "Download files"

    @property
    def body(self):
        return f"{self.ipath} -> {self.lpath}"

    @property
    def size(self):
        return self.ipath.size


class UploadOperation(BaseOperation):
    """Operation to upload data from the local file system to the iRODS system."""

    def __init__(self, lpath: Path | str, ipath: IrodsPath, overwrite: bool = False,
                 on_error: str = "fail",
                 resc_name: Optional[str] = "",
                 options: Optional[dict] = None):
        """Initialize upload operation.

        Parameters
        ----------
        lpath
            Local path where the data is located.
        ipath
            Remote path to data object where it is uploaded.
        overwrite
            Whether to overwrite the local file, by default False
        on_error
            What to do when an error is thrown, by default "fail"
        resc_name : str
            Optional resource name.
        options :
            Extra options to the python irodsclient put method.

        """
        self.lpath = lpath
        self.ipath = ipath
        self.overwrite = overwrite
        self.on_error = on_error
        self.resc_name = resc_name
        self.options = options

    def add_to_vfs(self, vfs_local: VirtualFileSystem, vfs_remote: VirtualFileSystem, op_id: int):
        if vfs_remote.exists(self.ipath):
            if not _transfer_needed(
                    self.lpath, self.ipath, overwrite=self.overwrite, on_error=self.on_error):
                raise SkipOperation()
        deps = [
            vfs_local.need_path(self.lpath, PathType.FILE, op_id),
            vfs_remote.need_path(self.ipath.parent, PathType.DIR, op_id),
            vfs_remote.create_path(self.ipath, PathType.FILE, op_id),
        ]
        return [d for d in deps if d is not None]

    def execute(self, session: Session, pbar, n_threads: int):
        _obj_put(session, self.lpath, self.ipath, pbar=pbar, n_threads=n_threads,
                 resc_name=self.resc_name,
                 options=self.options)

    @property
    def header(self):
        return "Upload files"

    @property
    def body(self):
        return f"{self.lpath} -> {self.ipath}"

    @property
    def size(self):
        return self.lpath.stat().st_size


class CreateDirOperation(BaseOperation):
    """Operation to create a local directory."""

    def __init__(self, lpath: str | Path, exist_ok: bool = True):
        """Initialize create directory operation.

        Parameters
        ----------
        lpath
            Local path where to create the directory.
        exist_ok
            Whether it is okay if the directory already exists, by default True

        """
        self.lpath = lpath
        self.exist_ok = exist_ok

    def add_to_vfs(self, vfs_local: VirtualFileSystem,
                   vfs_remote: VirtualFileSystem, op_id: int) -> list[int]:
        if vfs_local.exists(self.lpath) and self.exist_ok:
            if vfs_local.path_type(self.lpath) != PathType.DIR:
                raise NotADirectoryError(self.lpath)
            raise SkipOperation()
        deps = [
            vfs_local.need_path(self.lpath.parent, PathType.DIR, op_id),
            vfs_local.create_path(self.lpath, PathType.DIR, op_id),
        ]
        return [d for d in deps if d is not None]

    def execute(self, session, pbar, n_threads):  # pylint: disable=unused-argument
        self.lpath.mkdir()
        pbar.update(self.size)

    @property
    def header(self):
        return "Create directories"

    @property
    def body(self):
        return str(self.lpath)

    @property
    def size(self):
        return 1


class CreateCollectionOperation(BaseOperation):
    """Operation to create a collection on the remote iRODS system."""

    def __init__(self, ipath: IrodsPath, exist_ok: bool = True):
        """Initialize the create collection operation.

        Parameters
        ----------
        ipath
            IrodsPath where to create the collection.
        exist_ok
            Whether it is okay if the collection already exists, by default True

        """
        self.ipath = ipath
        self.exist_ok = exist_ok

    def add_to_vfs(self, vfs_local: VirtualFileSystem, vfs_remote: VirtualFileSystem, op_id: int):
        if vfs_remote.exists(self.ipath):
            if self.exist_ok:
                if vfs_remote.path_type(self.ipath) != PathType.DIR:
                    raise NotACollectionError(self.ipath)
                raise SkipOperation()
            raise CollectionExistsError(self.ipath)

        deps = [
            vfs_remote.need_path(self.ipath.parent, PathType.DIR, op_id),
            vfs_remote.create_path(self.ipath, PathType.DIR, op_id)
        ]
        return [d for d in deps if d is not None]

    def execute(self, session, pbar, n_threads):
        self.ipath.create_collection()
        pbar.update(self.size)

    @property
    def header(self):
        return "Create Collections"

    @property
    def body(self):
        return str(self.ipath)

    @property
    def size(self):
        return 1


class DependencyGraph():
    """Class that keeps track of the dependencies between operations."""

    def __init__(self):
        """Initialize empty dependency graph."""
        self.dependency_of  = defaultdict(set)
        self.depends_on = {}
        self.queue = []
        self.running = set()

    def add(self, op_id, depends_on):
        """Add a new operation to the dependency graph.

        Parameters
        ----------
        op_id:
            Operation ID of the operation to be added.
        depends_on:
            List of operation IDs of operations on which the current operation depends.

        """
        self.depends_on[op_id] = depends_on
        for other_op_id in depends_on:
            self.dependency_of[other_op_id].add(op_id)
        if len(depends_on) == 0:
            self.queue.append(op_id)

    def next_op(self) -> int:
        """Get the next operation that do no depend on unfinished operations.

        Returns
        -------
        op_id:
            The operation ID of the operation to be run.

        """
        op_id = self.queue.pop()
        self.running.add(op_id)
        return op_id

    def finish_op(self, op_id: int):
        """Finish the operation and remove it from the queue.

        Parameters
        ----------
        op_id:
            The operation ID to finish.

        """
        self.running.remove(op_id)
        for dep_op_id in self.dependency_of[op_id]:
            self.depends_on[dep_op_id].remove(op_id)
            if len(self.depends_on[dep_op_id]) == 0:
                self.queue.append(dep_op_id)
        self.depends_on.pop(op_id)
        self.dependency_of.pop(op_id, None)

    def __len__(self) -> int:
        """Get the number of operations that are still to be scheduled."""
        return len(self.depends_on)

def _obj_put(  # pylint: disable=too-many-branches
    session: Session,
    local_path: Union[str, Path],
    irods_path: Union[str, IrodsPath],
    overwrite: bool = False,
    resc_name: str = "",
    options: Optional[dict] = None,
    on_error: str = "fail",
    pbar: Optional[tqdm_type] = None,
    n_threads: int = 4
) -> int:
    """Upload `local_path` to `irods_path` following iRODS `options`.

    Parameters
    ----------
    session :
        Session to upload the object.
    local_path : str or Path
        Path of local file.
    irods_path : str or IrodsPath
        Path of iRODS data object or collection.
    resc_name : str
        Optional resource name.
    overwrite :
        Whether to overwrite the object if it exists.
    options :
        Extra options to the python irodsclient put method.
    on_error:
        'fail': fail with an exception; 'warn': turn error into warning and continue;
        'skip': simply continue.
    pbar:
        Optional progress bar.
    n_threads:
        Maximum number of threads to be used for transfer.

    """
    transfers = 0

    if on_error and on_error.lower() not in ['fail', 'warn', 'skip']:
        raise ValueError(f"'on_error' {on_error} not a valid value. Choose fail, warn or skip.")

    local_path = Path(local_path)
    irods_path = IrodsPath(session, irods_path)

    if not local_path.is_file():
        err_msg = f"local_path '{local_path}' must be a file."
        _raise_transfer_errors(on_error, err_msg, ValueError)
        return 0

    # Check if irods object already exists
    obj_exists = (
        IrodsPath(session, irods_path / local_path.name).dataobject_exists()
        or irods_path.dataobject_exists()
    )

    _warn_ignored_keywords(options)

    if options is None:
        options = {}
    options.update({kw.NUM_THREADS_KW: n_threads, kw.REG_CHKSUM_KW: "", kw.VERIFY_CHKSUM_KW: ""})

    if pbar is not None:
        upd_put = "updatables" in signature(session.irods_session.data_objects.put).parameters
        if upd_put:
            options["updatables"] = [pbar.update]

    if overwrite:
        options[kw.FORCE_FLAG_KW] = ""
    if resc_name not in ["", None]:
        options[kw.RESC_NAME_KW] = resc_name
    if overwrite or not obj_exists:
        try:
            session.irods_session.data_objects.put(local_path, str(irods_path), **options)
            transfers += 1
        except (PermissionError, OSError) as error:
            err_msg = f"Cannot read {error.filename}."
            _raise_transfer_errors(on_error, err_msg, error, error)
        except irods.exception.CAT_NO_ACCESS_PERMISSION as error:
            err_msg = f"Cannot write iRODS path {str(irods_path)}."
            _raise_transfer_errors(on_error, err_msg, PermissionError, error)
        except irods.exception.OVERWRITE_WITHOUT_FORCE_FLAG as error:
            # This should generally not occur, but a race condition might trigger this.
            # obj does not exist -> someone else writes to object -> overwrite error
            err_msg = (f"Dataset {irods_path} already exists. "
                       "Use overwrite=True to overwrite the existing file."
                       "This error might be the result of simultaneous writing "
                       "to the same data object.")
            _raise_transfer_errors(on_error, err_msg, FileExistsError, error)
        except Exception as error: # pylint: disable=W0718
            err_msg = f"Cannot transfer {local_path} to {irods_path}, {repr(error)}"
            _raise_transfer_errors(on_error, err_msg, FileTransferFailedError, error)
    else:
        err_msg = (f"Dataset {irods_path} already exists. "
                    "Use overwrite=True to overwrite the existing file.")
        _raise_transfer_errors(on_error, err_msg, FileExistsError)
    if pbar is not None and not upd_put:
        pbar.update(IrodsPath(session, irods_path).size)
    return transfers


def _warn_ignored_keywords(options: Optional[dict]):
    if options is None:
        return

    all_ignored_set = set((kw.FORCE_FLAG_KW, kw.RESC_NAME_KW, kw.NUM_THREADS_KW, kw.REG_CHKSUM_KW,
                           kw.VERIFY_CHKSUM_KW))
    cur_ignored_set = set(options).intersection(all_ignored_set)
    if len(cur_ignored_set) > 0:
        warnings.warn(f"Some options will be ignored: {cur_ignored_set}", UserWarning)


def _raise_transfer_errors(on_error: str,
                           msg: str,
                           throw_error,
                           error: Optional[Exception] = None):
    if on_error == "fail":
        if error:
            raise throw_error(msg) from error
        raise throw_error(msg)
    if on_error == "warn":
        warnings.warn(msg)


def _obj_get(
    session: Session,
    irods_path: IrodsPath,
    local_path: Path,
    overwrite: bool = False,
    resc_name: Optional[str] = "",
    options: Optional[dict] = None,
    on_error: str = "fail",
    pbar: Optional[tqdm_type] = None,
    n_threads: int = 4,
 ) -> int:
    # pylint: disable=W0718,R0915,R0912
    """Download `irods_path` to `local_path` following iRODS `options`.

    Parameters
    ----------
    session :
        Session to get the object from.
    irods_path : str or IrodsPath
        Path of iRODS data object.
    local_path : str or Path
        Path of local file or directory/folder.
    overwrite :
        Whether to overwrite the local file if it exists.
    resc_name:
        Name of the resource to get the object from.
    options : dict
        Extra options to the python irodsclient get method.
    on_error:
        'fail': fail with an exception; 'warn': turn error into warning and continue
        'skip': simply continue.
    pbar:
        Optional progress bar.
    n_threads:
        Maximum number of threads to be used for downloading the object.

    """
    if on_error and on_error.lower() not in ["fail", "warn", "skip"]:
        raise ValueError(f"'on_error' {on_error} not a valid value. Choose fail, warn or skip.")
    _warn_ignored_keywords(options)

    if options is None:
        options = {}
    options.update(
        {
            kw.NUM_THREADS_KW: n_threads,
            kw.VERIFY_CHKSUM_KW: "",
        }
    )
    if overwrite:
        options[kw.FORCE_FLAG_KW] = ""
    if resc_name not in ["", None]:
        options[kw.RESC_NAME_KW] = resc_name

    # Compatibility with PRC<2.1
    if pbar is not None:
        upd_put = "updatables" in signature(session.irods_session.data_objects.put).parameters
        if upd_put:
            options["updatables"] = [pbar.update]

    transfers = 0

    # Quick fix for #126
    if Path(local_path).is_dir():
        local_path = Path(local_path).joinpath(irods_path.name)

    try:
        session.irods_session.data_objects.get(str(irods_path), local_path, **options)
        transfers += 1
    except (OSError, irods.exception.CAT_NO_ACCESS_PERMISSION) as error:
        msg = f"Cannot write to {local_path}."
        _raise_transfer_errors(on_error, msg, PermissionError, error)
    except irods.exception.CUT_ACTION_PROCESSED_ERR as error:
        msg = f"During download operation from '{irods_path}': iRODS server forbids action."
        _raise_transfer_errors(on_error, msg, PermissionError, error)
    except irods.exception.CollectionDoesNotExist:
        msg = f"{irods_path} does not exist."
        exception = CollectionDoesNotExist(msg)
        _raise_transfer_errors(on_error, msg, ObjectTransferFailedError, exception)
    except Exception as error:
        msg = f"Cannot transfer {irods_path} to {local_path}, {repr(error)}"
        _raise_transfer_errors(on_error, msg, ObjectTransferFailedError, error)
    if pbar is not None and not upd_put:
        pbar.update(IrodsPath(session, irods_path).size)
    return transfers
