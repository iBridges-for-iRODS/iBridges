"""Interactive authentication with iRODS server."""

import os
from getpass import getpass
from pathlib import Path
from typing import Optional, Union

from ibridges.session import LoginError, PasswordError, Session

DEFAULT_IENV_PATH = Path(os.path.expanduser("~")).joinpath(".irods", "irods_environment.json")


def interactive_auth(
    password: Optional[str] = None, irods_env_path: Union[None, str, Path] = None
) -> Session:
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
    if irods_env_path is None:
        irods_env_path = DEFAULT_IENV_PATH
    if not os.path.exists(irods_env_path):
        print(f"File not found: {irods_env_path}")
        raise FileNotFoundError

    session = None
    if (
        os.path.exists(Path(os.path.expanduser("~")).joinpath(".irods", ".irodsA"))
        and password is None
    ):
        session = _from_pw_file(irods_env_path)

    if password is not None:
        session = _from_password(irods_env_path, password)

    if session is not None:
        return session

    # If provided passwords in file or on prompt were wrong
    n_tries = 0
    success = False
    while not success and n_tries < 3:
        password = getpass("Your iRODS password: ")
        try:
            session = Session(irods_env=irods_env_path, password=password)
            session.write_pam_password()
            success = True
            return session
        except PasswordError as e:
            print(repr(e))
            print("INFO: The provided password is wrong.")
            n_tries += 1
    raise LoginError("Connection to iRODS could not be established.")


def _from_pw_file(irods_env_path):
    try:
        session = Session(irods_env_path)
        return session
    except IndexError:
        print("INFO: The cached password in ~/.irods/.irodsA has been corrupted")
    except PasswordError:
        print("INFO: The cached password in ~/.irods/.irodsA is wrong.")
    return None


def _from_password(irods_env_path, password):
    try:
        session = Session(irods_env=irods_env_path, password=password)
        session.write_pam_password()
        return session
    except PasswordError:
        print("INFO: Wrong password.")
    return None
