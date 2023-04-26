""" query operations
"""
from . import keywords as kw
from . import session


class Query(object):
    """Irods Query operations """

    def __init__(self, sess_man: session.Session):
        """ iRODS data operations initialization

            Parameters
            ----------
            sess_man : irods session
                instance of the Session class

        """
        self.sess_man = sess_man

    def search(self, key_vals: dict = None) -> list:
        """Given a dictionary with metadata attribute names as keys and
        associated values, query for collections and data objects that
        fullfill the criteria.  The key 'checksum' will be mapped to
        DataObject.checksum, the key 'path' will be mapped to
        Collection.name and the key 'object' will be mapped to
        DataObject.name:

        {
            'checksum': '',
            'key1': 'val1',
            'key2': 'val2',
            'path': '',
            'object': '',
        }

        By Default, if `key_vals` is empty, all accessible collections
        and data objects will be returned.

        Parameters
        ----------
        key_vals : dict
            Attribute name mapping to values.

        Returns
        -------
        list: [[Collection name, Object name, checksum]]

        """
        coll_query = None
        data_query = None
        # data query
        if 'checksum' in key_vals or 'object' in key_vals:
            data_query = self.sess_man.session.query(
                kw.COLL_NAME, kw.DATA_NAME, kw.DATA_CHECKSUM)
            if 'object' in key_vals:
                if key_vals['object']:
                    data_query = data_query.filter(
                        kw.LIKE(kw.DATA_NAME, key_vals['object']))
            if 'checksum' in key_vals:
                if key_vals['checksum']:
                    data_query = data_query.filter(kw.LIKE(
                        kw.DATA_CHECKSUM, key_vals['checksum']))
        else:
            coll_query = self.sess_man.session.query(kw.COLL_NAME)
            data_query = self.sess_man.session.query(
                kw.COLL_NAME, kw.DATA_NAME, kw.DATA_CHECKSUM)

        if 'path' in key_vals and key_vals['path']:
            if coll_query:
                coll_query = coll_query.filter(kw.LIKE(
                    kw.COLL_NAME, key_vals['path']))
            data_query = data_query.filter(kw.LIKE(
                kw.COLL_NAME, key_vals['path']))
        for key in key_vals:
            if key not in ['checksum', 'path', 'object']:
                if data_query:
                    data_query.filter(kw.META_DATA_ATTR_NAME == key)
                if coll_query:
                    coll_query.filter(kw.META_COLL_ATTR_NAME == key)
                if key_vals[key]:
                    if data_query:
                        data_query.filter(
                            kw.META_DATA_ATTR_VALUE == key_vals[key])
                    if coll_query:
                        coll_query.filter(
                            kw.META_COLL_ATTR_VALUE == key_vals[key])
        results = [['', '', ''], ['', '', ''], ['', '', '']]
        coll_batch = [[]]
        data_batch = [[]]
        # Return only 100 results.
        if coll_query:
            num_colls = len(list(coll_query))
            results[0] = [f'Collections found: {num_colls}', '', '']
            coll_batch = list(coll_query.get_batches())
        if data_query:
            num_objs = len(list(data_query))
            results[1] = [f'Objects found: {num_objs}', '', '']
            data_batch = list(data_query.get_batches())
        for res in coll_batch[0][:50]:
            results.append([res[list(res.keys())[0]], '', ''])
        for res in data_batch[0][:50]:
            results.append([res[list(res.keys())[0]],
                            res[list(res.keys())[1]],
                            res[list(res.keys())[2]]])
        return results
