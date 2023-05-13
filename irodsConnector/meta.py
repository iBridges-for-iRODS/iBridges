""" metadata operations
"""
import logging

import irods.exception
import irods.meta

from . import keywords as kw


class Meta(object):
    """Irods metadata operations """
    def add(self, items: list, key: str, value: str, units: str = None):
        """
        Adds metadata to all items

        Parameters
        ----------
        items: list of iRODS data objects or iRODS collections
        key: string
        value: string
        units: (optional) string

        Throws:
            CATALOG_ALREADY_HAS_ITEM_BY_THAT_NAME
        """
        for item in items:
            try:
                item.metadata.add(key.upper(), value, units)
            except irods.exception.CATALOG_ALREADY_HAS_ITEM_BY_THAT_NAME:
                logging.error('%sADD META: Metadata already present%s', kw.RED, kw.DEFAULT)
            except irods.exception.CAT_NO_ACCESS_PERMISSION as cnap:
                logging.error('UPDATE META: no permissions')
                raise cnap

    def add_multiple(self, items: list, avus: list):
        """
        Adds multiple metadata fields to all items

        Parameters
        ----------
        items: list of iRODS data objects or iRODS collections
        avus: list of a,v,u triplets
        """
        list_of_tags = [
            irods.meta.AVUOperation(operation='add',
                                    avu=irods.meta.iRODSMeta(a, v, u))
            for (a, v, u) in avus]
        for item in items:
            try:
                item.metadata.apply_atomic_operations(*list_of_tags)
            except irods.meta.BadAVUOperationValue:
                logging.error('%sADD MULTIPLE META: bad metadata value%s', kw.RED, kw.DEFAULT)
            except irods.exception.CAT_NO_ACCESS_PERMISSION as cnap:
                logging.error("UPDATE META: no permissions")
                raise cnap
            except Exception:
                logging.error('%sADD MULTIPLE META: unexpected error%s', kw.RED, kw.DEFAULT)

    def update(self, items: list, key: str, value: str, units: str = None):
        """
        Updates a metadata entry to all items

        Parameters
        ----------
        items: list of iRODS data objects or iRODS collections
        key: string
        value: string
        units: (optional) string

        Throws: CAT_NO_ACCESS_PERMISSION
        """
        try:
            for item in items:
                if key in item.metadata.keys():
                    metas = item.metadata.get_all(key)
                    value_units = [(m.value, m.units) for m in metas]
                    if (value, units) not in value_units:
                        # Remove all iCAT entries with that key
                        for meta in metas:
                            item.metadata.remove(meta)
                        # Add key, value, units
                        self.add(items, key, value, units)

                else:
                    self.add(items, key, value, units)
        except irods.exception.CAT_NO_ACCESS_PERMISSION as cnap:
            logging.error('UPDATE META: no permissions %s', item.path)
            raise cnap

    def delete(self, items: list, key: str, value: str, units: str = None):
        """
        Deletes a metadata entry of all items

        Parameters
        ----------
        items: list of iRODS data objects or iRODS collections
        key: string
        value: string
        units: (optional) string

        Throws:
            CAT_SUCCESS_BUT_WITH_NO_INFO: metadata did not exist
        """
        for item in items:
            try:
                item.metadata.remove(key, value, units)
            except irods.exception.CAT_SUCCESS_BUT_WITH_NO_INFO:
                logging.error('%sDELETE META: Metadata never existed%s', kw.RED, kw.DEFAULT)
            except irods.exception.CAT_NO_ACCESS_PERMISSION as cnap:
                logging.error('UPDATE META: no permissions %s', item.path)
                raise cnap
