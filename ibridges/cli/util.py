"""Utilities for the CLI and shell."""

from pathlib import Path
from typing import Union
import warnings
from typing import Union

from ibridges.authenticate import cli_auth
from ibridges.exception import NotACollectionError
from ibridges.path import IrodsPath
from ibridges.permissions import Permissions
from ibridges.session import Session
from ibridges.util import get_collection


def cli_authenticate(parser):
    """Authenticate with cli authentication."""
    warnings.warn("ibridges.cli.cli_authenticate() is deprecated, "
                  "use ibridges.authenticate.cli_auth() instead.")
    return cli_auth(parser)

def list_info(
    session: Session,
    remote_path: IrodsPath,
    metadata: bool = False,
    acls: bool = False,
    recursive=False,
):
    """List information on data objects and collections with default formatting."""
    print(str(remote_path) + ":")
    if metadata:
        meta_str = str(remote_path.meta)
        if len(meta_str) > 0:
            print(str(remote_path.meta))
            print()

    target = remote_path.collection if remote_path.collection_exists() else remote_path.dataobject
    if acls:
        perm = Permissions(session, target)
        print(perm)
        print()

    if remote_path.collection_exists() and recursive:
        coll = get_collection(session, remote_path)

        # List collections
        for sub_coll in coll.subcollections:
            if str(remote_path) == sub_coll.path:
                continue
            print("  C- " + sub_coll.path)
            if metadata and len((remote_path / sub_coll.name).meta) > 0:
                print((remote_path / sub_coll.name).meta)
                print()
            if acls:
                perm = Permissions(session, sub_coll)
                print(perm)
                print()

        # List data objects
        for data_obj in coll.data_objects:
            print("  " + data_obj.path)
            if metadata and len((remote_path / data_obj.name).meta) > 0:
                print((remote_path / data_obj.name).meta)
                print()
            if acls:
                perm = Permissions(session, data_obj)
                print(perm)
                print()


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
