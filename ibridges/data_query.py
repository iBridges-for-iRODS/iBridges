from typing import Optional

from ibridges.irodsconnector import keywords as kw
from ibridges import Session


def data_query(session: Session, path: Optional[str] = None, checksum: Optional[str] = None, 
               key_vals: Optional[dict] = {}) -> list[tuple[str, str, str]]:
    """Retrieves all collections and data objects (the absolute collection path, 
    data object or collection name) to the given user-defined and system metadata.
    By Default all accessible collections and data objects will be returned.
    Wildcard: %

    Parameters
    ----------
    path: str
        (Partial) path
    checksum: str
        (Partial) checksum
    key_vals : dict
        Attribute name mapping to values.

    Returns
    -------
    list: [(Collection name, Object name, checksum)]

    """
    if path is None and checksum is None and key_vals == {}:
        raise ValueError("QUERY DATA: No query criteria set.")

    coll_query = session.irods_session.query(kw.COLL_NAME)
    data_query = session.irods_session.query(kw.COLL_NAME, kw.DATA_NAME,
                                             kw.DATA_CHECKSUM)
    return_coll = True

    if path:
        coll_query = coll_query.filter(kw.LIKE(kw.COLL_NAME, path))
        data_query = data_query.filter(kw.LIKE(kw.COLL_NAME, path))
    for key in key_vals:
        data_query.filter(kw.LIKE(kw.META_DATA_ATTR_NAME, key))
        coll_query.filter(kw.LIKE(kw.META_COLL_ATTR_NAME, key))
        if key_vals[key]:
            data_query.filter(kw.LIKE(kw.META_DATA_ATTR_VALUE, key_vals[key]))
            coll_query.filter(kw.LIKE(kw.META_COLL_ATTR_VALUE, key_vals[key]))
    if checksum:
        data_query = data_query.filter(kw.LIKE(kw.DATA_CHECKSUM, checksum))
        return_coll == False
    # gather results
    results = [tuple(res.values()) for res in data_query.get_results()]
    if return_coll:
        results.extend([tuple((list(res.values())[0], '', ''))
                        for res in coll_query.get_results()])

    return results
