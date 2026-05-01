from __future__ import annotations

import json
import warnings
from collections import defaultdict
from enum import Enum
from inspect import signature
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Union

import irods.collection
import irods.data_object
import irods.exception
import irods.keywords as kw
from irods.exception import CollectionDoesNotExist
from tqdm import tqdm
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

NUM_THREADS = 4


class PathType(Enum):
    FILE = 1
    DIR = 2

class SkipOperation(ValueError):
    pass

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

class BaseOperation():
    def __getattribute__(self, attr):
        if attr == "ipath":
            if self.session is None:
                raise ValueError("Cannot access session.")
            ipath = super().__getattribute__(attr)
            ipath.session = self.session
        return super().__getattribute__(attr)

class DownloadOperation(BaseOperation):
    # name = "download"

    def __init__(self, ipath, lpath, overwrite=False, on_error="fail"):
        self.ipath = ipath
        self.lpath = lpath
        self.overwrite = overwrite
        self.on_error = on_error
        self.size = ipath.size

    def add_to_vfs(self, vfs_local, vfs_remote, op_id, session):
        ipath = IrodsPath(session, self.ipath_str)
        lpath = Path(self.lpath_str)
        if vfs_local.exists(lpath):
            if lpath.is_symlink():
                raise SkipOperation()
            if not _transfer_needed(
                    ipath, lpath, overwrite=self.overwrite, on_error=self.on_error):
                raise SkipOperation()
        deps = [
            vfs_remote.need_path(ipath, PathType.FILE, op_id),
            vfs_local.need_path(lpath.parent, PathType.DIR, op_id),
            vfs_local.create_path(lpath, PathType.FILE, op_id),
        ]
        return [d for d in deps if d is not None]

    def execute(self, session, pbar):
        ipath = IrodsPath(session, self.ipath_str)
        lpath = Path(self.lpath_str)
        _obj_get(session, ipath, lpath, pbar=pbar)

    @property
    def header(self):
        return "Download files"

    @property
    def body(self):
        return f"{self.ipath_str} -> {self.lpath_str}"

class UploadOperation():
    # name = "upload"

    def __init__(self, lpath, ipath, overwrite=False, on_error="fail"):
        self.lpath_str = str(lpath)
        self.ipath_str = str(ipath)
        self.size = self.lpath.stat().st_size

    def add_to_vfs(self, vfs_local, vfs_remote, op_id, session):
        ipath = IrodsPath(session, self.ipath_str)
        lpath = Path(self.lpath_str)
        if vfs_remote.exists(ipath):
            if not _transfer_needed(
                    lpath, ipath, overwrite=self.overwrite, on_error=self.on_error):
                raise SkipOperation()
        deps = [
            vfs_local.need_path(lpath, PathType.FILE, op_id),
            vfs_remote.need_path(ipath.parent, PathType.DIR, op_id),
            vfs_remote.create_path(ipath, PathType.FILE, op_id),
        ]
        return [d for d in deps if d is not None]

    def execute(self, session, pbar):
        lpath = Path(self.lpath_str)
        ipath = IrodsPath(session, self.ipath_str)
        _obj_put(session, lpath, ipath, pbar)

    @property
    def header(self):
        return "Upload files"

    @property
    def body(self):
        return f"{self.lpath_str} -> {self.ipath_str}"

class CreateDirOperation():
    # name = "create"
    def __init__(self, lpath, exist_ok=True):
        self.lpath_str = str(lpath)
        self.exist_ok = exist_ok
        self.size = 1

    def add_to_vfs(self, vfs_local, vfs_remote, op_id, session):
        lpath = Path(self.lpath_str)
        if vfs_local.exists(lpath) and self.exist_ok:
            if vfs_local.path_type(lpath) != PathType.DIR:
                raise NotADirectoryError(lpath)
            raise SkipOperation()
        deps = [
            vfs_local.need_path(lpath.parent, PathType.DIR, op_id),
            vfs_local.create_path(lpath, PathType.DIR, op_id),
        ]
        return [d for d in deps if d is not None]

    def execute(self, session, pbar):
        Path(self.lpath_str).mkdir()
        pbar.update(self.size)

    @property
    def header(self):
        return "Create directories"

    @property
    def body(self):
        return self.lpath_str


class CreateCollectionOperation():
    def __init__(self, ipath, exist_ok=True):
        self.ipath_str = str(ipath)
        self.exist_ok = True
        self.size = 1

    def add_to_vfs(self, vfs_local, vfs_remote, op_id, session):
        ipath = IrodsPath(session, self.ipath_str)
        if vfs_remote.exists(ipath, op_id) and self.exist_ok:
            if vfs_remote.path_type(ipath) != PathType.DIR:
                raise NotACollectionError(ipath)
            raise SkipOperation()
        elif not self.exist_ok:
            raise CollectionExistsError(ipath)

        deps = [
            vfs_remote.need_path(ipath.parent, PathType.DIR, op_id),
            vfs_remote.create_path(ipath, PathType.DIR, op_id)
        ]
        return [d for d in deps if d is not None]

    def execute(self, session, pbar):
        ipath = IrodsPath(session, self.ipath_str)
        ipath.create_collection()
        pbar.update(self.size)

    @property
    def header(self):
        return "Create Collections"

    @property
    def body(self):
        return self.ipath_str


class PathOperation(Enum):
    Exists = 1
    Missing = 2
    Create = 3
    Needed = 4
    Delete = 5


class VirtualFileSystem():
    def __init__(self):
        self.paths = {}

    def create_path(self, path, path_type, op_id, checksum=None):
        if self.exists(path):
            raise ValueError(f"Path {path} already exists.")
        elif self.path_type(path) is not None:
            raise ValueError(f"Wrong path type for {path} (path_type)")
        self.paths[str(path)].append((PathOperation.Create, path_type, op_id))
        return self.paths[str(path)][-2][2]

    def need_path(self, path, path_type, op_id):
        if not self.exists(path):
            raise ValueError(f"Need path {path}, but path doesn't exist yet.")
        elif self.path_type(path) != path_type:
            raise ValueError(f"Wrong path type for {path} (path_type)")
        self.paths[str(path)].append((PathOperation.Needed, path_type, op_id))
        return self.paths[str(path)][-2][2]

    def delete_path(self, path, path_type, op_id):
        if not self.exists(path):
            raise ValueError(f"Cannot delete {path}, because it does not exist.")
        elif self.path_type(path) != path_type:
            raise ValueError(f"Wrong path type for {path} (path_type)")
        self.paths[str(path)].append((PathOperation.Delete, path_type, op_id))
        return self.paths[str(path)][-2][2]

    def exists(self, path):
        if str(path) in self.paths:
            last_op, _, _ = self.paths[str(path)][-1]
            if last_op in [PathOperation.Missing, PathOperation.Delete]:
                return False
            else:
                return True
        else:
            exists = path.exists()
            if not exists:
                self.paths[str(path)] = [(PathOperation.Missing, None, None)]
                return False
            else:
                self.paths[str(path)] = [(PathOperation.Exists, self.path_type(path), None)]
                return True

    def path_type(self, path):
        if str(path) in self.paths:
            return self.paths[str(path)][-1][1]
        if isinstance(path, IrodsPath):
            if path.dataobject_exists():
                return PathType.FILE
            elif path.collection_exists():
                return PathType.DIR
            else:
                return None
        else:
            if path.is_file():
                return PathType.FILE
            elif path.is_dir():
                return PathType.DIR
            else:
                return None

    def print_all(self):
        for path, status in self.paths.items():
            print(f"{path}" + "  -> ".join(str(s) for s in status))

class DependencyGraph():
    def __init__(self):
        self.dependency_of  = defaultdict(set)
        self.depends_on = {}
        self.queue = []
        self.running = set()

    def add(self, op_id, depends_on):
        self.depends_on[op_id] = depends_on
        for other_op_id in depends_on:
            self.dependency_of[other_op_id].add(op_id)
        if len(depends_on) == 0:
            self.queue.append(op_id)

    def next_op(self):
        op_id = self.queue.pop()
        self.running.add(op_id)
        return op_id

    def finish_op(self, op_id):
        self.running.remove(op_id)
        for dep_op_id in self.depends_on[op_id]:
            self.dependency_of[dep_op_id].remove(op_id)
            if len(self.dependency_of[dep_op_id]) == 0:
                self.queue.append(dep_op_id)
        self.depends_on.pop(op_id)
        self.dependency_of.pop(op_id, None)

    def __len__(self):
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
    options.update({kw.NUM_THREADS_KW: NUM_THREADS, kw.REG_CHKSUM_KW: "", kw.VERIFY_CHKSUM_KW: ""})

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

    """
    if on_error and on_error.lower() not in ["fail", "warn", "skip"]:
        raise ValueError(f"'on_error' {on_error} not a valid value. Choose fail, warn or skip.")
    _warn_ignored_keywords(options)

    if options is None:
        options = {}
    options.update(
        {
            kw.NUM_THREADS_KW: NUM_THREADS,
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
