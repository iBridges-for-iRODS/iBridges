"""Module with implementation of ibridges shell command."""

import cmd
import os
import subprocess
import sys
import traceback
from pathlib import Path

try:
    from importlib_metadata import entry_points
except ImportError:
    from importlib.metadata import entry_points  # type: ignore

from ibridges.cli.data_operations import CliDownload, CliMakeCollection, CliRm, CliSync, CliUpload
from ibridges.cli.meta import CliMetaAdd, CliMetaDel, CliMetaList
from ibridges.cli.navigation import CliCd, CliGui, CliList, CliPwd, CliSearch, CliTree, CliVersion
from ibridges.cli.util import cli_authenticate
from ibridges.path import IrodsPath

ALL_BUILTIN_COMMANDS = [
    CliList,
    CliPwd,
    CliTree,
    CliMetaList,
    CliMetaAdd,
    CliMetaDel,
    CliMakeCollection,
    CliDownload,
    CliUpload,
    CliSearch,
    CliCd,
    CliRm,
    CliSync,
    CliGui,
    CliVersion,
]
IBSHELL_HISTORY_FILE = Path.home() / ".ibridges" / ".shell_history"


class IBridgesShell(cmd.Cmd):
    """Command class implementation for iBridges."""

    identchars = cmd.Cmd.identchars + "-"

    def __init__(self):
        """Initialize the shell creating the session."""
        # Autocomplete is not available on windows.
        try:
            import readline  # pylint: disable=import-outside-toplevel

            readline.set_completer_delims(readline.get_completer_delims().replace("-", ""))
            if IBSHELL_HISTORY_FILE.is_file():
                readline.read_history_file(IBSHELL_HISTORY_FILE)
            readline.set_history_length(1000)
        except ImportError:
            pass
        self.session = cli_authenticate(None)
        self.commands = {}
        for command_class in get_all_shell_commands():
            for name in command_class.names:
                self.commands[name] = command_class
        super().__init__()

    def do_shell(self, arg):
        """Run commands in the bash/zsh shell directly for local operations."""
        # cd command doesn't work properly with subprocess, so use Python chdir.
        if arg.startswith("cd ") or arg == "cd":
            try:
                new_dir = arg[3:].strip()
                if len(new_dir) == 0:
                    new_dir = Path.home()
                os.chdir(Path(new_dir).expanduser())
            except NotADirectoryError:
                print(f"Error: {arg[3:]} is not a directory.")
            except FileNotFoundError:
                print(f"Error: {arg[3:]} does not exist.")
        else:
            subprocess.run(arg, shell=True, check=False)

    def _universal_complete(self, text, line, begidx, endidx, command_class):  # pylint: disable=unused-argument
        arg_list = _prepare_args(line, add_last_space=True)[1:]
        if arg_list[-1].startswith("-"):
            return [text + " "]
        arg_list = [x for x in arg_list if not x.startswith("-")]

        # Don't have completions for positional argument.
        if len(arg_list) > len(command_class.autocomplete):
            return []

        complete = []
        if command_class.autocomplete[len(arg_list) - 1] == "remote_path":
            complete = complete_ipath(self.session, text, line, collections_only=False)
        elif command_class.autocomplete[len(arg_list) - 1] == "remote_coll":
            complete = complete_ipath(self.session, text, line, collections_only=True)
        elif command_class.autocomplete[len(arg_list) - 1] == "local_path":
            complete = complete_lpath(text, line, directories_only=False)
        elif command_class.autocomplete[len(arg_list) - 1] == "local_dir":
            complete = complete_lpath(text, line, directories_only=True)
        elif command_class.autocomplete[len(arg_list) - 1] == "any_dir":
            complete = complete_lpath(text, line, directories_only=True) + complete_ipath(
                self.session, text, line, collections_only=True
            )
        return complete

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
        try:
            import readline  # pylint: disable=import-outside-toplevel

            IBSHELL_HISTORY_FILE.parent.mkdir(exist_ok=True, parents=True)
            readline.write_history_file(IBSHELL_HISTORY_FILE)
        except ImportError:
            pass
        except Exception:  # pylint: disable=broad-exception-caught
            traceback.print_exception(*sys.exc_info())  # Python<3.10 compatibility

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
        if attr.startswith("do_") and attr[3:] in self.commands:
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
        fake_names = fake_names + [
            f"help_{cmd_name}"
            for cmd_name, cmd in self.commands.items()
            if cmd_name == cmd.names[0]
        ]
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
    split_args = [""]
    cur_pos = 0
    cur_quote = None
    while cur_pos < len(args):
        if args[cur_pos : cur_pos + 2] in ["\\ ", "\\'", '\\"']:
            if unescape:
                split_args[-1] += args[cur_pos + 1]
            else:
                split_args[-1] += args[cur_pos : cur_pos + 2]
            cur_pos += 1
        elif args[cur_pos] == " " and cur_quote is None:
            split_args.append("")
        elif args[cur_pos] in ["'", '"'] and cur_quote is None:
            cur_quote = args[cur_pos]
        elif args[cur_pos] == cur_quote:
            cur_quote = None
        else:
            split_args[-1] += args[cur_pos]
        cur_pos += 1
    if not add_last_space and split_args[-1] == "":
        return split_args[:-1]
    return split_args


def _filter(ipaths, collections_only, base_path, add_prefix=False):
    ipaths = [p for p in ipaths if str(p) != str(base_path)]
    if collections_only:
        ipaths = [p for p in ipaths if p.collection_exists()]
    names = [p.name + "/" if p.collection_exists() else p.name for p in ipaths]
    # col_names = [p.name for p in ipaths if p.collection_exists()]
    # else:
    # col_names = [p.name for p in ipaths]
    if add_prefix:
        return [f"irods:{c}" for c in names]
    return names


def complete_ipath(session, text, line, collections_only=False):  # pylint: disable=too-many-branches
    """Complete an IrodsPath."""
    args = _prepare_args(line, unescape=False)[1:]
    args = [x for x in args if not x.startswith("-")]

    # When nothing has been completed yet.
    if len(args) == 0 or args[-1] == "":
        ipath_list = list(IrodsPath(session).walk(depth=1))
        return _escape(_filter(ipath_list, collections_only, IrodsPath(session)))

    base_arg = args[-1]
    base_completion = []
    if args[-1].startswith("irods:"[: len(args[-1])]):
        if len(args[-1]) < len("irods:"):
            base_completion = [text[: len(text) - len(args[-1])] + "irods:"]
        else:
            base_arg = args[-1][len("irods:") :]

    # In case of matching "irods:"
    if len(base_arg) == 0:
        ipath_list = list(IrodsPath(session).walk(depth=1))
        return _escape(_filter(ipath_list, collections_only, IrodsPath(session), add_prefix=False))

    # Add collections to the list
    base_path = IrodsPath(session, _unescape(base_arg))
    if base_path.collection_exists():
        if line.endswith("/"):
            path_list = _filter(base_path.walk(depth=1), collections_only, base_path)
            return [f"{text}{_escape(ipath)}" for ipath in path_list]
        base_completion.append(f"{text}/")

    # Add data objects to the list
    if base_path.dataobject_exists():
        base_completion.append(text)

    # Add partial data object and collections to the list.
    last_part = base_path.parts[-1]
    base_path = IrodsPath(session, *base_path.parts[:-1])
    completions = []
    for ipath in base_path.walk(depth=1, include_base_collection=False):
        if str(ipath) == base_path or base_arg.endswith("/"):
            continue
        if (
            ipath.name.startswith(last_part)
            and not ipath.name == last_part
            and not (collections_only and not ipath.collection_exists())
        ):
            compl = text + _escape(ipath.name[len(last_part) :])
            if ipath.collection_exists():
                compl += "/"
            completions.append(compl)

    all_completions = list(set(base_completion + completions))

    if len(all_completions) == 1 and all_completions[0] == text:
        return []
    return all_completions


def _find_paths(base_path, directories_only):
    all_paths = [p for p in base_path.iterdir() if not (directories_only and not p.is_dir())]
    all_paths = [p.name + os.sep if p.is_dir() else p.name for p in all_paths]
    return all_paths


def complete_lpath(text, line, directories_only=False):
    """Complete a local path."""
    args = _prepare_args(line, unescape=False)[1:]
    args = [x for x in args if not x.startswith("-")]

    # If nothing has been typed yet
    if len(args) == 0:
        return _escape(_find_paths(Path.cwd(), directories_only))

    base_path = Path(args[-1])
    base_completion = []
    if base_path.is_dir():
        if line.endswith("/"):
            path_list = _find_paths(base_path, directories_only)
            return [f"{text}{_escape(ipath)}" for ipath in path_list]
        base_completion.append(f"{text}/")

    if base_path.is_file():
        base_completion.append(text)

    last_part = base_path.name
    parent_path = base_path.parent
    completions = []
    path_list = _find_paths(parent_path, directories_only)
    for lpath_str in path_list:
        lpath = parent_path / lpath_str
        if (
            lpath_str.startswith(last_part)
            and not lpath.name == last_part
            and not (directories_only and not lpath.is_dir())
        ):
            completions.append(text + _escape(lpath_str[len(last_part) :]))

    all_completions = list(set(base_completion + completions))
    if len(all_completions) == 1 and all_completions[0] == text:
        return []

    return all_completions


def get_all_shell_commands():
    """Get all available shell commands."""
    external_commands = []
    for entry in entry_points(group="ibridges.shell"):
        external_commands.extend(entry.load())
    return external_commands
