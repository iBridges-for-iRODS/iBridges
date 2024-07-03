"""Exporting metadata."""

from __future__ import annotations

from typing import Any, Optional, Union

from ibridges.path import IrodsPath
from ibridges.session import Session


<<<<<<< HEAD
def export_metadata_to_dict(
    meta: MetaData, session: Session, recursive: bool = True, keys: Optional[list] = None
) -> dict:
=======
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
>>>>>>> 6ea7c07 (Add metadata to operations)
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
<<<<<<< HEAD
    metadata_dict: dict[str, Any] = {"ibridges_metadata_version": 1.0}
    metadata_dict.update(meta.to_dict(keys=keys))
    if is_dataobject(meta.item):
        return metadata_dict
    if is_collection(meta.item):
        if recursive is True:
            objects, collections = _get_meta_from_irods_tree(
                session, meta.item, root=meta.item.path
            )
            metadata_dict["subcollections"] = collections
            metadata_dict["dataobjects"] = objects
            return metadata_dict
        return metadata_dict
    raise ValueError("Not a data collection or data object: {item}")


def _get_meta_from_irods_tree(
    session: Session, coll: iRODSCollection, root: Optional[Union[str, IrodsPath]] = None
) -> tuple[list[dict], list[dict]]:
    """Recursively gather the metadata for all subcollections and data objects."""
    if root is not None:
        root_path = IrodsPath(session, root)
=======
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
>>>>>>> 6ea7c07 (Add metadata to operations)
    else:
        if not ipath.collection_exists():
            raise ValueError(f"Supply collection (which {ipath} is not) for recursive metadata "
                             "dictionary.")
        for subpath in ipath.walk(depth):
            add_to_metadict(metadata_dict, subpath, ipath)
    return metadata_dict

<<<<<<< HEAD
    objects = [
        {
            "name": o.name,
            "irods_id": o.id,
            "checksum": o.checksum,
            "rel_path": "/".join(IrodsPath(session, o.path).parts[len(root_path.parts) :]),
            "metadata": MetaData(o).to_dict()["metadata"],
        }
        for o in coll.data_objects
    ]
    collections = [
        {
            "name": c.name,
            "irods_id": c.id,
            "rel_path": "/".join(IrodsPath(session, c.path).parts[len(root_path.parts) :]),
            "metadata": MetaData(c).to_dict()["metadata"],
        }
        for c in coll.subcollections
    ]
    if len(coll.subcollections) > 0:
        for subcoll in coll.subcollections:
            subobjects, subcollections = _get_meta_from_irods_tree(session, subcoll, root_path)
            objects.extend(subobjects)
            collections.extend(subcollections)
    else:
        collections = []
=======
>>>>>>> 6ea7c07 (Add metadata to operations)

def set_metadata_from_dict(ipath: IrodsPath, session: Session, metadata_dict: dict):
    for item_data in metadata_dict["collections"] + metadata_dict["data_objects"]:
        new_path = ipath / item_data["rel_path"]
        if not new_path.exists():
            raise ValueError("")
        meta = new_path.meta
        meta.from_dict(item_data["metadata"])
        print("set", new_path, item_data["metadata"])
