"""Exporting metadata."""

from __future__ import annotations

from ibridges.path import IrodsPath


def add_to_metadict(meta_dict: dict, ipath: IrodsPath, root_ipath: IrodsPath):
    """Add an item to the metadata dictionary.

    Parameters
    ----------
    meta_dict
        Dictionary to add the new item to.
    ipath
        IrodsPath to the item that the metadata is extracted from.
    root_ipath
        Root IrodsPath to which the relative path is calculated.

    """
    meta = ipath.meta
    if ipath.collection_exists():
        item_type = "collection"
    elif ipath.dataobject_exists():
        item_type = "data object"
    else:
        item_type = "unknown"

    new_metadata = {
        "rel_path": str(ipath.relative_to(root_ipath)),
        "type": item_type,
    }
    new_metadata.update(meta.to_dict())
    meta_dict["items"].append(new_metadata)


def empty_metadict(root_ipath: IrodsPath, recursive: bool = True) -> dict:
    """Create an empty dictionary to store the metadata in.

    Parameters
    ----------
    root_ipath
        IrodsPath that points to the root collection or dataobject.
    recursive, optional
        Whether the dictionary is built recursively, by default True

    Returns
    -------
        A dictionary for containing metadata with no items.

    """
    return {
        "ibridges_metadata_version": "1.0",
        "recursive": recursive,
        "root_path": str(root_ipath),
        "items": [],
    }

def set_metadata_from_dict(ipath: IrodsPath, metadata_dict: dict):
    """Set the metadata of an iRODS item from a dictionary.

    Parameters
    ----------
    ipath
        Path of the iRODS item for which the metadata is going to be set.
    metadata_dict
        Metadata to be set for the item.

    Raises
    ------
    ValueError
        When the irods path does not point to a data object or collection.

    """
    for item_data in metadata_dict["items"]:
        new_path = ipath / item_data["rel_path"]
        if not new_path.exists():
            raise ValueError(f"Path {new_path} for which there exists metadata does not exist "
                             "itself.")
        meta = new_path.meta
        meta.from_dict(item_data["metadata"])
