from pathlib import PurePosixPath
from pytest import mark
import os
from pathlib import Path

from ibridges import IrodsPath
from ibridges.irodsconnector.data_operations import _create_irods_dest

class MockIrodsSession:
    zone = "testzone"
    user = "testuser"
    host = "test.host.nl"
    server_version = "test_version"
    port = 9876
    home = "/testzone/home/testuser"
    # def home(self):
        # return "/"+self.zone+"/home/"+self.user


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
        ([], "/testzone/home/testuser", "", "."),
        (["~"], "/testzone/home/testuser", "~", "."),
        ([""], "/testzone/home/testuser", "", "."),
        (["."], "/testzone/home/testuser", "", "."),
        ([PurePosixPath(".")], "/testzone/home/testuser", "", "."),
        (["~", "xyz"], "/testzone/home/testuser/xyz", "xyz", "~"),
        (["xyz"], "/testzone/home/testuser/xyz", "xyz", "."),
        ([".", "xyz"], "/testzone/home/testuser/xyz", "xyz", "."),
        ([PurePosixPath("."), "xyz"], "/testzone/home/testuser/xyz", "xyz", "."),
        ([PurePosixPath(".", "xyz")], "/testzone/home/testuser/xyz", "xyz", "."),
        (["/x/y/z"], "/x/y/z", "z", "/x/y"),
        (["/x/y", "z"], "/x/y/z", "z", "/x/y"),
        ([IrodsPath(123, "/x/y"), "z"], "/x/y/z", "z", "/x/y")
        # ([PureWindowsPath("c:\\x\\y\\z")], "c:\\/x/y/z", "z", "/x/y")
    ])
def test_absolute_path(input, abs_path, name, parent):
    session = MockIrodsSession()
    ipath = IrodsPath(session, *input)
    assert ipath.absolute_path() == abs_path
    assert ipath.name == name
    assert isinstance(ipath.parent, IrodsPath)
    assert str(ipath.parent._path) == parent, str(ipath.parent)

@mark.parametrize(
    "path,to_join,result",
    [
        ("/etc", ["test"], "/etc/test"),
        ("123", ["test", "test2"], "123/test/test2"),
        ("~", [IrodsPath(123, "test")], "~/test")
    ]
)
def test_join_path(path, to_join, result):
    irods_path = IrodsPath(123, path)
    assert str(irods_path.joinpath(*to_join)._path) == result

# Create upload and download path tests for data_operations

def test_create_irods_paths():
    session = MockIrodsSession()
    local_path = Path("tests/testdata").absolute()
    irods_path = IrodsPath(123, session.home)
    source_to_dest = _create_irods_dest(local_path, irods_path)
    for source, dest in source_to_dest:
        local_parts = [part.replace(os.sep, "") 
                       for part in source.parts[source.parts.index("testdata"):]]
        irods_parts = dest.parts[dest.parts.index("testdata"):]
        assert local_parts == list(irods_parts)
        assert str(dest).split("testdata")[0].rstrip("/") == session.home
