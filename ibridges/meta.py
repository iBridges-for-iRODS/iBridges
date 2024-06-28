"""metadata operations."""

from __future__ import annotations

from typing import Any, Iterator, Optional, Sequence, Union

import irods
import irods.exception
import irods.meta

from ibridges.util import is_dataobject


class MetaData:
    """Irods metadata operations.

    This allows for adding and deleting of metadata entries for data objects
    and collections.

    Examples
    --------
    >>> meta = MetaData(coll)
    >>> "Author" in meta
    True
    >>> for entry in meta:
    >>>     print(entry.key, entry.value, entry.units)
    Author Ben
    Mass 10 kg
    >>> meta.add("Author", "Emma")
    >>> meta.set("Author", "Alice")
    >>> meta.delete("Author")
    >>> print(meta)
    {Mass, 10, kg}

    """

    def __init__(
        self, item: Union[irods.data_object.iRODSDataObject, irods.collection.iRODSCollection]
    ):
        """Initialize the metadata object.

        Parameters
        ----------
        item
            The data object or collection to attach the metadata object to.

        """
        self.item = item

    def __iter__(self) -> Iterator:
        """Iterate over all metadata key/value/units pairs."""
        yield from self.item.metadata.items()

    def __contains__(self, val: Union[str, Sequence]) -> bool:
        """Check whether a key, key/val, key/val/units pairs are in the metadata.

        Returns
        -------
            True if key/val/unit pairs are present in the item.

        Examples
        --------
        >>> "Author" in meta
        True
        >>> ("Author", "Ben") in meta
        False
        >>> ("Release", "2000", "year") in meta
        True

        """
        if isinstance(val, str):
            val = [val]
        all_attrs = ["name", "value", "units"][: len(val)]
        for meta in self:
            n_same = 0
            for i_attr, attr in enumerate(all_attrs):
                if getattr(meta, attr) == val[i_attr] or val[i_attr] is None:
                    n_same += 1
                else:
                    break
            if n_same == len(val):
                return True
        return False

    def __repr__(self) -> str:
        """Create a sorted representation of the metadata."""
        return f"MetaData<{self.item.path}>"

    def __str__(self) -> str:
        """Return a string showing all metadata entries."""
        # Sort the list of items name -> value -> units, where None is the lowest
        meta_list = list(self)
        meta_list = sorted(meta_list, key=lambda m: (m.units is None, m.units))
        meta_list = sorted(meta_list, key=lambda m: (m.value is None, m.value))
        meta_list = sorted(meta_list, key=lambda m: (m.name is None, m.name))
        meta_str = ""
        for meta in meta_list:
            meta_str += f" - {{name: {meta.name}, value: {meta.value}, units: {meta.units}}}\n"
        return meta_str

    def add(self, key: str, value: str, units: Optional[str] = None):
        """Add metadata to an item.

        This will never overwrite an existing entry.

        Parameters
        ----------
        key:
            Key of the new entry to add to the item.
        value:
            Value of the new entry to add to the item.
        units:
            The units of the new entry.

        Raises
        ------
        ValueError:
            If the metadata already exists.
        PermissionError:
            If the metadata cannot be updated because the user does not have sufficient permissions.

        Examples
        --------
        >>> meta.add("Author", "Ben")
        >>> meta.add("Mass", "10", "kg")

        """
        try:
            if (key, value, units) in self:
                raise irods.exception.CATALOG_ALREADY_HAS_ITEM_BY_THAT_NAME()
            self.item.metadata.add(key, value, units)
        except irods.exception.CATALOG_ALREADY_HAS_ITEM_BY_THAT_NAME as error:
            raise ValueError("ADD META: Metadata already present") from error
        except irods.exception.CAT_NO_ACCESS_PERMISSION as error:
            raise PermissionError("UPDATE META: no permissions") from error

    def set(self, key: str, value: str, units: Optional[str] = None):
        """Set the metadata entry.

        If the metadata entry already exists, then all metadata entries with
        the same key will be deleted before adding the new entry. An alternative
        is using the add method to only add to the metadata entries and not
        delete them.

        Parameters
        ----------
        key:
            Key of the new entry to add to the item.
        value:
            Value of the new entry to add to the item.
        units:
            The units of the new entry.

        Raises
        ------
        PermissionError:
            If the user does not have sufficient permissions to set the metadata.

        Examples
        --------
        >>> meta.set("Author", "Ben")
        >>> meta.set("mass", "10", "kg")

        """
        self.delete(key, None)
        self.add(key, value, units)

    def delete(self, key: str, value: Optional[str], units: Optional[str] = None):
        """Delete a metadata entry of an item.

        Parameters
        ----------
        key:
            Key of the new entry to add to the item.
        value:
            Value of the new entry to add to the item.
        units:
            The units of the new entry.

        Raises
        ------
        KeyError:
            If the to be deleted key cannot be found.
        PermissionError:
            If the user has insufficient permissions to delete the metadata.

        Examples
        --------
        >>> # Delete the metadata entry with mass 10 kg
        >>> meta.delete("mass", "10", "kg")
        >>> # Delete all metadata with key mass  and value 10
        >>> meta.delete("mass", "10")
        >>> # Delete all metadata with the key mass
        >>> meta.delete("mass")

        """
        try:
            if value is None:
                metas = self.item.metadata.get_all(key)
                value_units = [(m.value, m.units) for m in metas]
                if (value, units) not in value_units:
                    for meta in metas:
                        self.item.metadata.remove(meta)
            else:
                self.item.metadata.remove(key, value, units)
        except irods.exception.CAT_SUCCESS_BUT_WITH_NO_INFO as error:
            raise KeyError(
                f"Cannot delete metadata with key '{key}', value '{value}'"
                f" and units '{units}' since it does not exist."
            ) from error
        except irods.exception.CAT_NO_ACCESS_PERMISSION as error:
            raise ValueError(
                "Cannot delete metadata due to insufficient permission for path '{item.path}'."
            ) from error

    def clear(self):
        """Delete all metadata belonging to the item.

        Raises
        ------
        PermissionError:
            If the user has insufficient permissions to delete the metadata.

        """
        for meta in self:
            self.item.metadata.remove(meta)

    def to_dict(self, keys: Optional[list] = None) -> dict:
        """Convert iRODS metadata (AVUs) and system information to a python dictionary.

        {
            "name": item.name,
            "irods_id": item.id, #iCAT database ID
             "checksum": item.checksum if the item is a data object
             "metadata": [(m.name, m.value, m.units)]
        }

        Parameters
        ----------
        keys:
            List of Attribute names which should be exported to "metadata".
            By default all will be exported.

        Returns
        -------
            Dictionary containing the metadata.

        """
        meta_dict: dict[str, Any] = {}
        meta_dict["name"] = self.item.name
        meta_dict["irods_id"] = self.item.id
        if is_dataobject(self.item):
            meta_dict["checksum"] = self.item.checksum
        if keys is None:
            meta_dict["metadata"] = [(m.name, m.value, m.units) for m in self]
        else:
            meta_dict["metadata"] = [(m.name, m.value, m.units) for m in self if m.name in keys]
        return meta_dict
