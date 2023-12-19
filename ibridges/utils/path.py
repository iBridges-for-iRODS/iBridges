"""
A classes to handle iRODS and local (Win, linux) paths.
"""
import pathlib
import sys


def is_posix() -> bool:
    """Determine POSIXicity.

    Returns
    -------
    bool
        Whether or not this is a POSIX operating system.
    """
    return sys.platform not in ['win32', 'cygwin']


class IrodsPath(pathlib.PurePosixPath):
    """A path on the irods server."""
    # """
    # A POSIX path without file system functionality.
    # """

    # def __new__(cls, *args):
    #     """
    #     Instantiate an IrodsPath

    #     Returns
    #     -------
    #     IrodsPath
    #         Instance of PurePosixPath
    #     """
    #     path = pathlib.PurePosixPath(*args)
    #     return path


class LocalPath(pathlib.Path):
    """A local path."""
    # """
    # A platform-dependent local path with file system functionality.
    # """

    # def __new__(cls, *args, **kwargs):
    #     """Instantiate a LocalPath.

    #     Returns
    #     -------
    #     LocalPath
    #         Instance of a PosixPath or WindowsPath.

    #     """
    #     if is_posix():
    #         path = pathlib.PosixPath(*args)
    #     else:
    #         path = pathlib.WindowsPath(*args)
    #     return path
