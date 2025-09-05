import json

import irods
import pytest
from pytest import mark

from ibridges.data_operations import Operations
from ibridges.meta import MetaData, MetaDataItem
from ibridges.path import IrodsPath


@mark.parametrize("item_name", ["collection", "dataobject"])
def test_meta(item_name, request):
    item = request.getfixturevalue(item_name)
    meta = MetaData(item)
    meta.clear()

    assert len(str(meta)) == 0
    assert len(meta) == 0

    # Add key, value pair
    meta.add("x", "y")
    assert len(meta) == 1
    assert list(meta)[0].name == "x"
    assert list(meta)[0].value == "y"
    assert list(meta)[0].units == ""
    assert "x" in meta
    assert ("x", "y") in meta
    assert "y" not in meta
    assert ("x", "z") not in meta
    assert ("x", "y", "z") not in meta

    # Same key, but different value
    meta.add("x", "z")
    assert len(meta) == 2
    assert len(str(meta).split("\n")) == 2
    assert ("x", "z") in meta

    # Same key, value different units
    meta.add("x", "z", "m")
    assert len(meta) == 3
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
    assert len(meta) == 2

    meta.delete("x", "z")
    assert len(meta) == 1

    meta.delete("x")
    assert len(meta) == 0

    meta.add("x", "y")
    meta.add("y", "z")
    meta["y"] = "x"
    assert "x" in meta
    assert ("y", "z") not in meta
    assert ("y", "x") in meta

    meta["y"] = [["x", "u"], ["y", "u"]]
    assert ("y", "x") in meta
    assert ("y", "y") in meta
    with pytest.raises(ValueError):
        meta["y"] = "z"
    assert ("y", "x") in meta
    assert ("y", "y") in meta
    with pytest.raises(ValueError):
        meta["y"] = [["a", "b", "c"]]
    meta.delete(key="y")
    with pytest.raises(ValueError):
        meta["y"] = "a", "b", "c"
    meta.clear()

@mark.parametrize("item_name", ["collection", "dataobject"])
def test_metadata_todict(item_name, request):
    item = request.getfixturevalue(item_name)
    meta = MetaData(item)
    meta.clear()
    # test against:
    test_dict = {
            'name': item.name,
            'irods_id': item.id,
            'metadata': [('x', 'z', 'm')]
            }

    if isinstance(item, irods.data_object.iRODSDataObject):
        test_dict['checksum'] = item.checksum

    # Add some metadata
    meta.add("x", "z", "m")
    assert "x" in meta
    result = meta.to_dict()

    for key in result.keys():
        assert key in test_dict
    for value in result.values():
        assert value in test_dict.values()

@mark.parametrize("item_name", ["collection", "dataobject"])
def test_metadata_export(item_name, request, session, tmpdir):
    tmp_file = tmpdir/"meta.json"
    item = request.getfixturevalue(item_name)
    meta_dict = MetaData(item).to_dict()
    assert isinstance(meta_dict, dict)
    assert "name" in meta_dict
    assert "irods_id" in meta_dict
    assert "metadata" in meta_dict

    ops = Operations()
    ops.add_meta_download(IrodsPath(session, item.path), tmp_file)
    ops.execute(session)
    with open(tmp_file, "r", encoding="utf-8"):
        new_meta_dict = json.load(tmp_file)
    assert isinstance(new_meta_dict, dict)

@mark.parametrize("item_name", ["collection", "dataobject"])
def test_metadata_getitem(item_name, request):
    item = request.getfixturevalue(item_name)
    meta = MetaData(item)
    meta.clear()

    assert len(meta) == 0
    meta.add("some_key", "some_value", "some_units")
    assert isinstance(meta["some_key"], MetaDataItem)
    meta.add("some_key", "some_value", None)
    meta.add("some_key", "other_value", "some_units")
    meta.add("other_key", "third_value", "other_units")
    with pytest.raises(ValueError):
        meta["some_key"]
    with pytest.raises(ValueError):
        meta["some_key", "some_value"]
    assert isinstance(meta["some_key", "some_value", "some_units"], MetaDataItem)
    assert tuple(meta["other_key"]) == ("other_key", "third_value", "other_units")
    with pytest.raises(KeyError):
        meta["unknown"]
    with pytest.raises(KeyError):
        meta["some_key", "unknown"]
    with pytest.raises(KeyError):
        meta["some_key", "some_value", "unknown"]
    meta.clear()


@mark.parametrize("item_name", ["collection", "dataobject"])
def test_metadata_setitem(item_name, request):
    item = request.getfixturevalue(item_name)
    meta = MetaData(item)
    meta.clear()

    meta["key"] = "value", "units"
    assert ("key", "value", "units") in meta

    meta["key", "value"] = "other_units"
    assert ("key", "value", "units") not in meta
    assert ("key", "value", "other_units") in meta
    meta["key", "other_value"] = "units"
    assert ("key", "value", "other_units") in meta

    meta.add("key", "value", "even_units")
    assert len(meta) == 3
    with pytest.raises(ValueError):
        meta["key"] = "new_value"

    with pytest.raises(ValueError):
        meta["key", "value"] = "another_units"

    meta["key2"] = "value2"
    assert len(meta) == 4

    with pytest.raises(ValueError):
        meta["some_key", "some_value", "some_units"] = ""

    with pytest.raises(ValueError):
        meta["some_key", "some_value"] = "new_value", "new_units"


@mark.parametrize("item_name", ["collection", "dataobject"])
def test_metadata_rename(item_name, request, session):
    item = request.getfixturevalue(item_name)
    meta = MetaData(item)
    meta.clear()


    meta.add("some_key", "some_value", "some_units")
    meta["some_key"].key = "new_key"
    assert ("new_key", "some_value", "some_units") in meta
    assert len(meta) == 1

    meta["new_key"].value = "new_value"
    assert ("new_key", "new_value", "some_units") in meta
    assert len(meta) == 1

    meta["new_key"].units = "new_units"
    assert ("new_key", "new_value", "new_units") in meta
    assert len(meta) == 1

    meta.add("new_key", "new_value", "other_units")
    with pytest.raises(ValueError):
        meta["new_key", "new_value", "other_units"].units = "new_units"
    assert len(meta) == 2
    meta["new_key", "new_value", "other_units"].remove()

    meta.add("new_key", "other_value", "new_units")
    with pytest.raises(ValueError):
        meta["new_key", "other_value", "new_units"].value = "new_value"
    assert len(meta) == 2
    meta["new_key", "other_value", "new_units"].remove()

    meta.add("other_key", "new_value", "new_units")
    with pytest.raises(ValueError):
        meta["other_key", "new_value", "new_units"].key = "new_key"
    assert len(meta) == 2

    with pytest.raises(ValueError):
        meta["other_key"].key = "org_something"
    assert len(meta) == 2
    assert "other_key" in meta

    meta.clear()


@mark.parametrize("item_name", ["collection", "dataobject"])
def test_metadata_findall(item_name, request, session):
    item = request.getfixturevalue(item_name)
    meta = MetaData(item)
    meta.clear()


    meta.add("some_key", "some_value", "some_units")
    meta.add("some_key", "some_value", None)
    meta.add("some_key", "other_value", "some_units")
    meta.add("other_key", "third_value", "other_units")

    assert len(meta.find_all()) == 4
    assert len(meta.find_all(key="some_key")) == 3
    assert isinstance(meta.find_all(key="some_key")[0], MetaDataItem)
    assert len(meta.find_all(key="?")) == 0
    assert len(meta.find_all(value="some_value")) == 2
    assert len(meta.find_all(units="some_units")) == 2


@mark.parametrize("item_name", ["collection", "dataobject"])
def test_metadata_errors(item_name, request, session):
    item = request.getfixturevalue(item_name)
    meta = MetaData(item)
    meta.clear()

    with pytest.raises(ValueError):
        meta.add("", "some_value")
    with pytest.raises(TypeError):
        meta.add(None, "some_value")
    with pytest.raises(TypeError):
        meta.add(10, "some_value")

    with pytest.raises(ValueError):
        meta.add("key", "")
    with pytest.raises(TypeError):
        meta.add("key", None)
    with pytest.raises(TypeError):
        meta.add("key", 10)

    with pytest.raises(TypeError):
        meta.add("key", "value", 10)

