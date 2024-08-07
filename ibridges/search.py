"""Search for data and metadata on the iRODS server."""

from __future__ import annotations

from typing import Optional, Union

from ibridges import icat_columns as icat
from ibridges.path import IrodsPath
from ibridges.session import Session


def search_data(
    session: Session,
    path: Optional[Union[str, IrodsPath]] = None,
    path_pattern: Optional[str] = None,
    checksum: Optional[str] = None,
    key: Union[list[str], str, ..., None] = ...,
    value: Union[list[str], str, ..., None] = ...,
    units: Union[list[str], str, ..., None] = ...,
) -> list[dict]:
    """Search for collections, data objects and metadata.

    By default all accessible collections and data objects are returned.
    It is also possible to find items with specific metadata, using wild cards.
    The wildcard used in the iRODS universe is `%`, not `*`.

    Parameters
    ----------
    session:
        Session to search with.
    path:
        IrodsPath to the collection to search into, collection itself will not be considered.
        By default the home collection is searched.
    path_pattern:
        Search pattern in the path to look for. Allows for the '%' wildcard.
        For example, use '%.txt' to look for all txt data objects.
    checksum:
        Checksum of the dataobject, wildcard '%' can be used. If left out, no checksum will be
        matched.
    key:
        Metadata key that the data object or collection should contain. Can be either a string
        or a list of strings. In the latter case, all keys have to be present for that item.
    value:
        Metadata value that the data object or collection should contain.
    units:
        Metadata units that the data object or collection should contain.

    Raises
    ------
    ValueError:
        If no search criterium is supplied.

    Returns
    -------
        List of dictionaries with keys:
        COLL_NAME (absolute path of the collection),
        DATA_NAME (name of the data object),
        D_DATA_CHECKSUM (checksum of the data object)
        The latter two keys are only present of the found item is a data object.

    Examples
    --------
    >>> # Find data objects and collections
    >>> search_data(session, "/path/to/sub/col", path_pattern="somefile.txt")

    >>> # Find data ending with .txt
    >>> search_data(session, path_pattern="%.txt")
    >>> search_data(session, path_pattern="sub/%.txt")

    >>> # Find all data objects with a specific checksum in the home collection
    >>> search_data(session, checksum="sha2:wW+wG+JxwHmE1uXEvRJQxA2nEpVJLRY2bu1KqW1mqEQ=")
    [IrodsPath(/, somefile.txt), IrodsPath(/, someother.txt)]

    >>> # Checksums can have wildcards as well, but beware of collisions:
    >>> search_data(session, checksum="wW+wG%")
    [IrodsPath(/, somefile.txt), IrodsPath(/, someother.txt)]

    >>> # Find data objects and collections with some metadata key
    >>> search_data(session, key="some_key")
    >>> search_data(session, key=["some_key", "other_key"])

    >>> # Find data from metadata values
    >>> search_data(session, value="some_value")

    >>> # Find data using metadata units
    >>> search_data(session, units="kg")

    >>> # Different conditions can be combined, only items for which all is True will be returned
    >>> search_data(session, path="%.txt", key="some_key", units="kg")

    >>> # Find data without units
    >>> search_data(session, units=None)


    """
    if path_pattern is None and checksum is None and key is ... and value is ... and units is ...:
        raise ValueError(
            "QUERY: Error while searching in the metadata: No query criteria set."
            + " Please supply either a path_pattern, checksum, key, value or units."
        )

    # create the query for collections; we only want to return the collection name
    coll_query = session.irods_session.query(icat.COLL_NAME)
    # create the query for data objects; we need the collection name, the data name and its checksum
    data_query = session.irods_session.query(icat.COLL_NAME, icat.DATA_NAME, icat.DATA_CHECKSUM)
    data_name_query = session.irods_session.query(icat.COLL_NAME, icat.DATA_NAME, icat.DATA_CHECKSUM)

    # iRODS queries do not know the 'or' operator, so we need three searches
    # One for the collection, and two for the data
    # one data search in case path is a collection path and we want to retrieve all data there
    # one in case the path is or ends with a file name
    if path is None:
        path = session.home
    path = IrodsPath(session, path)

    # Filter only paths according to the search path.
    coll_query = coll_query.filter(icat.LIKE(icat.COLL_NAME, f"{path}/%"))
    data_query = data_query.filter(icat.LIKE(icat.COLL_NAME, f"{path}/%"))
    data_name_query.filter(icat.LIKE(icat.COLL_NAME, f"{path}"))
    queries = [coll_query, data_query, data_name_query]

    if path_pattern is not None:
        _path_filter(path, path_pattern, *queries)

    if key is not ...:
        if isinstance(key, str):
            _key_filter(key, *queries)
        else:
            for sub_key in key:
                _key_filter(sub_key, *queries)

    if value is not ...:
        if isinstance(value, str):
            _value_filter(value, *queries)
        else:
            for sub_val in value:
                _value_filter(sub_val, *queries)

    if units is not ...:
        if isinstance(units, str):
            _units_filter(units, *queries)
        else:
            for sub_units in units:
                _units_filter(sub_units, *queries)

    results = []
    if checksum is not None:
        if not checksum.startswith("sha2:"):
            checksum = f"sha2:{checksum}"
        data_query = data_query.filter(icat.LIKE(icat.DATA_CHECKSUM, checksum))
        data_name_query.filter(icat.LIKE(icat.DATA_CHECKSUM, checksum))
    else:
        # Gather collection results (not needed if checksum is used).
        results = list(coll_query.get_results())


    # gather results, data_query and data_name_query can contain the same results
    results.extend([
        dict(s) for s in set(frozenset(d.items())
                for d in list(data_query) + list(data_name_query))
    ])
    for item in results:
        if isinstance(item, dict):
            new_keys = [k.icat_key for k in item.keys()]
            for n_key, o_key in zip(new_keys, item.keys()):
                item[n_key] = item.pop(o_key)

    # Convert the results to IrodsPath objects.
    ipath_results = []
    for res in results:
        if "DATA_NAME" in res:
            ipath_results.append(IrodsPath(session, res["COLL_NAME"], res["DATA_NAME"]))
        else:
            ipath_results.append(IrodsPath(session, res["COLL_NAME"]))
    return ipath_results


def _prefix_wildcard(pattern):
    if pattern.startswith("%"):
        return pattern
    return f"%/{pattern}"

def _path_filter(root_path, path_pattern, coll_query, data_query, data_name_query):
    coll_query.filter(icat.LIKE(icat.COLL_NAME, _prefix_wildcard(path_pattern)))
    split_pat = path_pattern.rsplit("/", maxsplit=1)
    data_query.filter(icat.LIKE(icat.DATA_NAME, split_pat[-1]))
    data_name_query.filter(icat.LIKE(icat.DATA_NAME, split_pat[-1]))

    if len(split_pat) == 2:
        data_query.filter(icat.LIKE(icat.COLL_NAME, _prefix_wildcard(split_pat[0])))
        data_name_query.filter(icat.LIKE(icat.COLL_NAME, _prefix_wildcard(split_pat[0])))


def _key_filter(key, *queries):
    for q in queries:
        q.filter(icat.LIKE(icat.META_DATA_ATTR_NAME, key))


def _value_filter(value, *queries):
    for q in queries:
        q.filter(icat.LIKE(icat.META_DATA_ATTR_VALUE, value))

def _units_filter(units, *queries):
    for q in queries:
        q.filter(icat.LIKE(icat.META_DATA_ATTR_UNITS, units))
