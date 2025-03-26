"""Interface to the ibridges CLI configuration file."""
from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path
from typing import Union

from ibridges.interactive import DEFAULT_IENV_PATH, DEFAULT_IRODSA_PATH

IBRIDGES_CONFIG_FP = Path.home() / ".ibridges" / "ibridges_cli.json"


class IbridgesConf():
    """Interface to the iBridges configuration file class."""

    def __init__(self, parser: argparse.ArgumentParser,
                 config_fp: Union[str, Path]=IBRIDGES_CONFIG_FP):
        """Read configuration file and validate it.

        Parameters
        ----------
        parser
            Argument parser to display error messages.
        config_fp, optional
            Path to configuration file, by default ~/.ibridges/ibridges_cli.json

        """
        self.config_fp = config_fp
        self.parser = parser
        try:
            with open(self.config_fp, "r", encoding="utf-8") as handle:
                ibridges_conf = json.load(handle)
                self.servers = ibridges_conf["servers"]
                self.cur_env = ibridges_conf.get("cur_env", ibridges_conf.get("cur_ienv"))
        except Exception as exc:  # pylint: disable=broad-exception-caught
            if isinstance(exc, FileNotFoundError):
                # Don't worry if the ibridges configuration can't be found.
                self.reset(ask=False)
            else:
                print(repr(exc))
                self.reset()
        self.validate()

    def reset(self, ask: bool=True):
        """Reset the configuration file to its defaults.

        Parameters
        ----------
        ask, optional
            Ask whether to overwrite the current configuration file, by default True

        """
        if ask:
            answer = input(f"The ibridges configuration file {self.config_fp} cannot be read, "
                        "delete? (Y/N)")
            if answer != "Y":
                self.parser.error(
                    "Cannot continue without reading the ibridges configuration file.")
        self.cur_env = str(DEFAULT_IENV_PATH)
        self.servers = {str(DEFAULT_IENV_PATH): {"alias": "default"}}
        self.save()

    def validate(self):
        """Validate the ibridges configuration.

        Check whether the types are correct, the default iRODS path has not been removed,
        aliases are unique and more. If the assumptions are violated, try to reset the configuration
        to create a working configuration file.
        """
        changed = False
        try:
            if not isinstance(self.servers, dict):
                raise ValueError("Servers list is not a dictionary (old version of iBridges?).")
            if str(DEFAULT_IENV_PATH) not in self.servers:
                raise ValueError("Default iRODS path not in configuration file.")
            if not isinstance(self.cur_env, str):
                raise ValueError(f"Current environment should be a string not {type(self.cur_env)}")
            cur_aliases = set()
            new_servers = {}
            for ienv_path, entry in self.servers.items():
                if ienv_path != str(DEFAULT_IENV_PATH) and not Path(ienv_path).is_file():
                    warnings.warn(f"Environment with file '{ienv_path}' does not exist anymore, "
                                   "removing the entry.")
                    changed = True
                elif entry.get("alias", None) in cur_aliases:
                    warnings.warn(f"Environment with file '{ienv_path}' has a duplicate alias, "
                                  "removing...")
                    changed = True
                else:
                    new_servers[ienv_path] = entry
                    if "alias" in entry:
                        cur_aliases.add(entry["alias"])
            self.servers = new_servers
            if self.cur_env not in self.servers:
                warnings.warn("Current environment is not available, switching to first available.")
                self.cur_env = list(self.servers)[0]
                changed = True
        except ValueError as exc:
            print(exc)
            self.reset()
            changed = True
        if changed:
            self.save()

    def save(self):
        """Save the configuration back to the configuration file."""
        Path(self.config_fp).parent.mkdir(exist_ok=True, parents=True)
        with open(self.config_fp, "w", encoding="utf-8") as handle:
            json.dump(
                {"cur_env": self.cur_env,
                 "servers": self.servers},
                handle, indent=4)

    def get_entry(self, path_or_alias: Union[Path, str, None] = None) -> tuple[str, dict]:
        """Get the path and contents that belongs to a path or alias.

        Parameters
        ----------
        path_or_alias, optional
            Either an absolute path or an alias, by default None in which
            case the currently selected environment is chosen.

        Returns
        -------
        ienv_path:
            The absolute path to the iRODS environment file.
        entry:
            Entry for the environment file containing, cwd, alias, cached password.

        Raises
        ------
        KeyError
            If the entry can't be found.

        """
        path_or_alias = self.cur_env if path_or_alias is None else path_or_alias
        for ienv_path, entry in self.servers.items():
            if ienv_path == str(path_or_alias):
                return ienv_path, entry

        for ienv_path, entry in self.servers.items():
            if entry.get("alias", None) == str(path_or_alias):
                return ienv_path, entry

        raise KeyError(f"Cannot find entry with name/path '{path_or_alias}'")

    def set_env(self, ienv_path_or_alias: Union[str, Path, None] = None):
        """Change the currently selected iRODS environment file.

        Parameters
        ----------
        ienv_path_or_alias, optional
            Either a path to the iRODS environment file or an alias, by default None
            in which case the default location for the iRODS environment file will be chosen.

        Raises
        ------
        self.parser.error
            If the iRODS environment file does not exist.

        """
        ienv_path_or_alias = (str(DEFAULT_IENV_PATH) if ienv_path_or_alias is None
                              else ienv_path_or_alias)
        try:
            ienv_path, _ = self.get_entry(ienv_path_or_alias)
        except KeyError:
            ienv_path = str(ienv_path_or_alias)
            self.servers[ienv_path] = {}
            if not Path(ienv_path).is_file():
                raise self.parser.error(f"Cannot find iRODS environment file {ienv_path}.")  # pylint:disable=raise-missing-from
        if self.cur_env != ienv_path:
            self.cur_env = ienv_path
            ienv_entry = self.servers[ienv_path]
            if "irodsa_backup" in ienv_entry:
                with open(DEFAULT_IRODSA_PATH, "w", encoding="utf-8") as handle:
                    handle.write(ienv_entry["irodsa_backup"])
            self.save()

    def set_alias(self, alias: str, ienv_path: Union[Path, str]):
        """Set an alias for an iRODS environment file.

        Parameters
        ----------
        alias
            Alias to be created.
        ienv_path
            Path to the iRODS environment file for the new alias.

        """
        try:
            # Alias already exists change the path
            self.get_entry(alias)
            self.parser.error(f"Alias '{alias}' already exists. To rename, delete the alias first.")
        except KeyError:
            try:
                # Path already exists change the alias
                ienv_path, entry = self.get_entry(ienv_path)
                if entry.get("alias", None) == alias:
                    return
                entry["alias"] = alias
                print("Change alias for path")
            except KeyError:
                # Neither exists, create a new entry
                self.servers[ienv_path] = {"alias": alias}
                print(f"Created alias '{alias}'")
        self.save()

    def delete_alias(self, alias: str):
        """Delete an alias.

        Parameters
        ----------
        alias
            The alias to be deleted. Can also be an iRODS environment file path.

        """
        try:
            ienv_path, entry = self.get_entry(alias)
        except KeyError:
            self.parser.error(f"Cannot delete alias '{alias}'; does not exist.")

        if ienv_path == str(DEFAULT_IENV_PATH):
            try:
                entry.pop("alias")
            except KeyError:
                self.parser.error("Cannot remove default irods path from configuration.")
        else:
            self.servers.pop(ienv_path)
        self.save()
