"""Interactive authentication with iRODS server.
"""

import json
import os
from pathlib import Path
from typing import Optional, Union
from getpass import getpass

from ibridges.irodsconnector.session import Session

def authenticate(password: Optional[str] = None, irods_env_path: Optional[Union[str, Path]] =
                 os.path.expanduser("~/.irods/irods_environment.json")) -> Session:
    """Interactive authentication with iRODS server.

    Stores the password in ~/.irods/.irodsA upon success.
    """
    if not os.path.exists(irods_env_path):
        print(f'File not found: {irods_env_path}')
        raise FileNotFoundError

    if os.path.exists(os.path.expanduser("~/.irods/.irodsA")):
        try:
            session = Session(irods_env_path=os.path.expanduser("~/.irods/irods_environment.json"))
            return session
        except IndexError:
            # .irodsA file was tempered with and does not have right formatting anylonger
            pass
        except ValueError:
            # cached password is wrong
            pass

    with open(irods_env_path, "r", encoding="utf-8") as f:
        ienv = json.load(f)
    if password is not None:
        try:
            session = Session(irods_env=ienv, password=password)
            session.write_pam_password()
            return session
        except ValueError:
            #wrong password provided
            pass

    password = getpass("Your iRODS password: ")
    session = Session(irods_env=ienv, password=password)
    session.write_pam_password()
    return session
