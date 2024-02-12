import base64
import os
from pathlib import Path
from hashlib import sha256
from typing import NamedTuple
from ibridges.utils.path import IrodsPath
from ibridges.irodsconnector.data_operations import get_collection
from pprint import pprint


# now just doing folder --> collection (and vv), not files, --> collection. do that too?
# what to do if the target (does not) exists? create & copy or fail (if not), copy to tagregt/source or copy content (if does exist)
# -l: lists all the source files that needs to be synchronized  without actually doing the synchronization.
# ??? -K  verify checksum - calculate and verify the checksum on the data
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

class FileObject(NamedTuple):
    name: str       # filename
    path: str       # path (relative to source or target root)
    size: int       # file size
    checksum: int   # base64 encoded sha256 file hash

class FolderObject(NamedTuple):
    path: str       # path (relative to source or target root)

class IBridgesSync:

    def __init__(self, 
                 session, 
                 source, 
                 target,
                 max_level=None,
                 dry_run=False,
                 no_checksum=False) -> None:

        self.max_level=max_level
        self.dry_run=dry_run
        self.no_checksum=no_checksum

        assert isinstance(source, IrodsPath) or isinstance(target, IrodsPath), "Either source or target should be an iRODS path."
        # assert not (isinstance(source, IrodsPath) and isinstance(target, IrodsPath)), "iRODS to iRODS copying is not supported."

        self.sync(session=session, source=source, target=target)

    def sync(self, session, source, target):
        if isinstance(source, IrodsPath):
            assert source.collection_exists(), \
                "Source collection '%s' does not exist" % source.absolute_path()
            src_files, src_folders=self.get_irods_tree(
                coll=get_collection(session=session, path=source),
                max_level=self.max_level
                )
        else:
            assert Path(source).is_dir(), "Source folder '%s' does not exist" % source
            src_files, src_folders=self.get_local_tree(
                path=source,
                max_level=self.max_level
                )

        if isinstance(target, IrodsPath):
            assert target.collection_exists(), \
                "Target collection '%s' does not exist" % target.absolute_path()
            tgt_files, tgt_folders=self.get_irods_tree(
                coll=get_collection(session=session, path=target),
                max_level=self.max_level
                )
        else:
            assert Path(target).is_dir(), "Target folder '%s' does not exist" % target
            tgt_files, tgt_folders=self.get_local_tree(
                path=target,
                max_level=self.max_level
                )

        # compares the relative paths
        folders_diff=set(src_folders).difference(set(tgt_folders))
        # compares the checksum, file size, file name & relative path
        files_diff=set(src_files).difference(set(tgt_files))

        if isinstance(target, IrodsPath):
            self.create_irods_collections(target=target, collections=folders_diff)
            self.copy_local_to_irods(source=source, target=target, files=files_diff)
        else:
            self.create_local_folders(target=target, folders=folders_diff)
            self.copy_irods_to_local(source=source, target=target, objects=files_diff)
        
        # dry run only: print what overlaps (already exists at both sides)
        if self.dry_run:
            self.print_existing(label='folders/collections', 
                                root=target, 
                                existing=set(src_folders).intersection(set(tgt_folders)))
            self.print_existing(label='files', 
                                root=source, 
                                existing=set(src_files).intersection(set(tgt_files)))

    @staticmethod
    def get_local_tree(path, max_level=None):

        def calc_checksum(filename, prefix=''):
            h=sha256()
            mv=memoryview(bytearray(128*1024))
            with open(filename, 'rb', buffering=0) as f:
                for n in iter(lambda : f.readinto(mv), 0):
                    h.update(mv[:n])
            return prefix+str(base64.b64encode(h.digest()), encoding='utf-8')

        objects=[]
        collections=[]

        for root, dirs, files in os.walk(path):
            for file in files:
                full_path=Path(f"{root}/{file}")
                rel_path=str(full_path)[len(path):].lstrip(os.sep)
                if max_level is None or rel_path.count(os.sep)<max_level:
                    objects.append(FileObject(
                        file, 
                        rel_path,
                        full_path.stat().st_size,
                        calc_checksum(full_path, 'sha2:')))

            collections.extend([FolderObject(f"{root}/{dir}"[len(path):].lstrip(os.sep)) 
                                for dir in dirs 
                                if max_level is None or dir.count(os.sep)<max_level-1])

        return sorted(objects, key=lambda x: (str(x.path).count(os.sep), str(x))), \
            sorted(collections, key=lambda x: (str(x.path).count(os.sep), str(x)))

    @staticmethod
    def get_irods_tree(coll, root=None, level=0, max_level=None):
        
        root=coll.path if root is None else root

        # chksum() (re)calculates checksum, call only when checksum is empty
        objects=[FileObject(
            x.name,
            x.path[len(root):].lstrip('/'),
            x.size,
            x.checksum if len(x.checksum)>0 else x.chksum()) for x in coll.data_objects]

        if max_level is None or level<max_level-1:
            collections=[FolderObject(
                x.path[len(root):].lstrip('/')) for x in coll.subcollections]

            for subcoll in coll.subcollections:
                subobjects, subcollections=IBridgesSync.get_irods_tree(
                    coll=subcoll, 
                    root=root, 
                    level=level+1, 
                    max_level=max_level
                    )
                objects.extend(subobjects)
                collections.extend(subcollections)
        else:
            collections=[]

        return sorted(objects, key=lambda x: (x.path.count('/'), x.path)), \
            sorted(collections, key=lambda x: (x.path.count('/'), x.path))

    @staticmethod
    def print_existing(root, existing, label):
        print(f"Skipping {label} (already exist):")
        for item in existing:
            full_path=f"{root}/{item.path}"
            print(f"  {full_path}")
        print()

    def create_irods_collections(self, target, collections):
        if self.dry_run:
            print("Will create collection(s):")

        for collection in collections:
            full_path=target / collection.path
            if self.dry_run:
                print(f"  {full_path}")
            else:
                pass

        if self.dry_run:
            print()

    def create_local_folders(self, target, folders):
        if self.dry_run:
            print("will create folder(s):")

        for folder in folders:
            full_path=Path(target) / Path(folder.path)
            if self.dry_run:
                print(full_path)
            else:
                pass

        if self.dry_run:
            print()

    def copy_local_to_irods(self, source, target, files):
        if self.dry_run:
            print(f"Will copy {source} --> {target}")

        for file in files:
            source_path=Path(source) / file.path
            target_path=target / file.path
            if self.dry_run:
                print(f"  {file.path}  {file.size}")
            else:
                pass

        if self.dry_run:
            print()

    def copy_irods_to_local(self, source, target, objects):
        for object in objects:
            target_path=Path(target) / object.path
            source_path=source / object.path
            if self.dry_run:
                print(f"  {object.path}  {object.size}")
            else:
                pass

        if self.dry_run:
            print()
