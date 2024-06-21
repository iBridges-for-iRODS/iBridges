
"""Exporting metadata."""
from __future__ import annotations

from typing import Any, Optional, Union

from ibridges.path import IrodsPath
from ibridges.session import Session


def add_to_metadict(meta_dict: dict, ipath: IrodsPath, root_ipath: IrodsPath):
    meta = ipath.meta
    meta_dict["items"].append({
        "rel_path": str(ipath.relative_to(root_ipath)),
        "irods_id": meta.item.id,
        "metadata": meta.to_dict(),
    })


def empty_metadict(path, recursive=True):
    return {
        "ibridges_metadata_version": "1.0",
        "recursive": recursive,
        "root_path": str(path),
        "items": [],
    }

def export_metadata_to_dict(path: Union[IrodsPath, str], session: Session,
                            recursive: bool = True, keys: Optional[list] = None) -> dict:
    """Retrieve the metadata of the item and brings it into dict form.

    If the item is a collection all metadata from all subcollections
    and data objects will also be exported.

    {
        "name": name
        "irods_id": iRODS database ID
        "metadata": [(key, val, units), (key, val, units) ….]
        "collections”: [
            {
                "rel_path": relative path to upper rel_path
                "irods_id": iRODS database ID
                "metadata": [(key, val, units), (key, val, units) ….]
            },
            {
                "rel_path": relative path to upper rel_path
                "irods_id": iRODS database ID
                "metadata": [(key, val, units), (key, val, units) ….]
            },
            …
        ]
        "data_objects": [
            {
                "rel_path": relative path to upper rel_path
                "irods_id": iRODS database ID
                "checksum": <checksum>
                "metadata": [(key, val, units), (key, val, units) ….]
            },
            {
                "rel_path": relative path to upper rel_path
                "irods_id": iRODS database ID
                "checksum": <checksum>
                "metadata": [(key, val, units), (key, val, units) ….]
            },
            …
        ]
    }

    Parameters
    ----------
    meta:
        Metadata object to the collection or data object.
    session:
        Session for which the metadata is retrieved.
    recursive:
        Whether to also retrieve metadata for the sub collections (if applicable).
    keys:
        Select all entries that have a name within this list, other entries are discarded.
        If keys is None, then all metadata entries are selected.

    Raises
    ------
    ValueError:
        If the metadata object is not pointing to a collection or data object.

    Returns
    -------
        Dictionary containing the requested metadata items.

    """
    metadata_dict: dict[str, Any] = {
        "ibridges_metadata_version": "1.0",
        "recursive": recursive,
        "root_path": str(path),
        "collections": [],
        "data_objects": [],
    }
    depth = None if recursive else 0
    ipath = IrodsPath(session, path)
    if not recursive:
        add_to_metadict(metadata_dict, ipath, ipath)
    else:
        if not ipath.collection_exists():
            raise ValueError(f"Supply collection (which {ipath} is not) for recursive metadata "
                             "dictionary.")
        for subpath in ipath.walk(depth):
            add_to_metadict(metadata_dict, subpath, ipath)
    return metadata_dict


def set_metadata_from_dict(ipath: IrodsPath, session: Session, metadata_dict: dict):
    for item_data in metadata_dict["items"]:
        new_path = ipath / item_data["rel_path"]
        if not new_path.exists():
            raise ValueError("")
        meta = new_path.meta
        meta.from_dict(item_data["metadata"])
