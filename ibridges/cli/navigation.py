from ibridges.cli.base import ShellArgumentParser
from ibridges.cli.util import list_collection
from ibridges.exception import NotACollectionError
from ibridges.path import IrodsPath


class IbridgesList():
    autocomplete = ["remote_coll"]
    names = ["ls", "list", "l"]

    @staticmethod
    def get_parser():
        parser = ShellArgumentParser(
            prog="ibridges list", description="List a collection on iRODS.",
            exit_on_error=False,
        )
        parser.add_argument(
            "remote_coll",
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
        ipath = IrodsPath(session, args.remote_coll)
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

class IbridgesPwd():
    autocomplete = []
    names = ["pwd"]

    @staticmethod
    def get_parser():
        return ShellArgumentParser(prog="ibridges pwd",
                                  description="Show current working collection.")

    @staticmethod
    def run_command(session, parser, args):
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
            )
            continue
        build_list.append(str(rel_path))
        j_path += 1
    _print_build_list(build_list, prefix, show_max=show_max, pels=pels)
    return j_path



class IbridgesTree():
    autocomplete = ["remote_coll"]
    names = ["tree"]

    @staticmethod
    def get_parser():
        parser = ShellArgumentParser(
            prog="ibridges tree", description="Show collection/directory tree."
        )
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
            help="Print the tree in pure ascii",
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
    def run_command(session, parser, args):
        ipath = IrodsPath(session, args.remote_coll)
        if not ipath.collection_exists():
            parser.error(f"{ipath} is not a collection.")
            return
        if args.ascii:
            pels = _tree_elements["ascii"]
        else:
            pels = _tree_elements["pretty"]
        ipath_list = [cur_path for cur_path in ipath.walk(depth=args.depth)
                      if str(cur_path) != str(ipath)]
        _tree(ipath, ipath_list, show_max=args.show_max, pels=pels)
        n_col = sum(cur_path.collection_exists() for cur_path in ipath_list)
        n_data = len(ipath_list) - n_col
        print_str = f"\n{n_col} collections, {n_data} data objects"
        if args.depth is not None:
            print_str += " (possibly more at higher depths)"
        print(print_str)
