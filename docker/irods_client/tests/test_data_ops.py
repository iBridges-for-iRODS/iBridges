import hashlib
from pathlib import Path

import pytest

from ibridges.data_operations import (
    download,
    upload,
)
from ibridges.path import IrodsPath
from ibridges.util import is_collection, is_dataobject


def _get_digest(obj_or_file):
    with open(obj_or_file, "rb") as handle:
        digest = hashlib.sha256(handle.read()).digest()
    return digest

def _check_files_equal(*files):
    assert len(files) > 0
    digests = [_get_digest(f) for f in files]

    for dig in digests[1:]:
        if digests[0] != dig:
            return False
    return True


def _check_count(ops, nlist):
    for var, count, in zip(["create_collection", "create_dir", "download", "upload"],
                          nlist):
        assert len(ops[var]) == count



def test_upload_download_dataset(session, testdata):
    ipath = IrodsPath(session, "~", "plant.rtf")
    ipath.remove()
    ops = upload(session, testdata/"plant.rtf", IrodsPath(session, "~"))
    _check_count(ops, [0, 0, 0, 1])
    data_obj = ipath.dataobject
    assert is_dataobject(data_obj)
    assert not is_collection(data_obj)
    with pytest.raises(ValueError):
        _ = ipath.collection
    ops = download(session, ipath, testdata/"plant.rtf.copy", overwrite=True)
    assert _check_files_equal(testdata/"plant.rtf.copy", testdata/"plant.rtf")
    _check_count(ops, [0, 0, 1, 0])


def test_upload_download_collection(session, testdata, tmpdir):
    ipath = IrodsPath(session, "~", "test")
    ipath.remove()
    ops = upload(session, testdata, ipath)
    _check_count(ops, [2, 0, 0, 7])
    collection = ipath.collection
    assert is_collection(collection)
    assert not is_dataobject(collection)
    with pytest.raises(ValueError):
        ipath.dataobject
    ops = download(session, ipath, tmpdir/"test")
    _check_count(ops, [0, 4, 7, 0])
    files = list(testdata.glob("*"))

    for cur_file in files:
        copy_file = Path(tmpdir, "test", cur_file)
        orig_file = Path(testdata, cur_file)
        if orig_file.is_file():
            with open(orig_file, "r") as handle:
                orig_data = handle.read()
            with open(copy_file, "r") as handle:
                copy_data = handle.read()
            assert copy_data == orig_data
