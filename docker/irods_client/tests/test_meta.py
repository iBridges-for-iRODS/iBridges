import pytest
from pytest import mark

from ibridges.irodsconnector.data_operations import get_collection, get_dataobject, upload
from ibridges.irodsconnector.meta import MetaData
from ibridges.utils.path import IrodsPath


@pytest.fixture(scope="module")
def collection(session):
    return get_collection(session, IrodsPath(session, "~"))


@pytest.fixture(scope="module")
def dataobject(session, testdata):
    ipath = IrodsPath(session, "~", "bunny.rtf")
    upload(session, testdata/"bunny.rtf", IrodsPath(session, "~"), overwrite=True)
    yield get_dataobject(session, ipath)
    ipath.remove()


@mark.parametrize("item_name", ["collection", "dataobject"])
def test_meta(item_name, request):
    item = request.getfixturevalue(item_name)
    meta = MetaData(item)
    meta.clear()

    assert len(str(meta)) == 0
    assert len(list(meta)) == 0

    # Add key, value pair
    meta.add("x", "y")
    assert len(list(meta)) == 1
    assert list(meta)[0].name == "x"
    assert list(meta)[0].value == "y"
    assert list(meta)[0].units is None
    assert "x" in meta
    assert ("x", "y") in meta
    assert "y" not in meta
    assert ("x", "z") not in meta
    assert ("x", "y", "z") not in meta

    # Same key, but different value
    meta.add("x", "z")
    assert len(list(meta)) == 2
    assert len(str(meta).split("\n")) == 3  #\n at the end
    assert ("x", "z") in meta

    # Same key, value different units
    meta.add("x", "z", "m")
    assert len(list(meta)) == 3
    assert ("x", "z", "m") in meta

    # Test that we cannot add the same metadata twice
    with pytest.raises(ValueError):
        meta.add("x", "y")
    with pytest.raises(ValueError):
        meta.add("x", "z", "m")

    # Cannot delete value with different units
    assert ("x", "z", "kg") not in meta
    with pytest.raises(KeyError):
        meta.delete("x", "z", "kg")
    meta.delete("x", "z", "m")
    assert len(list(meta)) == 2

    meta.delete("x", "z")
    assert len(list(meta)) == 1

    meta.delete("x")
    assert len(list(meta)) == 0

    meta.add("x", "y")
    meta.set("y", "x")
    assert "x" not in meta
    assert ("y", "x") in meta
