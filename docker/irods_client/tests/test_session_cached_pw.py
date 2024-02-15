import os
from ibridges import Session

def test_session_from_cached_pw(config, irods_env):
    session = Session(irods_env_path=os.path.expanduser("~/.irods/irods_environment.json"))
    assert session.has_valid_irods_session()
    assert ".".join(str(x) for x in session.server_version) == config["server_version"]
    assert session.home == irods_env["irods_home"]
    assert session.default_resc == irods_env["irods_default_resource"]
    assert session.host == irods_env["irods_host"]
    assert session.port == irods_env["irods_port"]
    assert session.username == irods_env["irods_user_name"]
    assert session.zone == irods_env["irods_zone_name"]

    del session
