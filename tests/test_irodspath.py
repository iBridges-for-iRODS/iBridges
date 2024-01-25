from pathlib import PureWindowsPath
from pathlib import PurePosixPath

class MockIrodsSession:
    zone = "testzone"
    user = "testuser"
    host = "test.host.nl"
    server_version = "test_version"
    port = 9876
    
    def home(self):
        return "/"+self.zone+"/home/"+self.user

    def cwd(self):
        self.home()+"/mock"

# IrodsPath tests
mock_session = MockIrodsSession()
dirname = "blabla"
filename = "blublub"
irods_path = IrodsPath(mock_session, dirname, filename) 
windows_path = "windows\path\directory"
linux_path = "linux/or/mac/path"

def test_absolute_path():
    assert irods_path.absolute_path() == session.home()+"/"+dirname+"/"+filename

def test_name():
    assert irods_path.name == filename

def test_parent():
    assert irods_path.parent == session.home()+"/"+dirname

def test_raw_paths():
    assert irods_path._raw_paths == [mocksession.zone, "home", 
                                     mock_session.user, dirname, filename]

def test_join_win():
    assert irods_path.joinpath(windows_path)._raw_paths == [mocksession.zone, "home",
                                                            mock_session.user, dirname, filename,
                                                            "windows", "path", "directory"]

def test_join_linux():
    assert irods_path.joinpath(linux_path)._raw_paths == [mocksession.zone, "home",
                                                          mock_session.user, dirname, filename,
                                                          "linux", "or", "mac", "path"]


