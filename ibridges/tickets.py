"""Ticket operations."""

from __future__ import annotations

from collections import namedtuple
from datetime import date, datetime
from typing import Iterable, Optional, Union

import irods.ticket
from irods.models import TicketQuery

import ibridges.icat_columns as icat
from ibridges.path import IrodsPath
from ibridges.session import Session

TicketData = namedtuple("TicketData", ["name", "type", "path", "expiration_date"])


class Tickets:
    """iRODS Ticket operations.

    Tickets allow users to give temporary access to other users.
    These tickets are stored on the iRODS server, and can be deleted whenever
    the access is not needed anymore.

    Parameters
    ----------
    session:
        Session connecting to the iRODS server.

    """  # noqa: D403

    def __init__(self, session: Session):
        """Initialize for ticket operations."""
        self.session = session
        self._all_tickets = self.fetch_tickets()

    def create_ticket(
        self,
        irods_path: Union[str, IrodsPath],
        ticket_type: str = "read",
        expiry_date: Optional[Union[str, datetime, date]] = None,
    ) -> tuple:
        """Create an iRODS ticket.

        This allows read or write access to the object referenced by `obj_path`.

        Parameters
        ----------
        irods_path:
            Collection or data object path to create a ticket for.
        ticket_type, optional:
            read or write, default read
        expiry_date, optional:
            Expiration date as a datetime, date or string in the form strftime('%Y-%m-%d.%H:%M:%S').

        Raises
        ------
        TypeError:
            If the expiry_date has the wrong type.
        ValueError:
            If the expiration date cannot be set for whatever reason.

        Returns
        -------
        tuple
            Name of ticket and if expiration string successfully set:
            (str, bool)

        """
        ticket = irods.ticket.Ticket(self.session.irods_session)
        ticket.issue(ticket_type, str(irods_path))
        expiration_set = False
        if expiry_date is not None:
            if isinstance(expiry_date, date):
                expiry_date = datetime.combine(expiry_date, datetime.min.time())
            if isinstance(expiry_date, datetime):
                expiry_date = expiry_date.strftime("%Y-%m-%d.%H:%M:%S")
            if not isinstance(expiry_date, str):
                raise TypeError(
                    "Expecting datetime, date or string type for 'expiry_date' "
                    f"argument, got {type(expiry_date)}"
                )
            try:
                expiration_set = ticket.modify("expire", expiry_date) == ticket
            except Exception as error:
                self.delete_ticket(ticket)
                raise ValueError("Could not set expiration date") from error
        self.fetch_tickets()
        return ticket.ticket, expiration_set

    def __iter__(self) -> Iterable[TicketData]:
        """Iterate over all ticket data."""
        yield from self.fetch_tickets()

    @property
    def all_ticket_strings(self) -> list[str]:
        """Get the names of all tickets."""
        return [tick_data.name for tick_data in self._all_tickets]

    def get_ticket(self, ticket_str: str) -> irods.ticket.Ticket:
        """Obtain a ticket using its string identifier.

        Parameters
        ----------
        ticket_str:
            Unique string identifier with which the ticket can be retrieved.

        Raises
        ------
        KeyError:
            If the ticket cannot be found.

        Returns
        -------
            Ticket with the correct identifier.

        """
        if ticket_str in self.all_ticket_strings:
            return irods.ticket.Ticket(self.session.irods_session, ticket=ticket_str)
        raise KeyError(
            f"Cannot obtain ticket: ticket with ticket_str '{ticket_str}' " "does not exist."
        )

    def delete_ticket(self, ticket: Union[str, irods.ticket.Ticket], check: bool = False):
        """Delete iRODS ticket.

        This revokes the access that was granted with the ticket.

        Parameters
        ----------
        ticket:
            Ticket or ticket string identifier to be deleted.
        check:
            Whether to check whether the ticket actually exists.

        Raises
        ------
        KeyError:
            If check == True and the ticket does not exist.

        """
        if isinstance(ticket, str):
            ticket = self.get_ticket(ticket)
        if ticket.string in self.all_ticket_strings:
            ticket.delete()
            self.fetch_tickets()
        elif check:
            raise KeyError(f"Cannot delete ticket: ticket '{ticket}' does not exist (anymore).")

    def fetch_tickets(self) -> list[TicketData]:
        """Retrieve all tickets and their metadata belonging to the user.

        Parameters
        ----------
        update : bool
            Refresh information from server.

        Returns
        -------
            A list of all available tickets:
            [(ticket string, ticket type, irods obj/coll path, expiry data in epoche)]

        """
        user = self.session.username
        self._all_tickets = []
        for row in self.session.irods_session.query(TicketQuery.Ticket).filter(
            TicketQuery.Owner.name == user
        ):
            time = row[TicketQuery.Ticket.expiry_ts]
            time_stamp = datetime.fromtimestamp(int(time)) if time else ""
            self._all_tickets.append(
                TicketData(
                    row[TicketQuery.Ticket.string],
                    row[TicketQuery.Ticket.type],
                    IrodsPath(self.session,
                              self._id_to_path(str(row[TicketQuery.Ticket.object_id]))),
                    time_stamp,
                )
            )
        return self._all_tickets

    def clear(self):
        """Delete all tickets.

        This revokes all access to data objects and collections that was
        granted through these tickets.
        """
        for tick_data in self.fetch_tickets():
            self.delete_ticket(tick_data.name)
        self.fetch_tickets()

    def _id_to_path(self, itemid: str) -> str:
        """Get an iRODS path from a given an iRODS item id.

        The item (data object or collection) id should come from the
        TicketQuery.Ticket.object_id.

        Parameters
        ----------
        itemid : str
            iRODS identifier for a collection or data object
            (str(row[TicketQuery.Ticket.object_id]))

        Returns
        -------
        str
            collection or data object path
            returns '' if the identifier does not exist any longer

        """
        data_query = self.session.irods_session.query(icat.COLL_NAME, icat.DATA_NAME)
        data_query = data_query.filter(icat.DATA_ID == itemid)

        if len(list(data_query)) > 0:
            res = next(data_query.get_results())
            return list(res.values())[0] + "/" + list(res.values())[1]
        coll_query = self.session.irods_session.query(icat.COLL_NAME)
        coll_query = coll_query.filter(icat.COLL_ID == itemid)
        if len(list(coll_query)) > 0:
            res = next(coll_query.get_results())
            return list(res.values())[0]
        return ""
