"""Utilities to work with dataobjects and collections."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import irods

from ibridges.path import IrodsPath

try:
    from importlib_metadata import entry_points
except ImportError:
    from importlib.metadata import entry_points  # type: ignore


def get_dataobject(session, path: Union[str, IrodsPath]) -> irods.data_object.iRODSDataObject:
    """Instantiate an iRODS data object.

    See :meth:`ibridges.path.IrodsPath.dataobject` for details.

    """
    path = IrodsPath(session, path)
    return path.dataobject


def get_collection(session, path: Union[str, IrodsPath]) -> irods.collection.iRODSCollection:
    """Instantiate an iRODS collection.

    See :meth:`ibridges.path.IrodsPath.collection` for details.
    """
    return IrodsPath(session, path).collection


def get_size(
    session, item: Union[irods.data_object.iRODSDataObject, irods.collection.iRODSCollection]
) -> int:
    """Collect the sizes of a data object or a collection.

    See :meth:`ibridges.path.IrodsPath.size` for details.
    """
    return IrodsPath(session, item.path).size


def is_dataobject(item) -> bool:
    """Determine if item is an iRODS data object."""
    return isinstance(item, irods.data_object.iRODSDataObject)


def is_collection(item) -> bool:
    """Determine if item is an iRODS collection."""
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
    list(tuple(int, str, str, int, str)):
        List with tuple where each tuple contains replica index/number, resource name on which
        the replica is stored about one replica, replica checksum, replica size,
        replica status of the replica

    """
    # replicas = []
    repl_states = {"0": "stale", "1": "good", "2": "intermediate", "3": "write-locked"}

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
