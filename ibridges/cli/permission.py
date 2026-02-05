"""Subcommands for permissions operations."""
from ibridges.cli.base import BaseCliCommand
from ibridges.cli.util import parse_remote
from ibridges.exception import DoesNotExistError
from ibridges.permissions import Permissions

class CliACLList(BaseCliCommand):
    """Subcommand to list all permissions of a data object or collection."""
    autocomplete = ["remote_path"]
    names = ["permission-list"]
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

