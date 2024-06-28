"""Data transfers.

Transfer data between local file system and iRODS, includes upload, download and sync.
"""

from __future__ import annotations

import base64
import os
import warnings
from hashlib import sha256
from pathlib import Path
from typing import Optional, Union

import irods.collection
import irods.data_object
import irods.exception
import irods.keywords as kw
from tqdm import tqdm

from ibridges.path import CachedIrodsPath, IrodsPath
from ibridges.session import Session

NUM_THREADS = 4


def _obj_put(
    session: Session,
    local_path: Union[str, Path],
    irods_path: Union[str, IrodsPath],
    overwrite: bool = False,
    resc_name: str = "",
    options: Optional[dict] = None,
    ignore_err: bool = False,
):
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
    ignore_err:
        If True, convert errors into warnings.

    """
    local_path = Path(local_path)
    irods_path = IrodsPath(session, irods_path)

    if not local_path.is_file():
        err_msg = f"local_path '{local_path}' must be a file."
        if not ignore_err:
            raise ValueError(err_msg)
        warnings.warn(err_msg)
        return

    # Check if irods object already exists
    obj_exists = (
        IrodsPath(session, irods_path / local_path.name).dataobject_exists()
        or irods_path.dataobject_exists()
    )

    if options is None:
        options = {}
    options.update({kw.NUM_THREADS_KW: NUM_THREADS, kw.REG_CHKSUM_KW: "", kw.VERIFY_CHKSUM_KW: ""})

    if resc_name not in ["", None]:
        options[kw.RESC_NAME_KW] = resc_name
    if overwrite or not obj_exists:
        try:
            session.irods_session.data_objects.put(local_path, str(irods_path), **options)
        except (PermissionError, OSError) as error:
            err_msg = f"Cannot read {error.filename}."
            if not ignore_err:
                raise PermissionError(err_msg) from error
            warnings.warn(err_msg)
        except irods.exception.CAT_NO_ACCESS_PERMISSION as error:
            err_msg = f"Cannot write {str(irods_path)}."
            if not ignore_err:
                raise PermissionError(err_msg) from error
            warnings.warn(err_msg)
        except irods.exception.OVERWRITE_WITHOUT_FORCE_FLAG as error:
            raise FileExistsError(
                f"Dataset {irods_path} already exists. "
                "Use overwrite=True to overwrite the existing file."
            ) from error
    else:
        if not ignore_err:
            raise FileExistsError(
                f"Dataset {irods_path} already exists. "
                "Use overwrite=True to overwrite the existing file."
            )
        warnings.warn(f"Cannot overwrite dataobject with name '{local_path.name}'.")


def upload(
    session: Session,
    local_path: Union[str, Path],
    irods_path: Union[str, IrodsPath],
    overwrite: bool = False,
    ignore_err: bool = False,
    resc_name: str = "",
    copy_empty_folders: bool = True,
    options: Optional[dict] = None,
    dry_run: bool = False,
):
    """Upload a local directory or file to iRODS.

    Parameters
    ----------
    session :
        Session to upload the data to.
    local_path : Path
        Absolute path to the directory to upload
    irods_path : IrodsPath
        Absolute irods destination path
    overwrite : bool
        If data object or collection already exists on iRODS, overwrite
    ignore_err : bool
        If an error occurs during upload, and ignore_err is set to True, any errors encountered
        will be transformed into warnings and iBridges will continue to upload the remaining files.
        By default all errors will stop the process of uploading.
    resc_name : str
        Name of the resource to which data is uploaded, by default the server will decide
    copy_empty_folders : bool
        Create respective iRODS collection for empty folders. Default: True.
    options : dict
        More options for the upload
    dry_run:
        Whether to do a dry run before uploading the files/folders.

    Raises
    ------
    ValueError:
        If the local_path is not a valid filename of directory.
    PermissionError:
        If the iRODS server does not allow the collection or data object to be created.

    Examples
    --------
    >>> ipath = IrodsPath(session, "~/some_col")
    >>> upload(session, Path("dir"), ipath)
    >>> upload(session, Path("dir"), ipath, overwrite=True)
    >>> ops = upload(session, Path("some_file.txt"), ipath, dry_run)  # Does not upload
    >>> print(ops)
    {'create_dir': set(),
    'create_collection': set(),
    'upload': [(PosixPath('some_file.txt'), IrodsPath(~, some_col))],
    'download': [],
    'resc_name': '',
    'options': None}

    """
    local_path = Path(local_path)
    ipath = IrodsPath(session, irods_path)
    ops = _empty_ops()
    if local_path.is_dir():
        idest_path = ipath / local_path.name
        if not overwrite and idest_path.exists():
            raise FileExistsError(f"{idest_path} already exists.")
        ops = _up_sync_operations(
            local_path, idest_path, copy_empty_folders=copy_empty_folders, depth=None
        )
        ops["create_collection"].add(str(idest_path))
    elif local_path.is_file():
        if ipath.collection_exists():
            ipath = ipath / local_path.name
        obj_exists = ipath.dataobject_exists()

        if obj_exists and not overwrite:
            raise FileExistsError(
                f"Dataset {irods_path} already exists. "
                "Use overwrite=True to overwrite the existing file."
            )

        if not (obj_exists and _calc_checksum(local_path) == _calc_checksum(ipath)):
            ops["upload"].append((local_path, ipath))
    elif local_path.is_symlink():
        raise FileNotFoundError(
            f"Cannot upload symbolic link {local_path}, please supply a direct " "path."
        )
    else:
        raise FileNotFoundError(f"Cannot upload {local_path}: file or directory does not exist.")
    ops.update({"resc_name": resc_name, "options": options})
    if not dry_run:
        perform_operations(session, ops, ignore_err=ignore_err)
    return ops


def _obj_get(
    session: Session,
    irods_path: IrodsPath,
    local_path: Path,
    overwrite: bool = False,
    resc_name: Optional[str] = "",
    options: Optional[dict] = None,
    ignore_err: bool = False,
):
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
    ignore_err:
        If True, convert errors into warnings.

    """
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

    # Quick fix for #126
    if Path(local_path).is_dir():
        local_path = Path(local_path).joinpath(irods_path.name)

    try:
        session.irods_session.data_objects.get(str(irods_path), local_path, **options)
    except (OSError, irods.exception.CAT_NO_ACCESS_PERMISSION) as error:
        msg = f"Cannot write to {local_path}."
        if not ignore_err:
            raise PermissionError(msg) from error
        warnings.warn(msg)
    except irods.exception.CUT_ACTION_PROCESSED_ERR as exc:
        msg = f"During download operation from '{irods_path}': iRODS server forbids action."
        if not ignore_err:
            raise PermissionError(msg) from exc
        warnings.warn(msg)


def download(
    session: Session,
    irods_path: Union[str, IrodsPath],
    local_path: Union[str, Path],
    overwrite: bool = False,
    ignore_err: bool = False,
    resc_name: str = "",
    copy_empty_folders: bool = True,
    options: Optional[dict] = None,
    dry_run: bool = False,
):
    """Download a collection or data object to the local filesystem.

    Parameters
    ----------
    session :
        Session to download the collection from.
    irods_path : IrodsPath
        Absolute irods source path pointing to a collection
    local_path : Path
        Absolute path to the destination directory
    overwrite : bool
        If an error occurs during download, and ignore_err is set to True, any errors encountered
        will be transformed into warnings and iBridges will continue to download the remaining
        files.
        By default all errors will stop the process of downloading.
    ignore_err : bool
        Collections: If download of an item fails print error and continue with next item.
    resc_name : str
        Name of the resource from which data is downloaded, by default the server will decide.
    copy_empty_folders : bool
        Create respective local directory for empty collections.
    options : dict
        More options for the download
    dry_run:
        Whether to do a dry run before uploading the files/folders.

    Raises
    ------
    PermissionError:
        If the iRODS server (for whatever reason) forbids downloading the file or
        (part of the) collection.
    ValueError:
        If the irods_path is not pointing to either a collection or a data object.
    FileExistsError:
        If the irods_path points to a data object and the local file already exists.
    NotADirectoryError:
        If the irods_path is a collection, while the destination is a file.

    Examples
    --------
    >>> download(session, "~/some_collection", "some_local_dir")
    >>> download(session, IrodsPath(session, "some_obj.txt"), "some_local_dir")
    >>> ops = download(session, "~/some_obj.txt", "some_local_dir", dry_run=True)
    >>> print(ops)
    {'create_dir': set(),
    'create_collection': set(),
    'upload': [],
    'download': [(IrodsPath(~, some_obj.txt), PosixPath('some_local_dir'))],
    'resc_name': '',
    'options': None}

    """
    irods_path = IrodsPath(session, irods_path)
    local_path = Path(local_path)

    if irods_path.collection_exists():
        if local_path.is_file():
            raise NotADirectoryError(
                f"Cannot download to directory {local_path} "
                "since a file with the same name exists."
            )

        ops = _down_sync_operations(
            irods_path, local_path / irods_path.name, copy_empty_folders=copy_empty_folders
        )
        ops["create_dir"].add(str(local_path / irods_path.name))
        if not local_path.is_dir():
            ops["create_dir"].add(str(local_path))
    elif irods_path.dataobject_exists():
        ops = _empty_ops()

        if local_path.is_dir():
            local_path = local_path / irods_path.name
        if (not overwrite) and local_path.is_file():
            raise FileExistsError(
                f"File or directory {local_path} already exists. "
                "Use overwrite=True to overwrite the existing file(s)."
            )
        if not (
            local_path.is_file() and (_calc_checksum(irods_path) == _calc_checksum(local_path))
        ):
            ops["download"].append((irods_path, local_path))

    else:
        raise ValueError(f"Data object or collection not found: '{irods_path}'")

    ops.update({"resc_name": resc_name, "options": options})
    if not dry_run:
        perform_operations(session, ops, ignore_err=ignore_err)
    return ops


def create_collection(
    session: Session, coll_path: Union[IrodsPath, str]
) -> irods.collection.iRODSCollection:
    """Create a collection and all parent collections that do not exist yet.

    Alias for :meth:`ibridges.path.IrodsPath.create_collection`

    Parameters
    ----------
    session:
        Session to create the collection for.
    coll_path: IrodsPath
        Collection path

    Raises
    ------
    PermissionError:
        If creating a collection is not allowed by the server.


    Examples
    --------
    >>> create_collection(session, IrodsPath("~/new_collection"))

    """
    return IrodsPath.create_collection(session, coll_path)


def perform_operations(session: Session, operations: dict, ignore_err: bool = False):
    """Execute data operations.

    The operations can be obtained with a dry run of the upload/download/sync function.

    Parameters
    ----------
    session
        Session to do the data operations for.
    operations
        Dictionary containing the operations to perform.
    ignore_err
        Ignore any errors and convert them into warnings if True.

    Raises
    ------
    PermissionError:
        When the operation is not allowed on either the iRODS server or locally.

    Examples
    --------
    >>> perform_operations(session, ops)

    """
    up_sizes = [lpath.stat().st_size for lpath, _ in operations["upload"]]
    down_sizes = [ipath.size for ipath, _ in operations["download"]]
    disable = len(up_sizes) + len(down_sizes) == 0
    pbar = tqdm(
        total=sum(up_sizes) + sum(down_sizes),
        unit="B",
        unit_scale=True,
        unit_divisor=1024,
        disable=disable,
    )

    # The code below does not work as expected, since connections in the
    # pool can be reused. Another solution for dynamic timeouts might be needed
    # Leaving the previous solution in here for documentation.

    # For large files, the checksum computation might take too long, which can result in a timeout.
    # This is why we increase the time out from file sizes > 1 GB
    # This might still result in a time out if your server is very busy or a potato.
    # max_size = max([*up_sizes, *down_sizes, 0])
    # original_timeout = session.irods_session.pool.connection_timeout
    # if max_size > 1e9 and original_timeout == DEFAULT_CONNECTION_TIMEOUT:
    #     session.irods_session.pool.connection_timeout = int(
    #         DEFAULT_CONNECTION_TIMEOUT*(max_size/1e9)+0.5)

    for col in operations["create_collection"]:
        IrodsPath.create_collection(session, col)
    for curdir in operations["create_dir"]:
        try:
            Path(curdir).mkdir(parents=True, exist_ok=True)
        except NotADirectoryError as error:
            raise PermissionError(f"Cannot create {error.filename}") from error

    options = operations.get("options", None)
    options = {} if options is None else options
    resc_name = operations.get("resc_name", "")
    for (lpath, ipath), size in zip(operations["upload"], up_sizes):
        _obj_put(
            session,
            lpath,
            ipath,
            overwrite=True,
            ignore_err=ignore_err,
            options=options,
            resc_name=resc_name,
        )
        pbar.update(size)
    for (ipath, lpath), size in zip(operations["download"], down_sizes):
        _obj_get(
            session,
            ipath,
            lpath,
            overwrite=True,
            ignore_err=ignore_err,
            options=options,
            resc_name=resc_name,
        )
        pbar.update(size)
    # session.irods_session.pool.connection_timeout = original_timeout


def sync(
    session: Session,
    source: Union[str, Path, IrodsPath],
    target: Union[str, Path, IrodsPath],
    max_level: Optional[int] = None,
    dry_run: bool = False,
    ignore_err: bool = False,
    copy_empty_folders: bool = False,
    resc_name: str = "",
    options: Optional[dict] = None,
) -> dict:
    """Synchronize the data between a local copy (local file system) and the copy stored in iRODS.

    The command can be in one of the two modes: synchronization of data from the client's local file
    system to iRODS, or from iRODS to the local file system. The mode is determined by the type of
    the values for `source` and `target` (IrodsPath or str/Path).

    The command considers the file size and the checksum to determine whether a file should be
    synchronized.


    Parameters
    ----------
    session : ibridges.Session
        An authorized iBridges session.
    source : str or Path or IrodsPath
        Existing local folder or iRODS collection. An exception will be raised if it doesn't exist.
    target : str or Path or IrodsPath
        Existing local folder or iRODS collection. An exception will be raised if it doesn't exist.
    max_level : int, default None
        Controls the depth up to which the file tree will be synchronized. A max level of 1
        synchronizes only the source's root, max level 2 also includes the first set of
        subfolders/subcollections and their contents, etc. Set to None, there is no limit
        (full recursive synchronization).
    dry_run : bool, default False
        List all source files and folders that need to be synchronized without actually
        performing synchronization.
    ignore_err : If an error occurs during the transfer, and ignore_err is set to True,
        any errors encountered will be transformed into warnings and iBridges will continue
        to transfer the remaining files.
    copy_empty_folders : bool, default False
        Controls whether folders/collections that contain no files or subfolders/subcollections
        will be synchronized.
    resc_name : str
        Name of the resource from which data is downloaded, by default the server will decide.
    options : dict
        More options for the download/upload


    Returns
    -------
        A dict object containing four keys:
            'create_dir' : Create local directories when sync from iRODS to local
            'create_collection' : Create collections when sync from local to iRODS
            'upload' : Tuple(local path, iRODS path) when sync from local to iRODS
            'download' : Tuple(iRODS path, local path) when sync from iRODS to local
        (or of to-be-changed folders and files, when in dry-run mode).

    """
    _param_checks(source, target)

    if isinstance(source, IrodsPath):
        if not source.collection_exists():
            raise ValueError(f"Source collection '{source.absolute()}' does not exist")
    else:
        if not Path(source).is_dir():
            raise ValueError(f"Source folder '{source}' does not exist")

    if isinstance(source, IrodsPath):
        ops = _down_sync_operations(
            source, Path(target), copy_empty_folders=copy_empty_folders, depth=max_level
        )
    else:
        ops = _up_sync_operations(
            Path(source), target, copy_empty_folders=copy_empty_folders, depth=max_level
        )

    ops.update({"resc_name": resc_name, "options": options})
    if not dry_run:
        perform_operations(session, ops, ignore_err=ignore_err)

    return ops


def _param_checks(source, target):
    if not isinstance(source, IrodsPath) and not isinstance(target, IrodsPath):
        raise TypeError("Either source or target should be an iRODS path.")

    if isinstance(source, IrodsPath) and isinstance(target, IrodsPath):
        raise TypeError("iRODS to iRODS copying is not supported.")


def _calc_checksum(filepath):
    if isinstance(filepath, IrodsPath):
        return filepath.checksum
    f_hash = sha256()
    memv = memoryview(bytearray(128 * 1024))
    with open(filepath, "rb", buffering=0) as file:
        for item in iter(lambda: file.readinto(memv), 0):
            f_hash.update(memv[:item])
    return f"sha2:{str(base64.b64encode(f_hash.digest()), encoding='utf-8')}"


def _empty_ops():
    return {
        "create_dir": set(),
        "create_collection": set(),
        "upload": [],
        "download": [],
    }


def _down_sync_operations(isource_path, ldest_path, copy_empty_folders=True, depth=None):
    operations = _empty_ops()
    for ipath in isource_path.walk(depth=depth):
        lpath = ldest_path.joinpath(*ipath.relative_to(isource_path).parts)
        if ipath.dataobject_exists():
            if lpath.is_file():
                l_chksum = _calc_checksum(lpath)
                i_chksum = _calc_checksum(ipath)
                if i_chksum != l_chksum:
                    operations["download"].append((ipath, lpath))
            else:
                operations["download"].append((ipath, lpath))
            if not lpath.parent.exists():
                operations["create_dir"].add(str(lpath.parent))
        elif ipath.collection_exists() and copy_empty_folders:
            if not lpath.exists():
                operations["create_dir"].add(str(lpath))
    return operations


def _up_sync_operations(lsource_path, idest_path, copy_empty_folders=True, depth=None):  # pylint: disable=too-many-branches
    operations = _empty_ops()
    session = idest_path.session
    try:
        remote_ipaths = {str(ipath): ipath for ipath in idest_path.walk()}
    except irods.exception.CollectionDoesNotExist:
        remote_ipaths = {}
    for root, folders, files in os.walk(lsource_path):
        root_part = Path(root).relative_to(lsource_path)
        if depth is not None and len(root_part.parts) > depth:
            continue
        root_ipath = idest_path.joinpath(*root_part.parts)
        for cur_file in files:
            ipath = root_ipath / cur_file
            lpath = lsource_path / root_part / cur_file

            # Ignore symlinks
            if lpath.is_symlink():
                warnings.warn(f"Ignoring symlink {lpath}.")
                continue
            if str(ipath) in remote_ipaths:
                ipath = remote_ipaths[str(ipath)]
                l_chksum = _calc_checksum(lpath)
                i_chksum = _calc_checksum(ipath)

                if i_chksum != l_chksum:
                    operations["upload"].append((lpath, ipath))
            else:
                ipath = CachedIrodsPath(session, None, False, None, str(ipath))
                operations["upload"].append((lpath, ipath))
        if copy_empty_folders:
            for fold in folders:
                # Ignore folder symlinks
                lpath = lsource_path / root_part / fold
                if lpath.is_symlink():
                    warnings.warn(f"Ignoring symlink {lpath}.")
                    continue
                if str(root_ipath / fold) not in remote_ipaths:
                    operations["create_collection"].add(str(root_ipath / fold))
        if str(root_ipath) not in remote_ipaths and str(root_ipath) != str(idest_path):
            operations["create_collection"].add(str(root_ipath))
    return operations
