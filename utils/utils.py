"""iBridges utility classes and functions.

"""
import datetime
import logging
import logging.handlers
import os
import socket
import sys

import irods.collection
import irods.data_object
import irods.exception
import irods.path

from . import path


def is_posix() -> bool:
    """Determine POSIXicity.

    Returns
    -------
    bool
        Whether or not this is a POSIX operating system.
    """
    return sys.platform not in ['win32', 'cygwin']


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
    dirpath = path.LocalPath(pathname)
    try:
        dirpath.mkdir(parents=True, exist_ok=True)
    except (PermissionError, OSError) as error:
        logging.info(f'Error ensuring directory: {error}')
    return dirpath.is_dir()


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
        pathobj = path.LocalPath(pathname)
        if pathobj.is_dir():
            for dirname, _, filenames in os.walk(pathobj):
                for filename in filenames:
                    filepath = path.LocalPath(dirname, filename)
                    sizes.append(filepath.stat().st_size)
        elif pathobj.is_file():
            sizes.append(pathobj.stat().st_size)
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


def get_downloads_dir() -> path.LocalPath:
    """Find the platform-dependent 'Downloads' directory.

    Returns
    -------
    LocalPath
        Absolute path to 'Downloads' directory.

    """
    if is_posix():
        return path.LocalPath('~', 'Downloads').expanduser()
    else:
        import winreg
        sub_key = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders'
        downloads_guid = '{374DE290-123F-4565-9164-39C4925E467B}'
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key) as key:
            return path.LocalPath(winreg.QueryValueEx(key, downloads_guid)[0])


def get_working_dir() -> path.LocalPath:
    """Determine working directory where iBridges started.

    Returns
    -------
    LocalPath
        Directory path of the executable.

    """
    if getattr(sys, 'frozen', False):
        return path.LocalPath(sys.executable).parent
    elif __file__:
        return path.LocalPath(__file__).parent
    else:
        return path.LocalPath('.')


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
    return path.LocalPath(pathname).is_dir()


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
    return path.LocalPath(pathname).is_file()


def setup_logger(logdir: str, appname: str):
    """Initialize the application logging service.

    Parameters
    ----------
    logdir : str
        Path to logging location.
    appname : str
        Base name for the log file.

    """
    logdir = path.LocalPath(logdir).expanduser()
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
