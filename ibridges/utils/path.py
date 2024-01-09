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
        if self.session.irods_session.collections.exists(item.path):
            logging.info('IRODS DELETE: %s', item.path)
            try:
                item.remove(recurse=True, force=True)
            except irods.exception.CAT_NO_ACCESS_PERMISSION as error:
                logging.error('IRODS DELETE: no permissions %s', item.path)
                raise error
        elif self.session.irods_session.data_objects.exists(item.path):
            logging.info('IRODS DELETE: %s', item.path)
            try:
                item.unlink(force=True)
            except irods.exception.CAT_NO_ACCESS_PERMISSION as error:
                logging.error('IRODS DELETE: no permissions %s', item.path)
                raise error
    
    def rename(self) -> IrodsPath:
        """
        Rename the collection or data object
        """

    def is_collection(self) -> bool:
        """
        Check if the path points to an iRODS collection
        """
        return self.session.irods_session.collections.exists(path)

    def is_dataobject(self) -> bool:
        """
        Check if the path points to an iRODS data object
        """
        return self.session.irods_session.data_objects.exists(path)

    def absolute(self) -> IrodsPath:
        """
        Return the path if the path starts with '/zone/home', otherwise 
        concatenate the '/zone/home' prefix to the current path.
        """

    def exists(self) -> bool:
        """
        Check if the path already exists on the iRODS server
        """

    def home(self) -> IrodsPath:
        """
        If the session environment defines an 'irods_home', checks if this path exists 
        and returns the path.
        If 'irods_home' is not defined, returns the path /zone/home
        """

    def walk(self, depth: int) -> tuple(IrodsPath, list(IrodsPath), list(IrodsPath)):
        """
        Walk on a collection.

        Parameters
        ----------
        depth : int
            Stops after depth many iterations, even if the tree is deeper.
        """

    def ensure_collection(coll_name, self) -> irods.collection.iRODSCOllection:
        """Create a collection with `coll_name` if one does
        not exist.

        Parameters
        ----------
        coll_name : str
            Name of the collection to check/create.

        Returns
        -------
        iRODSCollection
            Existing or new iRODS collection.

        Raises:
            irods.exception.CAT_NO_ACCESS_PERMISSION
            irods.exception.CAT_NAME_EXISTS_AS_DATAOBJ
        """
        try:
            if self.session.irods_session.collections.exists(coll_name):
                return self.session.irods_session.collections.get(coll_name)
            return self.session.irods_session.collections.create(coll_name)
        except irods.exception.CAT_NO_ACCESS_PERMISSION as error:
            logging.info('ENSURE COLLECTION', exc_info=True)
            raise error

    def ensure_data_object(self) -> irods.data_object:
        """
        Creates an empty data object if the path does not exist and returns the data object.
        Throws irods.exception.CAT_NAME_EXISTS_AS_COLLECTION if path already exists as collection.
        """
