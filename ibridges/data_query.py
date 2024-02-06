from typing import Optional

from ibridges.irodsconnector import keywords as kw
from ibridges import Session


def data_query(session: Session, path: Optional[str] = None, checksum: Optional[str] = None, 
               key_vals: Optional[dict] = None) -> list:
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
    list: [[Collection name, Object name, checksum]]

    """
    coll_query = None
    data_query = None
    
    if checksum:
        # data query
        data_query = self.sess_man.irods_session.query(kw.COLL_NAME, kw.DATA_NAME, 
                                                       kw.DATA_CHECKSUM)
        data_query = data_query.filter(kw.LIKE(kw.DATA_CHECKSUM, checksum))
    else:
        # data query and coll query
        coll_query = self.sess_man.irods_session.query(kw.COLL_NAME)
        data_query = self.sess_man.irods_session.query(
            kw.COLL_NAME, kw.DATA_NAME, kw.DATA_CHECKSUM)

    if path:
        if coll_query:
            coll_query = coll_query.filter(kw.LIKE(kw.COLL_NAME, path))
        data_query = data_query.filter(kw.LIKE(kw.COLL_NAME, path))
    for key in key_vals:
        data_query.filter(kw.LIKE(kw.META_DATA_ATTR_NAME, key))
        if coll_query:
            coll_query.filter(kw.LIKE(kw.META_COLL_ATTR_NAME, key))
        if key_vals[key]:
            data_query.filter(kw.LIKE(kw.META_DATA_ATTR_VALUE, key_vals[key]))
            if coll_query:
                coll_query.filter(kw.LIKE(kw.META_COLL_ATTR_VALUE == key_vals[key]))
    # gather results
    results = [res for res in data_query.get_results()]
    if coll_query:
        results.extend([res for res in coll_query.get_results()])

    return results
