"""Module with implementation of ibridges shell command."""
import cmd
import os
import subprocess
from pathlib import Path

from ibridges.cli.data_operations import CliDownload, CliMakeCollection, CliRm, CliSync, CliUpload
from ibridges.cli.meta import CliMetaAdd, CliMetaDel, CliMetaList
from ibridges.cli.navigation import CliCd, CliList, CliPwd, CliSearch, CliTree
from ibridges.cli.util import cli_authenticate
from ibridges.path import IrodsPath

ALL_BUILTIN_COMMANDS=[CliList, CliPwd, CliTree, CliMetaList,
                      CliMetaAdd, CliMetaDel, CliMakeCollection, CliDownload,
                      CliUpload, CliSearch, CliCd, CliRm, CliSync]


class IBridgesShell(cmd.Cmd):
    """Command class implementation for iBridges."""

    identchars = cmd.Cmd.identchars + "-"

    def __init__(self):
        """Initialize the shell creating the session."""

        # Autocomplete is not available on windows.
        try:
            import readline
            readline.set_completer_delims(readline.get_completer_delims().replace("-", ""))
        except ImportError:
            pass
        self.session = cli_authenticate(None)
        self.commands = {}
        for command_class in ALL_BUILTIN_COMMANDS:
            for name in command_class.names:
                self.commands[name] = command_class
        super().__init__()

    def do_shell(self, arg):
        """Run commands in the bash/zsh shell directly for local operations."""
        # cd command doesn't work properly with subprocess, so use Python chdir.
        if arg.startswith("cd "):
            try:
                os.chdir(arg[3:])
            except NotADirectoryError:
                print(f"Error: {arg[3:]} is not a directory.")
            except FileNotFoundError:
                print(f"Error: {arg[3:]} does not exist.")
        else:
            subprocess.run(arg, shell=True, check=False)

    def _universal_complete(self, text, line, begidx, endidx, command_class):  # pylint: disable=unused-argument
        arg_list = _prepare_args(line, add_last_space=True)[1:]
        if len(arg_list) > len(command_class.autocomplete):
            return []
        if command_class.autocomplete[len(arg_list)-1] == "remote_path":
            return complete_ipath(self.session, text, line, collections_only=False)
        if command_class.autocomplete[len(arg_list)-1] == "remote_coll":
            return complete_ipath(self.session, text, line, collections_only=True)
        if command_class.autocomplete[len(arg_list)-1] == "local_path":
            return complete_lpath(text, line, directories_only=False)
        if command_class.autocomplete[len(arg_list)-1] == "local_dir":
            return complete_lpath(text, line, directories_only=True)
        return []

    def _universal_do(self, arg, command_class):
        parser = command_class.get_parser()
        args = parser.parse_args(_prepare_args(arg))
        if not getattr(parser, "printed_help", False):
            command_class.run_shell(self.session, parser, args)

    def _universal_help(self, command_class):
        command_class.get_parser().print_help()

    def do_quit(self, arg):  # pylint: disable=unused-argument
        """Quit the shell."""
        self.close()
        return True

    def do_EOF(self, arg):  # noqa # pylint: disable=invalid-name
        """Quit the shell with ctrl+D shortcut."""
        return self.do_quit(arg)

    def close(self):
        """Close the session."""
        self.session.close()

    def _wrap_complete(self, command_class):
        def _wrap(*args):
            return self._universal_complete(*args, command_class)
        return _wrap

    def _wrap_do(self, command_class):
        def _wrap(*args):
            self._universal_do(*args, command_class)
        return _wrap

    def _wrap_help(self, command_class):
        def _wrap(*args):
            self._universal_help(*args, command_class)
        return _wrap

    def __getattribute__(self, attr):
        """Catch the do_, complete_ and help_ methods and replace them with a wrapper."""
        if attr.startswith("do_") and attr[ 3:] in self.commands:
            return self._wrap_do(self.commands[attr[3:]])
        if attr.startswith("complete_") and attr[9:] in self.commands:
            return self._wrap_complete(self.commands[attr[9:]])
        if attr.startswith("help_") and attr[5:] in self.commands:
            return self._wrap_help(self.commands[attr[5:]])
        return super().__getattribute__(attr)

    def get_names(self):
        """Get all available subcommands."""
        fake_names = [f"do_{cmd}" for cmd in self.commands]
        fake_names = fake_names + [f"complete_{cmd}" for cmd in self.commands]
        fake_names = fake_names + [f"help_{cmd}" for cmd in self.commands]
        return fake_names + super().get_names()

    @property
    def prompt(self):
        """Modify the prompt to show the current collection."""
        return f"ibshell:{IrodsPath(self.session).name}> "

def _escape(line):
    if isinstance(line, str):
        return line.replace(" ", "\\ ")
    return [_escape(x) for x in line]

def _unescape(line):
    if isinstance(line, str):
        return line.replace("\\ ", " ")
    return [_unescape(x) for x in line]

def _prepare_args(args, add_last_space=False, unescape=True):
    split_args = args.split()
    new_args = []
    cur_arg = ""
    for str_arg in split_args:
        if not str_arg.endswith("\\"):
            cur_arg += str_arg
            new_args.append(cur_arg)
            cur_arg = ""
        else:
            cur_arg += str_arg[:-1] + " "
    if cur_arg != "":
        new_args.append(cur_arg)
    if add_last_space and args.endswith(" ") and not args.endswith("\\ "):
        new_args.append("")
    if unescape:
        return _unescape(new_args)
    return new_args

def _filter(ipaths, collections_only, base_path):
    ipaths = [p for p in ipaths if str(p) != str(base_path)]
    if collections_only:
        return [p.name for p in ipaths if p.collection_exists()]
    return [p.name for p in ipaths]


def complete_ipath(session, text, line, collections_only=False):
    """Complete an IrodsPath."""
    args = _prepare_args(line, unescape=False)[1:]
    if len(args) == 0 or args[-1] == "":
        ipath_list = list(IrodsPath(session).walk(depth=1))
        return _escape(_filter(ipath_list, collections_only, IrodsPath(session)))

    base_path = IrodsPath(session, args[-1])
    if base_path.collection_exists():
        if line.endswith("/"):
            prefix = text
        else:
            prefix = f"{text}/"
        path_list = _filter(base_path.walk(depth=1), collections_only, base_path)
        return [f"{prefix}{_escape(ipath)}" for ipath in path_list]

    if base_path.dataobject_exists():
        return []

    last_part = base_path.parts[-1]
    base_path = IrodsPath(session, *base_path.parts[:-1])
    completions = []
    for ipath in base_path.walk(depth=1):
        if str(ipath) == base_path:
            continue
        if ipath.name.startswith(last_part) and not (
                collections_only and not ipath.collection_exists()):
            completions.append(text + _escape(ipath.name[len(last_part):]))
    return completions

def _find_paths(base_path, directories_only):
    all_paths = []
    for path in base_path.iterdir():
        if directories_only and not path.is_dir():
            continue
        all_paths.append(path.name)
    return all_paths


def complete_lpath(text, line, directories_only=False):
    """Complete a local path."""
    args = _prepare_args(line, unescape=False)[1:]
    if len(args) == 0:
        return _escape(_find_paths(Path.cwd(), directories_only))

    base_path = Path(args[-1])
    if base_path.is_dir():
        if line.endswith("/"):
            prefix = text
        else:
            prefix = f"{text}/"
        path_list = _find_paths(base_path, directories_only)
        return [f"{prefix}{_escape(ipath)}" for ipath in path_list]

    if base_path.is_file():
        return []

    last_part = base_path.name
    parent_path = base_path.parent
    completions = []
    path_list = _find_paths(parent_path, directories_only)
    for lpath_str in path_list:
        lpath = parent_path / lpath_str
        if lpath_str.startswith(last_part) and not (
                directories_only and not lpath.is_dir()):
            completions.append(text + _escape(lpath_str[len(last_part):]))
    return completions
