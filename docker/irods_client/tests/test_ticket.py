import datetime

import irods
import pytest
from pytest import mark

from ibridges.tickets import Tickets
from ibridges.path import IrodsPath

@mark.parametrize("item_name", ["collection", "dataobject"])
@mark.parametrize("ticket_type", ["read", "write"])
@mark.parametrize("n_days_ahead", [1, 100])
def test_tickets(item_name, ticket_type, n_days_ahead, session, config, request):
    item = request.getfixturevalue(item_name)
    ipath = IrodsPath(session, item.path)
    tickets = Tickets(session)
    tickets.clear()
    assert len(tickets.fetch_tickets()) == 0

    exp_date = datetime.datetime.today() + datetime.timedelta(days=n_days_ahead)
    tickets.create_ticket(ipath, ticket_type=ticket_type, expiry_date=exp_date)
    assert len(tickets.fetch_tickets()) == 1
    ticket_str = tickets.all_ticket_strings[0]
    tick = tickets.get_ticket(ticket_str)
    assert isinstance(tick, irods.ticket.Ticket)
    ticket_data = tickets.fetch_tickets()[0]
    assert ticket_data.name == ticket_str
    assert ticket_data.type == ticket_type
    assert str(ticket_data.path) == str(ipath)

    # It seems that generally irods invalidates the tickets at midnight of the same day
    if config.get("ticket_date_only", False):
        assert ticket_data.expiration_date.date() == exp_date.date()
    else:
        assert ticket_data.expiration_date == exp_date
    tickets.delete_ticket(tick)
    assert len(tickets.fetch_tickets()) == 0
    with pytest.raises(KeyError):
        tickets.delete_ticket(tick, check=True)
