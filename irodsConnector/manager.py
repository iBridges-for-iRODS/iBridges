""" Irods connection factory
"""
import irods.collection
import irods.resource
import irods.session
import irodsConnector.keywords as kw
import irodsConnector


class IrodsConnector(object):
    """Create python or icommands class instance
    """

    def __init__(self, irods_env_file='', password='', application_name=None):
        """iRODS authentication with Python client.

        Parameters
        ----------
        irods_env_file : str
            JSON document with iRODS connection parameters.
        password : str
            Plain text password.
        application_name : str
            Name of the application using this connector.

        """
        self.__name__ = 'IrodsConnector'
        self.application_name = application_name
        self.multiplier = kw.MULTIPLIER
        self._data_op = irodsConnector.dataOperations.DataOperation(self)
        self._icommands = irodsConnector.Icommands.IrodsConnectorIcommands(self)
        self._meta = irodsConnector.meta.Meta(self)
        self._permission = irodsConnector.permission.Permission(self)
        self._query = irodsConnector.query.Query(self)
        self._rules = irodsConnector.rules.Rules(self)
        self._resource = irodsConnector.resource.Resource(self)
        self._session = irodsConnector.session.Session(irods_env_file, password)
        self._tickets = irodsConnector.tickets.Tickets()
        self._users = irodsConnector.users.Users()
        " Connect to iRODS server"
        self._session.connect(application_name)


    """ Implementation of metadata class"""
    def add_metadata(self, items: list, key: str, value: str, units: str = None):
        return self._meta.add(items, key, value, units)

    def add_multiple_metadata(self, items, avus):
        return self._meta.add_multiple(items, avus)

    def update_metadata(self, items: list, key: str, value: str, units: str = None):
        return self._meta.update(items, key, value, units)

    def delete_metadata(self, items: list, key: str, value: str, units: str = None):
        return self._meta.delete(items, key, value, units)

    """ Implementation of permission class"""
    def permissions(self) -> dict:
        return self._permission.permissions(self._session)

    def get_permissions(self, path: str = '', obj: irods.collection = None) -> list:
        return self._permission.get_permissions(self._session, path, obj)

    def set_permissions(self, perm: str, path: str, user: str = '', zone: str = '',
                        recursive: bool = False, admin: bool = False):
        return self._permission.set_permissions(self._session, perm, path, user, zone, recursive, admin)

    """ Implementation of resource class"""
    def resources(self) -> dict:
        return self._resource.resources(self._session)

    def list_resources(self, attr_names: list = None) -> tuple:
        return self._resource.list_resources(self._session, attr_names)

    def get_resource(self, resc_name: str) -> irods.resource.Resource:
        return self._resource.get_resource(self._session, resc_name)

    def resource_space(self, resc_name: str) -> int:
        return self._resource.resource_space(self._session, resc_name)

    def get_free_space(self, resc_name: str, multiplier: int = 1) -> int:
        return self._resource.get_free_space(self._session, resc_name, multiplier)

    def get_resource_children(self, resc: irods.resource.Resource) -> list:
        return self._resource.get_resource_children(resc)

    """ Implementation of session class"""
    def irods_env_file(self) -> str:
        return self._session.irods_env_file

    def password(self) -> str:
        return self._session.password

    def session(self) -> irods.session.iRODSSession:
        return self._session.session

    def upload_data(self, source: str, destination: irods.collection.Collection,
                    res_name: str, size: int, buff: int, force: bool = False, diffs: tuple = None):
        if self._icommands.icommands():
            return self._icommands.upload_data(self._session, self._resource, source, destination,
                                               res_name, size, buff, force)
        else:
            return self._data_op.upload_data(self._session, source, destination, res_name, size, buff, force, diffs)

    def download_data(self, source: None, destination: str,
                      size: int, buff: int, force: bool = False, diffs: tuple = None):
        if self._icommands.icommands():
            return self._icommands.download_data(self._session, source, destination, size, buff, force)
        else:
            return self._data_op.download_data(self._session, source, destination, size, buff, force, diffs)

    def irods_put(self, local_path: str, irods_path: str, res_name: str = ''):
        if self._icommands.icommands():
            return self._icommands.irods_put(local_path, irods_path, res_name)
        else:
            return self._data_op.irods_put(self._session, local_path, irods_path, res_name)

    def irods_get(self, irods_path: str, local_path: str, options: dict = None):
        if self._icommands.icommands():
            return self._icommands.irods_get(irods_path, local_path)
        else:
            return self._data_op.irods_get(self._session, irods_path, local_path, options)

    def diff_obj_file(self, objpath: str, fspath: str, scope: str = "size") -> tuple:
        return self._data_op.diff_obj_file(self._session, objpath, fspath, scope)

    def diff_irods_localfs(self, coll: irods.collection.Collection,
                           dirpath: str, scope: str = "size") -> tuple:
        return self._data_op.diff_irods_localfs(self._session, coll, dirpath, scope)

    def delete_data(self, item: None):
        return self._data_op.delete_data(self._session, item)

    def get_irods_size(self, path_names: list) -> int:
        return self._data_op.get_irods_size(self._session, path_names)

    """ Implementation of ticket class"""
    def create_ticket(self, obj_path: str, expiry_string: str = '') -> tuple:
        return self._tickets.create_ticket(self._session, obj_path, expiry_string)

    def get_user_info(self) -> tuple:
        return self._users.get_user_info(self._session)

    def search(self, key_vals: dict = None) -> list:
        return self._query.search(self._session, key_vals)

    def execute_rule(self, rule_file: str, params: dict, output: str = 'ruleExecOut') -> tuple:
        return self._rules.execute_rule(self._session, rule_file, params, output)
