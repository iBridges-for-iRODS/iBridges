import json

import irods
import pytest
from pytest import mark

from ibridges.data_operations import Operations
from ibridges.meta import MetaData
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
    assert list(meta)[0].units is None
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
    meta.set("y", "x")
    assert "x" in meta
    assert ("y", "z") not in meta
    assert ("y", "x") in meta

@mark.parametrize("item_name", ["collection", "dataobject"])
def test_meta_update():
    # prepare test metadata
    item = request.getfixturevalue(item_name)
    meta = MetaData(item)
    meta.clear()
    meta.add('key', 'val')
    meta.add('key', 'val', 'unit')
    meta.add('key', 'val', 'test')
    meta.add('key1', 'val1', 'unit1')

    #tests
    meta.update('key', 'val', 'unit', new_value='new_val')
    assert ('key', 'new_val', 'unit') in meta and ('key', 'val', 'unit') not in meta
    meta.update('key', 'new_val', 'unit', new_units='new_unit')
    assert ('key', 'new_val', 'new_unit') in meta and ('key', 'new_val', 'unit') not in meta
    meta.update('key', 'new_val', 'new_unit', new_value='val', new_units='unit')
    assert ('key', 'val', 'unit') in meta and ('key', 'new_val', 'new_unit') not in meta
    meta.update('key1', 'val1', 'unit1', new_units='')
    assert ('key1', 'val1') in meta and ('key1', 'val1', 'unit1') not in meta

    # test insufficient input
    with pytest.raises(ValueError):
        meta.update('key', 'val')
    with pytest.raises(ValueError):
        meta.update('key', 'val', 'unit', new_value='')
    # test fail when new metadata would already exist
    with pytest.raises(ValueError):
        meta.update('key', 'val', 'unit', new_units='test')
    # test fail when metadata does not exist
    with pytest.raises(ValueError):
        meta.update('Notex_key', 'Notex_val', 'Notex_unit')

    

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
    ops.add_meta_download(IrodsPath(session, item.path), IrodsPath(session, item.path), tmp_file)
    ops.execute(session)
    with open(tmp_file, "r", encoding="utf-8"):
        new_meta_dict = json.load(tmp_file)
    assert isinstance(new_meta_dict, dict)
