import os
import tempfile
from pathlib import Path
from ibridges.irodsconnector.sync import sync
from ibridges.utils.path import IrodsPath
from ibridges.irodsconnector.data_operations import create_collection

def _get_local_tree(path, max_level):
    objects=[]
    collections=[]
    for root, dirs, files in os.walk(path):
        for file in files:
            fpath=f"{root}/{file}"
            if max_level is None or fpath.count(os.sep)<max_level:
                objects.append(fpath[len(str(path)):].lstrip(os.sep))
        collections.extend([str(Path(root) / dir)[len(str(path)):].lstrip(os.sep)
            for dir in dirs if max_level is None or dir.count(os.sep)<max_level-1])
    return objects, collections

def _get_irods_tree(coll, root, level, max_level):
    root=coll.path if len(root)==0 else root
    objects=[x.path[len(root):].lstrip('/') for x in coll.data_objects]
    if max_level is None or level<max_level-1:
        collections=[x.path[len(root):].lstrip('/') for x in coll.subcollections]
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

def test_sync_upload_download(session, testdata, tmpdir):
    ipath = IrodsPath(session, "~", "empty")
    coll = create_collection(session=session, coll_path=ipath)

    local_obj, local_coll = _get_local_tree(testdata, None)
    irods_obj, irods_coll = _get_irods_tree(coll, '', 0, None)

    assert (len(irods_obj)+len(irods_coll))==0, "iRODS folder not empty"

    # upload
    sync(session=session,
         source=testdata,
         target=ipath,
         max_level=None,
         dry_run=False,
         ignore_checksum=False,
         copy_empty_folders=True,
         verify_checksum=True)

    irods_obj, irods_coll = _get_irods_tree(coll, '', 0, None)

    assert set(local_coll)==set(irods_coll), "Collection upload failed"
    assert set(local_obj)==set(irods_obj), "Object upload failed"

    # download
    sync(session=session,
        source=ipath,
        target=tmpdir,
        max_level=None,
        dry_run=False,
        ignore_checksum=False,
        copy_empty_folders=True,
        verify_checksum=True)

    local_obj, local_coll = _get_local_tree(tmpdir, None)

    assert set(local_coll)==set(irods_coll), "Collection download failed"
    assert set(local_obj)==set(irods_obj), "Object download failed"
