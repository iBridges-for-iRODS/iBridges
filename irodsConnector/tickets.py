""" ticket operations
"""
from random import choice
from string import ascii_letters
from subprocess import Popen, PIPE
import logging
import irods.ticket
import irods.session
from irodsConnector.utils import IrodsUtils


class Tickets(object):
    """Irods Ticket operations """
    def create_ticket(self, session: irods.session, obj_path: str, expiry_string: str = '') -> tuple:
        """Create an iRODS ticket to allow read access to the object
        referenced by `obj_path`.

        Parameters
        ----------
        session : irods session
        obj_path : str
            Name to create ticket for.
        expiry_string : str
            Optional expiration date in the form: CCYY-MM-DD.hh:mm:ss

        Returns
        -------
        tuple
            Name of ticket and if expiration string successfully set:
            (str, bool)

        """
        ticket_id = ''.join(choice(ascii_letters) for _ in range(20))
        ticket = irods.ticket.Ticket(session, ticket_id)
        ticket.issue('read', obj_path)
        logging.info('CREATE TICKET: %s: %s', ticket.ticket, obj_path)
        expiration_set = False
        if expiry_string != '':
            try:
                expiration_set = self._modify_ticket(ticket, expiry_string)
            except Exception as error:
                logging.info('Could not set expiration date: %s', str(error))
        return ticket.ticket, expiration_set

    def _modify_ticket(self, ticket: irods.ticket.Ticket, expiry_string: str) -> bool:
        """Modify iRODS `ticket` updating the expriration date.

        Parameters
        ----------
        ticket : irods.ticket.Ticket
            iRODS ticket to be modified.
        expiry_string : str
           Expiration date in the form: CCYY-MM-DD.hh:mm:ss.

        Returns
        -------
        bool
            If `ticket` successfully modified.

        """
        # TODO improve error handling, if necessary
        if not IrodsUtils.icommands():
            return ticket.modify('expire', expiry_string) == ticket
        else:
            command = f'iticket mod {ticket.ticket} expire {expiry_string}'
            p = Popen(
                command, stdout=PIPE, stderr=PIPE,
                shell=True)
            _, err = p.communicate()
            return err == b''
