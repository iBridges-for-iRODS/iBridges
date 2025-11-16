"""Navigational subcommands for the shell and CLI."""

from __future__ import annotations

import argparse
import importlib.util
import os
import platform
from importlib.metadata import version
from typing import Optional

from ibridges.cli.base import BaseCliCommand
from ibridges.cli.config import IbridgesConf
from ibridges.cli.util import cli_authenticate, list_collection, parse_remote
from ibridges.exception import NotACollectionError
from ibridges.path import IrodsPath
from ibridges.search import search_data


class CliList(BaseCliCommand):
    """Subcommand to list a collection on an iRODS server."""

    autocomplete = ["remote_coll"]
    names = ["ls", "list", "l"]
    description = "List a collection on iRODS."
    examples = ["", "irods:some_collection"]

    @classmethod
    def _mod_parser(cls, parser):
        parser.add_argument(
            "remote_coll",
            help="Path to remote iRODS location starting with 'irods:'.",
            type=str,
            default=".",
            nargs="?",
        )
        parser.add_argument(
            "-m",
            "--metadata",
            help="Show metadata for each iRODS location, only in combination with -i/--icommands.",
            action="store_true",
        )
        parser.add_argument(
            "-i",
            "--icommands",
            help="Display available data objects/collections in iCommands form.",
            action="store_true",
        )
        parser.add_argument(
            "-l",
            "--long",
            help="Display available data objects/collections in long form.",
            action="store_true",
        )
        parser.add_argument(
            "--nocolor",
            help="Disable printing with color.",
            action="store_true",
        )
        return parser

    @staticmethod
    def run_shell(session, parser, args):
        """List a collection on an iRODS server."""
        ipath = parse_remote(args.remote_coll, session)
        dir_color = None if args.nocolor else _check_dir_color(session)
        try:
            if args.icommands or args.metadata:
                if args.long:
                    parser.error("Cannot use combination of long format (-l) and metadata (-m).")
                    return
                list_collection(session, ipath, args.metadata)
            elif args.long:
                for cur_path in ipath.walk(depth=1, include_base_collection=False):
                    if cur_path.collection_exists():
                        print(f"{64*' '}{_path_with_color(cur_path, dir_color)}")
                    else:
                        print(f"{cur_path.checksum: <50} {cur_path.size: <12} {cur_path.name}")
            else:
                print(
                    " ".join(
                        [
                            _path_with_color(x, dir_color)
                            for x in ipath.walk(depth=1)
                            if str(x) != str(ipath)
                        ]
                    )
                )
        except NotACollectionError:
            parser.error(f"{ipath} is not a collection")


class CliCd(BaseCliCommand):
    """Subcommand to change collection."""

    autocomplete = ["remote_coll"]
    names = ["cd"]
    description = "Change current working collection for the iRODS server."
    examples = ["", "irods:some_collection"]

    @classmethod
    def _mod_parser(cls, parser):
        parser.add_argument(
            "remote_coll",
            help="Path to remote iRODS location.",
            type=str,
            default="~",
            nargs="?",
        )
        return parser

    @staticmethod
    def run_shell(session, parser, args):
        """Change collection in the shell."""
        new_path = parse_remote(args.remote_coll, session)
        if new_path.collection_exists():
            session.cwd = new_path
        else:
            parser.error(f"{new_path} is not a collection.")

    @classmethod
    def run_command(cls, args):
        """Change collection in the cli."""
        parser = cls.get_parser(argparse.ArgumentParser)
        with cli_authenticate(parser) as session:
            new_ipath = parse_remote(args.remote_coll, session)
            if not new_ipath.collection_exists():
                parser.error(f"Collection {new_ipath} does not exist.")
            ibridges_conf = IbridgesConf(parser)
            entry = ibridges_conf.get_entry()
            entry[1]["cwd"] = str(new_ipath)
            ibridges_conf.save()


class CliPwd(BaseCliCommand):
    """Subcommand to show the current working collection."""

    autocomplete = []
    names = ["pwd"]
    description = "Show current working collection."
    examples = [""]

    @staticmethod
    def run_shell(session, parser, args):
        """Show the current working collection."""
        print(session.cwd)


# prefix components:
_tree_elements = {
    "pretty": {
        "space": "    ",
        "branch": "│   ",
        "skip": "...",
        "tee": "├── ",
        "last": "└── ",
    },
    "ascii": {
        "space": "    ",
        "branch": "|   ",
        "skip": "...",
        "tee": "|-- ",
        "last": "\\-- ",
    },
}


def _print_build_list(build_list: list[str], prefix: str, pels: dict[str, str], show_max: int = 10):
    if len(build_list) > show_max:
        n_half = (show_max) // 2
        n_half = max(n_half, 1)
        for item in build_list[:n_half]:
            print(prefix + pels["tee"] + item)
        print(prefix + pels["skip"])
        for item in build_list[-n_half:-1]:
            print(prefix + pels["tee"] + item)
    else:
        for item in build_list[:-1]:
            print(prefix + pels["tee"] + item)
    if len(build_list) > 0:
        print(prefix + pels["last"] + build_list[-1])


def _tree(
    ipath: IrodsPath,
    path_list: list[IrodsPath],
    pels: dict[str, str],
    prefix: str = "",
    show_max: int = 10,
    dir_color: Optional[str] = None,
):
    """Generate A recursive generator, given a directory Path object.

    will yield a visual tree structure line by line
    with each line prefixed by the same characters

    """
    j_path = 0
    build_list: list[str] = []
    while j_path < len(path_list):
        cur_path = path_list[j_path]
        try:
            rel_path = cur_path.relative_to(ipath)
        except ValueError:
            break
        if len(rel_path.parts) > 1:
            _print_build_list(build_list, prefix, show_max=show_max, pels=pels)
            build_list = []
            j_path += _tree(
                cur_path.parent,
                path_list[j_path:],
                show_max=show_max,
                prefix=prefix + pels["branch"],
                pels=pels,
                dir_color=dir_color,
            )
            continue
        str_path = _path_with_color(cur_path, dir_color)
        # if cur_path.dataobject_exists() or dir_color is None:
        # str_path = str(rel_path)
        # else:
        # str_path = f"\033[{dir_color}m" + str(rel_path) + "\033[0m"
        build_list.append(str_path)
        j_path += 1
    _print_build_list(build_list, prefix, show_max=show_max, pels=pels)
    return j_path


class CliTree(BaseCliCommand):
    """Subcommand to show the tree of a collection."""

    autocomplete = ["remote_coll"]
    names = ["tree"]
    description = "Show collection/directory tree."
    examples = ["", "irods:some_collection"]

    @classmethod
    def _mod_parser(cls, parser):
        parser.add_argument(
            "remote_coll",
            help="Path to collection to make a tree of.",
            type=str,
            nargs="?",
            default=".",
        )
        parser.add_argument(
            "--show-max",
            help="Show only up to this number of dataobject in the same collection, default 10.",
            default=10,
            type=int,
        )
        parser.add_argument(
            "--ascii",
            help="Print the tree in pure ascii.",
            action="store_true",
        )
        parser.add_argument(
            "--depth",
            help="Maximum depth of the tree to be shown, default no limit.",
            default=None,
            type=int,
        )
        return parser

    @staticmethod
    def run_shell(session, parser, args):
        """Show the tree of a collection."""
        ipath = IrodsPath(session, args.remote_coll)
        dir_color = _check_dir_color(session)

        if not ipath.collection_exists():
            parser.error(f"{ipath} is not a collection.")
            return
        if args.ascii:
            pels = _tree_elements["ascii"]
        else:
            pels = _tree_elements["pretty"]
        ipath_list = [
            cur_path for cur_path in ipath.walk(depth=args.depth) if str(cur_path) != str(ipath)
        ]
        _tree(ipath, ipath_list, show_max=args.show_max, pels=pels, dir_color=dir_color)
        n_col = sum(cur_path.collection_exists() for cur_path in ipath_list)
        n_data = len(ipath_list) - n_col
        print_str = f"\n{n_col} collections, {n_data} data objects"
        if args.depth is not None:
            print_str += " (possibly more at higher depths)"
        print(print_str)


class CliSearch(BaseCliCommand):
    """Subcommand to search for kdata objects and collections."""

    autocomplete = ["remote_path"]
    names = ["search"]
    description = "Search for dataobjects and collections."
    examples = [
        '--path-pattern "%.txt"',
        '--checksum "sha2:5dfasd%"',
        '--metadata "key" "value" "units"',
        '--metadata "key" --metadata "key2" "value2"',
        "irods:some_collection --item_type data_object",
        "irods:some_collection --item_type collection",
    ]

    @classmethod
    def _mod_parser(cls, parser):
        parser.add_argument(
            "remote_path",
            help="Remote path to search inn. The path itself will not be matched.",
            type=str,
            default=".",
            nargs="?",
        )
        parser.add_argument(
            "--path-pattern",
            default=None,
            type=str,
            help=(
                "Pattern of the path constraint. For example, use '%%.txt' "
                "to find all data objects"
                " and collections that end with .txt. You can also use the name of the item here "
                "to find all items with that name."
            ),
        )
        parser.add_argument(
            "--checksum", default=None, type=str, help="Checksum of the data objects to be found."
        )
        parser.add_argument(
            "--metadata",
            nargs="+",
            action="append",
            help="Constrain the results using metadata, see examples. Can be used multiple times.",
        )
        parser.add_argument(
            "--item_type",
            type=str,
            default=None,
            help="Use data_object or collection to show only items of that type. "
            "By default all items are returned.",
        )
        return parser

    @staticmethod
    def run_shell(session, parser, args):
        """Search for data objects and collections."""
        ipath = parse_remote(args.remote_path, session)
        search_res = search_data(
            session,
            ipath,
            path_pattern=args.path_pattern,
            checksum=args.checksum,
            metadata=args.metadata,
            item_type=args.item_type,
        )
        for cur_path in search_res:
            print(cur_path)


def _check_dir_color(session):
    if hasattr(session, "dir_color"):
        return getattr(session, "dir_color")

    if platform.system() == "Windows":
        try:
            import ctypes  # pylint: disable=import-outside-toplevel

            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
            dir_color = "34"
        except Exception:  # pylint: disable=broad-exception-caught
            dir_color = None
    else:
        ls_colors = os.environ.get("LS_COLORS", "")
        dir_color = [x for x in ls_colors.split(":") if x.startswith("di=")]
        dir_color = "34" if len(dir_color) == 0 else dir_color[0][3:]

    session.dir_color = dir_color
    return dir_color


def _path_with_color(path, dir_color):
    if path.dataobject_exists() or dir_color is None:
        str_path = str(path.name)
    else:
        str_path = f"\033[{dir_color}m" + str(path.name) + "\033[0m"
    return str_path


class CliGui(BaseCliCommand):
    """Subcommand to open the iBridges GUI."""

    names = ["gui"]
    description = "Start the iBridges GUI."
    examples = [""]

    @staticmethod
    def run_shell(session, parser, args):
        """Running the GUI from the shell is not available (yet)."""  # noqa: D401
        if (importlib.util.find_spec("ibridgesgui")) is not None:
            from ibridgesgui.__main__ import main  # type: ignore # pylint: disable=E0401, C0415

            try:
                main(session)
            except RuntimeError:
                parser.error("The iBridges gui cannot start. Try restarting the shell.")
        else:
            parser.error(
                "'ibridgesgui' is not installed. Please install with\n pip install ibridgesgui"
            )

    @classmethod
    def run_command(cls, args):
        """Start the GUI."""
        parser = cls.get_parser(argparse.ArgumentParser)

        if (importlib.util.find_spec("ibridgesgui")) is not None:
            from ibridgesgui.__main__ import main  # type: ignore # pylint: disable=E0401, C0415

            main()
        else:
            parser.error(
                "'ibridgesgui' is not installed. Please install with\n pip install ibridgesgui"
            )


class CliVersion(BaseCliCommand):
    """Subcommand to open the iBridges GUI."""

    names = ["version"]
    description = "Print the version of iBridges."
    examples = [""]

    @staticmethod
    def run_shell(session, parser, args):
        """Print the version."""
        print(f"""iBridges CLI version {version("ibridges")}""")

    @classmethod
    def run_command(cls, args):
        """Print tha version."""
        print(f"""iBridges CLI version {version("ibridges")}""")
