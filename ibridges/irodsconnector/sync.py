import base64
from pathlib import Path
from hashlib import sha256
from typing import NamedTuple
from ibridges.utils.path import IrodsPath
from ibridges.irodsconnector.data_operations import get_collection
from pprint import pprint


class FileObject(NamedTuple):
    name: str       # filename
    abs_path: str   # full path
    rel_path: str   # path relative to source or target root
    size: int       # file size
    checksum: int   # base64 encoded sha256 file hash


class FolderObject(NamedTuple):
    abs_path: str   # full path
    rel_path: str   # path relative to source or target root


class IBridgesSync:

    def __init__(self, session, source, target) -> None:
        self.sync(session=session, source=source, target=target)

    @staticmethod
    def get_filesystem_tree(path):

        def calc_checksum(filename, prefix=''):
            mv=memoryview(bytearray(128*1024))
            with open(filename, 'rb', buffering=0) as f:
                for n in iter(lambda : f.readinto(mv), 0):
                    sha256().update(mv[:n])
            return prefix+str(base64.b64encode(sha256().digest()), encoding='utf-8')

        objects=[]
        collections=[]

        for root, dirs, files in Path(path).walk(on_error=print):
            for file in files:
                objects.append(FileObject(
                    file, 
                    root / file,
                    str(root / file)[len(path):].lstrip('/'),
                    (root / file).stat().st_size,
                    calc_checksum(root / file, 'sha2:')))
                collections.extend([FolderObject(
                    root / dir,
                    str(root / dir)[len(path):].lstrip('/')
                    ) for dir in dirs])

        return sorted(objects, key=lambda x: (str(x.abs_path).count('/'), str(x))), \
            sorted(collections, key=lambda x: (str(x.abs_path).count('/'), str(x)))

    @staticmethod
    def get_irods_tree(coll, root=None):
        
        root=coll.path if root is None else root

        objects=[FileObject(
            x.name,
            x.path,
            x.path[len(root):].lstrip('/'),
            x.size,
            x.checksum) for x in coll.data_objects]

        collections=[FolderObject(
            x.path,
            x.path[len(root):].lstrip('/')) for x in coll.subcollections]

        for subcoll in coll.subcollections:
            subobjects, subcollections=IBridgesSync.get_irods_tree(coll=subcoll, root=root)
            objects.extend(subobjects)
            collections.extend(subcollections)

        return sorted(objects, key=lambda x: (x.abs_path.count('/'), x.abs_path)), \
            sorted(collections, key=lambda x: (x.abs_path.count('/'), x.abs_path))

    def sync(self, session, source, target):
        if isinstance(source, IrodsPath):
            assert source.collection_exists(), "source collection '%s' does not exist" % source.absolute_path()
            src_files, src_folders=self.get_irods_tree(get_collection(session=session, path=source))
        else:
            assert Path(source).is_dir(), "source folder '%s' does not exist" % source
            src_files, src_folders=self.get_filesystem_tree(source)

        if isinstance(target, IrodsPath):
            assert target.collection_exists(), "target collection '%s' does not exist" % target.absolute_path()
            tgt_files, tgt_folders=self.get_irods_tree(get_collection(session=session, path=target))
        else:
            assert Path(target).is_dir(), "target folder '%s' does not exist" % target
            tgt_files, tgt_folders=self.get_filesystem_tree(target)

        pprint(src_files)
        pprint(tgt_files)
        pprint(src_folders)
        pprint(tgt_folders)

