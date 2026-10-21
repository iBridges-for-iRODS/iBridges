"""Subcommands for tickets operations."""

import argparse
from datetime import date

from ibridges.cli.base import BaseCliCommand
from ibridges.cli.util import parse_remote
from ibridges.tickets import TicketAccess, Tickets


class CliTicketCreate(BaseCliCommand):
    """Subcommand to create a ticket."""

    autocomplete = ["remote_path"]
    names = ["ticket-create"]
    description = "Create a ticket to access a data object or collection."
    examples = [
        "irods:/zone/home/user/collection --mode write --date 2026-12-31",
        "irods:/zone/home/user/dataobject --mode read",
    ]

    @classmethod
    def _mod_parser(cls, parser):
        parser.add_argument(
            "remote_path",
            help="Path to the data object or collection.",
            type=str,
        )
        parser.add_argument(
            "--mode",
            help="Access mode. Available: read, write. Default: read",
            type=str,
            choices=["read", "write"],
            default="read",
        )
        parser.add_argument(
            "--date",
            type=date.fromisoformat,
            help="Date when ticket expires in YYYY-MM-DD format",
        )
        return parser

    @staticmethod
    def run_shell(session, parser, args):
        """Create a ticket."""
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


class CliTicketDelete(BaseCliCommand):
    """Subcommand to delete a ticket."""

    autocomplete = []
    names = ["ticket-delete"]
    description = "Delete a ticket."
    examples = ["ticket_string"]

    @classmethod
    def _mod_parser(cls, parser):
        parser.add_argument("ticket", help="The ticket.", type=str)
        return parser

    @staticmethod
    def run_shell(session, parser, args):
        """Delete a ticket."""
        tickets = Tickets(session)
        try:
            tickets.delete_ticket(args.ticket, check=True)
        except KeyError as error:
            parser.error(str(error.args[0]))
            return
        print(f"Deleted ticket {args.ticket}.")


class CliTicketList(BaseCliCommand):
    """Subcommand to list all tickets."""

    autocomplete = []
    names = ["ticket-list"]
    description = "List all tickets."
    examples = [""]

    @classmethod
    def _mod_parser(cls, parser):
        return parser

    @staticmethod
    def run_shell(session, parser, args):
        """List all tickets."""
        print(Tickets(session))


class CliTicketSupply(BaseCliCommand):
    """Subcommand to supply a ticket to the session, to access data by path."""

    autocomplete = ["remote_path"]
    names = ["ticket-supply"]
    description = "Supply a ticket to access data by path."
    examples = ["ticket_string irods:/zone/home/user/collection"]

    @classmethod
    def _mod_parser(cls, parser):
        parser.add_argument("ticket", help="The ticket string.", type=str)
        parser.add_argument(
            "remote_path",
            help="Path to the data object or collection.",
            type=str,
        )
        return parser

    @classmethod
    def run_command(cls, args):
        """Run from the CLI; 'ticket-supply' is only available in the shell."""
        cls.get_parser(argparse.ArgumentParser).error(
            "'ticket-supply' can only be used in the shell, because a supplied ticket only "
            "exists in the session that supplied it. "
            "Use: ibridges shell --with-ticket <ticket> <remote_path>"
        )

    @staticmethod
    def run_shell(session, parser, args):
        """Supply a ticket and move to the ticketed path."""
        ipath = parse_remote(args.remote_path, session)
        access = TicketAccess(session, args.ticket, irods_path=str(ipath), supply=True)
        path = access.path
        if not path.exists():
            parser.error(f"Path {path} does not exist or the ticket does not give access to it.")
            return

        print(f"Ticket {args.ticket} supplied for {path}.")
        if path.collection_exists():
            session.cwd = str(path)
        else:
            session.cwd = str(path.parent)
