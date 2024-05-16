"""Collections and data objects."""
from __future__ import annotations

import os
import warnings
from pathlib import Path
from typing import Optional, Union

import irods.collection
import irods.data_object
import irods.exception
import irods.keywords as kw
from tqdm import tqdm

from ibridges.path import IrodsPath
from ibridges.session import Session

NUM_THREADS = 4


def _obj_put(session: Session, local_path: Union[str, Path], irods_path: Union[str, IrodsPath],
             overwrite: bool = False, resc_name: str = '', options: Optional[dict] = None):
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
        TODO: this seems currently unused?

    """
    local_path = Path(local_path)
    irods_path = IrodsPath(session, irods_path)

    if not local_path.is_file():
        raise ValueError("local_path must be a file.")

    # Check if irods object already exists
    obj_exists = IrodsPath(session,
                           irods_path / local_path.name).dataobject_exists() \
                 or irods_path.dataobject_exists()

    if options is None:
        options = {}
    options.update({
        kw.NUM_THREADS_KW: NUM_THREADS,
        kw.REG_CHKSUM_KW: '',
        kw.VERIFY_CHKSUM_KW: ''
    })

    if resc_name not in ['', None]:
        options[kw.RESC_NAME_KW] = resc_name
    if overwrite or not obj_exists:
        session.irods_session.data_objects.put(local_path, str(irods_path), **options)
    else:
        raise irods.exception.OVERWRITE_WITHOUT_FORCE_FLAG

def _obj_get(session: Session, irods_path: Union[str, IrodsPath], local_path: Union[str, Path],
             overwrite: bool = False, resc_name: Optional[str] = '',
             options: Optional[dict] = None):
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
        iRODS transfer options.

    """
    irods_path = IrodsPath(session, irods_path)
    if not irods_path.dataobject_exists():
        raise ValueError("irods_path must be a data object.")
    if options is None:
        options = {}
    options.update({
        kw.NUM_THREADS_KW: NUM_THREADS,
        kw.VERIFY_CHKSUM_KW: '',
        })
    if overwrite:
        options[kw.FORCE_FLAG_KW] = ''
    if resc_name not in ['', None]:
        options[kw.RESC_NAME_KW] = resc_name
    #Quick fix for #126
    if Path(local_path).is_dir():
        local_path = Path(local_path).joinpath(irods_path.parts[-1])
    session.irods_session.data_objects.get(str(irods_path), local_path, **options)

def _create_irods_dest(local_path: Path, irods_path: IrodsPath
                       ) -> list[tuple[Path, IrodsPath]]:
    """Assembles the irods destination paths for upload of a folder."""
    upload_path = irods_path.joinpath(local_path.name)
    paths = [(str(Path(root).relative_to(local_path)), f)
             for root, _, files in os.walk(local_path) for f in files]

    source_to_dest = [(local_path.joinpath(folder.lstrip(os.sep), file_name),
                       upload_path.joinpath(folder.lstrip(os.sep), file_name))
                       for folder, file_name in paths]

    return source_to_dest

def _create_irods_subtree(local_path: Path, irods_path: IrodsPath):
    # create all collections from folders including empty ones
    folders = [Path(root).relative_to(local_path).joinpath(f)
               for root, folders, _ in os.walk(local_path) for f in folders]
    for folder in folders:
        IrodsPath.create_collection(irods_path.session,
                                    irods_path.joinpath(local_path.parts[-1], *folder.parts))

def _upload_collection(session: Session, local_path: Union[str, Path],
                       irods_path: Union[str, IrodsPath],
                       overwrite: bool = False, ignore_err: bool = False, resc_name: str = '',
                       copy_empty_folders: bool = True, options: Optional[dict] = None):
    """Upload a local directory to iRODS.

    Parameters
    ----------
    session :
        Session to upload the collection to.
    local_path : Path
        Absolute path to the directory to upload
    irods_path : IrodsPath
        Absolute irods destination path
    overwrite : bool
        If data already exists on iRODS, overwrite
    ignore_err : bool
        If an error occurs during upload, and ignore_err is set to True, any errors encountered
        will be transformed into warnings and iBridges will continue to upload the remaining files.
        By default all errors will stop the process of uploading.
    resc_name : str
        Name of the resource to which data is uploaded, by default the server will decide
    copy_empty_folders : bool
        Create collection even if the corresponding source folder is empty.
    options : dict
        More options for the upload

    """
    local_path = Path(local_path)
    irods_path = IrodsPath(session, irods_path)
    # get all files and their relative path to local_path
    if not local_path.is_dir():
        raise ValueError("local_path must be a directory.")

    if copy_empty_folders:
        _create_irods_subtree(local_path, irods_path)
    source_to_dest = _create_irods_dest(local_path, irods_path)
    for source, dest in source_to_dest:
        _ = create_collection(session, dest.parent)
        try:
            _obj_put(session, source, dest, overwrite, resc_name, options)
        except irods.exception.OVERWRITE_WITHOUT_FORCE_FLAG:
            warnings.warn(f'Object already exists\tSkipping {source}')
        except KeyError as e:
            if ignore_err is True:
                warnings.warn(f'Upload failed: {source}\n'+repr(e))
            else:
                raise ValueError(f'Upload failed: {source}: '+repr(e)) from e

def _create_local_dest(irods_path: IrodsPath, local_path: Path,
                       copy_empty_folders: bool = True
                       ) -> list[tuple[IrodsPath, Path]]:
    """Assembles the local destination paths for download of a collection."""
    download_path = local_path.joinpath(irods_path.name.lstrip('/'))
    source_to_dest: list[tuple[IrodsPath, Path]] = []
    for cur_ipath in irods_path.walk():
        cur_lpath = download_path / cur_ipath.relative_to(irods_path)
        if copy_empty_folders and cur_ipath.collection_exists():
            cur_lpath.mkdir(parents=True, exist_ok=True)
        elif cur_ipath.dataobject_exists():
            source_to_dest.append((cur_ipath, cur_lpath))
            cur_lpath.parent.mkdir(parents=True, exist_ok=True)
    return source_to_dest

def _download_collection(session: Session, irods_path: Union[str, IrodsPath], local_path: Path,
                         overwrite: bool = False, ignore_err: bool = False, resc_name: str = '',
                         copy_empty_folders: bool = True, options: Optional[dict] = None):
    """Download a collection to the local filesystem.

    Parameters
    ----------
    session :
        Session to download the collection from.
    irods_path : IrodsPath
        Absolute irods source path pointing to a collection
    local_path : Path
        Absolute path to the destination directory
    overwrite : bool
        Overwrite existing local data
    ignore_err : bool
        If an error occurs during download, and ignore_err is set to True, any errors encountered
        will be transformed into warnings and iBridges will continue to download the remaining
        files.
        By default all errors will stop the process of uploading.
    resc_name : str
        Name of the resource from which data is downloaded, by default the server will decide
    copy_empty_folders : bool
        Create a respective folder for empty colletions.
    options : dict
        More options for the download

    """
    irods_path = IrodsPath(session, irods_path)
    if not irods_path.collection_exists():
        raise ValueError("irods_path must be a collection.")

    source_to_dest = _create_local_dest(irods_path, local_path, copy_empty_folders)

    for source, dest in source_to_dest:
        try:
            _obj_get(session, source, dest, overwrite, resc_name, options)
        except irods.exception.OVERWRITE_WITHOUT_FORCE_FLAG:
            warnings.warn(f'File already exists\tSkipping {source}')
        except KeyError as e:
            if ignore_err is True:
                warnings.warn(f'Download failed: {source}i\n'+repr(e))
            else:
                raise ValueError(f'Download failed: {source}: '+repr(e)) from e

def upload(session: Session, local_path: Union[str, Path], irods_path: Union[str, IrodsPath],
           overwrite: bool = False, ignore_err: bool = False,
           resc_name: str = '', copy_empty_folders: bool = True, options: Optional[dict] = None):
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

    Raises
    ------
    ValueError:
        If the local_path is not a valid filename of directory.
    PermissionError:
        If the iRODS server does not allow the collection or data object to be created.

    """
    local_path = Path(local_path)
    try:
        if local_path.is_dir():
            _upload_collection(session, local_path, irods_path, overwrite, ignore_err,
                               resc_name, copy_empty_folders, options)
        elif local_path.is_file():
            _obj_put(session, local_path, irods_path, overwrite, resc_name, options)
        else:
            raise FileNotFoundError(f"Cannot find local file '{local_path}', check the path.")
    except irods.exception.CUT_ACTION_PROCESSED_ERR as exc:
        raise PermissionError(
            f"During upload operation to '{irods_path}': iRODS server forbids action.") from exc
    except irods.exception.OVERWRITE_WITHOUT_FORCE_FLAG as exc:
        raise FileExistsError(f"Dataset or collection (in) {irods_path} already exists. "
                              "Use overwrite=True to overwrite the existing file(s).") from exc

def download(session: Session, irods_path: Union[str, IrodsPath], local_path: Union[str, Path],
             overwrite: bool = False, ignore_err: bool = False, resc_name: str = '',
             copy_empty_folders: bool = True, options: Optional[dict] = None):
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

    Raises
    ------
    PermissionError:
        If the iRODS server (for whatever reason) forbids downloading the file or
        (part of the) collection.
    ValueError:
        If the irods_path is not pointing to either a collection or a data object.

    """
    irods_path = IrodsPath(session, irods_path)
    local_path = Path(local_path)
    try:
        if irods_path.collection_exists():
            _download_collection(session, irods_path, local_path, overwrite, ignore_err, resc_name,
                                 copy_empty_folders, options)
        elif irods_path.dataobject_exists():
            _obj_get(session, irods_path, local_path, overwrite, resc_name, options)
        else:
            raise ValueError(f"Data object or collection not found: '{irods_path}'")
    except irods.exception.CUT_ACTION_PROCESSED_ERR as exc:
        raise PermissionError(
            f"During download operation from '{irods_path}': iRODS server forbids action."
            ) from exc
    except irods.exception.OVERWRITE_WITHOUT_FORCE_FLAG as exc:
        raise FileExistsError(f"File or directory {local_path} already exists. "
                              "Use overwrite=True to overwrite the existing file(s).") from exc


def create_collection(session: Session,
                      coll_path: Union[IrodsPath, str]) -> irods.collection.iRODSCollection:
    """Create a collection and all collections in its path.

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

    """
    try:
        return session.irods_session.collections.create(str(coll_path))
    except irods.exception.CUT_ACTION_PROCESSED_ERR as exc:
        raise PermissionError(
                f"While creating collection at '{coll_path}': iRODS server forbids action."
              ) from exc


def perform_operations(session: Session, operations: dict, ignore_err: bool=False):
    """Perform data operations.

    Parameters
    ----------
    session
        Session to do the data operations for.
    operations
        Dictionary containing the operations to perform.
    ignore_err
        Ignore any errors and convert them into warnings if True.

    """
    up_sizes = [lpath.stat().st_size for lpath, _ in operations["upload"]]
    down_sizes = [ipath.size for ipath, _ in operations["download"]]
    # pbar = tqdm(total=sum(up_sizes) + sum(down_sizes), unit="MiB",
                # bar_format="{desc}: {percentage:3.0f}% {n_fmt:.3f}/{total_fmt:.3f} "
                # "[{elapsed}<{remaining}, {rate_fmt}{postfix}]")
    pbar = tqdm(total=sum(up_sizes) + sum(down_sizes), unit="B", unit_scale=True, unit_divisor=1024)

    # print(operations["upload"])
    for col in operations["create_collection"]:
        IrodsPath.create_collection(session, col)
    for curdir in operations["create_dir"]:
        Path(curdir).mkdir(parents=True, exist_ok=True)
    for (lpath, ipath), size in zip(operations["upload"], up_sizes):
        upload(session, lpath, ipath, overwrite=True, ignore_err=ignore_err)
        pbar.update(size)
    for (ipath, lpath), size in zip(operations["download"], down_sizes):
        download(session, ipath, lpath, overwrite=True, ignore_err=ignore_err)
        pbar.update(size)
