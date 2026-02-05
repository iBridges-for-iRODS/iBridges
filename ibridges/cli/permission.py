"""Subcommands for permissions operations."""

from ibridges.cli.base import BaseCliCommand
from ibridges.cli.util import parse_remote
from ibridges.permissions import Permissions


class CliACLList(BaseCliCommand):
    """Subcommand to list all permissions of a data object or collection."""

    autocomplete = ["remote_path"]
    names = ["perm"]
    description = "List the permissions of a data object or collection on iRODS."
    examples = ["", "irods:remote_collection"]

    @classmethod
    def _mod_parser(cls, parser):
        parser.add_argument(
            "remote_path",
            help="iRODS path for listing permissions, starting with 'irods:'.",
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
        if ipath.dataobject_exists():
            perm = Permissions(ipath.session, ipath.dataobject)
        elif ipath.collection_exists():
            perm = Permissions(ipath.session, ipath.collection)
        else:
            parser.error(f"Path {ipath} is neither a data ibject nor collection.")

        print(str(ipath) + ":\n")
        print(perm)


class CliACLEdit(BaseCliCommand):
    """Subcommand to manipulate the permissions of a data object or collection."""

    autocomplete = ["remote_path"]
    names = ["chmod"]
    description = "Manipulate the permissions of a data object or collection."
    examples = [
        "irods:dataobject username read",
        "irods:dataobject username delete",
        "irods:collection username read --recursive",
    ]

    @classmethod
    def _mod_parser(cls, parser):
        parser.add_argument(
            "remote_path",
            help="Path to the data object or collection.",
            type=str,
        )
        parser.add_argument(
            "user",
            help="User or group.",
            type=str,
        )
        parser.add_argument(
            "mode",
            help="Access mode. Available: read, write, own, delete.",
            type=str,
        )
        parser.add_argument(
            "userzone",
            nargs="?",
            default="",
            help="Zone of the user being granted access (optional).",
        )
        parser.add_argument(
            "-l", help="List permissions after applying changes.", action="store_true"
        )

        parser.add_argument(
            "--recursive",
            "-r",
            help="If path points to a collection, apply permission changes to all members.",
            action="store_true",
        )

        return parser

    @staticmethod
    def run_shell(session, parser, args):
        """Manipulate permissions."""
        ipath = parse_remote(args.remote_path, session)
        if not ipath.exists():
            parser.error(f"Path {ipath} does not exist, can't list metadata.")
            return
        if ipath.dataobject_exists():
            perm = Permissions(ipath.session, ipath.dataobject)
        elif ipath.collection_exists():
            perm = Permissions(ipath.session, ipath.collection)
        else:
            parser.error(f"Path {ipath} is neither a data ibject nor collection.")

        mode = "null" if args.mode == "delete" else args.mode
        perm.set(mode, user=args.user, zone=args.userzone, recursive=args.recursive)

        if args.l:
            print(perm)
