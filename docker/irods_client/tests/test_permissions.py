import pytest
from pytest import mark

from ibridges.path import IrodsPath
from ibridges.permissions import Permissions


@mark.parametrize("item_name", ["collection", "dataobject"])
def test_perm_own(session, item_name, request, tmpdir, config):
    item = request.getfixturevalue(item_name)
    perm = Permissions(session, item)
    ipath = IrodsPath(session, item.path)

    assert isinstance(str(perm), str)
    assert isinstance(perm.available_permissions, dict)
    with pytest.raises(ValueError):
        perm.set("null", user=session.username, zone=session.zone)
    with pytest.raises(ValueError):
        perm.set("read", user=session.username, zone=session.zone)
    with pytest.raises(ValueError):
        perm.set("own", user=session.username, zone=session.zone)

@mark.parametrize("item_name", ["collection", "dataobject"])
def test_perm_user(session, item_name, request, config):
    # Testing access for another user if defined in config.toml
    testuser = config.get("test_user", None)
    item = request.getfixturevalue(item_name)
    perm = Permissions(session, item)
    if testuser:
        
        ipath = IrodsPath(session, item.path)
        perm.set("read", user=testuser, zone=session.zone)
        assert testuser in [p.user_name for p in perm]
        assert (testuser, 1050) in [(p.user_name, p.to_int(
            p.access_name.replace(" ", "_"))) for p in perm]
        perm.set("write", user=testuser, zone=session.zone)
        assert (testuser, 1120) in [(p.user_name, p.to_int(
            p.access_name.replace(" ", "_"))) for p in perm]
        perm.set("null", user=testuser, zone=session.zone)
        assert testuser not in [p.user_name for p in perm]

@mark.parametrize("item_name", ["collection"])
def test_inherit_coll(session, item_name, request, config):
    #Testing inherit keyword
    item = request.getfixturevalue(item_name)
    irods_path = IrodsPath(session, item.path)
    perm = Permissions(session, item)
    perm.set("inherit")
    assert irods_path.collection.inheritance

    perm.set("noinherit")
    assert not irods_path.collection.inheritance
