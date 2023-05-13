"""iBridges context: configurations and common services.

"""
import json
import logging

from . import json_config
from . import path

IBRIDGES_DIR = '~/.ibridges'
IRODS_DIR = '~/.irods'
DEFAULT_IBRIDGES_CONF_FILE = f'{IBRIDGES_DIR}/ibridges_config.json'
IBRIDGES_TEMPLATE = {
    'check_free_space': True,
    'force_transfers': False,
    'verbose': 'info',
}
MANDATORY_IRODS_KEYS = [
    'irods_default_resource',
    'irods_host',
    'irods_port',
    'irods_user_name',
    'irods_zone_name',
]


class Context:
    """The singleton context of an iBridges session including singleton
    configurations and iBridges session instance.

    """
    _ibridges_conf_file = ''
    _ibridges_configuration = None
    _instance = None
    _irods_connector = None
    _irods_env_file = ''
    _irods_environment = None
    application_name = ''

    def __new__(cls):
        """Give only a single new instance ever.

        Returns
        -------
        Context
            A singleton instance.

        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __del__(self):
        del self.irods_connector

    @property
    def ibridges_conf_file(self) -> str:
        """iBridges configuration filename.

        Returns
        -------
        str
            Name of configuration file

        """
        return self._ibridges_conf_file

    @ibridges_conf_file.setter
    def ibridges_conf_file(self, filename: str):
        """iBridges configuration filename setter.

        Parameters
        ----------
        filename : str
            Name of the configuration file.

        """
        self._ibridges_conf_file = path.LocalPath(filename).expanduser()
        if self._ibridges_configuration:
            self._ibridges_configuration.filepath = self._ibridges_conf_file

    @property
    def ibridges_configuration(self) -> json_config.JsonConfig:
        """iBridges configuration dictionary loaded from the
        configuration file or from template.

        Returns
        -------
        utils.json_config.JsonConfig
            Configuration instance.

        """
        if self._ibridges_configuration is None:
            if not self.ibridges_conf_file:
                self.ibridges_conf_file = DEFAULT_IBRIDGES_CONF_FILE
            filepath = path.LocalPath(self.ibridges_conf_file).expanduser()
            if not filepath.parent.is_dir():
                filepath.parent.mkdir()
            if not filepath.is_file():
                filepath.write_text(json.dumps(IBRIDGES_TEMPLATE))
            self._ibridges_configuration = json_config.JsonConfig(filepath)
        # iBridges configuration check/default entry update.  Do not overwrite!
        conf_dict = self._ibridges_configuration.config
        for key, val in IBRIDGES_TEMPLATE.items():
            if key not in conf_dict:
                logging.info(
                    'Adding missing entry to iBridges configuration: (%s, %s)',
                    key, val)
                conf_dict[key] = val
        return self._ibridges_configuration

    @property
    def irods_connector(self):
        """An iBridges connection manager.

        Returns
        -------
        irodsConnector.manager.IrodsConnector
            The iBridges connection manager.
        """
        return self._irods_connector

    @irods_connector.setter
    def irods_connector(self, connector):
        """Connection manager setter.

        Parameters
        ----------
        connector : irodsConnector.manager.IrodsConnector
            The iBridges connection manager.

        """
        self._irods_connector = connector
        import irodsConnector
        if isinstance(connector, irodsConnector.manager.IrodsConnector):
            self._irods_connector.ibridges_configuration = self.ibridges_configuration
            logging.debug('self._irods_connector.ibridges_configuration')
            self._irods_connector.irods_environment = self.irods_environment
            logging.debug('self._irods_connector.irods_environment')

    @irods_connector.deleter
    def irods_connector(self):
        """Connection manager deleter.

        """
        if self._irods_connector is not None:
            del self._irods_connector
        self._irods_connector = None

    @property
    def irods_env_file(self) -> str:
        """iRODS environment filename.

        Returns
        -------
        str
            Name of environment file

        """
        logging.debug('getting: self._irods_env_file')
        return self._irods_env_file

    @irods_env_file.setter
    def irods_env_file(self, filename: str):
        """iRODS environment filename setter.

        Parameters
        ----------
        filename : str
            Name of the environment file.

        """
        self._irods_env_file = path.LocalPath(filename).expanduser()
        logging.debug('setting: self._irods_env_file')
        self._irods_environment.filepath = self._irods_env_file
        import irodsConnector
        if isinstance(self.irods_connector, irodsConnector.manager.IrodsConnector):
            self._irods_connector.irods_env_file = self._irods_env_file

    @property
    def irods_environment(self) -> json_config.JsonConfig:
        """iRODS environment dictionary loaded from the configuration
        file.  Returns a blank, initialized instance if the
        configuration is not set.

        Returns
        -------
        utils.json_config.JsonConfig
            Configuration instance.

        """
        if self._irods_environment is None:
            # TODO add existence check, running "iinit" when missing?
            self._irods_environment = json_config.JsonConfig(self.irods_env_file)
        return self._irods_environment

    def ienv_is_complete(self) -> bool:
        """Check if iRODS environment is complete.

        Returns
        -------
        bool
            Whether the environment is complete.

        """
        if self._irods_environment is not None:
            env_dict = self._irods_environment.config
            if env_dict:
                return is_complete(
                    env_dict, MANDATORY_IRODS_KEYS, 'iRODS environment')
            return False
        return False

    def save_ibridges_configuration(self):
        """Save iBridges configuration to disk.

        """
        self.ibridges_configuration.save()

    def save_irods_environment(self):
        """Save iRODS environment to disk.

        """
        self.irods_environment.save()

    def reset(self):
        """Reset existing instances of dynamic class members

        """
        del self.irods_connector
        if self.ibridges_configuration:
            self.ibridges_configuration.reset()
            filepath = path.LocalPath(self.ibridges_conf_file).expanduser()
            self.ibridges_configuration.filepath = filepath
        if self.irods_environment:
            self.irods_environment.reset()
            filepath = path.LocalPath(self.irods_env_file).expanduser()
            self.irods_environment.filepath = filepath


def is_complete(conf_dict: dict, mandatory: list, conf_type: str) -> bool:
    """Check if given iRODS environment has all mandatory keys.

    Parameters
    ----------
    conf_dict : dict
        Configuration to check.
    mandatory : list
        Values to check for.
    conf_type : str
        Type of configuration.

    Returns
    -------
    bool
        If the given configuration is complete.

    """
    missing = []
    for key in mandatory:
        if key not in conf_dict:
            missing.append(key)
    if len(missing) > 0:
        print(f'Missing key(s) in {conf_type}: {missing}')
        print('Please fix and try again!')
        return False
    return True


class ContextContainer:
    """Abstract base class for classes needing to use context.

    """
    context = Context()

    @property
    def conf(self) -> dict:
        """iBridges configuration dictionary.

        Returns
        -------
        dict
            Configuration from JSON serialized string.

        """
        if self.context.ibridges_configuration:
            return self.context.ibridges_configuration.config
        return {}

    @property
    def conn(self):
        """IrodsConnector instance.

        Returns
        -------
        irodsConnector.manager.IrodsConnector
            iRODS connection instance set into the context.
        """
        return self.context.irods_connector

    @property
    def ienv(self) -> dict:
        """iRODS environment dictionary.

        Returns
        -------
        dict
            Environment from JSON serialized string.
        """
        if self.context.irods_environment:
            return self.context.irods_environment.config
        return {}
