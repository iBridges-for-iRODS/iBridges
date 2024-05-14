from pytest import mark

from ibridges.path import IrodsPath


@mark.parametrize("item_name", ["collection", "dataobject"])
def test_move(session, item_name, request):
    item = request.getfixturevalue(item_name)
    old_path = IrodsPath(session, item.path)
    new_path = IrodsPath(session, '~', 'moved')

    old_path.rename(new_path)
    assert new_path.exists()
    assert not old_path.exists()

    new_path.rename(old_path)
    assert old_path.exists()
    assert not new_path.exists()
