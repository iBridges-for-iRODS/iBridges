"""Subcommands that do data operations."""

import argparse
from pathlib import Path
from typing import Literal, Union

from ibridges.cli.base import BaseCliCommand
from ibridges.cli.util import parse_remote
from ibridges.data_operations import download, sync, upload
from ibridges.exception import (
    CollectionDoesNotExistError,
    DataObjectExistsError,
    DoesNotExistError,
    NotACollectionError,
)
from ibridges.path import IrodsPath

ON_ERROR_HELP = (
    "When a transfer of a file fails, by default the whole transfer will stop and print the error "
    "message(fail). By setting 'on-error' to 'warn', those errors will be turned into warnings and "
    "the transfer continues with the next file. "
    "Setting 'on-error' to 'skip' will omit any message and simply proceed."
)



class CliMakeCollection(BaseCliCommand):
    """Subcommand for creating a new collection."""

    autocomplete = ["remote_coll"]
    names = ["mkcoll"]
    description = "Create a new collecion with all its parent collections."
    examples = ["irods:~/test"]

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
        """Create the new collection with the arguments."""
        ipath = parse_remote(args.remote_coll, session)
        if ipath.exists():
            parser.error(f"Cannot create collection {ipath}: already exists.")
        ipath.create_collection()


class CliRm(BaseCliCommand):
    """Subcommand for removing a data object or collection."""

    autocomplete = ["remote_path"]
    names = ["rm", "remove", "del"]
    description = "Remove collection or data object."
    examples = ["irods:~/test.txt", "-r irods:~/test_collection"]

    @classmethod
    def _mod_parser(cls, parser):
        parser.add_argument(
            "remote_path",
            help="Collection or data object to remove.",
            type=str,
        )
        parser.add_argument(
            "-r",
            "--recursive",
            help="Remove collections and their content recursively.",
            action="store_true",
        )
        return parser

    @staticmethod
    def run_shell(session, parser, args):
        """Remove a data object or collection."""
        ipath = parse_remote(args.remote_path, session)
        if ipath.dataobject_exists():
            ipath.remove()
        elif ipath.collection_exists():
            if args.recursive:
                ipath.remove()
            else:
                parser.error(
                    f"Cannot remove {ipath}: is a collection. Use -r to remove collections."
                )


def _get_metadata_path(
    args, ipath: IrodsPath, lpath: Union[str, Path], mode: str
) -> Union[None, str, Path]:
    metadata: Union[Literal[False], Path, None]
    metadata = False if not hasattr(args, "metadata") else args.metadata
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
    """Subcommand for downloading a data object or collection."""

    autocomplete = ["remote_path", "local_dir"]
    names = ["download"]
    description = "Download a data object or collection from an iRODS server."
    examples = ["irods:~/test.txt", "irods:~/some_collection"]

    @classmethod
    def _mod_parser(cls, parser):
        parser.add_argument(
            "remote_path",
            help="Path to remote iRODS location starting with 'irods:'.",
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
            help="Path to the metadata file which will be created.",
            default=argparse.SUPPRESS,
            type=Path,
            nargs="?",
        )
        parser.add_argument(
            "--on-error",
            help=ON_ERROR_HELP,
            type=str,
        )
        return parser

    @staticmethod
    def run_shell(session, parser, args):
        """Download the data object or collection."""
        if args.on_error and args.on_error.lower() not in ["fail", "warn", "skip"]:
            parser.error(
                f"'on-error': Unknown keyword {args.on_error}, choose 'fail', 'warn' or 'skip'")
        ipath = parse_remote(args.remote_path, session)
        lpath = Path(args.local_path)
        metadata = _get_metadata_path(args, ipath, lpath, "download")
        try:
            ops = download(
                ipath,
                lpath,
                overwrite=args.overwrite,
                resc_name=args.resource,
                dry_run=args.dry_run,
                on_error=args.on_error,
                metadata=metadata,
            )
        except (DoesNotExistError, PermissionError, NotADirectoryError, FileExistsError) as exc:
            parser.error(str(exc))
            return
        if args.dry_run:
            ops.print_summary()


class CliUpload(BaseCliCommand):
    """Subcommand to upload data to an iRODS server."""

    autocomplete = ["local_path", "remote_coll"]
    names = ["upload"]
    description = "Upload a data object or collection to an iRODS server."
    examples = [
        "local_file.txt",
        "local_file.txt irods:remote_collection",
        "local_dir irods:remote_collection",
    ]

    @classmethod
    def _mod_parser(cls, parser):
        parser.add_argument(
            "local_path",
            help="Local path to upload the data object/collection from.",
            type=Path,
        )
        parser.add_argument(
            "remote_path",
            help="Path to remote iRODS location starting with 'irods:'.",
            type=str,
            default=".",
            nargs="?",
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
            help="Path to the metadata json.",
            default=argparse.SUPPRESS,
            type=Path,
            nargs="?",
        )
        parser.add_argument(
            "--on-error",
            help=ON_ERROR_HELP,
            default="fail",
            type=str,
        )
        return parser

    @staticmethod
    def run_shell(session, parser, args):
        """Upload a data object or collection to the iRODS server."""
        if args.on_error and args.on_error.lower() not in ["fail", "warn", "skip"]:
            parser.error(
                f"'on-error': Unknown keyword {args.on_error}, choose 'fail', 'warn' or 'skip'")
        lpath = args.local_path
        ipath = parse_remote(args.remote_path, session)
        metadata = _get_metadata_path(args, ipath, lpath, "upload")
        try:
            ops = upload(
                lpath,
                ipath,
                overwrite=args.overwrite,
                resc_name=args.resource,
                dry_run=args.dry_run,
                metadata=metadata,
                on_error=args.on_error,
            )
        except (FileNotFoundError, PermissionError, DataObjectExistsError) as exc:
            parser.error(exc)
            return

        if args.dry_run:
            ops.print_summary()


def _parse_str(remote_or_local: str, session) -> Union[Path, IrodsPath]:
    if remote_or_local.startswith("irods:"):
        return parse_remote(remote_or_local, session)
    return Path(remote_or_local)


class CliSync(BaseCliCommand):
    """Subcommand to synchronize collections and directories."""

    autocomplete = ["any_dir", "any_dir"]
    names = ["sync"]
    description = "Synchronize files/directories between local and remote."
    examples = ["local_dir irods:remote_collection", "irods:remote_collection local_dir"]

    @classmethod
    def _mod_parser(cls, parser):
        parser.add_argument(
            "source",
            help="Source path to synchronize from (collection on irods server or local directory).",
            type=str,
        )
        parser.add_argument(
            "destination",
            help="Destination path to synchronize to "
            "(collection on irods server or local directory).",
            type=str,
        )
        parser.add_argument(
            "--dry-run",
            help="Do not perform the synchronization, but list the files to be updated.",
            action="store_true",
        )
        parser.add_argument(
            "--metadata",
            help="Path to the metadata json file.",
            default=argparse.SUPPRESS,
            type=Path,
            nargs="?",
        )
        parser.add_argument(
            "--on-error",
            help=ON_ERROR_HELP,
            default="fail",
            type=str,
        )
        return parser

    @staticmethod
    def run_shell(session, parser, args):
        """Synchronize a directory and collection."""
        if args.on_error and args.on_error.lower() not in ["fail", "warn", "skip"]:
            parser.error(
                f"'on-error': Unknown keyword {args.on_error}, choose 'fail', 'warn' or 'skip'")
        src_path = _parse_str(args.source, session)
        dest_path = _parse_str(args.destination, session)
        if isinstance(src_path, Path) and isinstance(dest_path, IrodsPath):
            metadata = _get_metadata_path(args, dest_path, src_path, "sync")
        elif isinstance(src_path, IrodsPath) and isinstance(dest_path, Path):
            metadata = _get_metadata_path(args, src_path, dest_path, "sync")
        else:
            parser.error(
                "Please provide as the source and destination exactly one local path,"
                " and one remote path."
            )
            return
        try:
            ops = sync(
                src_path,
                dest_path,
                dry_run=args.dry_run,
                metadata=metadata,
                on_error=args.on_error,
            )
        except (CollectionDoesNotExistError, NotACollectionError, NotADirectoryError) as exc:
            parser.error(exc)
            return
        if args.dry_run:
            ops.print_summary()
