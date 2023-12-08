""" Irods connection factory

"""
import logging

import irods.collection
import irods.data_object
import irods.resource
import irods.session

from . import session
from . import permissions

class IrodsConnector():
    """Top-level connection to the Python iRODS client

    """

    def __init__(self, irods_env: dict, password: str = ''):
        """Initialize connection to iRODS functionality based on the
        user's credentials.

        Parameters
        ----------
        irods_env : dict
            Dictionary dereived from an irods_environment.json
        password : str
            Plain text password.

        """
        self.__name__ = 'IrodsConnector'
        self._irods_env = irods_env
        self._password = password
        self.session = connect()

    def __del__(self):
        del self.session

    
    @property
    def irods_environment(self) -> dict:
        """iRODS environment.

        Returns
        -------
        dict or None
            iRODS environment.

        """
        return self._irods_env

    @property 
    def password(self) -> str:
        return self._password

    @property
    def user_info(self) -> tuple:
        """Returns user type and groups the user who started the sessionbelongs to.

        Returns
        -------
        (user_type, user_groups) -> (str, list)
        """
        query = self.session.query(kw.USER_TYPE).filter(
                kw.LIKE(kw.USER_NAME, self.sess_man.username))
        user_type = [list(result.values())[0] for result in query.get_results()][0]
        query = self.session.query(kw.USER_GROUP_NAME).filter(
                kw.LIKE(kw.USER_NAME, self.sess_man.username))
        user_groups = [list(result.values())[0] for result in query.get_results()]
        return user_type, user_groups


    # Data operation/iCommands functionality
    #
    def collection_exists(self, path: str) -> bool:
        return "Not implemented"

    def dataobject_exists(self, path: str) -> bool:
        return "Not implemented"

    def delete_data(self, item: None):
        return "Not implemented"

    def ensure_coll(self, coll_name: str) -> irods.collection.iRODSCollection:
        return "Not implemented"

    def ensure_data_object(self, data_object_name: str) -> irods.data_object.iRODSDataObject:
        return "Not implemented"

    def get_collection(self, path: str) -> irods.collection.iRODSCollection:
        return "Not implemented"

    def get_dataobject(self, path: str) -> irods.data_object.iRODSDataObject:
        return "Not implemented"

    def get_items_size(self, irods_path_names: list) -> int:
        """Retrieves the sizes of collections and objects and returns their cumulative size in bytes.
        """
        return "Not implemented"

    def irods_put(self, local_path: str, irods_path: str, res_name: str = '', options: dict = None):
        """Uploads a data object or collection to iRODS.
        """
        return "Not implemented"

    def irods_get(self, irods_path: str, local_path: str, options: dict = None):
        """Downloads a data object or collection from iRODS.
        """
        return "Not implemented"

    def is_collection(self, obj) -> bool:
        return "Not implemented"

    def is_dataobject(self, obj) -> bool:
        return "Not implemented"

    # Metadata functionality
    #
    def add_metadata(self, items: list, key: str, value: str, units: str = None):
        """Adds an iRODS key-value-units tag to all objects and collections in the items list.
        """
        return "Not implemented"

    def add_multiple_metadata(self, items, avus):
        """Adds multiple metadata fields to all items.
        """
        return "Not implemented"

    def delete_metadata(self, items: list, key: str, value: str, units: str = None):
        return "Not implemented"

    def update_metadata(self, items: list, key: str, value: str, units: str = None):
        return "Not implemented"

    # Permission functionality
    #
    @property
    def permissions(self) -> dict:
        """Returns available iRODS permissions for data objects.
        """
        return "Not implemented"

    def get_permissions(self, item: irods.collection | irods.data_object) -> list:
        return "Not implemented"

    def set_permissions(self, perm: str, itam: irods.collection | irods.data_object, 
                        user: str = '', zone: str = self.session.zone,
                        recursive: bool = False, admin: bool = False):
        return "Not implemented"

    # Resource functionality
    #
    @property
    def resources(self) -> dict:
        """Returns all iRODS resources and their metadata as dictionary.
        """
        return "Not implemented"

    def get_free_space(self, resc_name: str, multiplier: int = 1) -> int:
        """Returns the free_space of a resource, space is given in bytes.
        """
        return "Not implemented"

    def get_resource(self, resc_name: str) -> irods.resource.iRODSResource:
        return "Not implemented"

    def get_resource_children(self, resc: irods.resource.iRODSResource) -> list:
        return "Not implemented"

    def resource_space(self, root_name: str) -> int:
        """Accumulate all free space under a resource tree starting at a resource root_name
        """
        return "Not implemented"

    # Rules functionality
    #
    def execute_rule(self, rule_file: str, params: dict, output: str = 'ruleExecOut') -> tuple:
        return "Not implemented"


    # Tickets functionality
    #
    def create_ticket(self, item_path: str, expiry_string: str = '') -> tuple:
        return "Not implemented"


    # Session functionality
    #
    def connect(self):
        """Establish an iRODS session.

        """
        self._session = session.Session(self.irods_env_file, self.irods_environment.config,
                                        self.ibridges_configuration.config, self._password) 
        if not self.session.has_irods_session():
            self.session.connect()

    # iRODS session properties
    #
    @property
    def default_resc(self) -> str:
        return self.session.default_resc

    @property
    def host(self) -> str:
        return self.session.host

    @property
    def port(self) -> str:
        return self.session.port

    @property
    def server_version(self) -> tuple:
        return self.session.server_version

    @property
    def username(self) -> str:
        return self.session.username

    @property
    def zone(self) -> str:
        return self.session.zone
