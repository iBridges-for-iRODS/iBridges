"""Command line tools for the iBridges library."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Union

from ibridges.data_operations import download, sync, upload
from ibridges.interactive import DEFAULT_IENV_PATH, interactive_auth
from ibridges.path import IrodsPath
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


Program information:
    -v, --version - display CLI version and exit
    -h, --help    - display this help file and exit
"""

IBRIDGES_CONFIG_FP = Path.home() / ".ibridges" / "ibridges_cli.json"


def main() -> None:
    """CLI pointing to different entrypoints."""
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
    else:
        print(f"Invalid subcommand ({subcommand}). For help see ibridges --help")
        sys.exit(1)


def _set_ienv_path(ienv_path: Union[None, str, Path]):
    try:
        with open(IBRIDGES_CONFIG_FP, "r", encoding="utf-8") as handle:
            ibridges_conf = json.load(handle)
    except FileNotFoundError:
        if ienv_path is None:
            return None
        ibridges_conf = {}
        IBRIDGES_CONFIG_FP.parent.mkdir(exist_ok=True)

    if ienv_path is not None:
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
    args, _ = parser.parse_known_args()
    ienv_path = _set_ienv_path(args.irods_env_path)
    with interactive_auth(irods_env_path=ienv_path) as session:
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
    with interactive_auth(irods_env_path=_get_ienv_path()) as session:
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
    with interactive_auth(irods_env_path=_get_ienv_path()) as session:
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
        print(remainder)
        if remainder.startswith("~"):
            return IrodsPath(session, remainder)
        return IrodsPath(session, remote_path[7:])
    return IrodsPath(session, remote_path[6:])


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
    args = parser.parse_args()
    with interactive_auth(irods_env_path=_get_ienv_path()) as session:
        ops = download(
            session,
            _parse_remote(args.remote_path, session),
            _parse_local(args.local_path),
            overwrite=args.overwrite,
            resc_name=args.resource,
            dry_run=args.dry_run,
        )
        if args.dry_run:
            _summarize_ops(ops)


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
    args = parser.parse_args()

    with interactive_auth(irods_env_path=_get_ienv_path()) as session:
        ops = upload(
            session,
            _parse_local(args.local_path),
            _parse_remote(args.remote_path, session),
            overwrite=args.overwrite,
            resc_name=args.resource,
            dry_run=args.dry_run,
        )
        if args.dry_run:
            _summarize_ops(ops)


def _parse_str(remote_or_local: str, session) -> Union[str, IrodsPath]:
    if remote_or_local.startswith("irods:"):
        return IrodsPath(session, remote_or_local[6:])
    return remote_or_local


def _summarize_ops(ops):
    if len(ops["create_collection"]) > 0:
        print("Create collections:\n")
        for coll in ops["create_collection"]:
            print(str(coll))
        print("\n")
    if len(ops["create_dir"]) > 0:
        print("Create directories:\n")
        for cur_dir in ops["create_dir"]:
            print(str(cur_dir))
        print("\n")
    if len(ops["upload"]) > 0:
        print("Upload files:\n")
        for lpath, ipath in ops["upload"]:
            print(f"{lpath} -> {ipath}")
        print("\n")
    if len(ops["download"]) > 0:
        print("Download files:\n")
        for ipath, lpath in ops["download"]:
            print(f"{ipath} -> {lpath}")


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
    args = parser.parse_args()

    with interactive_auth(irods_env_path=_get_ienv_path()) as session:
        ops = sync(
            session,
            _parse_str(args.source, session),
            _parse_str(args.destination, session),
            dry_run=args.dry_run,
        )
        if args.dry_run:
            _summarize_ops(ops)


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
    with interactive_auth(irods_env_path=_get_ienv_path()) as session:
        ipath = _parse_remote(args.remote_path, session)
        if args.ascii:
            pels = _tree_elements["ascii"]
        else:
            pels = _tree_elements["pretty"]
        ipath_list = list(ipath.walk(depth=args.depth))
        _tree(ipath, ipath_list, show_max=args.show_max, pels=pels)
        n_col = sum(cur_path.collection_exists() for cur_path in ipath_list)
        n_data = len(ipath_list) - n_col
        print_str = f"\n{n_col} collections, {n_data} data objects"
        if args.depth is not None:
            print_str += " (possibly more at higher depths)"
        print(print_str)
