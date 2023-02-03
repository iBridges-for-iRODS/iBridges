"""iBridges utility classes and functions.

"""
import datetime
import logging
import logging.handlers
import json
import os
import pathlib
import socket
import sys

import irods.collection
import irods.data_object
import irods.exception
import irods.path


def is_posix() -> bool:
    """Determine POSIXicity.

    Returns
    -------
    bool
        Whether or not this is a POSIX operating system.
    """
    return sys.platform not in ['win32', 'cygwin']


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
        if is_posix() or cls._posix:
            path = pathlib.PurePosixPath(*args)
        else:
            path = pathlib.PureWindowsPath(*args)
        return super().__new__(cls, path.__str__())

    def __init__(self, *args):
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
            if is_posix():
                self._path = pathlib.PurePosixPath(*self.args)
            else:
                self._path = pathlib.PureWindowsPath(*self.args)
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
    def suffixes(self) -> list:
        """A list of the final component's suffixes, if any.  These
        include the leading periods. For example: ['.tar', '.gz'].

        Returns
        -------
        list[str]
            Suffixes of the path.

        """
        return self.path.suffixes


class IrodsPath(PurePath, irods.path.iRODSPath):
    """A pure POSIX path without file system functionality based on the
    best of str, pathlib, and iRODSPath.  This path is normalized upon
    instantiation.

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
    """A platform-dependent local path with file system functionality
    based on the best of str and pathlib.  This path is resolved and
    normalized upon instantiation.

    """

    def __new__(cls, *args, **kwargs):
        """Instantiate a LocalPath.

        Returns
        -------
        LocalPath
            Uninitialized instance.

        """
        if is_posix():
            path = pathlib.PosixPath(*args).resolve()
        else:
            path = pathlib.WindowsPath(*args).resolve()
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
            if is_posix():
                self._path = pathlib.PosixPath(*self.args)
            else:
                self._path = pathlib.WindowsPath(*self.args)
        return self._path

    def absolute(self):
        """Determine an absolute version of this path, i.e., a path
        with a root or anchor.

        No normalization is done, i.e. all '.' and '..' will be kept
        along.  Use resolve() to get the canonical path to a file.

        Returns
        -------
        LocalPath
            Not normalized full path.

        """
        return type(self)(str(self.path.absolute()))

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

    def mkdir(self, mode: int = 511, parents: bool = False, exist_ok: bool = False):
        """Create a new directory at this path.

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

    def resolve(self):
        """Make the path absolute (full path with a root or anchor),
        resolving all symlinks on the way and also normalizing it (for
        example turning slashes into backslashes under Windows).

        Returns
        -------
        LocalPath
            Normalized full path with relative segments and symlinks
            resolved.

        """
        return type(self)(str(self.path.resolve()))

    def stat(self) -> os.stat_result:
        """Run os.stat() on this path.

        Returns
        -------
        os.stat_result
            Stat structure.

        """
        return self.path.stat()

    def unlink(self, missing_ok: bool = False):
        """Remove this file or link.  If the path is a directory, use
        rmdir() instead.

        Parameters
        ----------
        missing_ok : bool
            Ignore missing files/directories.

        """
        self.path.unlink(missing_ok=missing_ok)


class JsonConfig:
    """A configuration stored in a JSON file.

    """

    def __init__(self, filepath: str):
        """Create the configuration.

        Parameters
        ----------
        filepath : str

        """
        self.filepath = LocalPath(filepath)
        self._config = None

    @property
    def config(self) -> dict:
        """Configuration getter.

        Attempt to load a configuration from the JSON file.

        Returns
        -------
        dict or None
            The configuration if it exists.

        """
        if self._config is None:
            if self.filepath.exists():
                with open(self.filepath, 'r', encoding='utf-8') as confd:
                    self._config = json.load(confd)
        return self._config

    @config.setter
    def config(self, conf_dict: dict):
        """Configuration setter.

        Set the configuration to `conf_dict` and write it to the JSON
        file.

        """
        self._config = conf_dict
        with open(self.filepath, 'w', encoding='utf-8') as confd:
            json.dump(conf_dict, confd, indent=4, sort_keys=True)

    @config.deleter
    def config(self):
        """Configuration deleter.

        Delete both the configuration and its JSON file.

        """
        self._config = None
        self.filepath.unlink(missing_ok=True)


def ensure_dir(pathname: str) -> bool:
    """Ensure `pathname` exists as a directory.

    Parameters
    ----------
    pathname : str
        The path to be ensured.

    Returns
    -------
    bool
        If `pathname` exists/was created.

    """
    path = LocalPath(pathname)
    try:
        path.mkdir(parents=True, exist_ok=True)
    except (PermissionError, OSError) as error:
        logging.info(f'Error ensuring directory: {error}')
    return path.is_dir()


def get_local_size(pathnames: list) -> int:
    """Collect the sizes of a set of local files and/or directories and
    determine the total size recursively.

    Parameters
    ----------
    pathnames : list
        Names of input paths.

    Returns
    -------
    int
        Total size [bytes] of all local files found from the paths in
        `pathnames`.

    """
    sizes = []
    for pathname in pathnames:
        path = LocalPath(pathname)
        if path.is_dir():
            for dirname, _, filenames in os.walk(path):
                for filename in filenames:
                    file_ = LocalPath(dirname, filename)
                    sizes.append(file_.stat().st_size)
        elif path.is_file():
            sizes.append(path.stat().st_size)
    return sum(sizes)


def get_data_size(obj: irods.data_object.iRODSDataObject) -> int:
    """For an iRODS data object, get the size as reported by the ICAT.
    This should be considered an estimate if the size cannot be verified.

    Parameters
    ----------
    obj : irods.data_object.iRODSDataObject
        The iRODS data object whose size is to be estimated.

    Returns
    -------
    int
        Estimated size of data object `obj`.

    """
    sizes = {repl.size for repl in obj.replicas if repl.status == '1'}
    if len(sizes) == 1:
        return list(sizes)[0]
    raise irods.exception.MiscException(f'No consistent size found for {obj.path}')


def get_coll_size(coll: irods.collection.iRODSCollection) -> int:
    """For an iRODS collection, sum the sizes of data objects
    recursively as reported by the ICAT.  This should be considered an
    estimate if the sizes cannot be verified.

    Parameters
    ----------
    coll : irods.collection.iRODSCollection
        The iRODS collection whose size is to be estimated.

    Returns
    -------
    int
        Estimated sum of total sizes of data objects in `coll`.

    """
    return sum(
        sum(get_data_size(obj) for obj in objs) for _, _, objs in coll.walk())


def can_connect(hostname: str) -> bool:
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


def get_coll_dict(root_coll: irods.collection.iRODSCollection) -> dict:
    """Create a recursive metadata dictionary for `coll`.

    Parameters
    ----------
    root_coll : irods.collection.iRODSCollection
        Root collection for the metadata gathering.

    Returns
    -------
    dict
        Keys of logical paths, values

    """
    return {this_coll.path: [data_obj.name for data_obj in data_objs]
            for this_coll, _, data_objs in root_coll.walk()}


def get_downloads_dir() -> LocalPath:
    """Find the platform-dependent 'Downloads' directory.

    Returns
    -------
    LocalPath
        Absolute path to 'Downloads' directory.

    """
    if is_posix:
        return LocalPath('~', 'Downloads').expanduser()
    else:
        import winreg
        sub_key = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders'
        downloads_guid = '{374DE290-123F-4565-9164-39C4925E467B}'
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key) as key:
            return LocalPath(winreg.QueryValueEx(key, downloads_guid)[0])


def save_irods_env(ienv: dict) -> LocalPath:
    """Write the `ienv` dictionary to the iRODS environment file
    specified in `ienv` or to the default location.

    Parameters
    ----------
    ienv : dict

    Returns
    -------
    LocalPath
        Absolute path to iRODS environment file just saved.

    """
    if "ui_ienvFilePath" in ienv:
        envname = LocalPath(ienv["ui_ienvFilePath"])
    else:
        envname = LocalPath('~', '.irods', 'irods_environment.json').expanduser()
        ienv["ui_ienvFilePath"] = envname
    # Writes the file.
    JsonConfig(envname).config = ienv
    return envname


def get_working_dir() -> LocalPath:
    """Determine working directory where iBridges started.

    Returns
    -------
    LocalPath
        Directory path of the executable.

    """
    if getattr(sys, 'frozen', False):
        return LocalPath(sys.executable).parent
    elif __file__:
        return LocalPath(__file__).parent
    else:
        return LocalPath('.')


def dir_exists(pathname: str) -> bool:
    """Does `pathname` exist as a directory?

    Parameters
    ----------
    pathname : str
        Name of path to check.

    Returns
    -------
    bool
        Whether the directory exists.

    """
    return LocalPath(pathname).is_dir()


def file_exists(pathname: str) -> bool:
    """Does `pathname` exist as a file?

    Parameters
    ----------
    pathname : str
        Name of path to check.

    Returns
    -------
    bool
        Whether the file exists.

    """
    return LocalPath(pathname).is_file()


def setup_logger(logdir: str, appname: str):
    """Initialize the application logging service.

    Parameters
    ----------
    logdir : str
        Path to logging location.
    appname : str
        Base name for the log file.

    """
    logdir = LocalPath(logdir)
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
        underscores = f'{"_" * 50}\n'
        logfd.write(underscores * 2)
        logfd.write(f'\t\t{datetime.datetime.now().isoformat()}\n')
        logfd.write(underscores * 2)


def bytes_to_str(value: int) -> str:
    """Render incoming number of bytes to a string with units.

    Parameters
    ----------
    value : int
        Number of bytes.

    Returns
    -------
    str
        Rendered string with units.

    """
    if value < 1e12:
        return f'{value / 1e9:.3f} GB'
    else:
        return f'{value / 1e12:.3f} TB'
