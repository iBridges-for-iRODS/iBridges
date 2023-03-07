

class Tickets(object):
    
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
        ticket_id = ''.join(random.choice(string.ascii_letters) for _ in range(20))
        ticket = irods.ticket.Ticket(self.session, ticket_id)
        ticket.issue('read', obj_path)
        logging.info(f'CREATE TICKET: {ticket.ticket}: {obj_path}')
        expiration_set = False
        if expiry_string != '':
            try:
                expiration_set = self._modify_ticket(ticket, expiry_string)
            except Exception as error:
                logging.info(f'Could not set expiration date: {error}')
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
        if not self.icommands:
            return ticket.modify('expire', expiry_string) == ticket
        else:
            command = f'iticket mod {ticket.ticket} expire {expiry_string}'
            p = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                shell=True)
            out, err = p.communicate()
            return err == b''