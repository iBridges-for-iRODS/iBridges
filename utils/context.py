"""iBridges context: configurations and common services.

"""
import logging

import irods.session as irods_session

from . import json_config
from . import path

IBRIDGES_DIR = '~/.ibridges'
IRODS_DIR = '~/.irods'
DEFAULT_IBRIDGES_CONF_FILE = f'{IBRIDGES_DIR}/ibridges_config.json'
DEFAULT_IRODS_ENV_FILE = f'{IRODS_DIR}/irods_environment.json'


class Context:
    """The singleton context of an iBridges session including singleton
    configurations and iBridges session instance.

    """
    _ibridges = None
    _instance = None
    _irods = None
    _session = None
    application_name = ''
    ibridges_conf_file = ''
    irods_env_file = ''

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
        del self.session

    @property
    def ibridges(self) -> dict:
        """iBridges configuration dictionary loaded from the
        configuration file.

        Returns
        -------
        dict or None
            Configuration dictionary if mandatory keys are present.

        """
        if self._ibridges is None:
            if not self.ibridges_conf_file:
                self.ibridges_conf_file = DEFAULT_IBRIDGES_CONF_FILE
            filepath = path.LocalPath(self.ibridges_conf_file).expanduser()
            if not filepath.parent.is_dir():
                filepath.parent.mkdir()
            if not filepath.is_file():
                filepath.write_text('{"force_unknown_free_space": false}')
            conf_dict = json_config.JsonConfig(filepath).config
            # iBridges configuration check.
            missing = []
            mandatory_keys = [
                'force_unknown_free_space',
            ]
            for key in mandatory_keys:
                if key not in conf_dict:
                    missing.append(key)
            if len(missing) > 0:
                logging.info(f'Missing key(s) in iBridges configuration: {missing}')
                logging.info('Please fix and try again!')
            else:
                self._ibridges = conf_dict
        return self._ibridges

    @property
    def irods(self) -> dict:
        """iRODS environment dictionary loaded from the
        configuration file.

        Returns
        -------
        dict or None
            Configuration dictionary if mandatory keys are present.

        """
        if self._irods is None:
            if not self.irods_env_file:
                self.irods_env_file = DEFAULT_IRODS_ENV_FILE
            filepath = path.LocalPath(self.irods_env_file).expanduser()
            # TODO add existence check, running "iinit" when missing?
            env_dict = json_config.JsonConfig(filepath).config or {}
            # iRODS environment check.
            missing = []
            mandatory_keys = [
                'irods_host',
                'irods_user_name',
                'irods_port',
                'irods_zone_name',
                'irods_default_resource',
            ]
            for key in mandatory_keys:
                if key not in env_dict:
                    missing.append(key)
            if len(missing) > 0:
                logging.info(f'Missing key(s) in iRODS environment: {missing}')
                logging.info('Please fix and try again!')
            else:
                self._irods = env_dict
        return self._irods

    @property
    def session(self) -> irods_session.iRODSSession:
        """iRODSSession instantiated from the iRODS environment.

        Returns
        -------
        irods.session.iRODSSession
            The iRODS session.
        """
        return self._session

    @session.setter
    def session(self, session: irods_session.iRODSSession):
        """iRODSSession setter.

        Parameters
        ----------
        irods.session.iRODSSession
            The iRODS session.

        """
        self._session = session

    @session.deleter
    def session(self):
        """iRODSSession deleter.

        """
        self._session.cleanup()
        del self._session
        self._session = None

    def save_ibridges(self):
        """Save iBridges configuration to disk.

        """
        filepath = path.LocalPath(self.ibridges_conf_file).expanduser()
        json_config.JsonConfig(filepath).config = self.ibridges

    def save_irods(self):
        """Save iRODS environment to disk.

        """
        filepath = path.LocalPath(self.irods_env_file).expanduser()
        json_config.JsonConfig(filepath).config = self.irods
