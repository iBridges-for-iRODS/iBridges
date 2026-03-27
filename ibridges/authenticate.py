"""Authentication with iRODS server."""

import os
import sys
from getpass import getpass
from pathlib import Path
from typing import Optional, Union

from ibridges.cli.config import IbridgesConf
from ibridges.session import LoginError, PasswordError, Session
from ibridges.util import DEFAULT_IENV_PATH, DEFAULT_IRODSA_PATH, ValueErrorParser, open_irodsa


def cli_auth(parser, reauthenticate: bool = False):
    """Authenticate for the CLI and shell."""
    ibridges_conf = IbridgesConf(parser)
    ienv_path, ienv_entry = ibridges_conf.get_entry()
    ienv_cwd = ienv_entry.get("cwd", None)

    if not Path(ienv_path).exists():
        parser.error(f"Error: Irods environment file or alias '{ienv_path}' does not exist.")
    irodsa_backup = None if reauthenticate else ienv_entry.get("irodsa_backup", None)
    session = interactive_auth(irods_env_path=ienv_path, cwd=ienv_cwd,
                               irodsa_backup=irodsa_backup, reauthenticate=reauthenticate)

    with open_irodsa(DEFAULT_IRODSA_PATH, "r", encoding="utf-8") as handle:
        irodsa_content = handle.read()
    if irodsa_content != ienv_entry.get("irodsa_backup"):
        ienv_entry["irodsa_backup"] = irodsa_content
        ibridges_conf.save()

    return session


def non_interactive_auth(*args, ienv_path_or_alias: Optional[str] = None,
                         cwd: Optional[str] = None,
                         parser=ValueErrorParser(), **kwargs):
    """Non interactive authentication that doesn't ask for a password.

    This authentication is integrated with the CLI configuration.
    I.e. by default it will try to connect with the last successfully used
    configuration (check with `ibridges alias` on the command line).
    Instead of using an irods_environment file path, you can also use the
    alias to connect. The last cached password for this environment will be
    used to authenticate.

    Parameters
    ----------
    args:
        Extra arguments for the Session object.
    ienv_path_or_alias:
        alias or iRODS environment file to use for authentication. If None,
        use the currently selected environment in the configuration file.
    cwd:
        Current working collection to set.
    parser:
        Parser to relay the error messages to. By default, errors are raised as
        ValueError's.
    kwargs:
        Extra keyword arguments for the session such as home and password.


    Returns
    -------
    session:
        Session after successfully authenticating.

    """
    # iBridges doesn't have a non-interactive auth, so make one.
    ibridges_conf = IbridgesConf(parser=parser)
    ienv_path: Optional[str]
    try:
        ienv_path, ienv_entry = ibridges_conf.get_entry(ienv_path_or_alias)
        irodsa_backup = ienv_entry.get("irodsa_backup", None)
        cwd_stored = ienv_entry.get("cwd", None)
        cwd_final = cwd_stored if cwd is None else cwd
        if irodsa_backup is not None:
            with open_irodsa(DEFAULT_IRODSA_PATH, "w", encoding="utf-8") as handle:
                handle.write(irodsa_backup)
    except KeyError:
        ienv_path = ienv_path_or_alias
        cwd_final = cwd
    if ienv_path is None:
        raise ValueError("Could not find specified irods environment.")

    return Session(ienv_path, *args, cwd=cwd_final, **kwargs)  # type: ignore


def interactive_auth(
    password: Optional[str] = None, irods_env_path: Union[None, str, Path] = None,
    irodsa_backup: Optional[str] = None, reauthenticate: bool = False,
    **kwargs
) -> Session:
    """Interactive authentication with iRODS server.

    The main difference with using the :class:`ibridges.Session` object directly is
    that it will ask for your password if the cached password does not exist or is outdated.
    This can be more secure, since you won't have to store the password in a file or notebook.
    By default uses `~/.irods/irods_environment.json` to authenticate.
    Caches the password in ~/.irods/.irodsA upon success.

    Parameters
    ----------
    password:
        Password to make the connection with. If not supplied, you will be asked interactively.
    irods_env_path:
        Path to the irods environment. Default `~/.irods/irods_environment.json.`
    irodsa_backup:
        Backup of the .irodsA file to be used in case authentication fails.
    reauthenticate:
        If reauthenticate is set to True, then cached passwords will be ignored and a new password
        can be submitted.
    kwargs:
        Extra parameters for the interactive auth. Mainly used for the cwd parameter.

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
    if DEFAULT_IRODSA_PATH.is_file() and password is None and not reauthenticate:
        session = _from_pw_file(irods_env_path, irodsa_backup=irodsa_backup, **kwargs)

    if password is not None:
        session = _from_password(irods_env_path, password, **kwargs)

    if session is not None:
        return session

    # If provided passwords in file or on prompt were wrong
    n_tries = 0
    success = False
    while not success and n_tries < 3:
        if sys.stdin.isatty() or 'ipykernel' in sys.modules:
            password = getpass('Your iRODS password: ')
        else:
            print('Your iRODS password: ')
            password = sys.stdin.readline().rstrip()
        try:
            session = Session(irods_env=irods_env_path, password=password, **kwargs)
            session.write_pam_password()
            success = True
            return session
        except PasswordError as e:
            print(repr(e))
            print("INFO: The provided username and/or password is wrong.")
            n_tries += 1
    raise LoginError("Connection to iRODS could not be established.")


def _from_pw_file(irods_env_path, irodsa_backup: Optional[str] = None, **kwargs):
    try:
        session = Session(irods_env_path, **kwargs)
        return session
    except IndexError:
        print("INFO: The cached password in ~/.irods/.irodsA has been corrupted")
    except PasswordError:
        if irodsa_backup is not None:
            with open_irodsa(DEFAULT_IRODSA_PATH, "w", encoding="utf-8") as handle:
                handle.write(irodsa_backup)
            try:
                session = Session(irods_env_path, **kwargs)
                return session
            except PasswordError:
                print("INFO: The cached password in ~/.irods/.irodsA is wrong.")
    return None


def _from_password(irods_env_path, password, **kwargs):
    try:
        session = Session(irods_env=irods_env_path, password=password, **kwargs)
        session.write_pam_password()
        return session
    except PasswordError:
        print("INFO: The provided username and/or password is wrong.")
    return None
