""" collections and data objects
"""
import logging

import irods.collection
import irods.data_object
import irods.exception

from ibridges import utils
from ibridges.irodsconnector import keywords as kw
from ibridges.irodsconnector import resources, session


class DataOperation(object):
    """ Irods collections and data objects operations"""

    def __init__(self, resources: resources.Resources, session: session.Session):
        """ iRODS data operations initialization

            Parameters
            ----------
            resources : resource.Resource
                Instance of the Resource class
            session : session.Session
                instance of the Session class

        """
        self.resources = resources
        self.session = session

    @staticmethod
    def is_dataobject_or_collection(obj: None):
        """Check if `obj` is an iRODS data object or collection.

        Parameters
        ----------
        obj : iRODS object instance
            iRODS instance to check.

        Returns
        -------
        bool
            If `obj` is an iRODS data object or collection.

        """
        return isinstance(obj, (
            irods.data_object.iRODSDataObject,
            irods.collection.iRODSCollection))

    def dataobject_exists(self, path: str) -> bool:
        """Check if an iRODS data object exists.

        Parameters
        ----------
        path : str
            Name of an iRODS data object.

        Returns
        -------
        bool
            Existence of the data object with `path`.

        """
        return self.session.irods_session.data_objects.exists(path)

    def collection_exists(self, path: str) -> bool:
        """Check if an iRODS collection exists.

        Parameters
        ----------
        path : str
            Name of an iRODS collection.

        Returns
        -------
        bool
            Existance of the collection with `path`.

        """
        return self.session.irods_session.collections.exists(path)

    @staticmethod
    def is_dataobject(obj) -> bool:
        """Check if `obj` is an iRODS data object.

        Parameters
        ----------
        obj : iRODS object instance
            iRODS instance to check.

        Returns
        -------
        bool
            If `obj` is an iRODS data object.

        """
        return isinstance(obj, irods.data_object.iRODSDataObject)

    @staticmethod
    def is_collection(obj) -> bool:
        """Check if `obj` is an iRODS collection.

        Parameters
        ----------
        obj : iRODS object instance
            iRODS instance to check.

        Returns
        -------
        bool
            If `obj` is an iRODS collection.

        """
        return isinstance(obj, irods.collection.iRODSCollection)


    def ensure_data_object(self, data_object_name: str) -> irods.data_object.iRODSDataObject:
        """Optimally create a data object with `data_object_name` if one does
        not exist.

        Parameters
        ----------
        data_object_name : str
            Name of the data object to check/create.

        Returns
        -------
        iRODS Data object
            Existing or new iRODS data object.

        Raises:
            irods.exception.CAT_NO_ACCESS_PERMISSION

        """
        try:
            if self.session.irods_session.data_objects.exists(data_object_name):
                return self.session.irods_session.data_objects.get(data_object_name)
            return self.session.irods_session.data_objects.create(data_object_name)
        except irods.exception.CAT_NO_ACCESS_PERMISSION as error:
            logging.info('ENSURE DATA OBJECT', exc_info=True)
            raise error

    def ensure_coll(self, coll_name: str) -> irods.collection.iRODSCollection:
        """Optimally create a collection with `coll_name` if one does
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

        """
        try:
            if self.session.irods_session.collections.exists(coll_name):
                return self.session.irods_session.collections.get(coll_name)
            return self.session.irods_session.collections.create(coll_name)
        except irods.exception.CAT_NO_ACCESS_PERMISSION as error:
            logging.info('ENSURE COLLECTION', exc_info=True)
            raise error

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

    def get_collection(self, path: str) -> irods.collection.iRODSCollection:
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

    def irods_get(self, irods_path: str, local_path: str, options: dict = None):
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


    def delete_data(self, item: (irods.collection.iRODSCollection, irods.data_object.iRODSDataObject)):
        """
        Delete a data object or a collection recursively.
        Parameters
        ----------
        item: iRODS data object or collection
            item to delete
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

    def get_irods_size(self, path_names: list) -> int:
        """Collect the sizes of a set of iRODS data objects and/or
        collections and determine the total size.

        Parameters
        ----------
        path_names : list
            Names of logical iRODS paths.

        Returns
        -------
        int
            Total size [bytes] of all iRODS objects found from the
            logical paths in `path_names`.

        """
        irods_sizes = []
        for path_name in path_names:
            irods_name = utils.path.IrodsPath(path_name)
            if self.collection_exists(irods_name):
                irods_sizes.append(
                    utils.utils.get_coll_size(
                        self.get_collection(irods_name)))
            elif self.dataobject_exists(irods_name):
                irods_sizes.append(
                    utils.utils.get_data_size(
                        self.get_dataobject(irods_name)))
        return sum(irods_sizes)
