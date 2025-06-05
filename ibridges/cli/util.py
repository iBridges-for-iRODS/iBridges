"""Utilities for the CLI and shell."""
from pathlib import Path
from typing import Union

from ibridges.cli.config import IbridgesConf
from ibridges.exception import NotACollectionError
from ibridges.interactive import DEFAULT_IRODSA_PATH, interactive_auth
from ibridges.path import IrodsPath
from ibridges.session import Session
from ibridges.util import get_collection


def cli_authenticate(parser):
    """Authenticate for the CLI and shell."""
    ibridges_conf = IbridgesConf(parser)
    ienv_path, ienv_entry = ibridges_conf.get_entry()
    ienv_cwd = ienv_entry.get("cwd", None)

    if not Path(ienv_path).exists():
        parser.error(f"Error: Irods environment file or alias '{ienv_path}' does not exist.")
    session = interactive_auth(irods_env_path=ienv_path, cwd=ienv_cwd,
                               irodsa_backup=ienv_entry.get("irodsa_backup", None))

    with open(DEFAULT_IRODSA_PATH, "r", encoding="utf-8") as handle:
        irodsa_content = handle.read()
    if irodsa_content != ienv_entry.get("irodsa_backup"):
        ienv_entry["irodsa_backup"] = irodsa_content
        ibridges_conf.save()

    return session

def list_collection(session: Session, remote_path: IrodsPath, metadata: bool = False):
    """List a collection with default formatting."""
    if remote_path.collection_exists():
        print(str(remote_path) + ":")
        if metadata:
            meta_str = str(remote_path.meta)
            if len(meta_str) > 0:
                print(str(remote_path.meta))
                print()
        coll = get_collection(session, remote_path)

        # List collections
        for sub_coll in coll.subcollections:
            if str(remote_path) == sub_coll.path:
                continue
            print("  C- " + sub_coll.path)
            if metadata and len((remote_path / sub_coll.name).meta) > 0:
                print((remote_path / sub_coll.name).meta)
                print()

        # List data objects
        for data_obj in coll.data_objects:
            print("  " + data_obj.path)
            if metadata and len((remote_path / data_obj.name).meta) > 0:
                print((remote_path / data_obj.name).meta)
                print()

    elif remote_path.dataobject_exists():
        print(remote_path)
    else:
        raise NotACollectionError(f"Irods path '{remote_path}' is not a collection.")

def parse_remote(remote_path: Union[None, str], session: Session) -> IrodsPath:
    """Parse a remote path."""
    if remote_path is None:
        return IrodsPath(session, session.cwd)
    if not remote_path.startswith("irods:") or IrodsPath(session, remote_path).collection_exists():
        return IrodsPath(session, remote_path)
    if remote_path.startswith("irods://"):
        remainder = remote_path[8:]
        if remainder.startswith("~"):
            return IrodsPath(session, remainder)
        return IrodsPath(session, remote_path[7:])
    return IrodsPath(session, remote_path[6:])
