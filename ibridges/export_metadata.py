from ibridges.data_operations import is_collection, is_dataobject
from ibridges.data_operations import get_collection, get_dataobject
from ibridges.meta import MetaData
from ibridges.path import IrodsPath

from ibridges import keywords as kw
from ibridges.session import Session
from typing import Optional

def export_metadata_to_dict(meta: MetaData, session: Session, 
            recursive: bool = True, keys: Optional[list] = None) -> dict:
    """Retrieves the metadata of the item and brings it into dict form.
    If the item is a collection all metadata from all subcollections
    and data objects will also be exported.

    {
        "rel_path": name
        "checksum": <checksum if data object>
        "metadata": [(key, val, units), (key, val, units) ….]
        "collections”: [ # only if collection and recursive == True
            {
                "rel_path": relative path to upper rel_path
                "metadata": [(key, val, units), (key, val, units) ….]
            },
            {
                "rel_path": relative path to upper rel_path
                "metadata": [(key, val, units), (key, val, units) ….]
            },
            …
        ]
        "data_objects":[ # only if collection and recurisve == True
            {
                "rel_path": relative path to upper rel_path
                "checksum": <checksum>
                "metadata": [(key, val, units), (key, val, units) ….]
            },
            {
                "rel_path": relative path to upper rel_path
                "checksum": <checksum>
                "metadata": [(key, val, units), (key, val, units) ….]
            },
            …
        ]
    }
    """
    if is_dataobject(meta.item):
        return meta.to_dict(keys = keys)
    elif is_collection(meta.item):
        metadata_dict = meta.to_dict(keys = keys)
        if recursive == True:
            objects, collections = get_subcolls(session, meta.item, root = meta.item.path) 
            metadata_dict["subcollections"] = collections
            metadata_dict["dataobjects"] = objects
            return metadata_dict
        else:
            return metadata_dict
    else:
        raise ValueError("Not a data collection or data object: {item}")

def get_subcolls(session, coll, root: Optional[IrodsPath] = None):
    if root is not None:
        coll_path = IrodsPath(session, root)
    else:
        coll_path = IrodsPath(session, coll.path)
    objects = [{'name': o.name, 'irods_id': o.id,
                'rel_path': '/'.join(IrodsPath(session, 
                                               o.path).parts[len(coll_path.parts):]),
                'metadata': MetaData(o).to_dict()}
                for o in coll.data_objects
               ]
    collections = [{'name': c.name, 'irods_id': c.id,
                    'rel_path': '/'.join(IrodsPath(session,
                                               c.path).parts[len(coll_path.parts):]),
                    'metadata': MetaData(c).to_dict()}
                    for c in coll.subcollections]
    if len(coll.subcollections) > 0:
        for subcoll in coll.subcollections:
            subobjects, subcollections = get_subcolls(session, subcoll, coll_path)
            objects.extend(subobjects)
            collections.extend(subcollections)
    else:
        collections = []

    return objects, collections

