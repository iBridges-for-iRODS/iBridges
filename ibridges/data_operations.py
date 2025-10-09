"""Data and metadata transfers.

Transfer data between local file system and iRODS, includes upload, download and sync.
Also includes operations for creating a local metadata archive and using this archive
to set the metadata.
"""

from __future__ import annotations

import os
import warnings
from pathlib import Path
from typing import Optional, Union

import irods.collection
import irods.data_object
import irods.exception

from ibridges.exception import (
    CollectionDoesNotExistError,
    DataObjectExistsError,
    DoesNotExistError,
    NotACollectionError,
)
from ibridges.executor import Operations
from ibridges.path import CachedIrodsPath, IrodsPath
from ibridges.util import checksums_equal

NUM_THREADS = 4


def upload(
    local_path: Union[str, Path],
    irods_path: IrodsPath,
    overwrite: bool = False,
    on_error: str = "fail",
    resc_name: str = "",
    copy_empty_folders: bool = True,
    options: Optional[dict] = None,
    dry_run: bool = False,
    metadata: Union[None, str, Path, dict] = None,
    progress_bar: bool = True,
) -> Operations:
    """Upload a local directory or file to iRODS.

    Parameters
    ----------
    local_path:
        Absolute path to the directory to upload
    irods_path:
        Absolute irods destination path
    overwrite:
        If data object or collection already exists on iRODS, overwrite
    on_error:
        When a transfer of a file fails, by default the whole transfer will stop and
        print the error message(fail). By setting 'on-error' to 'warn', those errors
        will be turned into warnings and the transfer continues with the next file.
        Setting 'on-error' to 'skip' will omit any message and simply proceed.
    resc_name:
        Name of the resource to which data is uploaded, by default the server will decide
    copy_empty_folders:
        Create respective iRODS collection for empty folders. Default: True.
    options:
        Python-irodsclient options found in ``irods.keywords``. The following keywords will be
        ignored since they are set by iBridges:
        FORCE_FLAG_KW, RESC_NAME_KW, NUM_THREADS_KW, REG_CHKSUM_KW, VERIFY_CHKSUM_KW.
    dry_run:
        Whether to do a dry run before uploading the files/folders.
    metadata:
        If not None, it should point to a file that contains the metadata for the upload.
    progress_bar:
        Whether to display a progress bar.

    Returns
    -------
        Operations object that can be used to execute the upload in case of a dry-run.

    Raises
    ------
    FileNotFoundError:
        If the local_path is not a valid filename of directory.
    DataObjectExistsError:
        If the data object to be uploaded already exists without using overwrite==True.
    PermissionError:
        If the iRODS server does not allow the collection or data object to be created.

    Examples
    --------
    >>> ipath = IrodsPath(session, "~/some_col")
    >>> # Below will create a collection with "~/some_col/dir".
    >>> upload(Path("dir"), ipath)

    >>> # Same, but now data objects that exist will be overwritten.
    >>> upload(Path("dir"), ipath, overwrite=True)

    >>> # Perform the upload in two steps with a dry-run
    >>> ops = upload(Path("some_file.txt"), ipath, dry_run=True)  # Does not upload
    >>> ops.print_summary()  # Check if this is what you want here.
    >>> ops.execute()  # Performs the upload

    """
    local_path = Path(local_path)
    session = irods_path.session
    ops = Operations()
    if local_path.is_dir():
        idest_path = irods_path / local_path.name
        if not overwrite and idest_path.dataobject_exists():
            raise DataObjectExistsError(f"Data object {idest_path} already exists.")
        ops = _up_sync_operations(
            local_path, idest_path, copy_empty_folders=copy_empty_folders, depth=None,
            overwrite=overwrite, on_error=on_error
        )
        if not idest_path.collection_exists():
            ops.add_create_coll(idest_path)
        if not irods_path.collection_exists():
            ops.add_create_coll(irods_path)
    elif local_path.is_file():
        idest_path = irods_path / local_path.name if irods_path.collection_exists() else irods_path
        obj_exists = idest_path.dataobject_exists()
        if not obj_exists or _transfer_needed(local_path, idest_path, overwrite, on_error):
            ops.add_upload(local_path, idest_path)
        else:
            ops.upload_unchanged += 1

    elif local_path.is_symlink():
        raise FileNotFoundError(
            f"Cannot upload symbolic link {local_path}, please supply a direct path."
        )
    else:
        raise FileNotFoundError(f"Cannot upload {local_path}: file or directory does not exist.")
    ops.resc_name = resc_name
    ops.options = options
    if metadata is not None:
        ops.add_meta_upload(idest_path, metadata)
    if not dry_run:
        ops.execute(session, on_error=on_error, progress_bar=progress_bar)
    return ops


def download(
    irods_path: IrodsPath,
    local_path: Union[str, Path],
    overwrite: bool = False,
    on_error: str = "fail",
    resc_name: str = "",
    copy_empty_folders: bool = True,
    options: Optional[dict] = None,
    dry_run: bool = False,
    metadata: Union[None, str, Path] = None,
    progress_bar: bool = True,
) -> Operations:
    """Download a collection or data object to the local filesystem.

    Parameters
    ----------
    irods_path:
        Absolute irods source path pointing to a collection
    local_path:
        Absolute path to the destination directory
    overwrite:
        If data object or collection already exists on iRODS, overwrite.
    on_error:
        When a transfer of a file fails, by default the whole transfer will stop and
        print the error message(fail). By setting 'on-error' to 'warn', those errors
        will be turned into warnings and the transfer continues with the next file.
        Setting 'on-error' to 'skip' will omit any message and simply proceed.
    resc_name:
        Name of the resource from which data is downloaded, by default the server will decide.
    copy_empty_folders:
        Create respective local directory for empty collections.
    options:
        Python-irodsclient options found in ``irods.keywords``. The following keywords will be
        ignored since they are set by iBridges:
        FORCE_FLAG_KW, RESC_NAME_KW, NUM_THREADS_KW, REG_CHKSUM_KW, VERIFY_CHKSUM_KW.
    dry_run:
        Whether to do a dry run before uploading the files/folders.
    metadata:
        If not None, the path to store the metadata to in JSON format.
        It is recommended to use the .json suffix.
    progress_bar:
        Whether to display a progress bar.

    Returns
    -------
        Operations object that can be used to execute the download in case of a dry-run.

    Raises
    ------
    PermissionError:
        If the iRODS server (for whatever reason) forbids downloading the file or
        (part of the) collection.
    DoesNotExistError:
        If the irods_path is not pointing to either a collection or a data object.
    FileExistsError:
        If the irods_path points to a data object and the local file already exists.
    NotADirectoryError:
        If the irods_path is a collection, while the destination is a file.

    Examples
    --------
    >>> # Below will create a directory "some_local_dir/some_collection"
    >>> download(IrodsPath(session, "~/some_collection"), "some_local_dir")

    >>> # Below will create a file "some_local_dir/some_obj.txt"
    >>> download(IrodsPath(session, "some_obj.txt"), "some_local_dir")

    >>> # Below will create a file "new_file.txt" in two steps.
    >>> ops = download(IrodsPath(session, "some_obj.txt", "new_file.txt", dry_run=True)
    >>> ops.execute()

    """
    session = irods_path.session
    local_path = Path(local_path)

    if irods_path.collection_exists():
        if local_path.is_file():
            raise NotADirectoryError(
                f"Cannot download to directory {local_path} "
                "since a file with the same name exists."
            )

        ops = _down_sync_operations(
            irods_path, local_path / irods_path.name, #metadata=metadata,
            copy_empty_folders=copy_empty_folders, overwrite=overwrite,
            on_error=on_error
        )
        if not local_path.is_dir():
            ops.add_create_dir(Path(local_path))
    elif irods_path.dataobject_exists():
        ops = Operations()

        if local_path.is_dir():
            local_path = local_path / irods_path.name
        if not local_path.is_file() or _transfer_needed(
                irods_path, local_path, overwrite, on_error):
            ops.add_download(irods_path, local_path)
        else:
            ops.download_unchanged += 1
        if metadata is not None:
            ops.add_meta_download(irods_path, metadata)

    else:
        raise DoesNotExistError(f"Data object or collection not found: '{irods_path}'")

    if metadata is not None:
        ops.add_meta_download(irods_path, metadata)
    ops.resc_name = resc_name
    ops.options = options
    if not dry_run:
        ops.execute(session, on_error=on_error, progress_bar=progress_bar)
    return ops


def sync(
    source: Union[str, Path, IrodsPath],
    target: Union[str, Path, IrodsPath],
    max_level: Optional[int] = None,
    dry_run: bool = False,
    on_error: str = "fail",
    copy_empty_folders: bool = False,
    resc_name: str = "",
    options: Optional[dict] = None,
    metadata: Union[None, str, Path, dict] = None,
    progress_bar: bool = True,
) -> Operations:
    """Synchronize data between local and remote copies.

    The command can be in one of the two modes: synchronization of data from the client's local file
    system to iRODS, or from iRODS to the local file system. The mode is determined by the type of
    the values for `source` and `target`: objects with type :class:`ibridges.path.IrodsPath`  will
    be interpreted as remote paths, while types :code:`str` and :code:`Path` with be interpreted
    as local paths.

    Files/data objects that have the same checksum will not be synchronized.


    Parameters
    ----------
    source:
        Existing local folder or iRODS collection. An exception will be raised if it doesn't exist.
    target:
        Existing local folder or iRODS collection. An exception will be raised if it doesn't exist.
    max_level:
        Controls the depth up to which the file tree will be synchronized. A max level of 1
        synchronizes only the source's root, max level 2 also includes the first set of
        subfolders/subcollections and their contents, etc. Set to None, there is no limit
        (full recursive synchronization).
    dry_run:
        List all source files and folders that need to be synchronized without actually
        performing synchronization.
    ignore_err:
        If an error occurs during the transfer, and ignore_err is set to True,
        any errors encountered will be transformed into warnings and iBridges will continue
        to transfer the remaining files.
    on_error:
        When a transfer of a file fails, by default the whole transfer will stop and
        print the error message(fail). By setting 'on-error' to 'warn', those errors
        will be turned into warnings and the transfer continues with the next file.
        Setting 'on-error' to 'skip' will omit any message and simply proceed.
    copy_empty_folders:
        Controls whether folders/collections that contain no files or subfolders/subcollections
        will be synchronized.
    resc_name:
        Name of the resource from which data is downloaded, by default the server will decide.
    options:
        Python-irodsclient options found in ``irods.keywords``. The following keywords will be
        ignored since they are set by iBridges:
        FORCE_FLAG_KW, RESC_NAME_KW, NUM_THREADS_KW, REG_CHKSUM_KW, VERIFY_CHKSUM_KW.
    metadata:
        If not None, the location to get the metadata from or store it to.
    progress_bar:
        Whether to display a progress bar.

    Raises
    ------
    CollectionDoesNotExistError:
        If the source collection does not exist
    NotACollectionError:
        If the source is a data object.
    NotADirectoryError:
        If the local source is not a directory.

    Returns
    -------
        An operations object to execute the sync if dry-run is True.

    Examples
    --------
    >>> # Below, all files/dirs in "some_local_dir" will be transferred into "some_remote_coll"
    >>> sync("some_local_dir", IrodsPath(session, "~/some_remote_col")

    >>> # Below, all data objects/collections in "col" will tbe transferred into "some_local_dir"
    >>> sync(IrodsPath(session, "~/col"), "some_local_dir")

    """
    _param_checks(source, target)

    if isinstance(source, IrodsPath):
        session = source.session
        if not source.collection_exists():
            if source.dataobject_exists():
                raise NotACollectionError(f"Source '{source.absolute()}' is a data object, "
                                     "can only sync collections.")
            raise CollectionDoesNotExistError(
                f"Source collection '{source.absolute()}' does not exist")
    elif isinstance(target, IrodsPath):
        session = target.session
        if not Path(source).is_dir():
            raise NotADirectoryError(f"Source folder '{source}' is not a directory or "
                                     "does not exist.")

    else:
        raise TypeError("Either source or target must be an IrodsPath")

    if isinstance(source, IrodsPath):
        if isinstance(metadata, dict):
            raise ValueError("Cannot use dictionary type for metadata download.")
        ops = _down_sync_operations(
            source, Path(target), copy_empty_folders=copy_empty_folders, depth=max_level,
            metadata=metadata, overwrite=True
        )
    else:
        ops = _up_sync_operations(
            Path(source), IrodsPath(session, target), copy_empty_folders=copy_empty_folders,
            depth=max_level, overwrite=True)
        if metadata is not None:
            ops.add_meta_upload(target, metadata)  # type: ignore

    ops.resc_name = resc_name
    ops.options = options
    if not dry_run:
        ops.execute(session, on_error=on_error, progress_bar=progress_bar)

    return ops


def _param_checks(source, target):
    if not isinstance(source, IrodsPath) and not isinstance(target, IrodsPath):
        raise TypeError("Either source or target should be an iRODS path.")

    if isinstance(source, IrodsPath) and isinstance(target, IrodsPath):
        raise TypeError("iRODS to iRODS copying is not supported.")

    if isinstance(source, (str, Path)) and isinstance(target, (str, Path)):
        raise TypeError("Local to local copying is not supported.")


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


def _down_sync_operations(isource_path: IrodsPath, ldest_path: Path,
                          overwrite: bool,
                          on_error: str = "fail",
                          copy_empty_folders: bool = True, depth: Optional[int] = None,
                          metadata: Union[None, str, Path] = None) -> Operations:
    ops = Operations()
    for ipath in isource_path.walk(depth=depth):
        lpath = ldest_path.joinpath(*ipath.relative_to(isource_path).parts)
        if ipath.dataobject_exists():
            if lpath.is_file():
                if _transfer_needed(ipath, lpath, overwrite, on_error):
                    ops.add_download(ipath, lpath)
                else:
                    ops.download_unchanged += 1
            else:
                ops.add_download(ipath, lpath)
            if not lpath.parent.exists():
                ops.add_create_dir(lpath.parent)
        elif ipath.collection_exists() and copy_empty_folders:
            if not lpath.exists():
                ops.add_create_dir(lpath)
    if metadata is not None:
        ops.add_meta_download(isource_path, metadata)
    return ops


def _up_sync_operations(lsource_path: Path, idest_path: IrodsPath,  # pylint: disable=too-many-branches
                        overwrite: bool,
                        copy_empty_folders: bool = True, depth: Optional[int] = None,
                        on_error: str = "fail") -> Operations:
    ops = Operations()
    session = idest_path.session
    try:
        remote_ipaths = {str(ipath): ipath for ipath in idest_path.walk()}
    except irods.exception.CollectionDoesNotExist:
        remote_ipaths = {}
    for root, folders, files in os.walk(lsource_path):
        root_part = Path(root).relative_to(lsource_path)
        if depth is not None and len(root_part.parts) > depth:
            continue
        source = idest_path.joinpath(*root_part.parts)
        for cur_file in files:
            ipath = source / cur_file
            lpath = lsource_path / root_part / cur_file

            # Ignore symlinks
            if lpath.is_symlink():
                warnings.warn(f"Ignoring symlink {lpath}.")
                continue
            if str(ipath) in remote_ipaths:
                ipath = remote_ipaths[str(ipath)]
                if _transfer_needed(lpath, ipath, overwrite, on_error):
                    ops.add_upload(lpath, ipath)
                else:
                    ops.upload_unchanged += 1
            else:
                ipath = CachedIrodsPath(session, None, False, None, str(ipath))
                ops.add_upload(lpath, ipath)
        if copy_empty_folders:
            for fold in folders:
                # Ignore folder symlinks
                lpath = lsource_path / root_part / fold
                if lpath.is_symlink():
                    warnings.warn(f"Ignoring symlink {lpath}.")
                    continue
                if str(source / fold) not in remote_ipaths:
                    ops.add_create_coll(source / fold)
        if str(source) not in remote_ipaths:
            ops.add_create_coll(source)
    return ops
