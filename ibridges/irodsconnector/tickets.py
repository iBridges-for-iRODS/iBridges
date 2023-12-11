""" ticket operations
"""
import irods.ticket
from irods.models import TicketQuery

from .session import Session
import ibridges.irodsconnector.keywords as kw
import warnings
from typing import Optional


class Tickets(object):
    """Irods Ticket operations """

    def __init__(self, session: Session):
        """ iRODS data operations initialization

            Parameters
            ----------
            session : session.Session
                instance of the Session class

        """
        self.session = session
        self._all_tickets = None

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
                raise Exception('Could not set expiration date: %r', error)
        return ticket.ticket, expiration_set

    @property
    def all_ticket_strings(self) -> list:
        return [name for name, _, _, _ in self.all_tickets()]

    def get_ticket(self, ticket_str: str) -> irods.ticket.Ticket:
        if ticket_str in self.all_ticket_strings:
            return irods.ticket.Ticket(self.session.irods_session, ticket=ticket_str)
        else:
            warnings.warn("Ticket does not exist.")
        return None

    def delete_ticket(self, ticket: irods.ticket.Ticket):
        if ticket and ticket.string in self.all_ticket_strings:
            ticket.delete()
            self.all_tickets(update=True)
        else:
            warnings.warn("Ticket does not exist.")

    def all_tickets(self, update: bool = False) -> list:
        """retrieves all tickets and their metadata belonging to the user.

        Parameters
        ----------
        update : bool
            Refresh information from server.

        Returns
        -------
        list
            [(ticket string, ticket type, irods obj/coll id, expiry data in epoche)]
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

    def _id_to_path(self, itemid: str) -> str:
        data_query = self.session.irods_session.query(kw.COLL_NAME, kw.DATA_NAME)
        data_query = data_query.filter(kw.DATA_ID == itemid)

        if len(list(data_query)) > 0:
            res = next(data_query.get_results())
            return list(res.values())[0] + "/" + list(res.values())[1]
        else:
            coll_query = self.session.irods_session.query(kw.COLL_NAME)
            coll_query = coll_query.filter(kw.COLL_ID == itemid)
            if len(list(coll_query)) > 0:
                res = next(coll_query.get_results())
                return list(res.values())[0]
            else:
                return ''
