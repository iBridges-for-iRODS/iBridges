""" metadata operations
"""
import irods.exception
import irods.meta
import irodsConnector.keywords as kw


class Meta(object):
    """Irods metadata operations """
    def add_metadata(self, items: list, key: str, value: str, units: str = None):
        """
        Adds metadata to all items
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
                print(kw.RED+"INFO ADD META: Metadata already present"+kw.DEFAULT)
            except irods.exception.CAT_NO_ACCESS_PERMISSION as cnap:
                print("ERROR UPDATE META: no permissions")
                raise cnap

    def add_multiple_metadata(self, items, avus):
        """
        Adds multiple metadata fields to all items
        """
        list_of_tags = [
            irods.meta.AVUOperation(operation='add',
                                    avu=irods.meta.iRODSMeta(a, v, u))
            for (a, v, u) in avus]
        for item in items:
            try:
                item.metadata.apply_atomic_operations(*list_of_tags)
            except irods.meta.BadAVUOperationValue:
                print(f"{kw.RED}INFO ADD MULTIPLE META: bad metadata value{kw.DEFAULT}")
            except irods.exception.CAT_NO_ACCESS_PERMISSION as cnap:
                print("ERROR UPDATE META: no permissions")
                raise cnap
            except Exception:
                print(f"{kw.RED}INFO ADD MULTIPLE META: unexpected error{kw.DEFAULT}")      

    def update_metadata(self, items, key, value, units=None):
        """
        Updates a metadata entry to all items
        items: list of iRODS data objects or iRODS collections
        key: string
        value: string
        units: (optional) string

        Throws: CAT_NO_ACCESS_PERMISSION
        """
        try:
            for item in items:
                if key in item.metadata.keys():
                    meta = item.metadata.get_all(key)
                    valuesUnits = [(m.value, m.units) for m in meta]
                    if (value, units) not in valuesUnits:
                        # Remove all iCAT entries with that key
                        for m in meta:
                            item.metadata.remove(m)
                        # Add key, value, units
                        self.add_metadata(items, key, value, units)

                else:
                    self.add_metadata(items, key, value, units)
        except irods.exception.CAT_NO_ACCESS_PERMISSION as cnap:
            print(f"ERROR UPDATE META: no permissions {item.path}")
            raise cnap

    def delete_metadata(self, items, key, value, units):
        """
        Deletes a metadata entry of all items
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
                print(kw.RED+"INFO DELETE META: Metadata never existed"+kw.DEFAULT)
            except irods.exception.CAT_NO_ACCESS_PERMISSION as cnap:
                print("ERROR UPDATE META: no permissions "+item.path)
                raise cnap
