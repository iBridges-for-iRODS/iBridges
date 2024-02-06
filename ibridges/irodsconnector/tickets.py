""" ticket operations
"""
from typing import Optional

import irods.ticket
from irods.models import TicketQuery

import ibridges.irodsconnector.keywords as kw
from ibridges.irodsconnector.session import Session


class Tickets():
    """Irods Ticket operations """

    def __init__(self, session: Session):
        """ iRODS data operations initialization

            Parameters
            ----------
            session : session.Session
                instance of the Session class

        """
        self.session = session
        self._all_tickets = self.all_tickets(update = True)

    def create_ticket(self, obj_path: str,
                      ticket_type: Optional[str] = 'read',
                      expiry_string: Optional[str] = None) -> tuple:
        """Create an iRODS ticket to allow read access to the object
        referenced by `obj_path`.

        Parameters
        ----------
        obj_path : str
            Collection or data object path to create a ticket for.
        ticket_type: str
            read or write, default read
        expiry_string : str
            Optional expiration date in the form: strftime('%Y-%m-%d.%H:%M:%S')

        Returns
        -------
        tuple
            Name of ticket and if expiration string successfully set:
            (str, bool)

        """
        ticket = irods.ticket.Ticket(self.session.irods_session)
        ticket.issue(ticket_type, obj_path)
        expiration_set = False
        if expiry_string is not None:
            try:
                expiration_set = ticket.modify('expire', expiry_string) == ticket
            except Exception as error:
                self.delete_ticket(ticket)
                raise ValueError('Could not set expiration date') from error
        self.all_tickets(update=True)
        return ticket.ticket, expiration_set

    @property
    def all_ticket_strings(self) -> list[str]:
        """Get the names of all tickets."""
        return [name for name, _, _, _ in self.all_tickets()]

    def get_ticket(self, ticket_str: str) -> Optional[irods.ticket.Ticket]:
        """Obtain a ticket using its string identifier."""
        if ticket_str in self.all_ticket_strings:
            return irods.ticket.Ticket(self.session.irods_session, ticket=ticket_str)
        raise KeyError(f"Cannot obtain ticket: ticket with ticket_str '{ticket_str}' "
                       "does not exist.")

    def delete_ticket(self, ticket: irods.ticket.Ticket, check: bool = False):
        """Delete irods ticket."""
        if ticket.string in self.all_ticket_strings:
            ticket.delete()
            self.all_tickets(update=True)
        if check:
            raise KeyError(f"Cannot delete ticket: ticket '{ticket}' does not exist (anymore).")

    def all_tickets(self, update: bool = False) -> list[tuple[str, str, str, str]]:
        """retrieves all tickets and their metadata belonging to the user.

        Parameters
        ----------
        update : bool
            Refresh information from server.

        Returns
        -------
        list
            [(ticket string, ticket type, irods obj/coll path, expiry data in epoche)]
        """
        user = self.session.username
        if update or self._all_tickets is None:
            self._all_tickets = []
            for row in self.session.irods_session.query(TicketQuery.Ticket).filter(
                    TicketQuery.Owner.name == user):
                self._all_tickets.append((row[TicketQuery.Ticket.string],
                                          row[TicketQuery.Ticket.type],
                                          self._id_to_path(str(row[TicketQuery.Ticket.object_id])),
                                          row[TicketQuery.Ticket.expiry_ts]
                                          ))
        return self._all_tickets

    def clear(self):
        """Delete all tickets.
        """
        self.all_tickets(update=True)
        for tick_data in self._all_tickets:
            tick_str = tick_data[0]
            tick = self.get_ticket(tick_str)
            self.delete_ticket(tick)

    def _id_to_path(self, itemid: str) -> str:
        """
        Given an iRODS item id (data object or collection) from the
        TicketQuery.Ticket.object_id this function retrieves the corresponding
        iRODS path.

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
        data_query = self.session.irods_session.query(kw.COLL_NAME, kw.DATA_NAME)
        data_query = data_query.filter(kw.DATA_ID == itemid)

        if len(list(data_query)) > 0:
            res = next(data_query.get_results())
            return list(res.values())[0] + "/" + list(res.values())[1]
        coll_query = self.session.irods_session.query(kw.COLL_NAME)
        coll_query = coll_query.filter(kw.COLL_ID == itemid)
        if len(list(coll_query)) > 0:
            res = next(coll_query.get_results())
            return list(res.values())[0]
        return ''
