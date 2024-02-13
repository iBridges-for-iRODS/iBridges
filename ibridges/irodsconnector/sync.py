import os
import base64
import logging
from tqdm import tqdm
from pathlib import Path
from hashlib import sha256
from ibridges.utils.path import IrodsPath
from ibridges.irodsconnector.data_operations import get_collection, get_dataobject, create_collection, upload, download

"""
Synchronize the data between a local copy (local file system) and
the copy stored in iRODS. The command can be  in one of the two 
modes: synchronization of data from the client's local file system
to iRODS, or from iRODS to the local file system. The mode is determined
by the type of the values for `source` and `target` (IrodsPath or str/Path).

Source and target must be an existing local folder, and an existing 
iRODS collection. An exception will be raised if either doesn't exist.

The command compares the checksum values and file sizes of the source
and target files to determine whether synchronization is needed. If 
the `ignore_checksum` option is set to True, only the file size
(instead of the the size and checksum value) is used for determining 
whether synchronization is needed. This mode gives a potentially faster
operation but the result is less accurate.
 
The `max_level` option controls the depth up to which the file tree will
be synchronized. With `max_level` set to None (default), there is no limit
(full recursive synchronization). A max level of 1 synchronizes only the
source's root, max level 2 also includes the first set of 
subfolders/subcollections and their contents, etc.

The `copy_empty_folders` option controls whether folders/collections that
contain no files or subfolders/subcollections will b synchronized (default
False).

The `dry_run` option lists all the source files and folders that need to
be synchronized without actually doing the synchronization.

The `verify_checksum` option will calculate and verify the checksum on the
data after up- or downloading. A checksum mismatch will generate an error,
but will not abort the synchronization process (default True).

Lastly, `session` requires an authorized instance of `ibridges.Session`.

"""

class FileObject:

    def __init__(self, name, path, size, checksum, ignore_checksum=False) -> None:
        self.name=name
        self.path=path
        self.size=size
        self.checksum=checksum
        self.ignore_checksum=ignore_checksum

    def __repr__(self):
        return f"{self.__class__.__name__}(name='{self.name}', path='{self.path}', size={self.size}, checksum='{self.checksum}, ignore_checksum={self.ignore_checksum})"

    def __eq__(self, other):
        if not isinstance(self,type(other)):
            return False

        if self.ignore_checksum:
            return self.name==other.name \
                and self.path==other.path \
                and self.size==other.size

        return self.name==other.name \
            and self.path==other.path \
            and self.size==other.size \
            and self.checksum==other.checksum

    def __hash__(self):
        if self.ignore_checksum:
            return hash((self.name, self.path, self.size))

        return hash((self.name, self.path, self.size, self.checksum))

class FolderObject:

    def __init__(self, path, n_files, n_folders) -> None:
        self.path=path            # path (relative to source or target root)
        self.n_files=n_files      # number of files in folder
        self.n_folders=n_folders  # number of subfolders in folder

    def is_empty(self):
        return (self.n_files+self.n_folders)==0

    def __repr__(self):
        return f"{self.__class__.__name__}(path='{self.path}', n_files={self.n_files}, n_folders={self.n_folders})"

    def __eq__(self, other):
        if not isinstance(self,type(other)):
            return False

        return self.path==other.path

    def __hash__(self):
        return hash(self.path)

log=logging.getLogger()
log.setLevel(logging.INFO)

def sync(session,
         source,
         target,
         max_level=None,
         dry_run=False,
         ignore_checksum=False,
         copy_empty_folders=False,
         verify_checksum=True) -> None:  

    assert isinstance(source, IrodsPath) or isinstance(target, IrodsPath), "Either source or target should be an iRODS path."
    assert not (isinstance(source, IrodsPath) and isinstance(target, IrodsPath)), "iRODS to iRODS copying is not supported."

    log.info(f"Syncing '{source}' --> '{target}'{' (dry run)' if dry_run else ''}")

    if isinstance(source, IrodsPath):
        assert source.collection_exists(), \
            "Source collection '%s' does not exist" % source.absolute_path()
        src_files, src_folders=_get_irods_tree(
            coll=get_collection(session=session, path=source),
            max_level=max_level,
            ignore_checksum=ignore_checksum)
    else:
        assert Path(source).is_dir(), "Source folder '%s' does not exist" % source
        src_files, src_folders=_get_local_tree(
            path=source,
            max_level=max_level,
            ignore_checksum=ignore_checksum)

    if isinstance(target, IrodsPath):
        assert target.collection_exists(), \
            "Target collection '%s' does not exist" % target.absolute_path()
        tgt_files, tgt_folders=_get_irods_tree(
            coll=get_collection(session=session, path=target),
            max_level=max_level,
            ignore_checksum=ignore_checksum)
    else:
        assert Path(target).is_dir(), "Target folder '%s' does not exist" % target
        tgt_files, tgt_folders=_get_local_tree(
            path=target,
            max_level=max_level,
            ignore_checksum=ignore_checksum)

    # compares the relative paths
    folders_diff=sorted(
        set(src_folders).difference(set(tgt_folders)), 
        key=lambda x: (x.path.count('/'), x.path))

    # compares the checksum, file size, file name & relative path
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
            source=source, 
            target=target, 
            files=files_diff,
            dry_run=dry_run, 
            verify_checksum=verify_checksum)
    else:
        _create_local_folders(
            target=target,
            folders=folders_diff,
            dry_run=dry_run,
            copy_empty_folders=copy_empty_folders)
        _copy_irods_to_local(
            session=session, 
            source=source, 
            target=target, 
            objects=files_diff,
            dry_run=dry_run, 
            verify_checksum=verify_checksum)

def _calc_checksum(filepath):
    h=sha256()
    mv=memoryview(bytearray(128*1024))
    with open(filepath, 'rb', buffering=0) as f:
        for n in iter(lambda : f.readinto(mv), 0):
            h.update(mv[:n])
    return f"sha2:{str(base64.b64encode(h.digest()), encoding='utf-8')}"

def _get_local_tree(path, max_level=None, ignore_checksum=False):    

    def fix_local_path(path):
        return "/".join(path.split(os.sep))

    objects=[]
    collections=[]

    for root, dirs, files in os.walk(path):
        for file in files:
            full_path=Path(f"{root}{os.sep}{file}")
            rel_path=str(full_path)[len(str(path)):].lstrip(os.sep)
            if max_level is None or rel_path.count(os.sep)<max_level:
                objects.append(FileObject(
                    name=file, 
                    path=fix_local_path(rel_path),
                    size=full_path.stat().st_size,
                    checksum=_calc_checksum(full_path),
                    ignore_checksum=ignore_checksum))

        collections.extend([FolderObject(
                fix_local_path(f"{root}{os.sep}{dir}"[len(str(path)):].lstrip(os.sep)),
                len([x for x in Path(f"{root}{os.sep}{dir}").iterdir() if x.is_file()]),
                len([x for x in Path(f"{root}{os.sep}{dir}").iterdir() if x.is_dir()])
            )
            for dir in dirs if max_level is None or dir.count(os.sep)<max_level-1])

    return objects, collections

def _get_irods_tree(coll, root=None, level=0, max_level=None, ignore_checksum=False):
    
    root=coll.path if root is None else root

    # chksum() (re)calculates checksum, call only when checksum is empty
    objects=[FileObject(
        x.name,
        x.path[len(root):].lstrip('/'),
        x.size,
        x.checksum if len(x.checksum)>0 else x.chksum(),
        ignore_checksum) for x in coll.data_objects]

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

def _create_irods_collections(session, target, collections, dry_run, copy_empty_folders):
    if dry_run:
        print("Will create collection(s):")
    else:
        pbar=tqdm(desc='Creating collections', total=len([x for x in collections if copy_empty_folders or not x.is_empty()]))

    for collection in collections:
        if collection.is_empty() and not copy_empty_folders:
            continue

        full_path=target / collection.path

        if dry_run:
            print(f"  {full_path}")
        else:
            _=create_collection(session, str(full_path))
            pbar.update(1)

def _create_local_folders(target, folders, dry_run, copy_empty_folders):
    if dry_run:
        print("Will create folder(s):")
    else:
        pbar=tqdm(desc='Creating folders', total=len([x for x in folders if copy_empty_folders or not x.is_empty()]))

    for folder in folders:
        if folder.is_empty() and not copy_empty_folders:
            continue

        full_path=Path(target) / Path(folder.path)

        if dry_run:
            print(f"  {full_path}")
        else:
            full_path.mkdir(parents=True, exist_ok=True)
            pbar.update(1)

def _copy_local_to_irods(session, source, target, files, dry_run, verify_checksum):
    if dry_run:
        print(f"Will upload from '{source}' to '{target}':")
    else:
        pbar=tqdm(desc='Uploading', total=sum([x.size for x in files]))

    for file in files:
        source_path=Path(source) / file.path
        target_path=str(target / file.path)
        if dry_run:
            print(f"  {file.path}  {file.size}")
        else:
            try:
                upload(session=session, local_path=source_path, irods_path=target_path, overwrite=True)
                if verify_checksum:
                    object=get_dataobject(session, target_path)
                    if file.checksum != (object.checksum if len(object.checksum)>0 else object.chksum()):
                        log.warning(f"Checksum mismatch after upload: '{target_path}'")
                pbar.update(file.size)
            except Exception as e:
                log.error(f"Error uploading '{source_path}': {repr(e)}")

def _copy_irods_to_local(session, source, target, objects, dry_run, verify_checksum):
    if dry_run:
        print(f"Will download from '{source}' to '{target}':")
    else:
        pbar=tqdm(desc='Downloading', total=sum([x.size for x in objects]))

    for object in objects:
        target_path=Path(target) / object.path
        source_path=str(source / object.path)
        if dry_run:
            print(f"  {object.path}  {object.size}")
        else:
            try:
                download(session=session, irods_path=source_path, local_path=target_path, overwrite=True)
                if verify_checksum and object.checksum != _calc_checksum(target_path):
                    log.warning(f"Checksum mismatch after download: '{target_path}'")
                pbar.update(object.size)
            except Exception as e:
                log.error(f"Error downloading from '{source_path}': {repr(e)}")