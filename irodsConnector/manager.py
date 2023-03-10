""" Irods connection factory
"""
from json import load
import irods.collection
import irodsConnector.keywords as kw
import irodsConnector
from utils import utils


class IrodsConnector(object):
    """Create python or icommands class instance
    """
    _ienv = {}

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

        self._meta = irodsConnector.meta.Meta(self)
        self._permission = irodsConnector.permission.Permission(self)
        self._resource = irodsConnector.resource.Resource(self)
        self._session = irodsConnector.session.Session(irods_env_file, password)
        #self._session.connect(application_name, default_resc, self._ienv)

    @property
    def ienv(self):
        """iRODS environment dictionary.

        Returns
        -------
        dict
            iRODS environment dictionary obtained from its JSON file.

        """
        if not self._ienv:
            irods_env_file = utils.LocalPath(self._session.irods_env_file)
            if irods_env_file.is_file():
                with open(irods_env_file, encoding='utf-8') as envfd:
                    self._ienv = load(envfd)
        return self._ienv

    @property
    def davrods(self):
        """DavRODS server URL.

        Returns
        -------
        str
            URL of the configured DavRODS server.

        """
        # FIXME move iBridges parameters to iBridges configuration
        return self.ienv.get('davrods_server', None)

    """ Implementation of metadata clas"""
    def add_metadata(self, items: list, key: str, value: str, units: str = None):
        return self._meta.add(items, key, value, units)

    def add_multiple_metadata(self, items, avus):
        return self._meta.add_multiple(items, avus)

    def update_metadata(self, items: list, key: str, value: str, units: str = None):
        return self._meta.update(items, key, value, units)

    def delete_metadata(self, items: list, key: str, value: str, units: str = None):
        return self._meta.delete(items, key, value, units)

    """ Implementation of permission clas"""
    def permissions(self) -> dict:
        return self._permission.permissions(self._session.session)

    def get_permissions(self, path: str = '', obj: irods.collection = None) -> list:
        return self._permission.get_permissions(self._session.session, path, obj)

    def set_permissions(self, perm: str, path: str, user: str = '', zone: str = '',
                        recursive: bool = False, admin: bool = False):
        return self._permission.set_permissions(self._session.session, perm, path, user, zone, recursive, admin)

    """ Implementation of resource clas"""
    def resources(self) -> dict:
        return self._resource.resources(self._session.session)

    def list_resources(self, attr_names: list = None) -> tuple:
        return self._resource.list_resources(self._session.session, self.ienv, attr_names)

    def get_resource(self, resc_name: str) -> irods.resource.Resource:
        return self._resource.get_resource(self._session.session, resc_name)

    def resource_space(self, resc_name: str) -> int:
        return self._resource.resource_space(self._session.session, resc_name)

    def get_free_space(self, resc_name: str, multiplier: int = 1) -> int:
        return self._resource.get_free_space(self._session.session, resc_name, multiplier)

    def get_resource_children(self, resc: irods.resource.Resource) -> list:
        return self._resource.get_resource_children(resc)