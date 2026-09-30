import json
from pathlib import Path

import pytest
import tomli

from ibridges import Session
from ibridges.data_operations import upload
from ibridges.path import IrodsPath

# Keys of the (admin) environment that are useful for an anonymous session.
_SSL_PREFIXES = ("irods_ssl_", "irods_encryption_", "irods_client_server_")
_ANONYMOUS_KEEP = (
    "irods_host",
    "irods_port",
    "irods_zone_name",
    "irods_default_resource",
    "irods_home",
)

@pytest.fixture(scope="session")
def config_dir(request):
    return Path("environment")


@pytest.fixture(scope="session")
def irods_env_file(config, config_dir):
    return config.get("env_path", config_dir / "irods_environment.json")


@pytest.fixture(scope="session")
def irods_env(irods_env_file):
    with open(irods_env_file, "r") as handle:
        ienv = json.load(handle)
    return ienv


@pytest.fixture(scope="session")
def config(config_dir):
    with open(config_dir / "config.toml", "rb") as handle:
        config_data = tomli.load(handle)
    return config_data


@pytest.fixture(scope="session")
def session(irods_env, config):
    session = Session(irods_env=irods_env, password=config["password"])
    yield session
    del session


@pytest.fixture(scope="session")
def testdata():
    return Path("/tmp/testdata")


@pytest.fixture(scope="session")
def collection(session):
    ipath = IrodsPath(session, "~", "test_collection")
    coll = ipath.create_collection()
    yield coll
    IrodsPath(session, coll.path).remove()


@pytest.fixture(scope="session")
def dataobject(session, testdata):
    ipath = IrodsPath(session, "~", "bunny.rtf")
    upload(testdata/"bunny.rtf", IrodsPath(session, "~"), overwrite=True)
    yield ipath.dataobject
    ipath.remove()


@pytest.fixture(scope="session")
def anonymous_irods_env(irods_env):
    """Anonymous environment derived from the environment the tests run against.

    Host, port, zone, home and default resource are copied. SSL and encryption
    settings are copied only if the environment has them, so the plain
    environment (no SSL keys) gives a session without SSL settings and the
    SSL environment gives one with them. The password is never copied.
    """
    env = {
        key: value
        for key, value in irods_env.items()
        if key in _ANONYMOUS_KEEP or key.startswith(_SSL_PREFIXES)
    }
    env["irods_user_name"] = "anonymous"
    return env


@pytest.fixture
def anonymous_session(anonymous_irods_env):
    """Fresh anonymous session per test.

    A supplied ticket sticks to a session, so never share this session
    between tests. Request ``read_ticket`` before this fixture in a test, so
    the session is closed before the ticket is deleted.
    """
    anon = Session(dict(anonymous_irods_env))  # Session modifies the dict it gets.
    yield anon
    anon.close()


@pytest.fixture(scope="session")
def ticket_file(session, collection):
    """Data object inside the test collection."""
    path = f"{collection.path}/ticket_file.txt"
    obj = session.irods_session.data_objects.create(path)
    with obj.open("w") as handle:
        handle.write(b"ticket test")
    return path


@pytest.fixture
def read_ticket(session, collection, ticket_file):
    """Read ticket on the test collection, deleted after the test."""
    tickets = Tickets(session)
    ticket_str, _ = tickets.create_ticket(collection.path)
    yield ticket_str
    try:
        tickets.delete_ticket(ticket_str)
    except KeyError:  # Already deleted by the test.
        pass
