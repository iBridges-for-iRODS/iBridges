""" ticket operations
"""
import logging
from random import choice
from string import ascii_letters
from subprocess import Popen, PIPE

import irods.ticket

from . import Icommands
from . import session


class Tickets(object):
    """Irods Ticket operations """

    def __init__(self, sess_man: session.Session):
        """ iRODS data operations initialization

            Parameters
            ----------
            sess_man : session.Session
                instance of the Session class

        """
        self.sess_man = sess_man

    def create_ticket(self, obj_path: str, expiry_string: str = '') -> tuple:
        """Create an iRODS ticket to allow read access to the object
        referenced by `obj_path`.

        Parameters
        ----------
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
        ticket = irods.ticket.Ticket(self.sess_man.irods_session, ticket_id)
        ticket.issue('read', obj_path)
        logging.info('CREATE TICKET: %s: %s', ticket.ticket, obj_path)
        expiration_set = False
        if expiry_string != '':
            try:
                expiration_set = self._modify_ticket(ticket, expiry_string)
            except Exception as error:
                logging.error('Could not set expiration date: %r', error)
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
        if not Icommands.IrodsConnectorIcommands.icommands():
            return ticket.modify('expire', expiry_string) == ticket
        else:
            command = f'iticket mod {ticket.ticket} expire {expiry_string}'
            p = Popen(
                command, stdout=PIPE, stderr=PIPE,
                shell=True)
            _, err = p.communicate()
            return err == b''
