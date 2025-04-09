import argparse
import cmd
import os
import subprocess

from ibridges.cli.util import cli_authenticate, list_collection
from ibridges.exception import NotACollectionError
from ibridges.path import IrodsPath


class ShellArgumentParser(argparse.ArgumentParser):
    def exit(self, status=0, message=None):
        if status:
            print(f'Error: {message}')
        self.printed_help = True

class IBridgesList():
    @staticmethod
    def get_parser():
        parser = ShellArgumentParser(
            prog="ibridges list", description="List a collection on iRODS.",
            exit_on_error=False,
        )
        parser.add_argument(
            "remote_path",
            help="Path to remote iRODS location starting with 'irods:'",
            type=str,
            default=".",
            nargs="?",
        )
        parser.add_argument(
            "-m", "--metadata",
            help="Show metadata for each iRODS location.",
            action="store_true",
        )
        parser.add_argument(
            "-s", "--short",
            help="Display available data objects/collections in short form.",
            action="store_true"
        )
        parser.add_argument(
            "-l", "--long",
            help="Display available data objects/collections in long form.",
            action="store_true",
        )
        return parser

    @staticmethod
    def run_command(session, parser, args):
        # ipath =  _parse_remote(args.remote_path, session)
        ipath = IrodsPath(session, args.remote_path)
        try:
            if args.long:
                for cur_path in ipath.walk(depth=1):
                    if str(cur_path) == str(ipath):
                        continue
                    if cur_path.collection_exists():
                        print(f"C- {cur_path.name}")
                    else:
                        print(f"{cur_path.checksum: <50} {cur_path.size: <12} {cur_path.name}")
            elif args.short:
                print(" ".join([x.name for x in ipath.walk(depth=1) if str(x) != str(ipath)]))
            else:
                list_collection(session, ipath, args.metadata)
        except NotACollectionError:
            parser.error(f"{ipath} is not a collection")



class IBridgesShell(cmd.Cmd):
    prompt = "ibridges> "

    def __init__(self):
        self.session = cli_authenticate(None)
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

    def do_ls(self, arg):
        self.do_list(arg)

    def do_list(self, arg):
        parser = IBridgesList.get_parser()
        args, extra_args = parser.parse_known_args(_prepare_args(arg))
        if not getattr(parser, "printed_help", False):
            IBridgesList.run_command(self.session, parser, args)
        # try:
            # list_collection(self.session, remote_path=IrodsPath(self.session, arg))
        # except NotACollectionError:
            # print(f"{arg} is not a collection.")

    def do_cd(self, arg):
        new_path = IrodsPath(self.session, arg)
        if new_path.collection_exists():
            self.session.cwd = new_path
        else:
            print(f"Error: {new_path} is not a collection.")

    def complete_list(self, text, line, begidx, endidx):
        return complete_ipath(self.session, text, line, collections_only=True)

    def complete_cd(self, text, line, begidx, endidx):
        return complete_ipath(self.session, text, line, collections_only=True)

    def do_EOF(self, arg):
        self.close()
        return True

    def close(self):
        self.session.close()

def main():
    IBridgesShell().cmdloop()

def _filter(ipaths, collections_only, base_path):
    ipaths = [p for p in ipaths if str(p) != str(base_path)]
    if collections_only:
        return [p.name for p in ipaths if p.collection_exists()]
    return [p.name for p in ipaths]


def _prepare_args(args):
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
    return new_args

def complete_ipath(session, text, line, collections_only=False):
    cmd, *args = line.split()
    if len(args) == 0:
        ipath_list = list(IrodsPath(session).walk(depth=1))
        return _filter(ipath_list, collections_only, IrodsPath(session))

    # if len(args) > 1:
        # return []

    base_path = IrodsPath(session, args[0])
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
