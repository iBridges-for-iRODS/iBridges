import json
import warnings
from pathlib import Path

from ibridges.interactive import DEFAULT_IENV_PATH

IBRIDGES_CONFIG_FP = Path.home() / ".ibridges" / "ibridges_cli.json"


class IbridgesConf():
    def __init__(self, parser, config_fp=IBRIDGES_CONFIG_FP):
        self.config_fp = config_fp
        self.parser = parser
        self._load()
        self.validate()

    def reset(self):
        answer = input("The ibridges configuration file cannot be read, delete? (Y/N)")
        if answer != "Y":
            self.parser.error("Cannot continue without reading the ibridges configuration file.")
        self.cur_env = str(DEFAULT_IENV_PATH)
        self.servers = {str(DEFAULT_IENV_PATH): {"alias": "default"}}
        self.save()

    def validate(self):
        try:
            if not isinstance(self.servers, dict):
                raise ValueError("Servers list not a dictionary (old version of iBridges?).")
            if str(DEFAULT_IENV_PATH) not in self.servers:
                raise ValueError("Default iRODS path not in configuration file.")
            cur_aliases = set()
            new_servers = {}
            for ienv_path, entry in self.servers.items():
                if ienv_path != str(DEFAULT_IENV_PATH) and not Path(ienv_path).is_file():
                    warnings.warn(f"Environment with file '{ienv_path}' does not exist anymore, "
                                   "removing the entry.")
                elif entry.get("alias", None) in cur_aliases:
                    warnings.warn(f"Environment with file '{ienv_path}' has a duplicate alias, "
                                  "removing...")
                else:
                    new_servers[ienv_path] = entry
                    if "alias" in entry:
                        cur_aliases.add(entry["alias"])
            self.servers = new_servers
            if self.cur_env not in self.servers:
                warnings.warn("Current environment is not available, switching to first available.")
                self.cur_env = list(self.servers)[0]
        except ValueError as exc:
            print(exc)
            self.reset()
        self.save()

    def _load(self):
        try:
            with open(self.config_fp, "r", encoding="utf-8") as handle:
                ibridges_conf = json.load(handle)
                self.servers = ibridges_conf["servers"]
                self.cur_env = ibridges_conf.get("cur_env", ibridges_conf.get("cur_ienv"))
        except Exception as exc:
            print(repr(exc))
            self.reset()


    def save(self):
        with open(IBRIDGES_CONFIG_FP, "w", encoding="utf-8") as handle:
            json.dump(
                {"cur_env": self.cur_env,
                 "servers": self.servers},
                handle, indent=4)

    def get_entry(self, path_or_alias = None):
        path_or_alias = self.cur_env if path_or_alias is None else path_or_alias
        for ienv_path, entry in self.servers.items():
            if ienv_path == str(path_or_alias):
                return ienv_path, entry

        for ienv_path, entry in self.servers.items():
            if entry.get("alias", None) == str(path_or_alias):
                return ienv_path, entry

        raise KeyError(f"Cannot find entry with name/path '{path_or_alias}'")

    def set_env(self, ienv_path_or_alias = None):
        ienv_path_or_alias = str(DEFAULT_IENV_PATH) if ienv_path_or_alias is None else ienv_path_or_alias
        try:
            ienv_path, _ = self.get_entry(ienv_path_or_alias)
        except KeyError:
            ienv_path = str(ienv_path_or_alias)
            self.servers[ienv_path] = {}
            if not Path(ienv_path).is_file():
                raise self.parser.error(f"Cannot find iRODS environment file {ienv_path}.")  # pylint:disable=raise-missing-from
        self.cur_env = ienv_path
        self.save()

    def set_alias(self, alias, ienv_path):
        try:
            # Alias already exists change the path
            self.get_entry(alias)
            self.parser.error(f"Alias '{alias}' already exists. To rename, delete the alias first.")
        except KeyError:
            try:
                # Path already exists change the alias
                ienv_path, entry = self.get_entry(ienv_path)
                entry["alias"] = alias
                print("Change alias for path")
            except KeyError:
                # Neither exists, create a new entry
                self.servers[ienv_path] = {"alias": alias}
                print(f"Created alias '{alias}'")
        self.save()

    def delete_alias(self, alias):
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
