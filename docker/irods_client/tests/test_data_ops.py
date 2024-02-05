from pathlib import Path

import pytest

from ibridges.irodsconnector.data_operations import (
    download,
    get_collection,
    get_dataobject,
    is_collection,
    is_dataobject,
    upload,
)
from ibridges.utils.path import IrodsPath


def test_upload_download_dataset(session, testdata):
    ipath = IrodsPath(session, "~", "bunny.rtf")
    ipath.remove()
    upload(session, testdata/"bunny.rtf", IrodsPath(session, "~"))
    data_obj = get_dataobject(session, ipath)
    assert is_dataobject(data_obj)
    assert not is_collection(data_obj)
    with pytest.raises(ValueError):
        get_collection(session, ipath)
    print(session)
    download(session, ipath, testdata/"bunny.rtf.copy", overwrite=True)
    # with open(data_obj, "r") as handle:
        # data_irods = handle.read()
    with open(testdata/"bunny.rtf.copy") as handle:
        data_redownload = handle.read()
    with open(testdata/"bunny.rtf") as handle:
        data_original = handle.read()
    assert data_original == data_redownload
    # assert data_irods == data_original
    # assert data_irods == data_redownload


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
        with open(orig_file, "r") as handle:
            orig_data = handle.read()
        with open(copy_file, "r") as handle:
            copy_data = handle.read()
        assert copy_data == orig_data
