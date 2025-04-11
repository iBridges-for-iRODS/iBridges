import argparse
from pathlib import Path
from typing import Literal, Union

from ibridges.cli.base import ShellArgumentParser, BaseCliCommand
from ibridges.cli.util import parse_remote
from ibridges.data_operations import download, sync, upload
from ibridges.path import IrodsPath


class CliMakeCollection(BaseCliCommand):
    autocomplete = ["remote_coll"]
    names = ["mkcoll"]
    description = "Create a new collecion with all its parent collections."

    @classmethod
    def _mod_parser(cls, parser):
        parser.add_argument(
            "remote_coll",
            help="Path to a new collection, should start with 'irods:'.",
            type=str,
        )
        return parser

    @staticmethod
    def run_shell(session, parser, args):
        ipath = parse_remote(args.remote_coll, session)
        if ipath.exists():
            parser.error(f"Cannot create collection {ipath}: already exists.")
        ipath.create_collection(session, ipath)

class CliRm(BaseCliCommand):
    autocomplete = ["remote_path"]
    names = ["rm", "del"]
    description = "Remove collection or data object."

    @classmethod
    def _mod_parser(cls, parser):
        parser.add_argument(
            "remote_path",
            help="Collection or data object to remove.",
            type=str,
        )
        parser.add_argument(
            "-r", "--recursive",
            help="Remove collections and their content recursively.",
            action="store_true"
        )
        return parser

    @staticmethod
    def run_shell(session, parser, args):
        ipath = parse_remote(args.remote_path, session)
        if ipath.dataobject_exists():
            ipath.remove()
        elif ipath.collection_exists():
            if args.recursive:
                ipath.remove()
            else:
                parser.error("Cannot remove {ipath}: is a collection. Use -r to remove collections.")

def _get_metadata_path(args, ipath: IrodsPath, lpath: Union[str, Path],
                       mode: str) -> Union[None, str, Path]:
    metadata: Union[Literal[False], Path, None
                    ] = False if not hasattr(args, "metadata") else args.metadata
    if ipath.dataobject_exists() and metadata is None:
        raise ValueError("Supply metadata path for downloading metadata of data objects.")
    if mode == "download":
        default_meta_path = Path(lpath, ipath.name, ".ibridges_metadata.json")
    elif mode in ["upload", "sync"]:
        default_meta_path = Path(lpath, ".ibridges_metadata.json")
    else:
        raise ValueError("Internal error, contact the iBridges team.")
    if metadata is None:
        return default_meta_path
    if metadata is False:
        return None
    return metadata

class CliDownload(BaseCliCommand):
    autocomplete = ["remote_path", "local_dir"]
    names = ["download"]
    description="Download a data object or collection from an iRODS server."

    @classmethod
    def _mod_parser(cls, parser):
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
            default=Path.cwd(),
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
        return parser

    @staticmethod
    def run_shell(session, parser, args):
        print(args.local_path)
        ipath = parse_remote(args.remote_path, session)
        lpath = Path(args.local_path)
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


class CliUpload(BaseCliCommand):
    autocomplete = ["local_path", "remote_coll"]
    names = ["upload"]
    description = "Upload a data object or collection from an iRODS server."

    @classmethod
    def _mod_parser(cls, parser):
        parser.add_argument(
            "local_path",
            help="Local path to upload the data object/collection from.",
            type=Path,
        )
        parser.add_argument(
            "remote_path",
            help="Path to remote iRODS location starting with 'irods:'",
            type=str,
            default=".",
            nargs="?"
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
        return parser

    @staticmethod
    def run_shell(session, parser, args):
        lpath = args.local_path
        ipath = parse_remote(args.remote_path, session)
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
        return parse_remote(remote_or_local)
    return Path(remote_or_local)


class CliSync(BaseCliCommand):
    autocomplete = ["any_path", "any_path"]
    names = ["sync"]
    description = "Synchronize files/directories between local and remote."

    @classmethod
    def _mod_parser(cls, parser):
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
        return parser

    @staticmethod
    def run_shell(session, parser, args):
        src_path = _parse_str(args.source, session)
        dest_path = _parse_str(args.destination, session)
        if isinstance(src_path, Path) and isinstance(dest_path, IrodsPath):
            metadata = _get_metadata_path(args, dest_path, src_path, "sync")
        elif isinstance(src_path, IrodsPath) and isinstance(dest_path, Path):
            metadata = _get_metadata_path(args, src_path, dest_path, "sync")
        else:
            parser.error("Please provide as the source and destination exactly one local path,"
                         " and one remote path.")
            return
        ops = sync(
            session,
            src_path,
            dest_path,
            dry_run=args.dry_run,
            metadata=metadata,
        )
        if args.dry_run:
            ops.print_summary()
