from utils import LocalPath
from utils import JsonConfig

import json
import os

# Parameter irods_environment.json
class IbridgesContext():
    """
    Gathers all config parameters from the irods_environment.json and 
    the ~/.ibridges/ibridges_config.json if present
    """

    def __init__(self, irods_env_file_path: str):
        self.irods_env_file_path = irods_env_file_path
        self.irods_config = JsonConfig(irods_env_file_path)
        #self._mandatory_keys_present()

        # ibridges config path: ~/.ibridges/ibridges_config.json
        self.ibridges_config_file_path = LocalPath(os.path.expanduser('~/.ibridges/config.json'))
        self.ibridges_config = JsonConfig(os.path.expanduser(self.ibridges_config_file_path))
    

    def _mandatory_keys_present(self):
        mandatory_keys = ['irods_host', 'irods_user_name', 
                          'irods_port', 'irods_zone_name', 
                          'irods_default_resource']
        for key in mandatory_keys:
            if key not in self.irods_config.config:
                raise Exception(f'Missing key in irods_environment: {key}')

    @property
    def irods_env_file(self):
        return self.irods_env_file_path


    @property
    def ibridges_config_file(self):
        return self.ibridges_config_file_path


    # Additional parameters to instantiate irodsConnectors
    @property
    def force_unknown_free_space(self):
        if ibridges_config.config and 'force_unknown_free_space' in self.ibridges_config.config:
            return self.ibridges_config.config.get('force_unknown_free_space', None)
        elif 'force_unknown_free_space' in self.irods_config.config:
            return self.irods_config.config['force_unknown_free_space']
        else:
            return None
        

    @property
    def davrods(self):
        if ibridges_config.config and 'davrods_server' in self.ibridges_config.config:
            return self.ibridges_config.config.get('davrods_server', None)
        elif 'davrods_server' in self.irods_config.config:
            return self.irods_config.config['davrods_server']
        else:
            return None


    # API tokens
    @property
    def eln_token(self):
        if self.ibridges_config.config:
            return self.ibridges_config.config.get('eln_token', None)
        else:
            return None
    
    @property
    def amber_token(self):
        if self.ibridges_config.config:
            return self.ibridges_config.config.get('amber_token', None)
        else:
            return None

    @property
    def ienv(self):
        return self.irods_config.config


    @property
    def ibridges_env(self):
        return self.ibridges_config.config


    def update_ibridges_keyval(self, key, value):
        try:
            if self.ibridges_config.config:
                self.ibridges_config.config[key] = value
            else:
                self.ibridges_config.config = {}
                self.ibridges_config.config[key] = value
        except Exception as e:
            raise e

    def update_irods_keyval(self, key, value):
        try:
            self.irods_config.config[key] = value
        except Exception as e:
            raise e


    def save_config(self, config: JsonConfig):
        config.config = config.config
