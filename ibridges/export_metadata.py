from ibridges.data_operations import is_collection, is_dataobject
from ibridges.data_operations import get_collection, get_dataobject
from ibridges.data_operations import _get_data_objects
from ibridges.meta import MetaData

from ibridges import keywords as kw
from ibridges.session import Session

def obj_meta_to_dict(meta: MetaData, keys: Optional[list] = None) -> dict:
    """Returns the metadata of an object as a dictionary. Adds the checksum
    {"checksum": <checksum>
     "metadata": [(key1, value1, units1), (key2, value2, units2) ...]
    }
    """
    meta = {}
    meta["checksum"] = self.item.checksum
    if keys is None:
        meta["Metadata"] = [(m.name, m.value, m.units) for m in self]
    else:
        meta["Metadata"] = [(m.name, m.value, m.units) for m in self if m.name in keys]
    return meta

def coll_meta_to_dict(meta: MetaData, keys: Optional[list] = None) -> dict:
    """Returns the metadata of an object as a dictionary.
    {
     "metadata": [(key1, value1, units1), (key2, value2, units2) ...]
    }
    """
    meta = {}
    if keys is None:
        meta["Metadata"] = [(m.name, m.value, m.units) for m in self]
    else:
        meta["Metadata"] = [(m.name, m.value, m.units) for m in self if m.name in keys]
    return meta
def to_dict(meta: MetaData, session: Session, 
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
    meta_dict = {"rel_path": self.item.name}
    if is_dataobject(self.item):
        meta_dict.update(self.obj_meta_to_dict(keys = keys))
        return meta_dict
    elif is_collection(self.item):
        meta_dict.update(self.coll_meta_to_dict(keys = keys))
        if recursive == True:
            # get all data objects and their metadata
            objs = [get_dataobject(session, path+'/'+name)
                    for path, name, _, _ in _get_data_objects(session, coll)]

            print("collection")
        else:
            return meta_dict
    else:
        raise ValueError("Not a data collection or data object: {item}")
