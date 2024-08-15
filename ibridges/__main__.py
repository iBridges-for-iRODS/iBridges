"""Command line tools for the iBridges library."""

from __future__ import annotations

import argparse
import json
import sys
from argparse import RawTextHelpFormatter
from pathlib import Path
from typing import Optional, Union

from ibridges.data_operations import download, sync, upload
from ibridges.interactive import DEFAULT_IENV_PATH, DEFAULT_IRODSA_PATH, interactive_auth
from ibridges.path import IrodsPath
from ibridges.search import search_data
from ibridges.session import Session
from ibridges.util import (
    find_environment_provider,
    get_collection,
    get_environment_providers,
    print_environment_providers,
)

try:  # Python < 3.10 (backport)
    from importlib_metadata import version  # type: ignore
except ImportError:
    from importlib.metadata import version  # type: ignore [assignment]

IBRIDGES_CONFIG_FP = Path.home() / ".ibridges" / "ibridges_cli.json"


MAIN_HELP_MESSAGE = f"""
iBridges CLI version {version("ibridges")}

Usage: ibridges [subcommand] [options]

Available subcommands:
    init:
        Attempt to cache the password and choose the irods_environment.json.
    download:
        Download a data object or collection from the iRODS server.
    upload:
        Upload a file or directory to the iRODS server
        (which converts it to a data object/collection respectively).
    sync:
        Synchronize files/folders and data objects/collections with each other.
        Only updated files will be downloaded/uploaded.
    list:
        List the content of a collections, if no path is given, the home collection will be listed.
    tree:
        List a collection and subcollections in a hierarchical way.
    mkcoll:
        Create the collection and all its parent collections.
    setup:
        Create an iRODS environment file to connect to an iRODS server.

The iBridges CLI does not implement the complete iBridges API. For example, there
are no commands to modify metadata on the irods server.

Example usage:

ibridges download "irods:~/test.txt"
ibridges upload ~/test.txt "irods:/test"
ibridges init
ibridges sync ~/directory "irods:~/collection"
ibridges list irods:~/collection
ibridges mkcoll irods://~/bli/bla/blubb
ibridges tree irods:~/collection
ibridges setup uu-its

Reuse a configuration by an alias:
ibridges init ~/.irods/irods_environment.json --alias my_irods
ibridges init my_irods

Program information:
    -v, --version - display CLI version and exit
    -h, --help    - display this help file and exit
"""



def main() -> None:
    """CLI pointing to different entrypoints."""
    # ensure .irods folder
    irods_loc = Path.home() / ".irods"
    irods_loc.mkdir(exist_ok=True)
    # show help by default, else consume first argument
    subcommand = "--help" if len(sys.argv) < 2 else sys.argv.pop(1)

    if subcommand in ["-h", "--help"]:
        print(MAIN_HELP_MESSAGE)
    elif subcommand in ["-v", "--version"]:
        print(f"iBridges version {version('ibridges')}")

    # find the subcommand in this module and run it!
    elif subcommand == "download":
        ibridges_download()
    elif subcommand == "upload":
        ibridges_upload()
    elif subcommand == "sync":
        ibridges_sync()
    elif subcommand == "init":
        ibridges_init()
    elif subcommand == "list":
        ibridges_list()
    elif subcommand == "mkcoll":
        ibridges_mkcoll()
    elif subcommand == "tree":
        ibridges_tree()
    elif subcommand == "setup":
        ibridges_setup()
    elif subcommand == "search":
        ibridges_search()
    else:
        print(f"Invalid subcommand ({subcommand}). For help see ibridges --help")
        sys.exit(1)

def _get_ibridges_conf(ienv_path) -> dict:
    try:
        with open(IBRIDGES_CONFIG_FP, "r", encoding="utf-8") as handle:
            ibridges_conf = json.load(handle)
    except FileNotFoundError:
        if ienv_path is None:
            return {}
        ibridges_conf = {}
        IBRIDGES_CONFIG_FP.parent.mkdir(exist_ok=True)
    return ibridges_conf

def _set_alias(alias, ienv_path: Union[str, Path]):
    ibridges_conf = _get_ibridges_conf(ienv_path)
    if "aliases" not in ibridges_conf:
        ibridges_conf["aliases"] = {}
    try:
        with open(DEFAULT_IRODSA_PATH, "r", encoding="utf-8") as handle:
            irodsa_backup = handle.read()
    except FileNotFoundError:
        irodsa_backup = None
    ibridges_conf["aliases"][alias] = {"path": str(Path(ienv_path).absolute()),
                                       "irodsa_backup": irodsa_backup}
    with open(IBRIDGES_CONFIG_FP, "w", encoding="utf-8") as handle:
        json.dump(ibridges_conf, handle)

def _set_ienv_path(ienv_path: Union[None, str, Path], alias: Optional[str] = None) -> Optional[str]:
    if ienv_path is None and alias is None:
        return None

    ibridges_conf = _get_ibridges_conf(ienv_path)

    # Detect possible alias.
    if alias is None and str(ienv_path) in ibridges_conf.get("aliases", {}):
        alias = str(ienv_path)
    if alias is not None:
        ienv_path = ibridges_conf["aliases"][alias]["path"]
        irodsa_backup = ibridges_conf["aliases"][alias]["irodsa_backup"]
        if irodsa_backup is not None:
            with open(DEFAULT_IRODSA_PATH, "w", encoding="utf-8") as handle:
                handle.write(irodsa_backup)

    if alias is not None:
        ibridges_conf["cli_last_env"] = alias
    elif ienv_path is not None:
        ibridges_conf["cli_last_env"] = str(Path(ienv_path).absolute())
    else:
        ibridges_conf["cli_last_env"] = None

    with open(IBRIDGES_CONFIG_FP, "w", encoding="utf-8") as handle:
        json.dump(ibridges_conf, handle)
    return ibridges_conf["cli_last_env"]


def _get_ienv_path() -> Union[None, str]:
    try:
        with open(IBRIDGES_CONFIG_FP, "r", encoding="utf-8") as handle:
            ibridges_conf = json.load(handle)
            return ibridges_conf.get("cli_last_env")
    except FileNotFoundError:
        return None


def _cli_auth(ienv_path: Union[None, str, Path]):
    ibridges_conf = _get_ibridges_conf(ienv_path)
    alias = None
    if str(ienv_path) in ibridges_conf.get("aliases", {}):
        alias = str(ienv_path)
        ienv_path = ibridges_conf["aliases"][alias]["path"]
    ienv_path = ienv_path if ienv_path is not None else DEFAULT_IENV_PATH
    if not Path(ienv_path).exists():
        print(f"Error: Irods environment file or alias '{ienv_path}' does not exist.")
        sys.exit(124)
    session = interactive_auth(irods_env_path=ienv_path)
    if alias is not None:
        with open(DEFAULT_IRODSA_PATH, "r", encoding="utf-8") as handle:
            irodsa_content = handle.read()
        if irodsa_content != ibridges_conf["aliases"][alias]["irodsa_backup"]:
            _set_alias(alias, ienv_path)
    return session

def ibridges_init():
    """Create a cached password for future use."""
    parser = argparse.ArgumentParser(
        prog="ibridges init", description="Cache your iRODS password to be used later."
    )
    parser.add_argument(
        "irods_env_path",
        help="The path to your iRODS environment JSON file.",
        type=Path,
        default=None,
        nargs="?",
    )
    parser.add_argument(
        "--alias",
        help="Create an alias for this configuration.",
        type=str,
        default=None,
        required=False,
    )
    args, _ = parser.parse_known_args()
    if args.alias is not None:
        _set_alias(args.alias, args.irods_env_path)
    _set_ienv_path(args.irods_env_path, args.alias)

    with _cli_auth(ienv_path=_get_ienv_path()) as session:
        if not isinstance(session, Session):
            raise ValueError(f"Irods session '{session}' is not a session.")
    print("ibridges init was succesful.")


def _list_coll(session: Session, remote_path: IrodsPath):
    if remote_path.collection_exists():
        print(str(remote_path) + ":")
        coll = get_collection(session, remote_path)
        print("\n".join(["  " + sub.path for sub in coll.data_objects]))
        print(
            "\n".join(
                [
                    "  C- " + sub.path
                    for sub in coll.subcollections
                    if not str(remote_path) == sub.path
                ]
            )
        )
    else:
        raise ValueError(f"Irods path '{remote_path}' is not a collection.")


def ibridges_setup():
    """Use templates to create an iRODS environment json."""
    parser = argparse.ArgumentParser(
        prog="ibridges setup", description="Tool to create a valid irods_environment.json"
    )
    parser.add_argument(
        "server_name",
        help="Server name to create your irods_environment.json for.",
        type=str,
        default=None,
        nargs="?",
    )
    parser.add_argument("--list", help="List all available server names.", action="store_true")
    parser.add_argument(
        "-o",
        "--output",
        help="Store the environment to a file.",
        type=Path,
        default=DEFAULT_IENV_PATH,
        required=False,
    )
    parser.add_argument(
        "--overwrite", help="Overwrite the irods environment file.", action="store_true"
    )
    args = parser.parse_args()
    env_providers = get_environment_providers()
    if args.list:
        if len(env_providers) == 0:
            print(
                "No server information was found. To use this function, please install a plugin"
                " such as:\n\nhttps://github.com/UtrechtUniversity/ibridges-servers-uu"
                "\n\nAlternatively create an irods_environment.json by yourself or with the help "
                "of your iRODS administrator."
            )
        print_environment_providers(env_providers)
        return

    try:
        provider = find_environment_provider(env_providers, args.server_name)
    except ValueError:
        print(
            f"Error: Unknown server with name {args.server_name}.\n"
            "Use `ibridges setup --list` to list all available server names."
        )
        sys.exit(123)

    user_answers = {}
    for question in provider.questions:
        user_answers[question] = input(question + ": ")

    json_str = provider.environment_json(args.server_name, **user_answers)
    if args.output.is_file() and not args.overwrite:
        print(f"File {args.output} already exists, use --overwrite or copy the below manually.")
        print("\n")
        print(json_str)
    if args.output.is_dir():
        print(f"Output {args.output} is a directory, cannot export irods_environment" " file.")
        sys.exit(234)
    else:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(json_str)


def ibridges_list():
    """List a collection on iRODS."""
    parser = argparse.ArgumentParser(
        prog="ibridges list", description="List a collection on iRODS."
    )
    parser.add_argument(
        "remote_path",
        help="Path to remote iRODS location starting with 'irods:'",
        type=str,
        default=None,
        nargs="?",
    )

    args, _ = parser.parse_known_args()
    with _cli_auth(ienv_path=_get_ienv_path()) as session:
        _list_coll(session, _parse_remote(args.remote_path, session))


def _create_coll(session: Session, remote_path: IrodsPath):
    if remote_path.exists():
        raise ValueError(f"New collection path {remote_path} already exists.")
    remote_path.create_collection(session, remote_path)


def ibridges_mkcoll():
    """Create a collection with all its parents given the new path."""
    parser = argparse.ArgumentParser(
        prog="ibridges mkcoll",
        description="Create a new collecion with all its parent collections.",
    )
    parser.add_argument(
        "remote_path",
        help="Path to a new collection, should start with 'irods:'.",
        type=str,
    )

    args, _ = parser.parse_known_args()
    with _cli_auth(ienv_path=_get_ienv_path()) as session:
        _create_coll(session, _parse_remote(args.remote_path, session))


def _parse_local(local_path: Union[None, str, Path]) -> Path:
    if local_path is None:
        return Path.cwd()
    if isinstance(local_path, str):
        if local_path.startswith("irods:"):
            raise ValueError("Please provide a local path (not starting with 'irods:')")
        local_path = Path(local_path)
    return local_path


def _parse_remote(remote_path: Union[None, str], session: Session) -> IrodsPath:
    if remote_path is None:
        return IrodsPath(session, session.home)
    if not remote_path.startswith("irods:"):
        raise ValueError("Please provide a remote path starting with 'irods:'.")
    if remote_path.startswith("irods://"):
        remainder = remote_path[8:]
        if remainder.startswith("~"):
            return IrodsPath(session, remainder)
        return IrodsPath(session, remote_path[7:])
    return IrodsPath(session, remote_path[6:])

def _get_metadata_path(args, ipath: IrodsPath, lpath: Union[str, Path],
                       mode: str) -> Union[None, str, Path]:
    metadata = False if not hasattr(args, "metadata") else args.metadata
    if ipath.dataobject_exists() and metadata is None:
        raise ValueError("Supply metadata path for downloading metadata of data objects.")
    if mode == "download":
        default_meta_path = Path(lpath, ipath.name, ".ibridges_metadata.json")
    elif mode in ["upload", "sync"]:
        default_meta_path = Path(lpath, ".ibridges_metadata.json")
    else:
        raise ValueError("Internal error, contact the iBridges team.")
    metadata = metadata if metadata is not None else default_meta_path
    metadata = None if metadata is False else metadata
    return metadata


def ibridges_download():
    """Download a remote data object or collection."""
    parser = argparse.ArgumentParser(
        prog="ibridges download",
        description="Download a data object or collection from an iRODS server.",
    )
    parser.add_argument(
        "remote_path",
        help="Path to remote iRODS location starting with 'irods:'",
        type=str,
    )
    parser.add_argument(
        "local_path",
        help="Local path to download the data object/collection to.",
        type=Path,
        nargs="?",
    )
    parser.add_argument(
        "--overwrite",
        help="Overwrite the local file(s) if it exists.",
        action="store_true",
    )
    parser.add_argument(
        "--resource",
        help="Name of the resource from which the data is to be downloaded.",
        type=str,
        default="",
        required=False,
    )
    parser.add_argument(
        "--dry-run",
        help="Do not perform the download, but list the files to be updated.",
        action="store_true",
    )
    parser.add_argument(
        "--metadata",
        help="Path for metadata",
        default=argparse.SUPPRESS,
        type=Path,
        nargs="?",
    )
    args = parser.parse_args()
    with interactive_auth(irods_env_path=_get_ienv_path()) as session:
        ipath = _parse_remote(args.remote_path, session)
        lpath = _parse_local(args.local_path)
        metadata = _get_metadata_path(args, ipath, lpath, "download")
        ops = download(
            session,
            ipath,
            lpath,
            overwrite=args.overwrite,
            resc_name=args.resource,
            dry_run=args.dry_run,
            metadata=metadata,
        )
        if args.dry_run:
            ops.print_summary()


def ibridges_upload():
    """Upload a local file or directory to the irods server."""
    parser = argparse.ArgumentParser(
        prog="ibridges upload",
        description="Upload a data object or collection from an iRODS server.",
    )
    parser.add_argument(
        "local_path",
        help="Local path to upload the data object/collection from.",
        type=Path,
    )
    parser.add_argument(
        "remote_path",
        help="Path to remote iRODS location starting with 'irods:'",
        type=str,
    )
    parser.add_argument(
        "--overwrite",
        help="Overwrite the remote file(s) if it exists.",
        action="store_true",
    )
    parser.add_argument(
        "--resource",
        help="Name of the resource to which the data is to be uploaded.",
        type=str,
        default="",
        required=False,
    )
    parser.add_argument(
        "--dry-run",
        help="Do not perform the upload, but list the files to be updated.",
        action="store_true",
    )
    parser.add_argument(
        "--metadata",
        help="Path for metadata",
        default=argparse.SUPPRESS,
        type=Path,
        nargs="?",
    )
    args = parser.parse_args()

    with interactive_auth(irods_env_path=_get_ienv_path()) as session:
        lpath = _parse_local(args.local_path)
        ipath = _parse_remote(args.remote_path, session)
        metadata = _get_metadata_path(args, ipath, lpath, "upload")
        ops = upload(
            session,
            lpath,
            ipath,
            overwrite=args.overwrite,
            resc_name=args.resource,
            dry_run=args.dry_run,
            metadata=metadata,
        )
        if args.dry_run:
            ops.print_summary()


def _parse_str(remote_or_local: str, session) -> Union[Path, IrodsPath]:
    if remote_or_local.startswith("irods:"):
        return IrodsPath(session, remote_or_local[6:])
    return Path(remote_or_local)


def ibridges_sync():
    """Synchronize files/directories between local and remote."""
    parser = argparse.ArgumentParser(
        prog="ibridges sync", description="Synchronize files/directories between local and remote."
    )
    parser.add_argument(
        "source",
        help="Source path to synchronize from (collection on irods server or local directory).",
        type=str,
    )
    parser.add_argument(
        "destination",
        help="Destination path to synchronize to (collection on irods server or local directory).",
        type=str,
    )
    parser.add_argument(
        "--dry-run",
        help="Do not perform the synchronization, but list the files to be updated.",
        action="store_true",
    )
    parser.add_argument(
        "--metadata",
        help="Path for metadata",
        default=argparse.SUPPRESS,
        type=Path,
        nargs="?",
    )
    args = parser.parse_args()

    with interactive_auth(irods_env_path=_get_ienv_path()) as session:
        src_path = _parse_str(args.source, session)
        dest_path = _parse_str(args.destination, session)
        if isinstance(src_path, Path) and isinstance(dest_path, IrodsPath):
            metadata = _get_metadata_path(args, dest_path, src_path, "sync")
        elif isinstance(src_path, IrodsPath) and isinstance(dest_path, Path):
            metadata = _get_metadata_path(args, src_path, dest_path, "sync")
        else:
            print("Please provide as the source and destination exactly one local path,"
                  " and one remote path.")
            sys.exit(192)
        ops = sync(
            session,
            src_path,
            dest_path,
            dry_run=args.dry_run,
            metadata=metadata,
        )
        if args.dry_run:
            ops.print_summary()


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
        n_half = (show_max - 1) // 2
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


def ibridges_tree():
    """Print a tree representation of a remote directory."""
    parser = argparse.ArgumentParser(
        prog="ibridges tree", description="Show collection/directory tree."
    )
    parser.add_argument(
        "remote_path",
        help="Path to collection to make a tree of.",
        type=str,
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
    args, _ = parser.parse_known_args()
    with _cli_auth(ienv_path=_get_ienv_path()) as session:
        ipath = _parse_remote(args.remote_path, session)
        if args.ascii:
            pels = _tree_elements["ascii"]
        else:
            pels = _tree_elements["pretty"]
        ipath_list = [cur_path for cur_path in ipath.walk(depth=args.depth)
                      if str(cur_path) != str(ipath)]
        print(ipath)
        _tree(ipath, ipath_list, show_max=args.show_max, pels=pels)
        n_col = sum(cur_path.collection_exists() for cur_path in ipath_list)
        n_data = len(ipath_list) - n_col
        print_str = f"\n{n_col} collections, {n_data} data objects"
        if args.depth is not None:
            print_str += " (possibly more at higher depths)"
        print(print_str)


def ibridges_search():
    """Search for collections and objects using constraints."""
    epilog = """Examples:

ibridges search --path-pattern "%.txt"
ibridges search --checksum "sha2:5dfasd%"
ibridges search --metadata "key" "value" "units"
ibridges search --metadata "key" --metadata "key2" "value2"
ibridges search irods:some_collection --item_type data_object
ibridges search irods:some_collection --item_type collection
"""
    parser = argparse.ArgumentParser(
        prog="ibridges search",
        description="Search for dataobjects and collections.",
        epilog=epilog,
        formatter_class=RawTextHelpFormatter,
    )
    parser.add_argument(
        "remote_path",
        help="Remote path to search inn. The path itself will not be matched.",
        type=str,
        default=None,
        nargs="?"
    )
    parser.add_argument(
        "--path-pattern",
        default=None,
        type=str,
        help=("Pattern of the path constraint. For example, use '%%.txt' to find all data objects"
              " and collections that end with .txt. You can also use the name of the item here "
              "to find all items with that name.")
    )
    parser.add_argument(
        "--checksum",
        default=None,
        type=str,
        help="Checksum of the data objects to be found."
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
        help="Use data_object or collection to show only items of that type. By default all items"
        " are returned."
    )

    args = parser.parse_args()
    with _cli_auth(ienv_path=_get_ienv_path()) as session:
        ipath = _parse_remote(args.remote_path, session)
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
