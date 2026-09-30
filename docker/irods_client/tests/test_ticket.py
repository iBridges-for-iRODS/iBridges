import datetime

import irods
import pytest
from pytest import mark

from ibridges.data_operations import download
from ibridges.path import IrodsPath
from ibridges.tickets import TicketAccess, TicketData, Tickets


def _find(tickets, ticket_str):
    return next(t for t in tickets.fetch_tickets() if t.name == ticket_str)

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

@mark.parametrize("as_type", ["date", "str"])
def test_create_ticket_expiry_input_types(as_type, session, collection, config):
    expiry_day = datetime.date.today() + datetime.timedelta(days=30)
    expected = datetime.datetime.combine(expiry_day, datetime.time.min)
    expiry = expiry_day if as_type == "date" else expiry_day.strftime("%Y-%m-%d.%H:%M:%S")

    tickets = Tickets(session)
    ticket_str, expiration_set = tickets.create_ticket(collection.path, expiry_date=expiry)
    try:
        assert expiration_set is True
        data = _find(tickets, ticket_str)
        if config.get("ticket_date_only", False):
            assert data.expiration_date.date() == expected.date()
        else:
            assert data.expiration_date == expected
    finally:
        tickets.delete_ticket(ticket_str)


def test_ticket_without_expiry(session, collection):
    tickets = Tickets(session)
    ticket_str, expiration_set = tickets.create_ticket(collection.path)
    try:
        assert expiration_set is False
        assert _find(tickets, ticket_str).expiration_date == ""
    finally:
        tickets.delete_ticket(ticket_str)


def test_create_ticket_wrong_expiry_type(session, collection):
    tickets = Tickets(session)
    before = {t.name for t in tickets.fetch_tickets()}
    try:
        with pytest.raises(TypeError):
            tickets.create_ticket(collection.path, expiry_date=12345)
    finally:
        # create_ticket issues the ticket before it checks the expiry type,
        # so it leaves a ticket behind. Clean up.
        for name in {t.name for t in tickets.fetch_tickets()} - before:
            tickets.delete_ticket(name)


def test_str_contains_ticket(session, read_ticket):
    assert read_ticket in str(Tickets(session))


def test_iter_yields_ticket_data(session, read_ticket):
    names = [data.name for data in Tickets(session)]
    assert read_ticket in names


def test_get_unknown_ticket(session):
    with pytest.raises(KeyError):
        Tickets(session).get_ticket("this-ticket-does-not-exist")


def test_delete_unknown_ticket(session):
    with pytest.raises(KeyError):
        Tickets(session).delete_ticket("this-ticket-does-not-exist", check=True)


# ---------------------------------------------------------------------------
# Table formatting: no server needed
# ---------------------------------------------------------------------------


def test_format_no_tickets():
    assert Tickets.format_tickets_table([]) == "No tickets found."


def test_format_tickets_table():
    tickets = [
        TicketData("abc", "read", "/z/home/u/coll", datetime.datetime(2026, 12, 31)),
        TicketData("defghi", "write", "/z/home/u/obj.txt", ""),
    ]
    lines = Tickets.format_tickets_table(tickets).splitlines()
    assert len(lines) == 4  # header, divider, two rows
    assert lines[0].split(" | ")[0].strip() == "Ticket"
    assert "2026-12-31 00:00:00" in lines[2]
    assert "never" in lines[3]
    assert len({len(line) for line in lines}) == 1  # aligned columns


# ---------------------------------------------------------------------------
# Recipient side, with an anonymous session
# ---------------------------------------------------------------------------


def test_ticket_access_lists_collection(read_ticket, anonymous_session, collection):
    access = TicketAccess(anonymous_session, read_ticket, irods_path=collection.path)
    path = access.path
    assert str(path) == collection.path
    assert path.collection_exists()
    names = [p.name for p in path.walk(depth=1, include_base_collection=False)]
    assert "ticket_file.txt" in names


def test_ticket_access_download(read_ticket, anonymous_session, collection, tmp_path):
    access = TicketAccess(anonymous_session, read_ticket, irods_path=collection.path)
    download(anonymous_session, IrodsPath(anonymous_session, access.path, "ticket_file.txt"), tmp_path)
    assert (tmp_path / "ticket_file.txt").read_bytes() == b"ticket test"


def test_ticket_access_path_lookup(read_ticket, anonymous_session, collection):
    access = TicketAccess(anonymous_session, read_ticket)
    try:
        path = access.path
    except ValueError:
        pytest.skip("This server does not allow looking up the ticket path.")
    assert str(path) == collection.path


def test_ticket_access_lookup_unknown_ticket(anonymous_session):
    access = TicketAccess(anonymous_session, "this-ticket-does-not-exist", supply=False)
    with pytest.raises(ValueError):
        _ = access.path


def test_no_access_without_ticket(read_ticket, anonymous_session, collection):
    assert not IrodsPath(anonymous_session, collection.path).exists()
