from datetime import datetime

import irods
import pytest
from pytest import mark

from ibridges.irodsconnector.tickets import Tickets


@mark.parametrize("item_name", ["collection", "dataobject"])
@mark.parametrize("ticket_type", ["read", "write"])
def test_tickets(item_name, ticket_type, session, config, request):
    item = request.getfixturevalue(item_name)
    ipath = item.path
    tickets = Tickets(session)
    tickets.clear()
    assert len(tickets.update_tickets()) == 0

    exp_date = datetime.today()
    tickets.create_ticket(str(ipath), ticket_type=ticket_type, expiry_date=exp_date)
    assert len(tickets.update_tickets()) == 1
    ticket_str = tickets.all_ticket_strings[0]
    tick = tickets.get_ticket(ticket_str)
    assert isinstance(tick, irods.ticket.Ticket)
    ticket_data = tickets.update_tickets()[0]
    assert ticket_data.name == ticket_str
    assert ticket_data.type == ticket_type
    assert ticket_data.path == str(ipath)
    if config.get("ticket_date_only", False):
        assert ticket_data.expiration_date.date() == exp_date.date()
    else:
        assert ticket_data.expiration_date == exp_date
    tickets.delete_ticket(tick)
    assert len(tickets.update_tickets()) == 0
    with pytest.raises(KeyError):
        tickets.delete_ticket(tick, check=True)
