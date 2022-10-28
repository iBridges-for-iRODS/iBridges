import datetime
import logging
import logging.handlers
import json
import os
import pathlib
import socket
import sys


def ensure_dir(path):
    try:
        if not os.path.exists(path):
            os.makedirs(path)
        return True
    except:
        return False 


def getSize(pathList):
    size = 0
    for p in pathList:
        if os.path.isdir(p):
            for dirpath, dirnames, filenames in os.walk(p):
                for i in filenames:
                    f = os.path.join(dirpath, i)
                    size += os.path.getsize(f)
        elif os.path.isfile(p):
            size = size + os.path.getsize(p)
    return size


def can_connect(hostname):
    """Check connectivity to an iRODS server.

    Parameters
    ----------
    hostname : str
        FQDN/IP of an iRODS server.

    Returns
    -------
    bool
        Connection to `hostname` possible.

    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.settimeout(10.0)
            sock.connect((hostname, 1247))
            return True
        except socket.error:
            return False


def walkToDict(root):
    #irods collection
    items = []
    for collection, subcolls, _ in root.walk():
        items.append(collection.path)
        items.extend([s.path for s in subcolls])
    walkDict = {key: None for key in sorted(set(items))}
    for collection, _,  objs in root.walk():
        walkDict[collection.path] = [o.name for o in objs]

    return walkDict


def getDownloadDir():
    if os.name == 'nt':
        import winreg
        sub_key = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders'
        downloads_guid = '{374DE290-123F-4565-9164-39C4925E467B}'
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key) as key:
            location = winreg.QueryValueEx(key, downloads_guid)[0]
        return location
    else:
        return os.path.join(os.path.expanduser('~'), 'Downloads')


def saveIenv(ienv):
    if "ui_ienvFilePath" in ienv:
        envFile = ienv["ui_ienvFilePath"]
    else:
        envFile = os.path.join(os.path.expanduser("~"), ".irods"+os.sep+"irods_environment.json")
        ienv["ui_ienvFilePath"] = envFile
    with open(envFile, 'w') as f:
        json.dump(ienv, f, indent=4)
    return envFile


# needed to get the workdir for executable & normal operation
def get_filepath():
    if getattr(sys, 'frozen', False):
        file_path = os.path.dirname(sys.executable)
    elif __file__:
        file_path = os.path.dirname(__file__)
    return file_path

# check if a given directory exists on the drive
def check_direxists(dir):
    if _check_exists(dir):
        return os.path.isdir(dir)
    return False

def check_fileexists(file):
    if _check_exists(file):
        return os.path.isfile(file)
    return False

def _check_exists(fname):
    if fname is None:
        return False
    if not os.path.exists(fname):
        return False
    return True


def setup_logger(logdir, appname):
    """Initialize the application logging service.

    Parameters
    ----------
    logdir : str, pathlib.Path
        Path to logging location.
    appname : str
        Base name for the log file.

    """
    logdir = pathlib.Path(logdir)
    logfile = logdir.joinpath(f'{appname}.log')
    log_format = '[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s'
    handlers = [
        logging.handlers.RotatingFileHandler(logfile, 'a', 100000, 1),
        logging.StreamHandler(sys.stdout),
    ]
    logging.basicConfig(
        format=log_format, level=logging.INFO, handlers=handlers)
    # Indicate start of a new session
    with open(logfile, 'a', encoding='utf-8') as logfd:
        logfd.write('\n\n')
        underscores = f'{"_"*50}\n'
        logfd.write(underscores)
        logfd.write(underscores)
        logfd.write(f'\t\t{datetime.datetime.now().isoformat()}\n')
        logfd.write(underscores)
        logfd.write(underscores)


class PurePath(str):
    """A platform-dependent pure path without file system functionality
    based on the best of str and pathlib.

    """

    _path = None
    _posix = None

    def __new__(cls, *args):
        """Instantiate a PurePath from whole paths or segments of paths,
        absolute or logical.

        Returns
        -------
        PurePath
            Uninitialized instance.

        """
        if sys.platform in ['win32', 'cygwin'] and not cls._posix:
            path = pathlib.PureWindowsPath(*args)
        else:
            path = pathlib.PurePosixPath(*args)
        return super().__new__(cls, path.__str__())

    def __init__(self, *args) -> None:
        """Initialize a PurePath.

        """
        self.args = args

    def __str__(self) -> str:
        """Render Paths into a string.

        Returns
        -------
        str
            String value of the pathlib.Path.

        """
        return self.path.__str__()

    def __repr__(self) -> str:
        """Render Paths into a representation.

        Returns
        -------
        str
            Representation of the pathlib.Path.

        """
        return f'{self.__class__.__name__}("{self.path.__str__()}")'

    @property
    def path(self) -> pathlib.PurePath:
        """A pathlib.Path instance providing extra functionality.

        Returns
        -------
        pathlib.PurePath
            Initialized from self.args.

        """
        if self._path is None:
            if sys.platform in ['win32', 'cygwin']:
                self._path = pathlib.PureWindowsPath(*self.args)
            else:
                self._path = pathlib.PurePosixPath(*self.args)
        return self._path

    def joinpath(self, *args):
        """Combine this path with one or several arguments, and return
        a new path representing either a subpath (if all arguments are
        relative paths) or a totally different path (if one of the
        arguments is anchored).

        Returns
        -------
        PurePath
            Joined Path.

        """
        return type(self)(str(self.path.joinpath(*args)))

    def with_suffix(self, suffix: str):
        """Create a new path with the file `suffix` changed.  If the
        path has no `suffix`, add given `suffix`.  If the given
        `suffix` is an empty string, remove the `suffix` from the path.

        Parameters
        ----------
        suffix : str
            New extension for the file 'stem'.

        Returns
        -------
        PurePath
            Suffix-updated Path.

        """
        return type(self)(str(self.path.with_suffix(suffix)))

    @property
    def name(self) -> str:
        """The final path component, if any.

        Returns
        -------
        str
            Name of the Path.

        """
        return self.path.name

    @property
    def parent(self):
        """The logical parent of the path.

        Returns
        -------
        PurePath
            Parent of the Path.

        """
        return type(self)(str(self.path.parent))

    @property
    def parts(self) -> tuple:
        """An object providing sequence-like access to the components
        in the filesystem path.

        Returns
        -------
        tuple
            Parts of the Path.

        """
        return self.path.parts

    @property
    def stem(self) -> str:
        """The final path component, minus its last suffix.

        Returns
        -------
        str
            Stem of the Path.

        """
        return self.path.stem

    @property
    def suffix(self) -> str:
        """The final component's last suffix, if any.  This includes
        the leading period. For example: '.txt'.

        Returns
        -------
        str
            Suffix of the path.

        """
        return self.path.suffix

    @property
    def suffixes(self) -> list[str]:
        """A list of the final component's suffixes, if any.  These
        include the leading periods. For example: ['.tar', '.gz'].

        Returns
        -------
        list[str]
            Suffixes of the path.

        """
        return self.path.suffixes


class IrodsPath(PurePath):
    """A pure POSIX path without file system functionality based on the
    best of str and pathlib.

    """

    def __new__(cls, *args):
        """Instantiate an IrodsPath.

        Returns
        -------
        IrodsPath
            Uninitialized instance.

        """
        cls._posix = True
        path = pathlib.PurePosixPath(*args)
        return super().__new__(cls, path.__str__())

    @property
    def path(self) -> pathlib.PurePosixPath:
        """A pathlib.PurePosixPath instance providing extra
        functionality.

        Returns
        -------
        pathlib.PurePosixPath
            Initialized from self.args.

        """
        if self._path is None:
            self._path = pathlib.PurePosixPath(*self.args)
        return self._path


class LocalPath(PurePath):
    """A local path with file system functionality based on the
    best of str and pathlib.

    """

    def __new__(cls, *args, **kwargs):
        """Instantiate a LocalPath.

        Returns
        -------
        LocalPath
            Uninitialized instance.

        """
        if sys.platform in ['win32', 'cygwin']:
            path = pathlib.WindowsPath(*args)
        else:
            path = pathlib.PosixPath(*args)
        return super().__new__(cls, path.__str__())

    @property
    def path(self) -> pathlib.Path:
        """A pathlib.Path instance providing extra functionality.

        Returns
        -------
        pathlib.Path
            Initialized from self.args.

        """
        if self._path is None:
            if sys.platform in ['win32', 'cygwin']:
                self._path = pathlib.WindowsPath(*self.args)
            else:
                self._path = pathlib.PosixPath(*self.args)
        return self._path

    def exists(self) -> bool:
        """Whether this path exists.

        Returns
        -------
        bool
            Path exists or not.

        """
        # try:
        return self.path.exists()
        # except AttributeError:
        #     return os.path.exists(self.path)

    def expanduser(self):
        """Return a new path with expanded ~ and ~user constructs (as
        returned by os.path.expanduser)

        Returns
        -------
        LocalPath
            User-expanded Path.
        """
        try:
            return type(self)(str(self.path.expanduser()))
        except AttributeError:
            return type(self)(os.path.expanduser(self.path))

    def glob(self, pattern: str) -> iter:
        """Iterate over this subtree and yield all existing files (of
        any kind, including directories) matching the given relative
        `pattern`.

        Parameters
        ----------
        pattern : str
            Wildcard patter to match files.

        Returns
        -------
        iter
            Generator of matches.

        """
        return self.path.glob(pattern=pattern)

    def is_dir(self) -> bool:
        """Whether this path is a directory.

        Returns
        -------
        bool
            Is a directory (folder) or not.

        """
        # try:
        return self.path.is_dir()
        # except AttributeError:
        #     return os.path.isdir(self.path)

    def is_file(self) -> bool:
        """Whether this path is a regular file (also True for symlinks
        pointing to regular files)

        Returns
        -------
        bool
            Is a regular file (symlink) or not.

        """
        # try:
        return self.path.is_file()
        # except AttributeError:
        #     return os.path.isfile(os.path)

    def mkdir(self, mode: int = 511, parents: bool = False, exist_ok: bool = False) -> None:
        """Create a new directory at this given path.

        Parameters
        ----------
        mode : int
            Creation mode of the directory (folder).
        parents : bool
            Create the parents too?
        exist_ok : bool
            Okay if directory already exists?

        """
        try:
            self.path.mkdir(mode=mode, parents=parents, exist_ok=exist_ok)
        except AttributeError:
            pass
