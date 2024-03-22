"""Exporting metadata.
"""
from __future__ import annotations

from typing import Optional, Union
from irods.collection import iRODSCollection

from ibridges.data_operations import is_collection, is_dataobject
from ibridges.meta import MetaData
from ibridges.path import IrodsPath
from ibridges.session import Session

def export_metadata_to_dict(meta: MetaData, session: Session,
                            recursive: bool = True, keys: Optional[list] = None) -> dict:
    """Retrieves the metadata of the item and brings it into dict form.
    If the item is a collection all metadata from all subcollections
    and data objects will also be exported.

    {
        "name": name
        "irods_id": iRODS database ID
        "metadata": [(key, val, units), (key, val, units) ….]
        "collections”: [ # only if collection and recursive == True
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
        "data_objects":[ # only if collection and recurisve == True
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
    """
    metadata_dict = {"ibridges_metadata_version": 1.0}
    metadata_dict.update(meta.to_dict(keys = keys))
    if is_dataobject(meta.item):
        return metadata_dict
    if is_collection(meta.item):
        if recursive is True:
            objects, collections = get_meta_from_irods_tree(session, meta.item,
                                                            root = meta.item.path)
            metadata_dict["subcollections"] = collections
            metadata_dict["dataobjects"] = objects
            return metadata_dict
        return metadata_dict
    raise ValueError("Not a data collection or data object: {item}")

def get_meta_from_irods_tree(session: Session, coll: iRODSCollection,
                             root: Optional[Union[str, IrodsPath]] = None):
    """Recursively gather the metadata for all subcollections and data objects.
    """
    if root is not None:
        root_path = IrodsPath(session, root)
    else:
        root_path = IrodsPath(session, coll.path)

    objects = [{'name': o.name, 'irods_id': o.id, 'checksum': o.checksum,
                'rel_path': '/'.join(IrodsPath(session, 
                                               o.path).parts[len(root_path.parts):]),
                'metadata': MetaData(o).to_dict()['metadata']}
                for o in coll.data_objects
               ]
    collections = [{'name': c.name, 'irods_id': c.id,
                    'rel_path': '/'.join(IrodsPath(session,
                                               c.path).parts[len(root_path.parts):]),
                    'metadata': MetaData(c).to_dict()['metadata']}
                    for c in coll.subcollections]
    if len(coll.subcollections) > 0:
        for subcoll in coll.subcollections:
            subobjects, subcollections = get_meta_from_irods_tree(session, subcoll, root_path)
            objects.extend(subobjects)
            collections.extend(subcollections)
    else:
        collections = []

    return objects, collections
