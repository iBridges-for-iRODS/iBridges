""" collections and data objects
"""
import logging
from typing import Optional, Union

import irods.collection
import irods.data_object
import irods.exception

from ibridges.irodsconnector import keywords as kw
from ibridges.irodsconnector.resources import Resources
from ibridges.irodsconnector.session import Session
from ibridges.utils.path import IrodsPath, LocalPath


class DataOperation():
    """ Irods collections and data objects operations"""

    def __init__(self, resources: Resources, session: Session):
        """ iRODS data operations initialization

            Parameters
            ----------
            resources : Resource
                Instance of the Resource class
            session : Session
                instance of the Session class

        """
        self.resources = resources
        self.session = session

    def get_dataobject(self, path: str) -> irods.data_object.iRODSDataObject:
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
        if self.dataobject_exists(path):
            return self.session.irods_session.data_objects.get(path)
        raise irods.exception.DataObjectDoesNotExist(path)

    @static
    def obj_replicas(obj: irods.data_object.iRODSDataObject) -> list(tuple(int, str, str. int, str)):
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
        if self.collection_exists(path):
            return self.session.irods_session.collections.get(path)
        raise irods.exception.CollectionDoesNotExist(path)

    def irods_put(self, local_path: str, irods_path: str, resc_name: str = ''):
        """Upload `local_path` to `irods_path` following iRODS `options`.

        Parameters
        ----------
        local_path : str
            Path of local file or directory/folder.
        irods_path : str
            Path of iRODS data object or collection.
        resc_name : str
            Optional resource name.

        """
        options = {
            kw.ALL_KW: '',
            kw.NUM_THREADS_KW: kw.NUM_THREADS,
            kw.REG_CHKSUM_KW: '',
            kw.VERIFY_CHKSUM_KW: ''
        }
        if resc_name not in ['', None]:
            options[kw.RESC_NAME_KW] = resc_name
        self.session.irods_session.data_objects.put(local_path, irods_path, **options)

    def irods_get(self, irods_path: IrodsPath, local_path: LocalPath,
                  options: Optional[dict] = None):
        """Download `irods_path` to `local_path` following iRODS `options`.

        Parameters
        ----------
        irods_path : str
            Path of iRODS data object or collection.
        local_path : str
            Path of local file or directory/folder.
        options : dict
            iRODS transfer options.

        """
        if options is None:
            options = {}
        options.update({
            kw.NUM_THREADS_KW: kw.NUM_THREADS,
            kw.VERIFY_CHKSUM_KW: '',
            })
        self.session.irods_session.data_objects.get(irods_path, local_path, **options)

# TODOx: find get_coll_size methods
    # def get_irods_size(self, path_names: list) -> int:
    #     """Collect the sizes of a set of iRODS data objects and/or
    #     collections and determine the total size.

    #     Parameters
    #     ----------
    #     path_names : list
    #         Names of logical iRODS paths.

    #     Returns
    #     -------
    #     int
    #         Total size [bytes] of all iRODS objects found from the
    #         logical paths in `path_names`.

    #     """
    #     irods_sizes = []
    #     for path_name in path_names:
    #         irods_name = utils.path.IrodsPath(path_name)
    #         if self.collection_exists(irods_name):
    #             irods_sizes.append(
    #                 utils.utils.get_coll_size(
    #                     self.get_collection(irods_name)))
    #         elif self.dataobject_exists(irods_name):
    #             irods_sizes.append(
    #                 utils.utils.get_data_size(
    #                     self.get_dataobject(irods_name)))
    #     return sum(irods_sizes)
