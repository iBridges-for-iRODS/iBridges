"""Subcommands for tickets operations."""

from datetime import date

from ibridges.cli.base import BaseCliCommand
from ibridges.cli.util import parse_remote
from ibridges.tickets import Tickets


class CliTicket(BaseCliCommand):
    """Subcommand to manipulate the permissions of a data object or collection."""

    autocomplete = ["remote_path"]
    names = ["ticket"]
    description = "Create or use tickets to access data."
    examples = [
        "create collection write expiry_date",
        "create dataobject read expiry_date",
        "supply ticket_string irods_path",
    ]

    @classmethod
    def _mod_parser(cls, parser):
        subparsers = parser.add_subparsers(
            title="Available commands",
            dest="command",
            metavar="<command>",
            required=True,
            help="Run 'ibridges ticket <command> --help' for more details",
        )
        create_parser = subparsers.add_parser("create", help = "Create a ticket.")
        create_parser.add_argument(
            "--mode",
            help="Access mode. Available: read, write. Default: read",
            type=str,
            choices=["read", "write"],
            default="read",
        )
        create_parser.add_argument(
            "remote_path",
            help="Path to the data object or collection.",
            type=str,
        )
        create_parser.add_argument(
            "--date",
            type=date.fromisoformat,
            help="Date when ticket expires in YYYY-MM-DD format",
        )

        delete_parser = subparsers.add_parser("delete", help = "Delete a ticket.")
        delete_parser.add_argument("ticket", help="The ticket.", type=str)

        list_parser = subparsers.add_parser("list", help = "List all tickets.")

        supply_parser = subparsers.add_parser("supply",
                                          help = "Supply a ticket to access data by path.")
        supply_parser.add_argument(
            "ticket",
            help="The ticket string.",
            type=str
        )
        supply_parser.add_argument(
            "remote_path",
            help="Path to the data object or collection.",
            type=str,
        )

        return parser

    @staticmethod
    def run_shell(session, parser, args):
        """Manipulate permissions."""
        #ipath = parse_remote(args.remote_path, session)
        #if not ipath.exists():
        #    parser.error(f"Path {ipath} does not exist, can't list permissions.")
        #    return
        if args.command == "supply":
            print("supply")
        elif args.command == "delete":
            print(args.ticket)
        elif args.command == "create":
            print(args.mode, args.remote_path, args.date)
        else:
            tickets = Tickets(session)
            print(tickets)
