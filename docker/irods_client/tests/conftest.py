import json
from pathlib import Path
import os

import pytest
import tomli

from ibridges import Session
from ibridges.irodsconnector.data_operations import (
    create_collection,
    get_collection,
    get_dataobject,
    upload,
)
from ibridges.irodsconnector.permissions import Permissions
from ibridges.utils.path import IrodsPath


@pytest.fixture(scope="session")
def config_dir(request):
    return Path("environment")


@pytest.fixture(scope="session")
def irods_env_file(config):
    return config["env_path"]


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
    ipath = IrodsPath(session, "~")
    perm = Permissions(session, get_collection(session, ipath))
    if config.get("set_home_perm", True):
        perm.set("own")
    yield session
    del session


@pytest.fixture(scope="session")
def testdata():
    return Path("/tmp/testdata")


@pytest.fixture(scope="session")
def collection(session):
    return create_collection(session, IrodsPath(session, "~", "test_collection"))


@pytest.fixture(scope="session")
def dataobject(session, testdata):
    ipath = IrodsPath(session, "~", "bunny.rtf")
    upload(session, testdata/"bunny.rtf", IrodsPath(session, "~"), overwrite=True)
    data_obj = get_dataobject(session, ipath)
    perm = Permissions(session, data_obj)
    perm.set("own")
    yield data_obj
    ipath.remove()
