"""
'sync' synchronizes the data between a local copy (local file system) and the copy stored in
iRODS. The command can be in one of the two modes: synchronization of data from the client's
local file system to iRODS, or from iRODS to the local file system. It broadly mirros the
behaviour of the irsync module of the icommands command line tool.
"""

from __future__ import annotations
import os
import base64
# import logging
from typing import Union, NamedTuple
from pathlib import Path
from hashlib import sha256
from tqdm import tqdm
from irods.collection import iRODSCollection
from ibridges import Session
from ibridges.utils.path import IrodsPath
from ibridges.irodsconnector.data_operations import get_collection, get_dataobject, \
    create_collection, upload, download

class FileObject(NamedTuple):
    """ 
    Object to hold attributes from local and remote files.
    """
    name: str
    path: str
    size: int
    checksum: Union[str, None]

class FolderObject:
    """ 
    Object to hold attributes from local and remote folders/collections.
    
    ...
    
    Attributes
    ----------
    path : str
        Path, relative to source or target root
    n_files : int
        Number of files in folder
    n_folders : int
        Number of subfolders in folder    

    Methods
    -------
    is_empty()
        Check whether folder is empty.
    """

    path=''
    n_files=0
    n_folders=0

    def __init__(self,
                 path: str,
                 n_files: int,
                 n_folders: int) -> None:
        self.path=path
        self.n_files=n_files
        self.n_folders=n_folders

    def is_empty(self):
        """ Check to see if folder has anything (files or subfolders) in it. """
        return (self.n_files+self.n_folders)==0

    def __repr__(self):
        return f"{self.__class__.__name__}(path='{self.path}', n_files={self.n_files}, \
            n_folders={self.n_folders})"

    def __eq__(self, other: object):
        if not isinstance(other, FolderObject):
            return NotImplemented

        return self.path==other.path

    def __hash__(self):
        return hash(self.path)

# log=logging.getLogger()
# log.setLevel(logging.INFO)

def sync(session: Session,   #pylint: disable=too-many-arguments
         source: Union[str, Path, IrodsPath],
         target: Union[str, Path, IrodsPath],
         max_level: Union[int, None] = None,
         dry_run: bool = False,
         ignore_checksum: bool = False,
         copy_empty_folders: bool = False,
         verify_checksum: bool = True) -> None:

    """  
    Synchronize the data between a local copy (local file system) and the copy stored in iRODS. The
    command can be in one of the two modes: synchronization of data from the client's local file
    system to iRODS, or from iRODS to the local file system. The mode is determined by the type of
    the values for `source` and `target` (IrodsPath or str/Path).

    
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
    ignore_checksum : bool, default False
        If set to True, only the file size is used for determining whether synchronization is
        needed, rather than size and checksum value. This mode gives a potentially faster
        operation but the result is less accurate.
    copy_empty_folders : bool, default False
        Controls whether folders/collections that contain no files or  subfolders/subcollections
        will be synchronized.
    verify_checksum : bool, default True
        Calculate and verify the checksum on files after up- or downloading. A checksum mismatch
        will generate an error, but will not abort the  synchronization process.
    """

    if not isinstance(source, IrodsPath) and not isinstance(target, IrodsPath):
        raise TypeError("Either source or target should be an iRODS path.")

    if isinstance(source, IrodsPath) and isinstance(target, IrodsPath):
        raise TypeError("iRODS to iRODS copying is not supported.")

    # log.info("Syncing '%s' --> '%s'%s", source, target, ' (dry run)' if dry_run else '')

    if isinstance(source, IrodsPath):
        if not source.collection_exists():
            raise ValueError(f"Source collection '{source.absolute_path()}' does not exist")
        src_files, src_folders=_get_irods_tree(
            coll=get_collection(session=session, path=source),
            max_level=max_level,
            ignore_checksum=ignore_checksum)
    else:
        if not Path(source).is_dir():
            raise ValueError(f"Source folder '{source}' does not exist")
        src_files, src_folders=_get_local_tree(
            path=Path(source),
            max_level=max_level,
            ignore_checksum=ignore_checksum)

    if isinstance(target, IrodsPath):
        if not target.collection_exists():
            raise ValueError(f"Target collection '{target.absolute_path()}' does not exist")
        tgt_files, tgt_folders=_get_irods_tree(
            coll=get_collection(session=session, path=target),
            max_level=max_level,
            ignore_checksum=ignore_checksum)
    else:
        if not Path(target).is_dir():
            raise ValueError(f"Target folder '{target}' does not exist")
        tgt_files, tgt_folders=_get_local_tree(
            path=Path(target),
            max_level=max_level,
            ignore_checksum=ignore_checksum)

    folders_diff=sorted(
        set(src_folders).difference(set(tgt_folders)),
        key=lambda x: (x.path.count('/'), x.path))

    files_diff=sorted(
        set(src_files).difference(set(tgt_files)),
        key=lambda x: (x.path.count('/'), x.path))

    if isinstance(target, IrodsPath):
        _create_irods_collections(
            session=session,
            target=target,
            collections=folders_diff,
            dry_run=dry_run,
            copy_empty_folders=copy_empty_folders)
        _copy_local_to_irods(
            session=session,
            source=Path(source),
            target=target,
            files=files_diff,
            dry_run=dry_run,
            verify_checksum=verify_checksum)
    else:
        _create_local_folders(
            target=Path(target),
            folders=folders_diff,
            dry_run=dry_run,
            copy_empty_folders=copy_empty_folders)
        _copy_irods_to_local(
            session=session,
            source=source,
            target=Path(target),
            objects=files_diff,
            dry_run=dry_run,
            verify_checksum=verify_checksum)

def _calc_checksum(filepath):
    f_hash=sha256()
    memv=memoryview(bytearray(128*1024))
    with open(filepath, 'rb', buffering=0) as file:
        for item in iter(lambda : file.readinto(memv), 0):
            f_hash.update(memv[:item])
    return f"sha2:{str(base64.b64encode(f_hash.digest()), encoding='utf-8')}"

def _get_local_tree(path: Path,
                    max_level: Union[int, None] = None,
                    ignore_checksum: bool = False):

    # change all sep into /, regardless of platform, for easier comparison
    def fix_local_path(path: str):
        return "/".join(path.split(os.sep))

    objects=[]
    collections=[]

    for root, dirs, files in os.walk(path):
        for file in files:
            full_path=Path(root) / file
            rel_path=str(full_path)[len(str(path)):].lstrip(os.sep)
            if max_level is None or rel_path.count(os.sep)<max_level:
                objects.append(FileObject(
                    name=file,
                    path=fix_local_path(rel_path),
                    size=full_path.stat().st_size,
                    checksum=None if ignore_checksum else _calc_checksum(full_path)))

        collections.extend([FolderObject(
                fix_local_path(str(Path(root) / dir)[len(str(path)):].lstrip(os.sep)),
                len([x for x in Path(f"{root}{os.sep}{dir}").iterdir() if x.is_file()]),
                len([x for x in Path(f"{root}{os.sep}{dir}").iterdir() if x.is_dir()])
            )
            for dir in dirs if max_level is None or dir.count(os.sep)<max_level-1])

    return objects, collections

def _get_irods_tree(coll: iRODSCollection,
                    root: str = '',
                    level: int = 0,
                    max_level: Union[int, None] = None,
                    ignore_checksum: bool = False):

    root=coll.path if len(root)==0 else root

    # chksum() (re)calculates checksum, call only when checksum is empty
    objects=[FileObject(
        x.name,
        x.path[len(root):].lstrip('/'),
        x.size,
        None if ignore_checksum else (x.checksum if len(x.checksum)>0 else x.chksum()))
        for x in coll.data_objects]

    if max_level is None or level<max_level-1:
        collections=[FolderObject(
            x.path[len(root):].lstrip('/'),
            len(x.data_objects),
            len(x.subcollections)) for x in coll.subcollections]

        for subcoll in coll.subcollections:
            subobjects, subcollections=_get_irods_tree(
                coll=subcoll,
                root=root,
                level=level+1,
                max_level=max_level,
                ignore_checksum=ignore_checksum
                )
            objects.extend(subobjects)
            collections.extend(subcollections)
    else:
        collections=[]

    return objects, collections

def _create_irods_collections(session: Session,
                              target: IrodsPath,
                              collections: list[FolderObject],
                              dry_run: bool,
                              copy_empty_folders: bool):
    if dry_run:
        print("Will create collection(s):")

    for collection in collections:
        if collection.is_empty() and not copy_empty_folders:
            continue

        full_path=target / collection.path

        if dry_run:
            print(f"  {full_path} {collection.n_files}/{collection.n_folders}")
        else:
            _=create_collection(session, str(full_path))

def _create_local_folders(target: Path,
                          folders: list[FolderObject],
                          dry_run: bool,
                          copy_empty_folders: bool):
    if dry_run:
        print("Will create folder(s):")

    for folder in folders:
        if folder.is_empty() and not copy_empty_folders:
            continue

        full_path=target / Path(folder.path)

        if dry_run:
            print(f"  {full_path}")
        else:
            full_path.mkdir(parents=True, exist_ok=True)

def _copy_local_to_irods(session: Session,
                         source: Path,
                         target: IrodsPath,
                         files: list[FileObject],
                         dry_run: bool,
                         verify_checksum: bool) -> None:  #pylint: disable=too-many-arguments
    if dry_run:
        print(f"Will upload from '{source}' to '{target}':")
    else:
        pbar=tqdm(desc='Uploading', total=sum(x.size for x in files))

    for file in files:
        source_path=Path(source) / file.path
        target_path=str(target / file.path)
        if dry_run:
            print(f"  {file.path}  {file.size}")
        else:
            try:
                upload(session=session,
                       local_path=source_path,
                       irods_path=target_path,
                       overwrite=True)
                if verify_checksum:
                    obj=get_dataobject(session, target_path)
                    if file.checksum != \
                            (obj.checksum if len(obj.checksum)>0 else obj.chksum()):
                        # log.warning("Checksum mismatch after upload: '%s'", target_path)
                        print("WARNING: Checksum mismatch after upload: '%s'", target_path)
                pbar.update(file.size)
            except Exception as err:
                # log.error("Error uploading '%s': %s", source_path, repr(err))
                print("ERROR: Uploading '%s' failed: %s", source_path, repr(err))

def _copy_irods_to_local(session: Session,
                         source: IrodsPath,
                         target: Path,
                         objects: list[FileObject],
                         dry_run: bool,
                         verify_checksum: bool) -> None:  #pylint: disable=too-many-arguments
    if dry_run:
        print(f"Will download from '{source}' to '{target}':")
    else:
        pbar=tqdm(desc='Downloading', total=sum(x.size for x in objects))

    for obj in objects:
        target_path=Path(target) / obj.path
        source_path=str(source / obj.path)
        if dry_run:
            print(f"  {obj.path}  {obj.size}")
        else:
            try:
                download(session=session,
                         irods_path=source_path,
                         local_path=target_path,
                         overwrite=True)
                if verify_checksum and obj.checksum != _calc_checksum(target_path):
                    # log.warning("Checksum mismatch after download: '%s'", target_path)
                    print("WARNING: Checksum mismatch after upload: '%s'", target_path)
                pbar.update(obj.size)
            except Exception as err:
                # log.error("Error downloading '%s': %s", source_path, repr(err))
                print("ERROR: Downloading '%s' failed: %s", source_path, repr(err))
