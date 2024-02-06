from datetime import datetime

import irods
import pytest
from pytest import mark

from ibridges.irodsconnector.tickets import Tickets


@mark.parametrize("item_name", ["collection", "dataobject"])
@mark.parametrize("ticket_type", ["read", "write"])
def test_tickets(item_name, ticket_type, session, request):
    item = request.getfixturevalue(item_name)
    ipath = item.path
    tickets = Tickets(session)
    tickets.clear()
    assert len(tickets.all_tickets(update=True)) == 0

    exp_date = datetime.today().strftime('%Y-%m-%d.%H:%M:%S')
    tickets.create_ticket(str(ipath), ticket_type=ticket_type, expiry_string=exp_date)
    assert len(tickets.all_tickets(update=True)) == 1
    ticket_str = tickets.all_ticket_strings[0]
    tick = tickets.get_ticket(ticket_str)
    assert isinstance(tick, irods.ticket.Ticket)
    ticket_data = tickets.all_tickets(update=True)[0]
    assert ticket_data[0] == ticket_str
    assert ticket_data[1] == ticket_type
    assert ticket_data[2] == str(ipath)
    # assert ticket_data[3] == exp_date
    assert isinstance(ticket_data[3], str)
    tickets.delete_ticket(tick)
    assert len(tickets.all_tickets(update=True)) == 0
    with pytest.raises(KeyError):
        tickets.delete_ticket(tick, check=True)
