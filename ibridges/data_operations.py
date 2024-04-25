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
from irods.models import DataObject

import ibridges.icat_columns as icat
from ibridges.path import IrodsPath
from ibridges.session import Session

NUM_THREADS = 4

def get_dataobject(session: Session,
                   path: Union[str, IrodsPath]) -> irods.data_object.iRODSDataObject:
    """Instantiate an iRODS data object.

    Parameters
    ----------
    session :
        Session with connection to the server to get the data object from.
    path : str
        Name of an iRODS data object.

    Raises
    ------
    ValueError:
        If the path is pointing to a collection and not a data object.

    Returns
    -------
    iRODSDataObject
        Instance of the data object with `path`.

    """
    path = IrodsPath(session, path)
    if path.dataobject_exists():
        return session.irods_session.data_objects.get(str(path))
    if path.collection_exists():
        raise ValueError("Error retrieving data object, path is linked to a collection."
                         " Use get_collection instead to retrieve the collection.")

    raise irods.exception.DataObjectDoesNotExist(path)

def get_collection(session: Session,
                   path: Union[str, IrodsPath]) -> irods.collection.iRODSCollection:
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
    path = IrodsPath(session, path)
    if path.collection_exists():
        return session.irods_session.collections.get(str(path))
    if path.dataobject_exists():
        raise ValueError("Error retrieving collection, path is linked to a data object."
                         " Use get_dataobject instead to retrieve the data object.")
    raise irods.exception.CollectionDoesNotExist(path)

def obj_replicas(obj: irods.data_object.iRODSDataObject) -> list[tuple[int, str, str, int, str]]:
    """Retrieve information about replicas (copies of the file on different resources).

    It does so for a data object in the iRODS system.

    Parameters
    ----------
    obj : irods.data_object.iRODSDataObject
        The data object

    Returns
    -------
    list(tuple(int, str, str, int, str)):
        List with tuple where each tuple contains replica index/number, resource name on which
        the replica is stored about one replica, replica checksum, replica size,
        replica status of the replica

    """
    #replicas = []
    repl_states = {
        '0': 'stale',
        '1': 'good',
        '2': 'intermediate',
        '3': 'write-locked'
    }

    replicas = [(r.number, r.resource_name, r.checksum,
                 r.size, repl_states.get(r.status, r.status)) for r in obj.replicas]

    return replicas

def is_dataobject(item) -> bool:
    """Determine if item is an iRODS data object."""
    return isinstance(item, irods.data_object.iRODSDataObject)

def is_collection(item) -> bool:
    """Determine if item is an iRODS collection."""
    return isinstance(item, irods.collection.iRODSCollection)

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
                       options: Optional[dict] = None):
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
    options : dict
        More options for the upload

    """
    local_path = Path(local_path)
    irods_path = IrodsPath(session, irods_path)
    # get all files and their relative path to local_path
    if not local_path.is_dir():
        raise ValueError("local_path must be a directory.")
    
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

def _create_local_dest(session: Session, irods_path: IrodsPath, local_path: Path
                       ) -> list[tuple[IrodsPath, Path]]:
    """Assembles the local destination paths for download of a collection."""
    # get all data objects
    coll = get_collection(session, irods_path)
    subcolls = _get_subcoll_paths(session, coll)
    all_objs = _get_data_objects(session, coll)

    # create all folders from collections including empty ones
    folders = [local_path.joinpath(coll.name, *sc.relative_to(irods_path).parts)
               for sc in subcolls]
    for folder in folders:
        folder.mkdir(parents=True, exist_ok=True)

    download_path = local_path.joinpath(irods_path.name.lstrip('/'))
    source_to_dest: list[tuple[IrodsPath, Path]] = []
    for subcoll_path, obj_name, _, _ in all_objs:
        cur_ipath = IrodsPath(session, subcoll_path, obj_name)
        cur_lpath = (download_path / IrodsPath(session, subcoll_path).relative_to(irods_path)
                                   / obj_name)
        source_to_dest.append((cur_ipath, cur_lpath))
    return source_to_dest


def _download_collection(session: Session, irods_path: Union[str, IrodsPath], local_path: Path,
                         overwrite: bool = False, ignore_err: bool = False, resc_name: str = '',
                         options: Optional[dict] = None):
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
    options : dict
        More options for the download

    """
    irods_path = IrodsPath(session, irods_path)
    if not irods_path.collection_exists():
        raise ValueError("irods_path must be a collection.")

    source_to_dest = _create_local_dest(session, irods_path, local_path)

    for source, dest in source_to_dest:
        # ensure local folder exists
        if not dest.parent.is_dir():
            os.makedirs(dest.parent)
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
           resc_name: str = '', options: Optional[dict] = None):
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
                               resc_name, options)
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
             options: Optional[dict] = None):
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
                                 options)
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

def get_size(session: Session, item: Union[irods.data_object.iRODSDataObject,
                               irods.collection.iRODSCollection]) -> int:
    """Collect the sizes of a data object or a collection.

    Parameters
    ----------
    session :
        Session with the connection to the item.
    item : iRODSDataObject or iRODSCollection
        Collection or data object to get the size of.

    Returns
    -------
    int :
        Total size [bytes] of the iRODS object or all iRODS objects in the collection.

    """
    if is_dataobject(item):
        return item.size
    all_objs = _get_data_objects(session, item)
    return sum(size for _, _, size, _ in all_objs)

def _get_data_objects(session: Session,
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

def _get_subcoll_paths(session: Session,
                     coll: irods.collection.iRODSCollection) -> list:
    """
    Retrieves all sub collections in a sub tree starting at coll and returns ther IrodsPaths.
    """
    coll_query = session.irods_session.query(icat.COLL_NAME)
    coll_query = coll_query.filter(icat.LIKE(icat.COLL_NAME, coll.path+"/%"))

    return [IrodsPath(session, p) for r in coll_query.get_results() for p in r.values()]

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
