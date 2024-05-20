"""Data query."""
from __future__ import annotations

from typing import Optional, Union

from ibridges import icat_columns as icat
from ibridges.path import IrodsPath
from ibridges.session import Session


def search_data(session: Session, path: Optional[Union[str, IrodsPath]] = None,
           checksum: Optional[str] = None, key_vals: Optional[dict] = None) -> list[dict]:
    """Retrieve all collections and data objects.

    (the absolute collection path,
    data object or collection name) to the given user-defined and system metadata.
    By Default all accessible collections and data objects will be returned.
    Wildcard: %

    Parameters
    ----------
    session:
        Session to search with.
    path: str
        (Partial) path or IrodsPath
    checksum: str
        (Partial) checksum
    key_vals : dict
        Attribute name mapping to values.

    Raises
    ------
    ValueError:
        If no search criterium is supplied.

    Returns
    -------
    list: [dict]
        List of dictionaries with keys:
        COLL_NAME (absolute path of the collection),
        DATA_NAME (name of the data object),
        D_DATA_CHECKSUM (checksum of the data object)
        The latter two keys are only present of the found item is a data object.

    """
    if path is None and checksum is None and key_vals is None:
        raise ValueError(
                "QUERY: Error while searching in the metadata: No query criteria set." \
                        + " Please supply either a path, checksum or key_vals.")

    # create the query for collections; we only want to return the collection name
    coll_query = session.irods_session.query(icat.COLL_NAME)
    # create the query for data objects; we need the collection name, the data name and its checksum
    data_query = session.irods_session.query(icat.COLL_NAME, icat.DATA_NAME,
                                             icat.DATA_CHECKSUM)
    data_name_query = session.irods_session.query(icat.COLL_NAME, icat.DATA_NAME,
                                                  icat.DATA_CHECKSUM)
    # iRODS queries do not know the 'or' operator, so we need three searches
    # One for the collection, and two for the data
    # one data search in case path is a collection path and we want to retrieve all data there
    # one in case the path is or ends with a file name
    if path:
        path = str(path)
        coll_query = coll_query.filter(icat.LIKE(icat.COLL_NAME, path))
        data_query = data_query.filter(icat.LIKE(icat.COLL_NAME, path))
        potential_data_name = path if '/' not in path else path.split("/")[-1]
        data_name_query = data_name_query.filter(icat.LIKE(icat.DATA_NAME, potential_data_name))
    if key_vals:
        for key in key_vals:
            data_query.filter(icat.LIKE(icat.META_DATA_ATTR_NAME, key))
            coll_query.filter(icat.LIKE(icat.META_COLL_ATTR_NAME, key))
            data_name_query.filter(icat.LIKE(icat.META_DATA_ATTR_NAME, key))
            if key_vals[key]:
                data_query.filter(icat.LIKE(icat.META_DATA_ATTR_VALUE, key_vals[key]))
                coll_query.filter(icat.LIKE(icat.META_COLL_ATTR_VALUE, key_vals[key]))
                data_name_query = data_name_query.filter(
                                    icat.LIKE(icat.META_DATA_ATTR_VALUE, key_vals[key]))
    if checksum:
        data_query = data_query.filter(icat.LIKE(icat.DATA_CHECKSUM, checksum))
        data_name_query = data_name_query.filter(icat.LIKE(icat.DATA_CHECKSUM, checksum))
    # gather results
    results = list(data_query.get_results())+list(data_name_query.get_results())
    if checksum is None:
        coll_res = list(coll_query.get_results())
        if len(coll_res) > 0:
            results.extend(coll_res)

    for item in results:
        if isinstance(item, dict):
            new_keys = [k.icat_key for k in item.keys()]
            for n_key, o_key in zip(new_keys, item.keys()):
                item[n_key] = item.pop(o_key)

    return results
