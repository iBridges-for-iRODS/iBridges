"""Interactive authentication with iRODS server.
"""

import json
import os
from pathlib import Path
from typing import Optional, Union
from getpass import getpass

from ibridges.irodsconnector.session import Session

DEFAULT_IENV_PATH = Path(os.path.expanduser("~")).joinpath(".irods", "irods_environment.json")

def interactive_auth(password: Optional[str] = None, 
                     irods_env_path: Optional[Union[str, Path]] = DEFAULT_IENV_PATH) -> Session:
    """Interactive authentication with iRODS server.

    Stores the password in ~/.irods/.irodsA upon success.
    """
    if not os.path.exists(irods_env_path):
        print(f'File not found: {irods_env_path}')
        raise FileNotFoundError

    if os.path.exists(Path(os.path.expanduser("~")).joinpath(".irods", ".irodsA")):
        try:
            session = Session(irods_env_path=irods_env_path)
            return session
        except IndexError:
            # .irodsA file was tempered with and does not have right formatting anylonger
            print('INFO: The cached password in ~/.irods/.irodsA has been corrupted')
        except ValueError:
            # cached password is wrong
            print('INFO: The cached password in ~/.irods/.irodsA is wrong.')

    with open(irods_env_path, "r", encoding="utf-8") as f:
        ienv = json.load(f)
    if password is not None:
        try:
            session = Session(irods_env=ienv, password=password)
            session.write_pam_password()
            return session
        except ValueError:
            #wrong password provided
            print('INFO: The provided password is wrong.')
    else:
        n_tries = 0
        success = False
        while not success and n_tries < 3:
            password = getpass("Your iRODS password: ")
            try:
                session = Session(irods_env=ienv, password=password)
                session.write_pam_password()
                success == True
                return session
            except:
                print('INFO: The provided password is wrong.')
                n_tries+=1
