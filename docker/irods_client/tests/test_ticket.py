import datetime

import irods
import pytest
from pytest import mark

from ibridges.tickets import TicketAccess, Tickets
from ibridges.path import IrodsPath
from ibridges.session import Session

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

@pytest.fixture
def anon_env(session):
    """Environment dictionary for an anonymous session on the same server."""
    return {
        "irods_user_name": "anonymous",
        "irods_host": session.host,
        "irods_port": session.port,
        "irods_zone_name": session.zone,
    }


@pytest.fixture
def anon_session(anon_env, config):
    """Anonymous session, skipped if the server does not allow anonymous logins.

    Extra options for the anonymous login (e.g. SSL settings) can be set with
    the 'anonymous_options' entry in the test configuration.
    """
    options = config.get("anonymous_options", {})
    try:
        anon = Session(anon_env, anonymous_options=options)
    except Exception as error:  # pylint: disable=broad-except
        pytest.skip(f"Anonymous login is not available on this server: {error!r}")
    yield anon
    anon.close()


@pytest.fixture(params=["collection", "dataobject"])
def ticketed_item(request, session):
    """Read ticket for a collection or data object: (ticket string, IrodsPath)."""
    item = request.getfixturevalue(request.param)
    ipath = IrodsPath(session, item.path)
    tickets = Tickets(session)
    tickets.clear()
    ticket_str, _ = tickets.create_ticket(ipath, ticket_type="read")
    yield ticket_str, ipath
    tickets.clear()


def test_anonymous_session(anon_session, anon_env):
    assert anon_session.username == "anonymous"
    assert anon_session.has_valid_irods_session()
    # The environment dictionary of the caller is not modified by the session.
    assert set(anon_env) == {
        "irods_user_name",
        "irods_host",
        "irods_port",
        "irods_zone_name",
    }


def test_anonymous_session_missing_parameters(anon_env):
    del anon_env["irods_zone_name"]
    with pytest.raises(ValueError):
        Session(anon_env)


def test_ticket_access_path_supplied(session, ticketed_item):
    ticket_str, ipath = ticketed_item
    access = TicketAccess(session, ticket_str, ipath)
    assert isinstance(access.path, IrodsPath)
    assert str(access.path) == str(ipath)


def test_ticket_access_path_lookup(session, ticketed_item):
    # The owner is allowed to query the ticket table, so the path can be found.
    ticket_str, ipath = ticketed_item
    access = TicketAccess(session, ticket_str)
    assert isinstance(access.path, IrodsPath)
    assert str(access.path) == str(ipath)


def test_ticket_access_anonymous(anon_session, ticketed_item):
    ticket_str, ipath = ticketed_item
    access = TicketAccess(anon_session, ticket_str, ipath)
    assert isinstance(access.path, IrodsPath)
    assert str(access.path) == str(ipath)
    assert access.path.exists()


def test_ticket_access_anonymous_no_ticket(anon_session, ticketed_item):
    # Without supplying the ticket, the anonymous user has no access.
    _, ipath = ticketed_item
    assert not IrodsPath(anon_session, str(ipath)).exists()


def test_ticket_access_anonymous_lookup(anon_session, ticketed_item):
    # Whether an anonymous user can look up the path depends on the server:
    # either we find the correct path or we get a clear error asking for the path.
    ticket_str, ipath = ticketed_item
    access = TicketAccess(anon_session, ticket_str)
    try:
        path = access.path
    except ValueError as error:
        assert "irods_path" in str(error)
    else:
        assert str(path) == str(ipath)


