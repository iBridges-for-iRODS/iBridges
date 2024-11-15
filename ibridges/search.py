"""Search for data and metadata on the iRODS server."""

from __future__ import annotations

from collections import namedtuple
from typing import List, Optional, Union

from ibridges import icat_columns as icat
from ibridges.path import CachedIrodsPath, IrodsPath
from ibridges.session import Session

META_COLS = {
    "collection": (icat.META_COLL_ATTR_NAME, icat.META_COLL_ATTR_VALUE, icat.META_COLL_ATTR_UNITS),
    "data_object": (icat.META_DATA_ATTR_NAME, icat.META_DATA_ATTR_VALUE, icat.META_DATA_ATTR_UNITS),
}


class MetaSearch(namedtuple("MetaSearch", ["key", "value", "units"], defaults=[..., ..., ...])):
    """Named tuple to search for objects and collections.

    The key, value and units default to the elipsis (...), which indicate that the search
    accepts anything for this slot. This is principally the same as using the iRODS wildcard
    '%' symbol except that during creation using elipses for key, value and units will raise
    a ValueError. Note that the None value has a different meaning, where it will actually test
    for the entry being None/empty.
    """

    def __new__(cls, key=..., value=..., units=...):
        """Create a new MetaSearch object."""
        if key is ... and value is ... and units is ...:
            raise ValueError(
                "Cannot create metasearch without specifying either key, value or units."
            )
        key = "%" if key is ... else key
        value = "%" if value is ... else value
        units = "%" if units is ... else units
        return super(MetaSearch, cls).__new__(cls, key, value, units)


def search_data(  # pylint: disable=too-many-branches
    session: Session,
    path: Optional[Union[str, IrodsPath]] = None,
    path_pattern: Optional[str] = None,
    checksum: Optional[str] = None,
    metadata: Union[None, MetaSearch, list[MetaSearch], list[tuple]] = None,
    item_type: Optional[str] = None,
    case_sensitive: bool = False,
) -> list[CachedIrodsPath]:
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
    metadata:
        Metadata triples that constrain the key, value and units of the results.
        For example, to get only items having a metadata entry with value "x",
        use MetaSearch(value="x"). See :class:`MetaSearch` for more detail.
        You can also provide a list of constraints. Then each of these constrains
        will have to be satisfied for the data item to show up in the results.
    item_type:
        Type of the item to search for, by default None indicating both data objects and collections
        are returned. Set to "data_object" for data objects and "collection" for collections.
    case_sensitive:
        Case sensitive search for Paths and metadata. Default: False

    Raises
    ------
    ValueError:
        If no search criterium is supplied.

    Returns
    -------
        List of CachedIrodsPaths.
        The CachedIrodsPaths for data objects contain the size and the checksum
        found in the search.

    Examples
    --------
    >>> # Find data objects and collections
    >>> search_data(session, "/path/to/sub/col", path_pattern="somefile.txt")

    >>> # Find data ending with .txt in your home and on a collection path with the substring "sub"
    >>> search_data(session, path_pattern="%.txt")
    >>> search_data(session, path_pattern="%sub/%.txt")

    >>> # Find all data objects with a specific checksum in the home collection
    >>> search_data(session, checksum="sha2:wW+wG+JxwHmE1uXEvRJQxA2nEpVJLRY2bu1KqW1mqEQ=")
    [IrodsPath(/, somefile.txt), IrodsPath(/, someother.txt)]

    >>> # Checksums can have wildcards as well, but beware of collisions:
    >>> search_data(session, checksum="sha2:wW+wG%")
    [IrodsPath(/, somefile.txt), IrodsPath(/, someother.txt)]

    >>> # Find data objects and collections with some metadata key
    >>> search_data(session, metadata=MetaSearch(key="some_key"))

    >>> # Search for data labeled with several metadata constraints
    >>> search_data(session, metadata=[MetaSearch("some_key"), MetaSearch(value="other_value")]

    >>> # Find data from metadata values using the wildcard
    >>> # Will find all data and collections with e.g. "my_value" and "some_value"
    >>> search_data(session, metadata=MetaSearch(value="%_value"))

    >>> # Find data using metadata units
    >>> search_data(session, metadata=MetaSearch(units="kg"))

    >>> # Different conditions can be combined, only items for which all is True will be returned
    >>> search_data(session, path_pattern="%.txt", metadata=MetaSearch(key="some_key", units="kg")

    >>> # Find data without units
    >>> search_data(session, metadata=MetaSearch(units=None)

    >>> Find only data objects
    >>> search_data(session, path_pattern="x%", item_type="data_object")

    """
    # Input validation
    if path_pattern is None and checksum is None and metadata is None:
        raise ValueError(
            "QUERY: Error while searching in the metadata: No query criteria set."
            + " Please supply either a path_pattern, checksum, key, value or units."
        )
    if path is None:
        path = session.home
    path = IrodsPath(session, path)

    if metadata is None:
        metadata = []
    if isinstance(metadata, MetaSearch):
        metadata = [metadata]

    # iRODS queries do not know the 'or' operator, so we need three searches
    # One for the collection, and two for the data
    # one data search in case path is a collection path and we want to retrieve all data there
    # one in case the path is or ends with a file name
    queries = []
    if item_type != "data_object" and checksum is None:
        # create the query for collections; we only want to return the collection name
        coll_query = session.irods_session.query(icat.COLL_NAME, case_sensitive=case_sensitive)
        coll_query = coll_query.filter(icat.LIKE(icat.COLL_NAME, _postfix_wildcard(path)))
        queries.append((coll_query, "collection"))
    if item_type != "collection":
        # create the query for data objects; we need the collection name, the data name and checksum
        data_query = session.irods_session.query(
            icat.COLL_NAME,
            icat.DATA_NAME,
            icat.DATA_CHECKSUM,
            icat.DATA_SIZE,
            case_sensitive=case_sensitive,
        )
        data_query = data_query.filter(icat.LIKE(icat.COLL_NAME, _postfix_wildcard(path)))
        queries.append((data_query, "data_object"))

        data_name_query = session.irods_session.query(
            icat.COLL_NAME,
            icat.DATA_NAME,
            icat.DATA_CHECKSUM,
            icat.DATA_SIZE,
            case_sensitive=case_sensitive,
        )
        data_name_query.filter(icat.LIKE(icat.COLL_NAME, f"{path}"))
        queries.append((data_name_query, "data_object"))

    if path_pattern is not None:
        _path_filter(path_pattern, queries)

    for mf in metadata:
        _meta_filter(mf, queries)

    if checksum is not None:
        _checksum_filter(checksum, queries)

    query_results = []
    for q in queries:
        query_results.extend(list(q[0]))

    # gather results, data_query and data_name_query can contain the same results
    results = [dict(s) for s in set(frozenset(d.items()) for d in query_results)]
    for item in results:
        if isinstance(item, dict):
            for meta_key in list(item.keys()):
                item[meta_key.icat_key] = item.pop(meta_key)

    # Convert the results to IrodsPath objects.
    ipath_results: List[CachedIrodsPath] = []
    for res in results:
        if "DATA_NAME" in res:
            ipath_results.append(
                CachedIrodsPath(
                    session,
                    res["DATA_SIZE"],
                    True,
                    res["D_DATA_CHECKSUM"],
                    res["COLL_NAME"],
                    res["DATA_NAME"],
                )
            )
        else:
            ipath_results.append(CachedIrodsPath(session, None, False, None, res["COLL_NAME"]))
    return ipath_results


def _prefix_wildcard(pattern):
    if pattern.startswith("%"):
        return pattern
    return f"%/{pattern}"


def _postfix_wildcard(path):
    if str(path).endswith("/"):
        return f"{path}%"
    return f"{path}/%"


def _path_filter(path_pattern, queries):
    for q, q_type in queries:
        if q_type == "collection":
            q.filter(icat.LIKE(icat.COLL_NAME, _prefix_wildcard(path_pattern)))
        else:
            split_pat = path_pattern.rsplit("/", maxsplit=1)
            q.filter(icat.LIKE(icat.DATA_NAME, split_pat[-1]))

            if len(split_pat) == 2:
                q.filter(icat.LIKE(icat.COLL_NAME, _prefix_wildcard(split_pat[0])))


def _meta_filter(metadata, queries):
    if len(metadata) < 1 or len(metadata) > 3:
        raise ValueError(f"Metadata contraints need 1-3 values, not {len(metadata)}")
    for q, q_type in queries:
        for i_elem, elem in enumerate(MetaSearch(*metadata)):
            q.filter(icat.LIKE(META_COLS[q_type][i_elem], elem))


def _checksum_filter(checksum, queries):
    for q, q_type in queries:
        if q_type == "data_object":
            q.filter(icat.LIKE(icat.DATA_CHECKSUM, checksum))
