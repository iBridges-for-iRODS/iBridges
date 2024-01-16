""" collections and data objects
"""
from typing import Optional, Union
from pathlib import Path
from os import walk, makedirs

import irods.collection
import irods.data_object
import irods.exception
from irods.models import DataObject

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
            replicas.append((r.number, r.resource_name, r.checksum, r.size, r.status))

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

    def irods_put(self, local_path: Path, irods_path: IrodsPath, resc_name: str = '',
                  options: Optional[dict] = None):
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

    def upload_collection(self, local_path: Path, irods_path: IrodsPath, 
                          resc_name: str = '', options: Optional[dict] = None):
        """Upload a local directory to iRODS

        Parameters
        ----------
        local_path : Path
            Absolute path to the directory to upload
        irods_path : IrodsPath
            Absolute irods destination path
        resc_name : str
            Name of the resource to which data is uploaded, by default the server will decide
        options : dict
            More options for the upload
        """


        # get all files and their relative path to local_path
        if not local_path.is_dir():
            raise ValueError("local_path must be a directory.")

        files = [] # (rel_path, name)

        for w in walk(local_path):
            files.extend([(w[0].removeprefix(str(local_path)), f) for f in w[2]])

        upload_path = IrodsPath(self.session,
                                str(irods_path.joinpath(local_path.name)))
        _ = self.create_collection(upload_path)

        for f in files:
            # ensure iRODS collection exists
            _ = self.create_collection(upload_path.joinpath(f[0].lstrip('/')))
            # call irods put for Path(local_path, f[0], f[1]) to destination collection
            dest = IrodsPath(self.session, str(upload_path), f[0].lstrip('/'))
            self.irods_put(Path(str(local_path), f[0].lstrip('/'), f[1]), dest,
                           resc_name, options)

    def download_collection(self, irods_path: IrodsPath, local_path: Path,
                            overwrite: bool=False, options: Optional[dict]=None):
        """Download a collection to the local filesystem

        Parameters
        ----------
        irods_path : IrodsPath
            Absolute irods source path pointing to a collection
        local_path : Path
            Absolute path to the destination directory
        overwrite : bool
            Overwrite existing local data
        options : dict
            More options for the download
        """
        if not irods_path.is_collection():
            raise ValueError("irods_path must be a collection.")

        # get all data objects
        coll = self.get_collection(irods_path)
        all_objs = self._get_data_objects(coll)

        for o in all_objs:
            # ensure local folder exists
            dest = Path(local_path, o[0].removeprefix(str(irods_path)).lstrip('/'))
            if not dest.is_dir():
                os.makedirs(dest)
            self.irods_get(IrodsPath(self.session, o[0], o[1]), local_path, overwrite, options)

    def get_size(self, item: Union[irods.data_object.iRODSDataObject,
                             irods.collection.iRODSCollection]) -> int:
        """Collect the sizes of a data object or a
        collection.

        Parameters
        ----------
        item : iRODSDataObject or iRODSCollection


        Returns
        -------
        int
            Total size [bytes] of the iRODS object or all iRODS objects in the collection.

        """
        if self.has_type_dataobj(item):
            return item.size
        elif self.has_type_collection(item):
            all_objs = self._get_data_objects(item)
            return sum([size for _, _, size, _ in all_objs])
        else:
            raise ValueError("Item must be an iRODS object or iRODS collection.")


    def _get_data_objects(self, coll: irods.collection.iRODSCollection) -> list[str, str, int, str]:
        """Retrieve all data objects in a collection and all its subcollections.

        Parameters
        ----------
        coll : irods.collection.iRODSCollection
            The collection to search for all data pbjects

        Returns
        -------
        list of all data objects
            [(cllection path, name, size, checksum)]
        """

        # all objects in the collection
        objs = [(obj.collection.path, obj.name, obj.size, obj.checksum) for obj in coll.data_objects]

        # all objects in subcollections
        data_query = self.session.irods_session.query(kw.COLL_NAME, kw.DATA_NAME,
                                                      DataObject.size, DataObject.checksum)
        data_query = data_query.filter(kw.LIKE(kw.COLL_NAME, coll.path+"/%"))
        for res in data_query.get_results():
            path, name, size, checksum = res.values()
            objs.append((path, name, size, checksum))

        return obj

    def create_collection(self, coll_path: Union[IrodsPath, str]) -> irods.collection.iRODSCollection:
        """Create a collection and all collections in its path.

        Parameters
        ----------
        coll_path: IrodsPath
            Collection path
        """
        return self.session.irods_session.collections.create(str(coll_path))
