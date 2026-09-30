import irods.session
import pytest

from ibridges.session import DEFAULT_ANONYMOUS_SSL_SETTINGS, Session

_SSL_PREFIXES = ("irods_ssl_", "irods_encryption_", "irods_client_server_")

BASE_ENV = {
    "irods_user_name": "anonymous",
    "irods_host": "example.org",
    "irods_port": 1247,
    "irods_zone_name": "tempZone",
    "irods_home": "/tempZone/home",  # Skips the home lookup on the server.
}


def _connect(monkeypatch, env, anonymous_options=None):
    """Create an anonymous Session against a fake server, return the kwargs sent to PRC."""
    captured = {}

    class FakeIrodsSession:
        server_version = (4, 3, 2)

        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(irods.session, "iRODSSession", FakeIrodsSession)
    monkeypatch.setattr(Session, "network_check", classmethod(lambda cls, host, port: True))
    Session(dict(env), anonymous_options=anonymous_options)
    return captured


def _ssl_keys(kwargs):
    return {key: value for key, value in kwargs.items() if key.startswith(_SSL_PREFIXES)}


# SSL settings: no server needed

def test_no_ssl_settings_without_ssl_env(monkeypatch):
    kwargs = _connect(monkeypatch, BASE_ENV)
    assert _ssl_keys(kwargs) == {}
    assert kwargs["user"] == "anonymous"
    assert kwargs["host"] == "example.org"
    assert "irods_default_resource" not in kwargs


def test_ssl_settings_from_env(monkeypatch):
    env = {
        **BASE_ENV,
        "irods_client_server_policy": "CS_NEG_REQUIRE",
        "irods_encryption_algorithm": "AES-256-CBC",
        "irods_ssl_verify_server": "none",
        "irods_default_resource": "irodsResc",
    }
    kwargs = _connect(monkeypatch, env)
    assert _ssl_keys(kwargs) == {
        "irods_client_server_policy": "CS_NEG_REQUIRE",
        "irods_encryption_algorithm": "AES-256-CBC",
        "irods_ssl_verify_server": "none",
    }
    assert kwargs["irods_default_resource"] == "irodsResc"


def test_explicit_ssl_settings_override_env(monkeypatch):
    env = {**BASE_ENV, "irods_encryption_algorithm": "AES-128-CBC"}
    kwargs = _connect(
        monkeypatch,
        env,
        anonymous_options={"ssl_settings": {"irods_encryption_algorithm": "AES-256-CBC"}},
    )
    assert kwargs["irods_encryption_algorithm"] == "AES-256-CBC"


def test_explicit_default_ssl_settings(monkeypatch):
    kwargs = _connect(
        monkeypatch,
        BASE_ENV,
        anonymous_options={"ssl_settings": DEFAULT_ANONYMOUS_SSL_SETTINGS},
    )
    assert kwargs["irods_client_server_policy"] == "CS_NEG_REQUIRE"
    assert kwargs["irods_encryption_key_size"] == 32


def test_connection_overrides(monkeypatch):
    kwargs = _connect(
        monkeypatch,
        BASE_ENV,
        anonymous_options={"host": "other.org", "port": 8247, "zone_name": "otherZone"},
    )
    assert (kwargs["host"], kwargs["port"], kwargs["zone"]) == ("other.org", 8247, "otherZone")


def test_missing_connection_parameters(monkeypatch):
    env = {key: value for key, value in BASE_ENV.items() if key != "irods_zone_name"}
    with pytest.raises(ValueError):
        _connect(monkeypatch, env)


# Integration test Against the test server


def test_anonymous_env_settings(anonymous_irods_env, irods_env):
    assert anonymous_irods_env["irods_user_name"] == "anonymous"
    assert "irods_password" not in anonymous_irods_env
    ssl_in_env = {key for key in irods_env if key.startswith(_SSL_PREFIXES)}
    assert set(_ssl_keys(anonymous_irods_env)) == ssl_in_env


def test_anonymous_session_connects(anonymous_session):
    assert anonymous_session.username == "anonymous"
    assert anonymous_session.has_valid_irods_session()
