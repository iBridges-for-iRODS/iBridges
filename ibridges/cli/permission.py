"""Subcommands for permissions operations."""

from ibridges.cli.base import BaseCliCommand
from ibridges.cli.util import parse_remote
from ibridges.permissions import Permissions


class CliACLEdit(BaseCliCommand):
    """Subcommand to manipulate the permissions of a data object or collection."""

    autocomplete = ["remote_path"]
    names = ["chmod"]
    description = "Manipulate the permissions of a data object or collection."
    examples = [
        "read username dataobject",
        "delete username dataobject",
        "read username collection --recursive",
        "inherit collection",
        "read username userzone dataobject",
    ]

    @classmethod
    def _mod_parser(cls, parser):
        parser.add_argument(
            "mode",
            help="Access mode. Available: read, write, own, delete, inherit, noinherit",
            type=str,
            choices=["read", "write", "own", "delete", "inherit", "noinherit"],
        )
        parser.add_argument(
            "user_info",
            help="User or group optionally followed by the zone name.",
            nargs="*",
            type=str,
            default=""
        )

        parser.add_argument(
            "remote_path",
            help="Path to the data object or collection.",
            type=str,
        )

        parser.add_argument(
            "-l", help="List permissions after applying changes.", action="store_true"
        )

        parser.add_argument(
            "--recursive",
            "-r",
            help=(
                "If path points to a collection, apply permission changes "
                "to all data objects and subcollections in that collection."
                ),
            action="store_true",
        )

        return parser

    @staticmethod
    def run_shell(session, parser, args):
        """Manipulate permissions."""
        ipath = parse_remote(args.remote_path, session)
        if not ipath.exists():
            parser.error(f"Path {ipath} does not exist, can't list permissions.")
            return

        user = None
        userzone = ""

        if len(args.user_info) == 1:
            user = args.user_info[0]
        elif len(args.user_info) == 2:
            user, userzone = args.user_info
        elif len(args.user_info) > 2:
            parser.error("Too many arguments before remote_path")

        #protect users from retracting access to own data
        if user == session.username and (userzone == "" or userzone == session.zone):
            parser.error("Cannot set your own permissions, since you would loose access. to data.")

        if ipath.dataobject_exists():
            perm = Permissions(ipath.session, ipath.dataobject)
        elif ipath.collection_exists():
            perm = Permissions(ipath.session, ipath.collection)
        else:
            parser.error(f"Path {ipath} is neither a data object nor collection.")
            return

        if  "inherit" not in args.mode and not user:
            parser.error("The following arguments are required: user [userzone]")
            return
        if "inherit" in args.mode and not ipath.collection_exists():
            parser.error("Cannot apply inherit/noinherit on data object.")
            return

        mode = "null" if args.mode == "delete" else args.mode
        perm.set(mode, user=user, zone=userzone, recursive=args.recursive)

        if args.l:
            print(perm)
