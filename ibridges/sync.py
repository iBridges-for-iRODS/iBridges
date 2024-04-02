"""Synchronize data between local and remote copies.

'sync' synchronizes the data between a local copy (local file system) and the copy stored in
iRODS. The command can be in one of the two modes: synchronization of data from the client's
local file system to iRODS, or from iRODS to the local file system. It broadly mirros the
behaviour of the irsync module of the icommands command line tool.
"""

from __future__ import annotations

import base64
import os
from hashlib import sha256
from pathlib import Path
from typing import NamedTuple, Optional, Union

from irods.collection import iRODSCollection
from tqdm import tqdm

from ibridges.data_operations import (
    create_collection,
    download,
    get_collection,
    get_dataobject,
    upload,
)
from ibridges.path import IrodsPath
from ibridges.session import Session


class FileObject(NamedTuple):
    """Object to hold attributes from local and remote files."""

    name: str
    path: str
    size: int
    checksum: str

class FolderObject:
    """Object to hold attributes from local and remote folders/collections."""

    def __init__(self,
                 path: str = '',
                 n_files: int = 0,
                 n_folders: int = 0) -> None:
        """Initialize FolderObject.

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
        self.path=path
        self.n_files=n_files
        self.n_folders=n_folders

    def is_empty(self):
        """Check to see if folder has anything (files or subfolders) in it."""
        return (self.n_files+self.n_folders)==0

    def __repr__(self):
        """Give a nicer representation for debug purposes."""
        return f"{self.__class__.__name__}(path='{self.path}', n_files={self.n_files}, \
            n_folders={self.n_folders})"

    def __eq__(self, other: object):
        """Check whether two folders (paths) are the same."""
        if not isinstance(other, FolderObject):
            return NotImplemented

        return self.path==other.path

    def __hash__(self):
        """Hash the path as a hash for the folder."""
        return hash(self.path)

def sync_data(session: Session,
         source: Union[str, Path, IrodsPath],
         target: Union[str, Path, IrodsPath],
         max_level: Optional[int] = None,
         dry_run: bool = False,
         copy_empty_folders: bool = False) -> dict:
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
    copy_empty_folders : bool, default False
        Controls whether folders/collections that contain no files or  subfolders/subcollections
        will be synchronized.


    Returns
    -------
        A dict object containing two keys: 'changed_folders' and 'changed_files'.
        These contain lists of changed folders and files, respectively
        (or of to-be-changed folders and files, when in dry-run mode).
    """
    _param_checks(source, target)

    if isinstance(source, IrodsPath):
        if not source.collection_exists():
            raise ValueError(f"Source collection '{source.absolute_path()}' does not exist")
        src_files, src_folders=_get_irods_tree(
            coll=get_collection(session=session, path=source),
            max_level=max_level)
    else:
        if not Path(source).is_dir():
            raise ValueError(f"Source folder '{source}' does not exist")
        src_files, src_folders=_get_local_tree(
            path=Path(source),
            max_level=max_level)

    if isinstance(target, IrodsPath):
        if not target.collection_exists():
            raise ValueError(f"Target collection '{target.absolute_path()}' does not exist")
        tgt_files, tgt_folders=_get_irods_tree(
            coll=get_collection(session=session, path=target),
            max_level=max_level)
    else:
        if not Path(target).is_dir():
            raise ValueError(f"Target folder '{target}' does not exist")
        tgt_files, tgt_folders=_get_local_tree(
            path=Path(target),
            max_level=max_level)

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
            dry_run=dry_run)
    else:
        _create_local_folders(
            target=Path(target),
            folders=folders_diff,
            dry_run=dry_run,
            copy_empty_folders=copy_empty_folders)
        _copy_irods_to_local(
            session=session,
            source=source,  # type: ignore
            target=Path(target),
            objects=files_diff,
            dry_run=dry_run)
    return {'changed_folders': folders_diff, 'changed_files': files_diff}

def _param_checks(source, target):
    if not isinstance(source, IrodsPath) and not isinstance(target, IrodsPath):
        raise TypeError("Either source or target should be an iRODS path.")

    if isinstance(source, IrodsPath) and isinstance(target, IrodsPath):
        raise TypeError("iRODS to iRODS copying is not supported.")

def _calc_checksum(filepath):
    f_hash=sha256()
    memv=memoryview(bytearray(128*1024))
    with open(filepath, 'rb', buffering=0) as file:
        for item in iter(lambda : file.readinto(memv), 0):
            f_hash.update(memv[:item])
    return f"sha2:{str(base64.b64encode(f_hash.digest()), encoding='utf-8')}"

def _get_local_tree(path: Path,
                    max_level: Optional[int] = None):

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
                    checksum=_calc_checksum(full_path)))

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
                    max_level: Optional[int] = None):

    root=coll.path if len(root)==0 else root

    # chksum() (re)calculates checksum, call only when checksum is empty
    objects=[FileObject(
        x.name,
        x.path[len(root):].lstrip('/'),
        x.size,
        x.checksum if len(x.checksum)>0 else x.chksum())
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
                max_level=max_level)
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
    new_colls=[str(target / x.path) for x in collections if not x.is_empty() or copy_empty_folders]
    if dry_run:
        print("Will create collection(s):")
        print(*[f"  {x}" for x in new_colls], sep='\n')
        return
    for coll in new_colls:
        create_collection(session, coll)

def _create_local_folders(target: Path,
                          folders: list[FolderObject],
                          dry_run: bool,
                          copy_empty_folders: bool):
    new_folders=[target / Path(x.path) for x in folders if not x.is_empty() or copy_empty_folders]
    if dry_run:
        print("Will create folder(s):")
        print(*[f"  {x}" for x in new_folders], sep='\n')
        return
    for folder in new_folders:
        folder.mkdir(parents=True, exist_ok=True)

def _copy_local_to_irods(session: Session,
                         source: Path,
                         target: IrodsPath,
                         files: list[FileObject],
                         dry_run: bool) -> None:
    if dry_run:
        print(f"Will upload from '{source}' to '{target}':")
        print(*[f"  {x.path}  {x.size}" for x in files], sep='\n')
        return

    if len(files)==0:
        return

    pbar=tqdm(desc='Uploading', total=sum(x.size for x in files))
    for file in files:
        source_path=Path(source) / file.path
        target_path=str(target / file.path)
        try:
            upload(session=session,
                    local_path=source_path,
                    irods_path=target_path,
                    overwrite=True)
            obj=get_dataobject(session, target_path)
            if file.checksum != \
                    (obj.checksum if len(obj.checksum)>0 else obj.chksum()):
                raise ValueError(f"Checksum mismatch after upload: '{target_path}'")

            pbar.update(file.size)
        except Exception as err:
            raise ValueError(f"Uploading '{source_path}' failed: {repr(err)}") from err

def _copy_irods_to_local(session: Session,
                         source: IrodsPath,
                         target: Path,
                         objects: list[FileObject],
                         dry_run: bool) -> None:
    if dry_run:
        print(f"Will download from '{source}' to '{target}':")
        print(*[f"  {x.path}  {x.size}" for x in objects], sep='\n')
        return

    if len(objects)==0:
        return

    pbar=tqdm(desc='Downloading', total=sum(x.size for x in objects))
    for obj in objects:
        target_path=Path(target) / obj.path
        source_path=str(source / obj.path)
        try:
            download(session=session,
                        irods_path=source_path,
                        local_path=target_path,
                        overwrite=True)
            if obj.checksum != _calc_checksum(target_path):
                raise ValueError(f"Checksum mismatch after download: '{source_path}'")

            pbar.update(obj.size)
        except Exception as err:
            raise ValueError(f"Downloading '{source_path}' failed: {repr(err)}") from err
