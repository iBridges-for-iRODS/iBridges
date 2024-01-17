"""
A classes to handle iRODS and local (Win, linux) paths.
"""
import pathlib
import sys
import irods

def is_posix() -> bool:
    """Determine POSIXicity.

    Returns
    -------
    bool
        Whether or not this is a POSIX operating system.
    """
    return sys.platform not in ['win32', 'cygwin']


class IrodsPath(pathlib.PurePosixPath):
    """Extending the posix path functionalities with iRODS functionalities."""

    def __init__(self, session, *args, **kwargs):
        self.session = session
        super().__init__()


    def __new__(cls, session, *args, **kwargs):
        """
        Instantiate an IrodsPath

        Returns
        -------
        IrodsPath
           Instance of PurePosixPath
        """
        return super().__new__(cls, *args, **kwargs)

    def remove(self):
        """
        Remove the collection or data object.
        """

    def rename(self):
        """
        Rename the collection or data object
        """

    def collection_exists(self) -> bool:
        """
        Check if the path points to an iRODS collection
        """
        return self.session.irods_session.collections.exists(str(self))

    def dataobject_exists(self) -> bool:
        """
        Check if the path points to an iRODS data object
        """
        return self.session.irods_session.data_objects.exists(str(self))

    def absolute(self):
        """
        Return the path if the path starts with '/zone/home', otherwise 
        concatenate the '/zone/home' prefix to the current path.
        """

    def exists(self) -> bool:
        """
        Check if the path already exists on the iRODS server
        """

    def home(self):
        """
        If the session environment defines an 'irods_home', checks if this path exists 
        and returns the path.
        If 'irods_home' is not defined, returns the path /zone/home
        """

    def walk(self, depth: int):
        """
        Walk on a collection.

        Parameters
        ----------
        depth : int
            Stops after depth many iterations, even if the tree is deeper.
        """
