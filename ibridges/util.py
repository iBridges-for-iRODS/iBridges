"""Utilities to work with dataobjects and collections."""

from __future__ import annotations

import base64
from collections.abc import Sequence
from hashlib import md5, sha256
from pathlib import Path
from typing import Union

import irods

from ibridges.path import IrodsPath

try:
    from importlib_metadata import entry_points
except ImportError:
    from importlib.metadata import entry_points  # type: ignore


def get_dataobject(session, path: Union[str, IrodsPath]) -> irods.data_object.iRODSDataObject:
    """Instantiate an iRODS data object.

    This function is deprecated, use :meth:`ibridges.path.IrodsPath.dataobject` instead.

    """
    path = IrodsPath(session, path)
    return path.dataobject


def get_collection(session, path: Union[str, IrodsPath]) -> irods.collection.iRODSCollection:
    """Instantiate an iRODS collection.

    This function is deprecated, use :meth:`ibridges.path.IrodsPath.collection` instead.
    """
    return IrodsPath(session, path).collection


def get_size(
    session, item: Union[irods.data_object.iRODSDataObject, irods.collection.iRODSCollection]
) -> int:
    """Collect the size of a data object or a collection.

    This function is deprecated, use :meth:`ibridges.path.IrodsPath.size` instead.
    """
    return IrodsPath(session, item.path).size


def is_dataobject(item) -> bool:
    """Determine if item is an iRODS data object.

    This function is deprecated, use :meth:`ibridges.path.IrodsPath.dataobject_exists` instead.
    """
    return isinstance(item, irods.data_object.iRODSDataObject)


def is_collection(item) -> bool:
    """Determine if item is an iRODS collection.

    This function is deprecated, use :meth:`ibridges.path.IrodsPath.collection_exists` instead.
    """
    return isinstance(item, irods.collection.iRODSCollection)


def obj_replicas(obj: irods.data_object.iRODSDataObject) -> list[tuple[int, str, str, int, str]]:
    """Retrieve information about replicas (copies of the file on different resources).

    It does so for a data object in the iRODS system.

    Parameters
    ----------
    obj : irods.data_object.iRODSDataObject
        The data object

    Returns
    -------
        List with tuple where each tuple contains replica index/number, resource name on which
        the replica is stored about one replica, replica checksum, replica size,
        replica status of the replica

    """
    repl_states = {
        "0": "stale",
        "1": "good",
        "2": "intermediate",
        "3": "read-locked",
        "4": "write-locked",
    }

    replicas = [
        (r.number, r.resource_name, r.checksum, r.size, repl_states.get(r.status, r.status))
        for r in obj.replicas
    ]

    return replicas


def get_environment_providers() -> list:
    """Get a list of all environment template providers.

    Returns
    -------
        The list that contains the providers.

    """
    return [entry.load() for entry in entry_points(group="ibridges_server_template")]


def print_environment_providers(env_providers: Sequence):
    """Print the environment providers to the screen.

    Parameters
    ----------
    env_providers
        A list of all installed environment providers.

    """
    for provider in env_providers:
        print(provider.name)
        print("-" * len(provider.name))
        print("\n")
        max_len = max(len(x) for x in provider.descriptions)
        for server_name, description in provider.descriptions.items():
            print(f"{server_name: <{max_len+1}} - {description}")


def find_environment_provider(env_providers: list, server_name: str) -> object:
    """Find the provider that provides the right template.

    Parameters
    ----------
    env_providers
        A list of all installed environment providers.
    server_name
        Name of the server for which the template is to be found.

    Returns
    -------
        The provider that contains the template.

    Raises
    ------
    ValueError
        If the server_name identifier can't be found in the providers.

    """
    for provider in env_providers:
        if provider.contains(server_name):
            return provider
    raise ValueError(
        "Cannot find provider with name {server_name} ensure that the plugin is installed."
    )


def calc_checksum(filepath: Union[Path, str, IrodsPath], checksum_type="sha2"):
    """Calculate the checksum for an iRODS dataobject or local file.

    Parameters
    ----------
    filepath:
        Can be either a local path, or an iRODS path.
        If filepath is a string, it will be assumed to be a local path.
    checksum_type:
        Checksum type to calculate, only sha2 and md5 are currently supported.
        Ignored for IrodsPath's, since that is configured by the server.

    Returns
    -------
        The base64 encoding of the sha256 sum of the object, prefixed by 'sha2:'.

    """
    if isinstance(filepath, IrodsPath):
        return filepath.checksum
    if checksum_type == "sha2":
        f_hash = sha256()
    else:
        f_hash = md5()
    memv = memoryview(bytearray(128 * 1024))
    with open(filepath, "rb", buffering=0) as file:
        for item in iter(lambda: file.readinto(memv), 0):
            f_hash.update(memv[:item])
    if checksum_type == "md5":
        return f"{f_hash.hexdigest()}"
    return f"sha2:{str(base64.b64encode(f_hash.digest()), encoding='utf-8')}"


def _detect_checksum(checksum: str):
    if checksum.startswith("sha2:"):
        return "sha2"
    return "md5"


def checksums_equal(remote_path: IrodsPath, local_path: Union[Path, str]):
    """Check whether remote and local paths have the same checksum.

    Parameters
    ----------
    remote_path
        Remote path to calculate the checksum for.
    local_path
        Local path to compute the checksum for.

    Returns
    -------
        Whether the two have equal checksums. The type of checksum done
        depends on what is configured on the remote server.

    """
    remote_check = calc_checksum(remote_path)
    local_check = calc_checksum(local_path, checksum_type=_detect_checksum(remote_check))
    return remote_check == local_check
