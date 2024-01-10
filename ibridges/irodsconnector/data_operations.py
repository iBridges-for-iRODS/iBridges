""" collections and data objects
"""
from typing import Optional, Union
from pathlib import Path

import irods.collection
import irods.data_object
import irods.exception

from ibridges.irodsconnector import keywords as kw
from ibridges.irodsconnector.session import Session
from ibridges.utils.path import IrodsPath


class DataOperations():
    """ Irods collections and data objects operations"""

    def __init__(self, session: Session):
        """ iRODS data operations initialization

            Parameters
            ----------
            session : Session
                instance of the Session class

        """
        self.session = session

    def get_dataobject(self, path: IrodsPath) -> irods.data_object.iRODSDataObject:
        """Instantiate an iRODS data object.

        Parameters
        ----------
        path : str
            Name of an iRODS data object.

        Returns
        -------
        iRODSDataObject
            Instance of the data object with `path`.

        """
        if path.is_dataobject():
            return self.session.irods_session.data_objects.get(str(path))
        raise irods.exception.DataObjectDoesNotExist(path)

    @staticmethod
    def obj_replicas(obj: irods.data_object.iRODSDataObject) -> list[tuple[int, str, str, int, str]]:
        """Retrieves information about replicas (copies of the file on different resources) 
        of the data object in the iRODS system.

        Parameters
        ----------
        obj : irods.data_object.iRODSDataObject
            The data object

        Returns
        -------
        list(tuple(int, str, str. int, str))
            List with tuple where each tuple contains replica index/number, resource name on which 
            the replica is stored about one replica, replica checksum, replica size, 
            replica status of the replica
        """
        replicas = []
        for r in obj.replicas:
            replicas.append((r.number, r.resource_name, r.checksum))

        return replicas

    def get_collection(self, path: IrodsPath) -> irods.collection.iRODSCollection:
        """Instantiate an iRODS collection.

        Parameters
        ----------
        path : str
            Name of an iRODS collection.

        Returns
        -------
        iRODSCollection
            Instance of the collection with `path`.

        """
        if path.is_collection():
            return self.session.irods_session.collections.get(str(path))
        raise irods.exception.CollectionDoesNotExist(path)

    @staticmethod
    def has_type_dataobj(item) -> bool:
        return isinstance(item, irods.data_object.iRODSDataObject)

    @staticmethod
    def has_type_collection(item) -> bool:
        return isinstance(item, irods.collection.iRODSCollection)

    def irods_put(self, local_path: Path, irods_path: IrodsPath, resc_name: str = ''):
        """Upload `local_path` to `irods_path` following iRODS `options`.

        Parameters
        ----------
        local_path : str
            Path of local file.
        irods_path : str
            Path of iRODS data object or collection.
        resc_name : str
            Optional resource name.

        """
        if not local_path.is_file():
            raise ValueError("local_path must be a file.")

        options = {
            kw.ALL_KW: '',
            kw.NUM_THREADS_KW: kw.NUM_THREADS,
            kw.REG_CHKSUM_KW: '',
            kw.VERIFY_CHKSUM_KW: ''
        }
        if resc_name not in ['', None]:
            options[kw.RESC_NAME_KW] = resc_name
        self.session.irods_session.data_objects.put(local_path, str(irods_path), **options)

    def irods_get(self, irods_path: IrodsPath, local_path: Path,
                  overwrite: bool=False, options: Optional[dict] = None):
        """Download `irods_path` to `local_path` following iRODS `options`.

        Parameters
        ----------
        irods_path : str
            Path of iRODS data object.
        local_path : str
            Path of local file or directory/folder.
        options : dict
            iRODS transfer options.

        """
        if not irods_path.is_dataobject():
            raise ValueError("irods_path must be a data object.")
        if options is None:
            options = {}
        options.update({
            kw.NUM_THREADS_KW: kw.NUM_THREADS,
            kw.VERIFY_CHKSUM_KW: '',
            })
        if overwrite:
            options[kw.FORCE_FLAG_KW] = ''

        self.session.irods_session.data_objects.get(str(irods_path), local_path, **options)

    def get_size(self, item: Union[irods.data_object.iRODSDataObject,
                                   irods.collection.iRODSCollection]) -> int:
        """Collect the sizes of a data object or a
        collection.

        Parameters
        ----------
        item : 


        Returns
        -------
        int
            Total size [bytes] of the iRODS object or all iRODS objects in the collection.

        """
        if self.has_type_dataobj(item):
            return item.size
        elif self.has_type_collection(item):
            irods_size = 0
            subcollections = [item]
            while len(subcollections) > 0:
                coll = subcollections.pop()
                for obj in coll.data_objects:
                    irods_size+= obj.size
                subcollections.extend(coll.subcollections)
            return irods_size
        else:
            raise ValueError("Item must be an iRODS object or iRODS collection.")
