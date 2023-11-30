""" Irods connection factory

"""
import logging

import irods.collection
import irods.data_object
import irods.resource
import irods.session

from . import session

class IrodsConnector():
    """Top-level connection to the Python iRODS client

    """
    _data_op = None
    _meta = None
    _permission = None
    _resource = None
    _rules = None
    _session = None
    _tickets = None
    _users = None
    _irods_environment = None

    def __init__(self, irods_env: dict, password='': str):
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

    def data_op(self):
        """Link to class that carries out the data operations
        """
        return None
    
    def metadata(self) -> meta.Meta:
        """Link to class that carries out all metadata operations
        """
        return None

    def permission(self) -> permission.Permission:
        """Link to class that carries out all permission operations
        """
        return None

    def resources(self) -> resource.Resource:
        return None

    def rules(self) -> rules.Rules:
        return None

    def tickets(self) -> tickets.Tickets:
        return None
    
    @property
    def user_info(self) -> tuple:
        """Returns user type and groups the user who started the sessionbelongs to.

        Returns
        -------
        (user_type, user_groups) -> (str, list)
        """
        query = self.irods_session.query(kw.USER_TYPE).filter(
                kw.LIKE(kw.USER_NAME, self.sess_man.username))
        user_type = [list(result.values())[0] for result in query.get_results()][0]
        query = self.sess_man.irods_session.query(kw.USER_GROUP_NAME).filter(
                kw.LIKE(kw.USER_NAME, self.sess_man.username))
        user_groups = [list(result.values())[0] for result in query.get_results()]
        return user_type, user_groups


    # Data operation/iCommands functionality
    #
    def collection_exists(self, path: str) -> bool:
        return self.data_op.collection_exists(path)

    def dataobject_exists(self, path: str) -> bool:
        return self.data_op.dataobject_exists(path)

    def delete_data(self, item: None):
        return self.data_op.delete_data(item)

    def ensure_coll(self, coll_name: str) -> irods.collection.iRODSCollection:
        return self.data_op.ensure_coll(coll_name)

    def ensure_data_object(self, data_object_name: str) -> irods.data_object.iRODSDataObject:
        return self.data_op.ensure_data_object(data_object_name)

    def get_collection(self, path: str) -> irods.collection.iRODSCollection:
        return self.data_op.get_collection(path)

    def get_dataobject(self, path: str) -> irods.data_object.iRODSDataObject:
        return self.data_op.get_dataobject(path)

    def get_items_size(self, path_names: list) -> int:
        return self.data_op.get_items_size(path_names)

    def irods_put(self, local_path: str, irods_path: str, res_name: str = '', options: dict = None):
        return self.data_op.irods_put(local_path, irods_path, res_name)

    def irods_get(self, irods_path: str, local_path: str, options: dict = None):
        return self.data_op.irods_get(irods_path, local_path, options)

    def is_collection(self, obj) -> bool:
        return self.data_op.is_collection(obj)

    def is_dataobject(self, obj) -> bool:
        return self.data_op.is_dataobject(obj)

    # Metadata functionality
    #
    def add_metadata(self, items: list, key: str, value: str, units: str = None):
        return self.meta.add(items, key, value, units)

    def add_multiple_metadata(self, items, avus):
        return self.meta.add_multiple(items, avus)

    def delete_metadata(self, items: list, key: str, value: str, units: str = None):
        return self.meta.delete(items, key, value, units)

    def update_metadata(self, items: list, key: str, value: str, units: str = None):
        return self.meta.update(items, key, value, units)

    # Permission functionality
    #
    @property
    def permissions(self) -> dict:
        """Returns available iRODS permissions for data objects
        """
        return self.permission.permissions

    def get_permissions(self, path: str, obj: irods.collection = None) -> list:
        return self.permission.get_permissions(path, obj)

    def set_permissions(self, perm: str, path: str, user: str = '', zone: str = '',
                        recursive: bool = False, admin: bool = False):
        return self.permission.set_permissions(perm, path, user, zone, recursive, admin)

    # Resource functionality
    #
    @property
    def resources(self) -> dict:
        return self.resource.resources

    def get_free_space(self, resc_name: str, multiplier: int = 1) -> int:
        return self.resource.get_free_space(resc_name, multiplier)

    def get_resource(self, resc_name: str) -> irods.resource.iRODSResource:
        return self.resource.get_resource(resc_name)

    def get_resource_children(self, resc: irods.resource.iRODSResource) -> list:
        return self.resource.get_resource_children(resc)

    def list_resources(self, attr_names: list = None) -> tuple:
        return self.resource.list_resources(attr_names)

    def resource_space(self, resc_name: str) -> int:
        return self.resource.resource_space(resc_name)

    # Rules functionality
    #
    def execute_rule(self, rule_file: str, params: dict, output: str = 'ruleExecOut') -> tuple:
        return self.rules.execute_rule(rule_file, params, output)


    # Tickets functionality
    #
    def create_ticket(self, obj_path: str, expiry_string: str = '') -> tuple:
        return self.tickets.create_ticket(obj_path, expiry_string)


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
