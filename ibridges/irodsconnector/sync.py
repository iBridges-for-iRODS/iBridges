import base64
import os
import logging
from pathlib import Path
from hashlib import sha256
from ibridges.utils.path import IrodsPath
from ibridges.irodsconnector.data_operations import get_collection, create_collection, upload, download
from pprint import pprint


# now just doing folder --> collection (and vv), not files, --> collection. do that too?
# what to do if the target (does not) exists? create & copy or fail (if not), copy to tagregt/source or copy content (if does exist)

# not doing:
#   --link - ignore symlink --> can we make that default?
#   -a   synchronize to all replicas if the target is an iRODS dataobject/collection.
#   --age age_in_minutes - The maximum age of the source copy in minutes for sync.

# do we want to support sync iRODS -> iRODS?

"""
Usage: irsync [-rahKsvV] [-N numThreads] [-R resource] [--link] [--age age_in_minutes]
          sourceFile|sourceDirectory [....] targetFile|targetDirectory
 
Synchronize the data between a local copy (local file system) and
the copy stored in iRODS or between two iRODS copies. The command can be 
in one of the three modes  : synchronization of data from the client's
local file system to iRODS, from iRODS to the local file system, or from
one iRODS path to another iRODS path. The mode is determined by
the way the sourceFile|sourceDirectory and targetFile|targetDirectory are
specified. Files and directories prepended with 'i:' are iRODS files and
collections. Local files and directories are specified without any prefix.
For example, the command:
 
     irsync -r foo1 i:foo2
 
synchronizes recursively the data from the local directory
foo1 to the iRODS collection foo2 and the command:
 
     irsync -r i:foo1 foo2
 
synchronizes recursively the data from the iRODS collection
foo1 to the local directory foo2.
 
     irsync -r i:foo1 i:foo2
 
synchronizes recursively the data from the iRODS collection foo1 to another
iRODS collection foo2.
 
The command compares the checksum values and file sizes of the source
and target files to determine whether synchronization is needed. Therefore,
the command will run faster if the checksum value for the specific iRODS file,
no matter whether it is a source or target, already exists and is registered
with iCAT. This can be achieved by using the -k or -K options of the iput
command at the time of  ingestion, or by using the ichksum command after the
data have already been ingested into iRODS.
If the -s option is used, only the file size (instead of the the size and
checksum value) is used for determining whether synchronization is needed.
This mode gives a faster operation but the result is less accurate.
 
The command accepts multiple sourceFiles|sourceDirectories and a single
targetFile|targetDirectory. It pretty much follows the syntax of the UNIX
cp command with one exception- irsync of a single source directory to a 
single target directory. In UNIX, the command:
 
     cp -r foo1 foo2
 
has a different meaning depending on whether the target directory foo2 
exists. If the target directory exists, the content of source directory foo1
is copied to the target directory foo2/foo1. But if the target directory
does not exist, the content is copied to the target directory foo2.
 
With the irsync command,
 
     irsync -r foo1 i:foo2
 
always means the synchronization of the local directory foo1 to collection
foo2, no matter whether foo2 exists.
 
 -K  verify checksum - calculate and verify the checksum on the data
 -N  numThreads - the number of threads to use for the transfer. A value of
       0 means no threading. By default (-N option not used) the server
       decides the number of threads to use.
 -R  resource - specifies the target resource. This can also be specified in
       your environment or via a rule set up by the administrator.
 -r  recursive - store the whole subdirectory
 -v  verbose
 -V  Very verbose
 -h  this help
 -l  lists all the source files that needs to be synchronized
       (including their filesize in bytes) with respect to the target
       without actually doing the synchronization.
 --link - ignore symlink. Valid only for rsync from local host to iRODS.
 -a   synchronize to all replicas if the target is an iRODS dataobject/collection.
 -s   use the size instead of the checksum value for determining
      synchronization.
 --age age_in_minutes - The maximum age of the source copy in minutes for sync.
      i.e., age larger than age_in_minutes will not be synced.
 
Also see 'irepl' for the replication and synchronization of physical
copies (replica).

iRODS Version 4.3.0                irsync

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


"""
    session         ibridges Session
    source          can only be a folder or a iRODS collection, not individual files
    target          iRODS collection or folder
    max_level       -r  recursive - store the whole subdirectory (max_level=None)
    dry_run         -l  lists all the source files that needs to be synchronized without actually doing the synchronization.
    ignore_checksum -s  use the size instead of the checksum value for determining synchronization.
    verify_checksum -K  verify checksum - calculate and verify the checksum on the data
    copy_empty_folders
"""

def sync(session,
         source,
         target,
         max_level=None,
         dry_run=False,
         ignore_checksum=False,
         copy_empty_folders=False,
         verify_checksum=False) -> None:  

    assert isinstance(source, IrodsPath) or isinstance(target, IrodsPath), "Either source or target should be an iRODS path."
    assert not (isinstance(source, IrodsPath) and isinstance(target, IrodsPath)), "iRODS to iRODS copying is not supported."

    if isinstance(source, IrodsPath):
        assert source.collection_exists(), \
            "Source collection '%s' does not exist" % source.absolute_path()
        src_files, src_folders=_get_irods_tree(
            coll=get_collection(session=session, path=source),
            max_level=max_level,
            ignore_checksum=ignore_checksum
            )
    else:
        assert Path(source).is_dir(), "Source folder '%s' does not exist" % source
        src_files, src_folders=_get_local_tree(
            path=source,
            max_level=max_level,
            ignore_checksum=ignore_checksum
            )

    if isinstance(target, IrodsPath):
        assert target.collection_exists(), \
            "Target collection '%s' does not exist" % target.absolute_path()
        tgt_files, tgt_folders=_get_irods_tree(
            coll=get_collection(session=session, path=target),
            max_level=max_level,
            ignore_checksum=ignore_checksum
            )
    else:
        assert Path(target).is_dir(), "Target folder '%s' does not exist" % target
        tgt_files, tgt_folders=_get_local_tree(
            path=target,
            max_level=max_level,
            ignore_checksum=ignore_checksum
            )

    # compares the relative paths
    folders_diff=set(src_folders).difference(set(tgt_folders))
    # compares the checksum, file size, file name & relative path
    files_diff=set(src_files).difference(set(tgt_files))

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
            dry_run=dry_run)
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
    
    # set(src_folders).intersection(set(tgt_folders))
    # set(src_files).intersection(set(tgt_files))

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
            rel_path=str(full_path)[len(path):].lstrip(os.sep)
            if max_level is None or rel_path.count(os.sep)<max_level:
                objects.append(FileObject(
                    name=file, 
                    path=fix_local_path(rel_path),
                    size=full_path.stat().st_size,
                    checksum=_calc_checksum(full_path),
                    ignore_checksum=ignore_checksum))

        collections.extend([FolderObject(
                fix_local_path(f"{root}{os.sep}{dir}"[len(path):].lstrip(os.sep)),
                len([x for x in Path(f"{root}{os.sep}{dir}").iterdir() if x.is_file()]),
                len([x for x in Path(f"{root}{os.sep}{dir}").iterdir() if x.is_dir()])
            )
            for dir in dirs if max_level is None or dir.count(os.sep)<max_level-1])

    return sorted(objects, key=lambda x: (str(x.path).count(os.sep), str(x))), \
        sorted(collections, key=lambda x: (str(x.path).count(os.sep), str(x)))

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

    return sorted(objects, key=lambda x: (x.path.count('/'), x.path)), \
        sorted(collections, key=lambda x: (x.path.count('/'), x.path))

def _create_irods_collections(session, target, collections, dry_run, copy_empty_folders):
    if dry_run:
        print("Will create collection(s):")

    for collection in collections:
        if collection.is_empty() and not copy_empty_folders:
            continue

        full_path=target / collection.path

        if dry_run:
            print(f"  {full_path}")
        else:
            _=create_collection(session, str(full_path))

    if dry_run:
        print()

def _create_local_folders(target, folders, dry_run, copy_empty_folders):
    if dry_run:
        print("will create folder(s):")

    for folder in folders:
        if folder.is_empty() and not copy_empty_folders:
            continue

        full_path=Path(target) / Path(folder.path)

        if dry_run:
            print(f"  {full_path}")
        else:
            full_path.mkdir(parents=True, exist_ok=True)

    if dry_run:
        print()

def _copy_local_to_irods(session, source, target, files, dry_run):
    if dry_run:
        print(f"Will copy from '{source}' to '{target}':")

    for file in files:
        source_path=Path(source) / file.path
        target_path=str(target / file.path)
        if dry_run:
            print(f"  {file.path}  {file.size}")
        else:
            upload(session=session, local_path=source_path, irods_path=target_path, overwrite=True)

    if dry_run:
        print()

def _copy_irods_to_local(session, source, target, objects, dry_run, verify_checksum):
    for object in objects:
        target_path=Path(target) / object.path
        source_path=str(source / object.path)
        if dry_run:
            print(f"  {object.path}  {object.size}")
        else:
            _=download(session=session, irods_path=source_path, local_path=target_path, overwrite=True)
            if verify_checksum and object.checksum != _calc_checksum(target_path):
                logging.warning(f"Checkum mismatch after download: '{target_path}'")
            

    if dry_run:
        print()
