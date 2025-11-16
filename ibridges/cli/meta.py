"""Subcommands for metadata operations."""
from ibridges.cli.base import BaseCliCommand
from ibridges.cli.util import parse_remote
from ibridges.exception import DoesNotExistError


class CliMetaList(BaseCliCommand):
    """Subcommand for listing the metadata of a data object or collection."""

    autocomplete = ["remote_path"]
    names = ["meta-list"]
    description = "List the metadata of a data object or collection on iRODS."
    examples = ["", "irods:remote_collection"]


    @classmethod
    def _mod_parser(cls, parser):
        parser.add_argument(
            "remote_path",
            help="iRODS path for metadata listing, starting with 'irods:'.",
            type=str,
            default=".",
            nargs="?",
        )
        return parser

    @staticmethod
    def run_shell(session, parser, args):
        """List the metadata of a data object or collection."""
        ipath = parse_remote(args.remote_path, session)
        if not ipath.exists():
            parser.error(f"Path {ipath} does not exist, can't list metadata.")
            return
        print(str(ipath) + ":\n")
        print(ipath.meta)


class CliMetaAdd(BaseCliCommand):
    """Subcommand to add metadata to a data object or collection."""

    autocomplete = ["remote_path"]
    names = ["meta-add"]
    description = "Add a metadata item to a collection or data object."
    examples = ["irods:some_dataobj_or_collection new_key new_value new_units"]

    @classmethod
    def _mod_parser(cls, parser):
        parser.add_argument(
            "remote_path",
            help="Path to add a new metadata item to.",
            type=str,
        )
        parser.add_argument(
            "key",
            help="Key for the new metadata item.",
            type=str,
        )
        parser.add_argument(
            "value",
            help="Value for the new metadata item.",
            type=str
        )
        parser.add_argument(
            "units",
            help="Units for the new metadata item.",
            type=str,
            default="",
            nargs="?"
        )
        return parser

    @staticmethod
    def run_shell(session, parser, args):
        """Add metadata to a data object or collection."""
        ipath = parse_remote(args.remote_path, session)
        try:
            ipath.meta.add(args.key, args.value, args.units)
        except DoesNotExistError:
            parser.error(f"Cannot add metadata: {ipath} does not exist.")
        except (ValueError, PermissionError) as exc:
            parser.error(str(exc))


class CliMetaDel(BaseCliCommand):
    """Subcommand to delete metadata for a data object or collection."""

    autocomplete = ["remote_path"]
    names = ["meta-del"]
    description = "Delete metadata for one collection or data object."
    examples = ["irods:remote_dataobj_or_coll", "irods:remote_dataobj_or_coll --key some_key",
                "irods:some_obj --key some_key --value some_val --units some_units"]

    @classmethod
    def _mod_parser(cls, parser):
        parser.add_argument(
            "remote_path",
            help="Path to delete metadata entries from.",
        )
        parser.add_argument(
            "--key",
            help="Key for which to delete the entries.",
            type=str,
            default=...,
        )
        parser.add_argument(
            "--value",
            help="Value for which to delete the entries.",
            type=str,
            default=...,
        )
        parser.add_argument(
            "--units",
            help="Units for which to delete the entries.",
            type=str,
            default=...,
        )
        parser.add_argument(
            "--ignore-blacklist",
            help="Ignore the metadata blacklist.",
            action="store_true"
        )
        return parser

    @staticmethod
    def run_shell(session, parser, args):
        """Delete metadata for a data object or collection."""
        ipath = parse_remote(args.remote_path, session)
        try:
            meta = ipath.meta
        except DoesNotExistError:
            parser.error(f"Cannot delete metadata: {ipath} does not exist.")
            return
        if args.ignore_blacklist:
            meta.blacklist = None
        if args.key is ... and args.value is ... and args.units is ...:
            answer = input(f"This command will delete all metadata for path {ipath},"
                            " are you sure? [y/n]")
            if answer.lower() != "y":
                return
        try:
            meta.delete(args.key, args.value, args.units)
        except (KeyError, PermissionError) as exc:
            parser.error(str(exc))
