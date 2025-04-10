import cmd
import os
import subprocess
from pathlib import Path
import readline

from ibridges.cli.util import cli_authenticate, list_collection
from ibridges.exception import NotACollectionError
from ibridges.path import IrodsPath
from ibridges.cli.navigation import IbridgesList, IbridgesPwd, IbridgesTree
from ibridges.cli.meta import CliMetaList, CliMetaAdd

ALL_BUILTIN_COMMANDS=[IbridgesList, IbridgesPwd, IbridgesTree, CliMetaList,
                      CliMetaAdd]


class IBridgesShell(cmd.Cmd):
    # prompt = "ibridges> "
    identchars = cmd.Cmd.identchars + "-"

    def __init__(self):
        readline.set_completer_delims(readline.get_completer_delims().replace("-", ""))
        self.session = cli_authenticate(None)
        self.commands = {}
        for command_class in ALL_BUILTIN_COMMANDS:
            for name in command_class.names:
                self.commands[name] = command_class
        super().__init__()

    def do_shell(self, arg):
        if arg.startswith("cd "):
            try:
                os.chdir(arg[3:])
            except NotADirectoryError:
                print(f"Error: {arg[3:]} is not a directory.")
            except FileNotFoundError:
                print(f"Error: {arg[3:]} does not exist.")
        else:
            subprocess.run(arg, shell=True)

    def do_cd(self, arg):
        new_path = IrodsPath(self.session, arg)
        if new_path.collection_exists():
            self.session.cwd = new_path
        else:
            print(f"Error: {new_path} is not a collection.")

    def complete_cd(self, text, line, begidx, endidx):
        return complete_ipath(self.session, text, line, collections_only=True)

    def _universal_complete(self, text, line, begidx, endidx, command_class):
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

    def _universal_do(self, arg, command_class):
        parser = command_class.get_parser()
        args, extra_args = parser.parse_known_args(_prepare_args(arg))
        if not getattr(parser, "printed_help", False):
            command_class.run_command(self.session, parser, args)

    def _universal_help(self, command_class):
        command_class.get_parser().print_help()

    def do_EOF(self, arg):
        self.close()
        return True

    def close(self):
        self.session.close()

    def wrap_complete(self, command_class):
        def _wrap(*args):
            return self._universal_complete(*args, command_class)
        return _wrap

    def wrap_do(self, command_class):
        def _wrap(*args):
            self._universal_do(*args, command_class)
        return _wrap

    def wrap_help(self, command_class):
        def _wrap(*args):
            self._universal_help(*args, command_class)
        return _wrap

    def __getattribute__(self, attr):
        if attr.startswith("do_") and attr[3:] in self.commands:
            return self.wrap_do(self.commands[attr[3:]])
        if attr.startswith("complete_") and attr[9:] in self.commands:
            return self.wrap_complete(self.commands[attr[9:]])
        if attr.startswith("help_") and attr[5:] in self.commands:
            return self.wrap_help(self.commands[attr[5:]])
        return super().__getattribute__(attr)

    def get_names(self):
        fake_names = [f"do_{cmd}" for cmd in self.commands]
        fake_names = fake_names + [f"complete_{cmd}" for cmd in self.commands]
        fake_names = fake_names + [f"help_{cmd}" for cmd in self.commands]
        return fake_names + super().get_names()

    @property
    def prompt(self):
        return f"ibshell:{IrodsPath(self.session).name}> "

    # def default(self, line):
        # raise ValueError(line)

    # def completenames(self, text, *ignored):
    #     print(text, "|", ignored, super().completenames(text, *ignored))
    #     return super().completenames(text, *ignored)

    # def completedefault(*ignored):
    #     print("failed complette", ignored)
    #     import traceback as tb
    #     print(tb.print_stack())
    #     # raise ValueError(ignored)
    #     # return []

    # def complete(self, text, state):
    #     print(text, state)
    #     return super().complete(text, state)

def main():
    IBridgesShell().cmdloop()



def _prepare_args(args, add_last_space=False):
    split_args = args.split()
    new_args = []
    cur_arg = ""
    for i_args, str_arg in enumerate(split_args):
        cur_arg += str_arg
        if not str_arg.endswith("\\ "):
            new_args.append(cur_arg.replace("\\ ", " "))
            cur_arg = ""
    if cur_arg != "":
        new_args.append(cur_arg.replace("\\ ", " "))
    if add_last_space and args.endswith(" ") and not args.endswith("\\ "):
        new_args.append("")
    return new_args

def _filter(ipaths, collections_only, base_path):
    ipaths = [p for p in ipaths if str(p) != str(base_path)]
    if collections_only:
        return [p.name for p in ipaths if p.collection_exists()]
    return [p.name for p in ipaths]


def complete_ipath(session, text, line, collections_only=False):
    # print(line)
    args = _prepare_args(line)[1:]
    # print(args)
    if len(args) == 0 or args[-1] == "":
        ipath_list = list(IrodsPath(session).walk(depth=1))
        return _filter(ipath_list, collections_only, IrodsPath(session))

    base_path = IrodsPath(session, args[-1])
    if base_path.collection_exists():
        if line.endswith("/"):
            prefix = text
        else:
            prefix = f"{text}/"
        path_list = _filter(base_path.walk(depth=1), collections_only, base_path)
        return [f"{prefix}{ipath}" for ipath in path_list]
    elif base_path.dataobject_exists():
        return []

    last_part = base_path.parts[-1]
    base_path = IrodsPath(session, *base_path.parts[:-1])
    completions = []
    for ipath in base_path.walk(depth=1):
        if str(ipath) == base_path:
            continue
        if ipath.name.startswith(last_part) and not (
                collections_only and not ipath.collection_exists()):
            completions.append(text + ipath.name[len(last_part):])
    return completions

def _find_paths(base_path, directories_only):
    all_paths = []
    for path in base_path.iterdir():
        if directories_only and not path.is_dir():
            continue
        all_paths.append(path.name)
    return all_paths


def complete_lpath(text, line, directories_only=False):
    args = _prepare_args(line)[1:]
    if len(args) == 0:
        return _find_paths(Path.cwd(), directories_only)

    base_path = Path(args[-1])
    if base_path.is_dir():
        if line.endswith("/"):
            prefix = text
        else:
            prefix = f"{text}/"
        path_list = _find_paths(base_path, directories_only)
        return [f"{prefix}{ipath}" for ipath in path_list]
    elif base_path.is_file():
        return []

    last_part = base_path.name
    parent_path = base_path.parent
    completions = []
    path_list = _find_paths(parent_path, directories_only)
    for lpath_str in path_list:
        lpath = parent_path / lpath_str
        if lpath_str.startswith(last_part) and not (
                directories_only and not lpath.is_dir()):
            completions.append(text + lpath_str[len(last_part):])
    return completions
