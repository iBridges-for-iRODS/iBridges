from ibridges.cli.base import ShellArgumentParser
from ibridges.path import IrodsPath

class CliMetaList():
    autocomplete = ["remote_path"]
    names = ["meta-list"]

    @staticmethod
    def get_parser():
        parser = ShellArgumentParser(
            prog="ibridges meta-list", description="List a collection on iRODS."
        )
        parser.add_argument(
            "remote_path",
            help="Path to remote iRODS location starting with 'irods:'",
            type=str,
            default=".",
            nargs="?",
        )
        return parser

    @staticmethod
    def run_command(session, parser, args):
        ipath = IrodsPath(session, args.remote_path)
        print(str(ipath) + ":\n")
        print(ipath.meta)


class CliMetaAdd():
    autocomplete = ["remote_path"]
    names = ["meta-add"]

    @staticmethod
    def get_parser():
        parser = ShellArgumentParser(
            prog="ibridges meta-add", description="Add metadata entry."
        )
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
    def run_command(session, parser, args):
        ipath = IrodsPath(session, args.remote_path)
        ipath.meta.add(args.key, args.value, args.units)
