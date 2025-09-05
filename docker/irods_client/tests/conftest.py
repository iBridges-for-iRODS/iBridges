import json
from pathlib import Path

import pytest
import tomli

from ibridges import Session
from ibridges.data_operations import upload
from ibridges.path import IrodsPath


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
