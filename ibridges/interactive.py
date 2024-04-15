"""Interactive authentication with iRODS server."""

import json
import os
from getpass import getpass
from pathlib import Path
from typing import Optional, Union

from ibridges.session import Session, LoginError

DEFAULT_IENV_PATH = Path(os.path.expanduser("~")).joinpath(".irods", "irods_environment.json")

def interactive_auth(password: Optional[str] = None,
                     irods_env_path: Union[str, Path] = DEFAULT_IENV_PATH) -> Session:
    """Interactive authentication with iRODS server.

    Stores the password in ~/.irods/.irodsA upon success.

    Parameters
    ----------
    password:
        Password to make the connection with. If not supplied, you will be asked interactively.
    irods_env_path:
        Path to the irods environment.

    Raises
    ------
    FileNotFoundError:
        If the irods_env_path does not exist.
    ValueError:
        If the connection to the iRods server cannot be established.

    Returns
    -------
        A connected session to the server.

    """
    if not os.path.exists(irods_env_path):
        print(f'File not found: {irods_env_path}')
        raise FileNotFoundError

    if os.path.exists(Path(os.path.expanduser("~")).joinpath(".irods", ".irodsA")) and \
            password is None:
        try:
            session = Session(irods_env_path)
            return session
        except LoginError as e:
            print(f'INFO: {e.args}')
            # environment.json is not setup correctly -> stop
            if 'not set correctly in irods_environment.json' in e.args[0]:
                raise(e)
            # non-iRODS key found
            if 'Unexpected value in irods_environment; ' in e.args:
                raise(ValueError('Non-iRODS key or value found in environment.json')) from e
        except IndexError:
            print('INFO: The cached password in ~/.irods/.irodsA has been corrupted')
        except ValueError:
            print('INFO: The cached password in ~/.irods/.irodsA is wrong.')

    if password is not None:
        try:
            session = Session(irods_env=irods_env_path, password=password)
            session.write_pam_password()
            return session
        except LoginError as e:
            print(f'INFO: {e.args}')
            # environment.json is not setup correctly -> stop
            if 'not set correctly in irods_environment.json' in e.args[0]:
                raise(e)
            if 'Unexpected value in irods_environment; ' in e.args:
                raise(ValueError('Non-iRODS key or value found in environment.json')) from e

    n_tries = 0
    success = False
    while not success and n_tries < 3:
        password = getpass("Your iRODS password: ")
        try:
            session = Session(irods_env=irods_env_path, password=password)
            session.write_pam_password()
            success = True
            return session
        except ValueError as e:
            print(repr(e))
            print('INFO: The provided password is wrong.')
            n_tries+=1
    raise ValueError("Connection to iRODS could not be established.")
