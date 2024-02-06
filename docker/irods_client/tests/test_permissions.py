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

    # TODO: Add more tests with other users.

    # assert len(list(perm)) == 0
    # ipath = IrodsPath(session, item.path)
    # with pytest.raises(CAT_NO_ACCESS_PERMISSION):
    #     download(session, ipath, tmpdir/"bunny.rt.copy", overwrite=True)
    # perm.set("read", user=session.username, zone=session.zone)
    # download(session, ipath, tmpdir/"bunny.rt.copy", overwrite=True)
    # assert (tmpdir/"bunny.rt.copy").is_file
    # with pytest.raises(ValueError):
    #     upload(session, tmpdir/"bunny.rt.copy", ipath, overwrite=True)
    # perm.set("write", user=session.username, zone=session.zone)
    # # if item_name == "dataobject":
    # upload(session, tmpdir/"bunny.rt.copy", ipath, overwrite=True)
    # # else:
    #     # upload(session, tmpdir/"bunny.rt.copy", ipath, overwrite=True)
    # assert ipath.is_dataobject()
