import pytest

from ibridges import Session


def test_session(session, config, irods_env):
    assert session.has_valid_irods_session()
    assert ".".join(str(x) for x in session.server_version) == config["server_version"]
    assert session.home == irods_env["irods_home"]
    assert session.default_resc == irods_env["irods_default_resource"]
    assert session.host == irods_env["irods_host"]
    assert session.port == irods_env["irods_port"]
    assert session.username == irods_env["irods_user_name"]
    assert session.zone == irods_env["irods_zone_name"]


def test_pam_password(session, config, irods_env):
    if not config["can_write_pam_pass"]:
        pytest.xfail("This iRods server cannot write pam passwords.")
    session._write_pam_password()
    test_session = Session(irods_env)
    assert test_session.has_valid_irods_session()
