"""Operations to directly manipulate metadata on the iRODS server."""

from __future__ import annotations

import re
import warnings
from typing import Any, Iterator, Optional, Sequence, Union

import irods
import irods.exception
import irods.meta


def _parse_tuple(key, value, units = ""):
    if key == "":
        raise ValueError("Key cannot be of size zero.")
    if not isinstance(key, (str, bytes)):
        raise TypeError(f"Key should have type str or bytes-like, not {type(key)}.")
    if value == "":
        raise ValueError("Value cannot be of size zero.")
    if not isinstance(value, (str, bytes)):
        raise TypeError(f"Value should have type str or bytes-like, not {type(value)}.")
    if not isinstance(units, (str, bytes, type(None))):
        raise TypeError(f"Key should have type str, bytes-like or None, not {type(units)}.")

class MetaData:
    """iRODS metadata operations.

    This allows for adding and deleting of metadata entries for data objects
    and collections.

    Parameters
    ----------
    item:
        The data object or collection to attach the metadata object to.
    blacklist:
        A regular expression for metadata names/keys that should be ignored.
        By default all metadata starting with `org_` is ignored.


    Examples
    --------
    >>> meta = MetaData(coll)
    >>> "Author" in meta
    True
    >>> for entry in meta:
    >>>     print(entry.key, entry.value, entry.units)
    Author Ben
    Mass 10 kg
    >>> len(meta)
    2
    >>> meta.add("Author", "Emma")
    >>> meta.set("Author", "Alice")
    >>> meta.delete("Author")
    >>> print(meta)
    {Mass, 10, kg}

    """

    def __init__(
        self,
        item: Union[irods.data_object.iRODSDataObject, irods.collection.iRODSCollection],
        blacklist: Optional[str] = r"^org_[\s\S]+",
    ):
        """Initialize the metadata object."""
        self.item = item
        self.blacklist = blacklist

    def __iter__(self) -> Iterator:
        """Iterate over all metadata key/value/units triplets."""
        for meta in self.item.metadata.items():
            if not self.blacklist or re.match(self.blacklist, meta.name) is None:
                yield MetaDataItem(self, meta)
            else:
                warnings.warn(
                    f"Ignoring metadata entry with key {meta.name}, because it matches "
                    f"the blacklist {self.blacklist}."
                )

    def __len__(self) -> int:
        """Get the number of non-blacklisted metadata entries."""
        return len([x for x in self])  # pylint: disable=unnecessary-comprehension

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
        search_pattern = _pad_search_pattern(val)
        if len(self.find_all(*search_pattern)) > 0:
            return True
        return False

    def __repr__(self) -> str:
        """Create a sorted representation of the metadata."""
        return f"MetaData<{self.item.path}>"

    def __str__(self) -> str:
        """Return a string showing all metadata entries."""
        # Sort the list of items name -> value -> units, where None is the lowest
        meta_list = sorted(list(self))
        return "\n".join(f" - {meta}" for meta in meta_list)

    def find_all(self, key=..., value=..., units=...):
        """Find all metadata entries belonging to the data object/collection.

        Wildcards can be used by leaving the key/value/units at default.
        """
        all_items = []
        for meta_item in self:
            if meta_item.matches(key, value, units):
                all_items.append(meta_item)
        return all_items

    def __getitem__(self, key: Union[str, Sequence[Union[str, None]]]) -> MetaDataItem:
        """Access the metadata like a dictionary of tuples.

        Parameters
        ----------
        key
            The key to get all metadata for.

        Raises
        ------
        KeyError
            If the key does not exist.


        Examples
        --------
        >>> meta["some_key"]
        ("some_key", "some_value", "some_units")
        >>> meta["some_key", "some_value"]
        >>> meta["some_key", "some_value", "some_units"]

        """
        search_pattern = _pad_search_pattern(key)
        all_items = self.find_all(*search_pattern)
        if len(all_items) == 0:
            raise KeyError(f"Cannot find metadata item with key '{key}'.")
        if len(all_items) > 1:
            raise ValueError(
                f"Found multiple items with key '{key}', specify value and "
                "units as well, for example: meta[key, value, units]."
            )
        return all_items[0]

    def __setitem__(self, key: Union[str, Sequence[str]],
                    other: Union[str, Sequence[str], Sequence[Sequence[str]]]):
        """Set metadata items like a dictionary of tuples.

        Parameters
        ----------
        key
            The key to get the metadata for.
        other
            Key, value, units to set the metadata item to. Units is optional.

        Raises
        ------
        TypeError:
            If the other parameter is a string.
        ValueError:
            If the item already exists.

        Examples
        --------
        >>> meta["key"] = "values"
        >>> meta["key"] = "values", "units"
        >>> meta["key", "value"] = "units"

        """
        if isinstance(other, str):
            other = [other]
        if isinstance(key, str):
            key = [key]

        if len(key) > 2:
            raise ValueError("Use either one or two values within the brackets [], for example "
                             f"meta['some_key', 'some_value'] = 'some_units', got: {key}")

        all_items = self.find_all(*key)
        if all(isinstance(o, str) for o in other):
            if len(all_items) > 1:
                raise ValueError(f"Cannot set item with '{key}' to single item: multiple entries"
                                 f" exist. Use meta[{key}] = [{other}] to remove all current values"
                                 f" with new values.")
            other = [other]  # type: ignore
        for subset in other:
            if not all(isinstance(s, str) for s in subset):
                raise ValueError(
                    "Badly formed argument to __setitem__: should be set to either string,"
                    " list of strings or list of list of strings.")
            if len(subset) + len(key) > 3:
                raise ValueError(
                    f"Too many items to create metadata triple {subset} + {key}. Use "
                    "meta['key'] = 'value', 'units' or meta['key', 'value'] = 'units'.")

        for item in all_items:
            item.remove()

        for sub in other:
            self.add(*key, *sub)

    def add(self, key: str, value: str, units: Optional[str] = ""):
        """Add metadata to an item.

        This will never overwrite an existing entry. If the triplet already exists
        it will throw an error instead. Note that entries are only considered the same
        if all of the key, value and units are the same.

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
        _parse_tuple(key, value, units)
        try:
            if (key, value, units) in self:
                raise ValueError("ADD META: Metadata already present")
            if self.blacklist:
                try:
                    if re.match(self.blacklist, key):
                        raise ValueError(f"ADD META: Key must not start with {self.blacklist}.")
                except TypeError as error:
                    raise TypeError(
                            f"Key {key} must be of type string, found {type(key)}") from error
            self.item.metadata.add(key, value, units)
        except irods.exception.CAT_NO_ACCESS_PERMISSION as error:
            raise PermissionError("UPDATE META: no permissions") from error

    def set(self, key: str, value: str, units: Optional[str] = ""):
        """Set the metadata entry.

        If the metadata entry already exists, then all metadata entries with
        the same key will be deleted before adding the new entry. An alternative
        is using the :meth:`add` method to only add to the metadata entries and not
        delete them.

        This method is deprecated, and will be removed in the future. You should use
        the bracket [] notation instead: meta[key] = value or meta[key] = value, units.

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
        warnings.warn("The 'set' method is deprecated and will be removed in iBridges 2.0. "
                      f"You can mimick the old behavior with meta.delete('{key}'); "
                      f"meta.add('{key}', '{value}', '{units}')",
                      DeprecationWarning, stacklevel=2)
        self.delete(key)
        self.add(key, value, units)

    def delete(
        self,
        key: str,
        value: Union[None, str] = ...,  # type: ignore
        units: Union[None, str] = ...,  # type: ignore
    ):
        """Delete a metadata entry of an item.

        Parameters
        ----------
        key:
            Key of the new entry to add to the item.
        value:
            Value of the new entry to add to the item. If the Ellipsis value [...] is used,
            then all entries with this value will be deleted.
        units:
            The units of the new entry. If the Elipsis value [...] is used, then all entries
            with any units will be deleted (but still constrained to the supplied keys and values).

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
        all_meta_items = self.find_all(key, value, units)
        if len(all_meta_items) == 0:
            raise KeyError(
                f"Cannot delete items with key='{key}', value='{value}' and units='{units}', "
                "since no metadata entries exist with those values."
            )
        for meta_item in all_meta_items:
            meta_item.remove()

    def clear(self):
        """Delete all metadata entries belonging to the item.

        Only entries that are on the blacklist are not deleted.

        Examples
        --------
        >>> meta.add("Ben", "10", "kg")
        >>> print(meta)
        - {name: Ben, value: 10, units: kg}
        >>> metadata.clear()
        >>> print(len(meta))  # empty
        0

        Raises
        ------
        PermissionError:
            If the user has insufficient permissions to delete the metadata.

        """
        self.refresh()
        for meta in self:
            self.item.metadata.remove(meta)

    def to_dict(self, keys: Optional[list] = None) -> dict:
        """Convert iRODS metadata (AVUs) and system information to a python dictionary.

        This dictionary can later be used to restore the metadata to an iRODS object with
        the :meth:`from_dict` method.

        Examples
        --------
        >>> meta.to_dict()
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
        if isinstance(self.item, irods.data_object.iRODSDataObject):
            meta_dict["checksum"] = self.item.checksum
        if keys is None:
            meta_dict["metadata"] = [tuple(m) for m in self]
        else:
            meta_dict["metadata"] = [tuple(m) for m in self if m.key in keys]
        return meta_dict

    def from_dict(self, meta_dict: dict):
        """Fill the metadata based on a dictionary.

        The dictionary that is expected can be generated from the :meth:`to_dict` method.

        Parameters
        ----------
        meta_dict
            Dictionary that contains all the key, value, units triples. This
            should use the same format as the output of the to_dict method.

        Examples
        --------
        >>> meta.add("Ben", "10", "kg")
        >>> meta_dict = meta.to_dict()
        >>> meta.clear()
        >>> len(meta)
        0
        >>> meta.from_dict(meta_dict)
        >>> print(meta)
        - {name: Ben, value: 10, units: kg}

        """
        for meta_tuple in meta_dict["metadata"]:
            try:
                self.add(*meta_tuple)
            except ValueError:
                pass

    def refresh(self):
        """Refresh the metadata of the item.

        This is only necessary if the metadata has been modified by another session.
        """
        if isinstance(self.item, irods.collection.iRODSCollection):
            self.item = self.item.manager.sess.collections.get(self.item.path)
        else:
            self.item = self.item.manager.sess.data_objects.get(self.item.path)


class MetaDataItem:
    """Interface for metadata entries.

    This is a substitute of the python-irodsclient iRODSMeta object.
    It implements setting the key/value/units, allows for sorting and can
    remove itself.

    This class is generally created by the MetaData class, not directly
    created by the user.

    Parameters
    ----------
    ibridges_meta:
        A MetaData object that the MetaDataItem is part of.
    prc_meta:
        A PRC iRODSMeta object that points to the entry.

    """

    def __init__(self, ibridges_meta: MetaData, prc_meta: irods.iRODSMeta):
        """Initialize the MetaDataItem object."""
        self._ibridges_meta = ibridges_meta
        self._prc_meta: irods.iRODSMeta = prc_meta

    @property
    def key(self) -> str:
        """Return the key of the metadata item."""
        return self._prc_meta.name

    @key.setter
    def key(self, new_key: str):
        if new_key == self._prc_meta.name:
            return
        new_item_values = [new_key, self._prc_meta.value, self._prc_meta.units]
        self.update(*new_item_values)

    @property
    def value(self) -> Optional[str]:
        """Return the value of the metadata item."""
        return self._prc_meta.value

    @value.setter
    def value(self, new_value: Optional[str]):
        if new_value == self._prc_meta.value:
            return
        new_item_values = [self._prc_meta.name, new_value, self._prc_meta.units]
        self.update(*new_item_values)

    @property
    def units(self) -> str:
        """Return the units of the metadata item."""
        return "" if self._prc_meta.units is None else self._prc_meta.units

    @units.setter
    def units(self, new_units: Optional[str]):
        if new_units == self._prc_meta.units:
            return
        new_item_values = [self._prc_meta.name, self._prc_meta.value, new_units]
        self.update(*new_item_values)

    def __repr__(self) -> str:
        """Representation of the MetaDataItem."""
        return f"<MetaDataItem ({self.key}, {self.value}, {self.units})>"

    def __str__(self) -> str:
        """User readable representation of MetaDataItem."""
        return f"(key: '{self.key}', value: '{self.value}', units: '{self.units}')"

    def __iter__(self) -> Iterator[Optional[str]]:
        """Allow iteration over key, value, units."""
        yield self.key
        yield self.value
        yield self.units

    def update(self, new_key: str, new_value: str, new_units: str = ""):
        """Update the metadata item changing the key/value/units.

        Parameters
        ----------
        new_key:
            New key to set the metadata item to.
        new_value:
            New value to set the metadata item to.
        new_units:
            New units to set the metadata item to, optional.

        Raises
        ------
        ValueError:
            If the operation could not be completed because of permission error.
            Or if the new to be created item already exists.

        """
        new_item_key = (new_key, new_value, new_units)
        try:
            _new_item = self._ibridges_meta[new_item_key]
        except KeyError:
            self._ibridges_meta.add(*new_item_key)
            try:
                self._ibridges_meta.item.metadata.remove(self._prc_meta)
            # If we get an error, roll back the added metadata
            except irods.exception.CAT_NO_ACCESS_PERMISSION as error:
                self._ibridges_meta.delete(*new_item_key)
                raise ValueError(
                    f"Cannot rename metadata due to insufficient permission "
                    f"for path '{self.item.path}'."
                ) from error
            self._prc_meta = self._ibridges_meta[new_item_key]._prc_meta  # pylint: disable=protected-access
        else:
            raise ValueError(
                f"Cannot change key/value/units to '{new_item_key}' metadata item "
                "already exists."
            )

    def __getattribute__(self, attr: str):
        """Add name attribute and check if the metadata item is already removed."""
        if attr == "name":
            return self.__getattribute__("key")
        if attr == "_prc_meta" and super().__getattribute__(attr) is None:
            raise KeyError("Cannot remove metadata item: it has already been removed.")
        return super().__getattribute__(attr)

    def remove(self):
        """Remove the metadata item."""
        try:
            self._ibridges_meta.item.metadata.remove(self._prc_meta)
        except irods.exception.CAT_SUCCESS_BUT_WITH_NO_INFO as error:
            raise KeyError(
                f"Cannot delete metadata with key '{self.key}', value '{self.value}'"
                f" and units '{self.units}' since it does not exist."
            ) from error
        except irods.exception.CAT_NO_ACCESS_PERMISSION as error:
            raise ValueError(
                f"Cannot delete metadata due to insufficient permission "
                f"for path '{self.item.path}'."
            ) from error
        self._prc_meta = None

    def __lt__(self, other: MetaDataItem) -> bool:
        """Compare two metadata items for sorting mainly."""
        if not isinstance(other, MetaDataItem):
            raise TypeError(f"Comparison between MetaDataItem and {type(other)} not supported.")
        comp_key = _comp_str_none(self.key, other.key)
        if comp_key is not None:
            return comp_key
        comp_value = _comp_str_none(self.value, other.value)
        if comp_value is not None:
            return comp_value
        comp_units = _comp_str_none(self.units, other.units)
        if comp_units is not True:
            return False
        return True

    def matches(self, key, value, units):
        """See whether the metadata item matches the key,value,units pattern."""
        units = "" if units is None else units
        if key is not ... and key != self.key:
            return False
        if value is not ... and value != self.value:
            return False
        if units is not ... and units != self.units:
            return False
        return True


def _comp_str_none(obj: Optional[str], other: Optional[str]) -> Optional[bool]:
    if obj is None and other is not None:
        return True
    if obj is not None and other is None:
        return False
    if str(obj) == str(other):
        return None
    return str(obj) < str(other)


def _pad_search_pattern(search_pattern) -> tuple:
    if isinstance(search_pattern, str):
        padded_pattern = (search_pattern, ..., ...)
    elif len(search_pattern) == 1:
        padded_pattern = (*search_pattern, ..., ...) # type: ignore
    elif len(search_pattern) == 2:
        padded_pattern = (*search_pattern, ...) # type: ignore
    elif len(search_pattern) > 3:
        raise ValueError("Too many arguments for '[]', use key, value, units.")
    else:
        padded_pattern = tuple(search_pattern) # type: ignore
    return padded_pattern
