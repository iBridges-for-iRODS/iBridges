"""Manipulate configurations stored as JSON files.

"""
import json

from . import path


class JsonConfig:
    """A configuration stored in a JSON file.

    """
    _config = None

    def __init__(self, filepath: str):
        """Create the configuration.

        Parameters
        ----------
        filepath : str

        """
        self.filepath = path.LocalPath(filepath)

    @property
    def config(self) -> dict:
        """Configuration getter.

        Attempt to load a configuration from the JSON file.

        Returns
        -------
        dict or None
            The configuration if it exists.

        """
        if self._config is None:
            if self.filepath.is_file():
                with open(self.filepath, 'r', encoding='utf-8') as confd:
                    self._config = json.load(confd)
        return self._config

    @config.setter
    def config(self, conf_dict: dict):
        """Configuration setter.

        Set the configuration to `conf_dict` and write it to the JSON
        file.

        """
        self._config = conf_dict
        with open(self.filepath, 'w', encoding='utf-8') as confd:
            json.dump(conf_dict, confd, indent=4, sort_keys=True)

    @config.deleter
    def config(self):
        """Configuration deleter.

        Delete both the configuration and its JSON file.

        """
        self._config = None
        self.filepath.unlink(missing_ok=True)
