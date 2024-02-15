import pytest
from irods.exception import CAT_NO_ACCESS_PERMISSION
from pytest import mark

from ibridges.irodsconnector.data_operations import download, upload
from ibridges.irodsconnector.permissions import Permissions
from ibridges.utils.path import IrodsPath


@mark.parametrize("item_name", ["collection", "dataobject"])
def test_permissions(session, item_name, request, tmpdir):
    item = request.getfixturevalue(item_name)
    perm = Permissions(session, item)
    ipath = IrodsPath(session, item.path)

    assert isinstance(str(perm), str)
    assert isinstance(perm.available_permissions, dict)
    with pytest.raises(ValueError):
        perm.set("null", user=session.username, zone=session.zone)
    perm.set("read")
    with pytest.raises(ValueError):
        upload(session, tmpdir/"bunny.rt.copy", ipath, overwrite=True)
    perm.set("own")

    # Testing access for another user, only on plain irods
    if not "set_home_perm" in config:
        assert len(list(perm)) == 1 # only one acl for rods
        ipath = IrodsPath(session, item.path)
        perm.set("read", user="testuser", zone=session.zone)
        assert "testuser" in [p.user_name for p in perm]
        assert ("testuser", "read_object") in [(p.user_name, p.access_name) for p in perm]
        perm.set("write", user="testuser", zone=session.zone)
        assert ("testuser", "modify_object") in [(p.user_name, p.access_name) for p in perm]
        perm.set("null", user="testuser", zone=session.zone)
        assert "testuser" not in [p.user_name for p in perm]
