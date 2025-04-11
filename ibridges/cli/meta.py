from ibridges.cli.base import BaseCliCommand, ShellArgumentParser
from ibridges.cli.util import parse_remote
from ibridges.exception import DoesNotExistError
from ibridges.path import IrodsPath


class CliMetaList(BaseCliCommand):
    autocomplete = ["remote_path"]
    names = ["meta-list"]
    description = "List a collection on iRODS."

    @classmethod
    def _mod_parser(cls, parser):
        parser.add_argument(
            "remote_path",
            help="Path to remote iRODS location starting with 'irods:'",
            type=str,
            default=".",
            nargs="?",
        )
        return parser

    @staticmethod
    def run_shell(session, parser, args):
        ipath = IrodsPath(session, args.remote_path)
        if not ipath.exists():
            parser.error(f"Path {ipath} does not exist, can't list metadata.")
            return
        print(str(ipath) + ":\n")
        print(ipath.meta)


class CliMetaAdd(BaseCliCommand):
    autocomplete = ["remote_path"]
    names = ["meta-add"]
    description = "Add a metadata item to a collection or data object."

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
        ipath = IrodsPath(session, args.remote_path)
        try:
            ipath.meta.add(args.key, args.value, args.units)
        except DoesNotExistError:
            parser.error(f"Cannot add metadata: {ipath} does not exist.")


class CliMetaDel(BaseCliCommand):
    autocomplete = ["remote_path"]
    names = ["meta-del"]
    description = "Delete metadata for one collection or data object."

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
        meta.delete(args.key, args.value, args.units)
