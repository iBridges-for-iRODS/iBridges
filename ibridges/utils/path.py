"""
A classes to handle iRODS and local (Win, linux) paths.
"""
import pathlib
import sys
import irods

from typing import Optional, Union

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
        """Removes the data behind an iRODS path
        """
        try:
            if self.collection_exists():
                coll = self.session.irods_session.collections.get(str(self))
                coll.remove()
            elif self.dataobject_exists():
                obj = self.session.irods_session.data_objects.get(irods_path)
                obj.unlink()
        except irods.exception.CUT_ACTION_PROCESSED_ERR:
            raise(irods.exception.CUT_ACTION_PROCESSED_ERR('iRODS server forbids action.'))

    @staticmethod
    def create_collection(session,  coll_path: str) -> irods.collection.iRODSCollection:
        """Create a collection and all collections in its path. Return he collection. If the
        collection already exists, return ir.
        
        Return
        ------
        irods.collection.iRODSCollection
            The 
        """
        try:
            return session.irods_session.collections.create(str(coll_path))
        except irods.exception.CUT_ACTION_PROCESSED_ERR:
            raise(irods.exception.CUT_ACTION_PROCESSED_ERR('iRODS server forbids action.'))

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
