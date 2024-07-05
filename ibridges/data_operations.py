"""Data transfers.

Transfer data between local file system and iRODS, includes upload, download and sync.
"""

from __future__ import annotations

import base64
import os
import warnings
from pathlib import Path
from typing import Optional, Union

import irods.collection
import irods.data_object
import irods.exception

from ibridges.executor import Operations
from ibridges.path import CachedIrodsPath, IrodsPath
from ibridges.session import Session
from ibridges.util import calc_checksum

NUM_THREADS = 4


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
    metadata: Union[None, str, Path] = None,
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
    metadata:
        If not None, it should point to a file that contains the metadata for the upload.

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
    ops = Operations()
    if local_path.is_dir():
        idest_path = ipath / local_path.name
        if not overwrite and idest_path.exists():
            raise FileExistsError(f"{idest_path} already exists.")
        ops = _up_sync_operations(
            local_path, idest_path, copy_empty_folders=copy_empty_folders, depth=None
        )
        ops.add_create_coll(idest_path)
        if not ipath.collection_exists():
            ops.add_create_coll(ipath)
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
            ops.add_upload(local_path, ipath)

    elif local_path.is_symlink():
        raise FileNotFoundError(
            f"Cannot upload symbolic link {local_path}, please supply a direct " "path."
        )
    else:
        raise FileNotFoundError(f"Cannot upload {local_path}: file or directory does not exist.")
    ops.resc_name = resc_name
    ops.options = options
    if metadata is not None:
        ops.add_meta_upload(ipath, metadata)
    if not dry_run:
        ops.execute(session, ignore_err=ignore_err)
    return ops


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
    metadata: Union[None, str, Path] = None,
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
    metadata:
        If not None, the path to store the metadata to in .json format.

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
            irods_path, local_path / irods_path.name, metadata=metadata,
            copy_empty_folders=copy_empty_folders
        )
        if not local_path.is_dir():
            ops.add_create_dir(Path(local_path))
    elif irods_path.dataobject_exists():
        ops = Operations()

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
            ops.add_download(irods_path, local_path)
        if metadata is not None:
            ops.add_meta_download(irods_path, irods_path, metadata)

    else:
        raise ValueError(f"Data object or collection not found: '{irods_path}'")

    ops.resc_name = resc_name
    ops.options = options
    if not dry_run:
        ops.execute(session, ignore_err=ignore_err)
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
    metadata: Union[None, str, Path] = None,
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
    metadata:
        If not None, the location to get the metadata from or store it to.


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
            source, Path(target), copy_empty_folders=copy_empty_folders, depth=max_level,
            metadata=metadata
        )
    else:
        ops = _up_sync_operations(
            Path(source), IrodsPath(session, target), copy_empty_folders=copy_empty_folders,
            depth=max_level)
        if metadata is not None:
            ops.add_meta_upload(target, metadata)

    ops.resc_name = resc_name
    ops.options = options
    if not dry_run:
        ops.execute(session, ignore_err=ignore_err)

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


def _down_sync_operations(isource_path: IrodsPath, ldest_path: Path,
                          copy_empty_folders: bool  =True, depth: Optional[int] = None,
                          metadata: Union[None, str, Path] = None):
    operations = Operations()
    for ipath in isource_path.walk(depth=depth):
        if metadata is not None:
            operations.add_meta_download(isource_path, ipath, metadata)
        lpath = ldest_path.joinpath(*ipath.relative_to(isource_path).parts)
        if ipath.dataobject_exists():
            if lpath.is_file():
                l_chksum = calc_checksum(lpath)
                i_chksum = calc_checksum(ipath)
                if i_chksum != l_chksum:
                    operations.add_download(ipath, lpath)
            else:
                operations.add_download(ipath, lpath)
            if not lpath.parent.exists():
                operations.add_create_dir(lpath.parent)
        elif ipath.collection_exists() and copy_empty_folders:
            if not lpath.exists():
                operations.add_create_dir(lpath)
    return operations


def _up_sync_operations(lsource_path: Path, idest_path: IrodsPath,  # pylint: disable=too-many-branches
                        copy_empty_folders: bool = True, depth: Optional[int] = None):
    operations = Operations()
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
                l_chksum = calc_checksum(lpath)
                i_chksum = calc_checksum(ipath)

                if i_chksum != l_chksum:
                    operations.add_upload(lpath, ipath)
            else:
                ipath = CachedIrodsPath(session, None, False, None, str(ipath))
                operations.add_upload(lpath, ipath)
        if copy_empty_folders:
            for fold in folders:
                # Ignore folder symlinks
                lpath = lsource_path / root_part / fold
                if lpath.is_symlink():
                    warnings.warn(f"Ignoring symlink {lpath}.")
                    continue
                if str(root_ipath / fold) not in remote_ipaths:
                    operations.add_create_coll(root_ipath / fold)
        if str(root_ipath) not in remote_ipaths:# and str(root_ipath) != str(idest_path):
            operations.add_create_coll(root_ipath)
    return operations
