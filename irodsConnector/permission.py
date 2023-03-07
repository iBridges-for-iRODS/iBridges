

class Permission(object):


    @property
    def permissions(self):
        """iRODS permissions mapping.

        Returns
        -------
        dict
            Correct permissions mapping for the current server version.

        """
        if self._permissions is None:
            self._permissions = {
                'null': 'none',
                'read_object': 'read',
                'modify_object': 'write',
                'own': 'own',
            }
            if self.session.server_version < (4, 3, 0):
                self._permissions.update(
                    {'read object': 'read', 'modify object': 'write'})
        return self._permissions

    def get_permissions(self, path='', obj=None):
        """Discover ACLs for an iRODS collection expressed as a `path`
        or an `obj`ect.

        Parameters
        ----------
        path : str
            Logical iRODS path of a collection or data object.
        obj : iRODSCollection, iRODSDataObject
            Instance of an iRODS collection or data object.

        Returns
        -------
        list
            iRODS ACL instances.

        """
        logging.info('GET PERMISSIONS')
        if isinstance(path, str) and path:
            try:
                return self.session.permissions.get(
                    self.session.collections.get(path))
            except irods.exception.CollectionDoesNotExist:
                return self.session.permissions.get(
                    self.session.data_objects.get(path))
        if self.is_dataobject_or_collection(obj):
            return self.session.permissions.get(obj)
        print('WARNING -- `obj` must be or `path` must resolve into, a collection or data object')
        return []

    def set_permissions(self, perm, path, user='', zone='', recursive=False, admin=False):
        """Set permissions (ACL) for an iRODS collection or data object.

        Parameters
        ----------
        perm : str
            Name of permission string: own, read, write, or null.
        path : str
            Name of iRODS logical path.
        user : str
            Name of user.
        zone : str
            Name of user's zone.
        recursive : bool
            Apply ACL to all children of `path`.
        admin : bool
            If a 'rodsadmin' apply ACL for another user.

        """
        acl = irods.access.iRODSAccess(perm, path, user, zone)
        try:
            if self.dataobject_exists(path) or self.collection_exists(path):
                self.session.permissions.set(acl, recursive=recursive, admin=admin)
        except irods.exception.CAT_INVALID_USER as ciu:
            print(f'{RED}ACL ERROR: user unknown{DEFAULT}')
            raise ciu
        except irods.exception.CAT_INVALID_ARGUMENT as cia:
            print(f'{RED}ACL ERROR: permission {perm} or path {path} not known{DEFAULT}')
            logging.info(
                'ACL ERROR: permission %s or path %s not known',
                perm, path, exc_info=True)
            raise cia