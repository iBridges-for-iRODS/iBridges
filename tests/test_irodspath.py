from pathlib import PurePosixPath

from pytest import mark

from ibridges import IrodsPath


class MockIrodsSession:
    zone = "testzone"
    user = "testuser"
    host = "test.host.nl"
    server_version = "test_version"
    port = 9876
    home = "/testzone/home/testuser"
    cwd = "/testzone/home/testuser/sub"
    irods_session = None


# IrodsPath tests
mock_session = MockIrodsSession()
dirname = "blabla"
filename = "blublub"
irods_path = IrodsPath(mock_session, dirname, filename)
windows_path = "windows\\path\\directory"
linux_path = "linux/or/mac/path"

@mark.parametrize(
    "input,abs_path,name,parent",
    [
        ([], "/testzone/home/testuser/sub", "sub", "/testzone/home/testuser"),
        (["~"], "/testzone/home/testuser", "testuser", "/testzone/home"),
        ([""], "/testzone/home/testuser/sub", "sub", "/testzone/home/testuser"),
        (["."], "/testzone/home/testuser/sub", "sub", "/testzone/home/testuser"),
        ([PurePosixPath(".")], "/testzone/home/testuser/sub", "sub", "/testzone/home/testuser"),
        (["~", "xyz"], "/testzone/home/testuser/xyz", "xyz", "/testzone/home/testuser"),
        (["xyz"], "/testzone/home/testuser/sub/xyz", "xyz", "/testzone/home/testuser/sub"),
        ([".", "xyz"], "/testzone/home/testuser/sub/xyz", "xyz", "/testzone/home/testuser/sub"),
        ([PurePosixPath("."), "xyz"], "/testzone/home/testuser/sub/xyz", "xyz", "/testzone/home/testuser/sub"),
        ([PurePosixPath(".", "xyz")], "/testzone/home/testuser/sub/xyz", "xyz", "/testzone/home/testuser/sub"),
        (["/x/y/z"], "/x/y/z", "z", "/x/y"),
        (["/x/y", "z"], "/x/y/z", "z", "/x/y"),
        ([IrodsPath(MockIrodsSession(), "/x/y"), "z"], "/x/y/z", "z", "/x/y")
        # ([PureWindowsPath("c:\\x\\y\\z")], "c:\\/x/y/z", "z", "/x/y")
    ])
def test_absolute_path(input, abs_path, name, parent):
    session = MockIrodsSession()
    ipath = IrodsPath(session, *input)
    assert str(ipath.absolute()) == abs_path
    assert ipath.name == name
    assert isinstance(ipath.parent, IrodsPath)
    assert str(ipath.parent._path) == parent, str(ipath.parent)

@mark.parametrize(
    "path,to_join,result",
    [
        ("/etc", ["test"], "/etc/test"),
        ("123", ["test", "test2"], "123/test/test2"),
        ("~", [IrodsPath(MockIrodsSession(), "test")], "~/test")
    ]
)
def test_join_path(path, to_join, result):
    irods_path = IrodsPath(MockIrodsSession(), path)
    assert str(irods_path.joinpath(*to_join)._path) == result
