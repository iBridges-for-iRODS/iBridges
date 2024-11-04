import pytest
from pytest import mark

from ibridges import IrodsPath, search_data, upload
from ibridges.search import MetaSearch


def _found(search_res, path):
    for res in search_res:
        assert isinstance(res, IrodsPath)
        if str(res) == str(path):
            return True
    return False

@mark.parametrize("item_name", ["collection", "dataobject"])
def test_find_path(session, item_name, request):
    item = request.getfixturevalue(item_name)
    ipath = IrodsPath(session, item.path)
    assert _found(search_data(session, path_pattern=item.name), item.path)
    assert _found(search_data(session, path_pattern=item.name[:4]+"%"), item.path)
    assert _found(search_data(session, ipath.parent, item.name), item.path)
    assert _found(search_data(session, ipath.parent.parent, item.name), item.path)
    assert _found(search_data(session, IrodsPath(session, "/"), item.name), item.path)
    pat = item.name[:4] + "%"
    assert _found(search_data(session, path_pattern=pat), item.path)
    pat = "%" + item.name[-3:]
    assert _found(search_data(session, path_pattern=pat), item.path)
    pat = f"{ipath.parent.name}/%{ipath.name[2:]}"
    assert _found(search_data(session, IrodsPath(session, "/"), path_pattern=pat), item.path)
    assert not _found(search_data(session, path_pattern="random_file"), item.path)


def test_find_checksum(session, dataobject):
    ipath = IrodsPath(session, dataobject.path)
    checksum = ipath.checksum
    assert _found(search_data(session, IrodsPath(session, "/"), checksum=checksum), ipath)
    assert not _found(search_data(session, IrodsPath(session, "/"), checksum="sha2:a9s8d7hjas"), ipath)
    assert _found(search_data(session, IrodsPath(session, "/"), checksum=checksum[:15] + "%"), ipath)


@mark.parametrize("metadata,is_found", [
    (MetaSearch("Author", "Ben"), True),
    (MetaSearch(units="kg"), True),
    (MetaSearch(value="10"), True),
    (MetaSearch(key="Random"), False),
    (MetaSearch(key="Author", value="10"), False),
    (MetaSearch(key="Author", units="kg"), False),
    (MetaSearch(key="Mass", units=None), False),
    ([MetaSearch(key="Author"), MetaSearch(value="10")], True),
    ([MetaSearch("Author"), MetaSearch("Random")], False),
])
@mark.parametrize("item_name", ["collection", "dataobject"])
def test_find_meta(session, item_name, request, metadata, is_found):
    item = request.getfixturevalue(item_name)
    ipath = IrodsPath(session, item.path)
    ipath.meta.clear()
    ipath.meta.add("Author", "Ben")
    ipath.meta.add("Mass", "10", "kg")

    res = _found(search_data(session, metadata=metadata), ipath)
    assert res == is_found

@mark.parametrize("metadata,is_found", [
    (MetaSearch("author", "Ben"), True),
    (MetaSearch(units="KG"), True)
])
@mark.parametrize("item_name", ["collection", "dataobject"])
def test_find_case_ins_meta(session, item_name, request, metadata, is_found):
    item = request.getfixturevalue(item_name)
    ipath = IrodsPath(session, item.path)
    ipath.meta.clear()
    ipath.meta.add("Author", "Ben")
    ipath.meta.add("Mass", "10", "kg")

    res = _found(search_data(session, metadata=metadata), ipath)
    assert res == is_found
    res = _found(search_data(session, metadata=metadata, case_sensitive=True), ipath)
    with pytest.raises(AssertionError):
        assert res == is_found


@mark.parametrize("item_name", ["collection", "dataobject"])
def test_find_case_ins_path(session, item_name, request):
    item = request.getfixturevalue(item_name)
    ipath = IrodsPath(session, item.path)
    assert _found(search_data(session, path_pattern=item.name.upper()), item.path)
    with pytest.raises(AssertionError):
        assert _found(search_data(session, path_pattern=item.name.upper(), case_sensitive=True), item.path)
