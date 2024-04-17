import hashlib
from pathlib import Path

import pytest

from ibridges.data_operations import (
    download,
    get_collection,
    get_dataobject,
    is_collection,
    is_dataobject,
    upload,
)
from ibridges.path import IrodsPath


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


def test_upload_download_dataset(session, testdata):
    ipath = IrodsPath(session, "~", "plant.rtf")
    ipath.remove()
    upload(session, testdata/"plant.rtf", IrodsPath(session, "~"))
    data_obj = get_dataobject(session, ipath)
    assert is_dataobject(data_obj)
    assert not is_collection(data_obj)
    with pytest.raises(ValueError):
        get_collection(session, ipath)
    download(session, ipath, testdata/"plant.rtf.copy", overwrite=True)
    assert _check_files_equal(testdata/"plant.rtf.copy", testdata/"plant.rtf")


def test_upload_download_collection(session, testdata, tmpdir):
    ipath = IrodsPath(session, "~", "test")
    ipath.remove()
    upload(session, testdata, ipath)
    collection = get_collection(session, ipath)
    assert is_collection(collection)
    assert not is_dataobject(collection)
    with pytest.raises(ValueError):
        get_dataobject(session, ipath)
    download(session, ipath, tmpdir/"test")
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
