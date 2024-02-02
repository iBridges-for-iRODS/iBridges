import json
from pathlib import Path

import pytest
import tomli

from ibridges import Session

# def pytest_addoption(parser):
    # parser.addoption("--configdir", action="store")


@pytest.fixture(scope="session")
def config_dir(request):
    # config_dir_name = request.config.option.configdir
    # if config_dir_name is None:
        # pytest.skip()
    return Path("environment")


@pytest.fixture(scope="session")
def irods_env_file(config_dir):
    return config_dir / "irods_environment.json"


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
