"""Subcommands for tickets operations."""

import shlex
import sys
import traceback
from datetime import date

from ibridges.cli.base import BaseCliCommand
from ibridges.cli.util import parse_remote
from ibridges.tickets import TicketAccess, Tickets


class CliTicket(BaseCliCommand):
    """Subcommand to create, list, delete and use tickets."""

    autocomplete = ["remote_path"]
    names = ["ticket"]
    description = "Create or use tickets to access data."
    examples = [
        "create irods:/zone/home/user/collection --mode write --date 2026-12-31",
        "create irods:/zone/home/user/dataobject --mode read",
        "list",
        "delete ticket_string",
        "supply ticket_string irods:/zone/home/user/collection",
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
        create_parser = subparsers.add_parser("create", help="Create a ticket.")
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

        delete_parser = subparsers.add_parser("delete", help="Delete a ticket.")
        delete_parser.add_argument("ticket", help="The ticket.", type=str)

        subparsers.add_parser("list", help="List all tickets.")

        supply_parser = subparsers.add_parser(
            "supply", help="Supply a ticket to access data by path."
        )
        supply_parser.add_argument("ticket", help="The ticket string.", type=str)
        supply_parser.add_argument(
            "remote_path",
            help="Path to the data object or collection.",
            type=str,
        )

        return parser

    @classmethod
    def allowed_at_startup(cls, argv):
        """Only 'supply' makes sense as a shell startup command."""
        return len(argv) > 0 and argv[0] == "supply"

    @classmethod
    def run_command(cls, args):
        """Run a ticket command; 'supply' opens a shell and supplies the ticket there."""
        if args.command != "supply":
            super().run_command(args)
            return
        # pylint: disable-next=import-outside-toplevel,cyclic-import
        from ibridges.cli.shell import IBridgesShell

        supply_line = f"ticket supply {shlex.quote(args.ticket)} {shlex.quote(args.remote_path)}"
        try:
            IBridgesShell(startup_commands=[supply_line]).cmdloop()
        except KeyboardInterrupt:
            pass
        except Exception:  # pylint: disable=broad-exception-caught
            traceback.print_exception(*sys.exc_info())

    @staticmethod
    def run_shell(session, parser, args):  # pylint: disable=too-many-branches
        """Create, list, delete and supply tickets."""
        if args.command == "create":
            ipath = parse_remote(args.remote_path, session)
            if not ipath.exists():
                parser.error(f"Path {ipath} does not exist, can't create a ticket.")
                return
            tickets = Tickets(session)
            try:
                ticket_str, expiration_set = tickets.create_ticket(
                    ipath, ticket_type=args.mode, expiry_date=args.date
                )
            except (TypeError, ValueError) as error:
                parser.error(str(error))
                return
            print(f"Created {args.mode} ticket for {ipath}: {ticket_str}")
            if args.date is not None:
                if expiration_set:
                    print(f"Expires on {args.date.isoformat()}.")
                else:
                    print("Warning: the expiration date could not be confirmed.")

        elif args.command == "delete":
            tickets = Tickets(session)
            try:
                tickets.delete_ticket(args.ticket, check=True)
            except KeyError as error:
                parser.error(str(error.args[0]))
                return
            print(f"Deleted ticket {args.ticket}.")

        elif args.command == "supply":
            ipath = parse_remote(args.remote_path, session)
            access = TicketAccess(session, args.ticket, irods_path=str(ipath), supply=True)
            path = access.path
            if not path.exists():
                parser.error(
                    f"Path {path} does not exist or the ticket does not give access to it."
                )
                return

            print(f"Ticket {args.ticket} supplied for {path}.")
            if path.collection_exists():
                session.cwd = str(path)
            else:
                session.cwd = str(path.parent)
        else:  # list
            print(Tickets(session))
