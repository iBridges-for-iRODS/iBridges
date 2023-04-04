""" resource operations
"""
import logging

import irods.exception
import irods.session
import irods.resource

from . import keywords as kw
from . import session
import utils

context = utils.context.Context()
IENV = context.irods_environment


class FreeSpaceNotSet(Exception):
    """Custom Exception for when free_space iRODS parameter missing.

    """


class NotEnoughFreeSpace(Exception):
    """Custom Exception for when the reported free_space is too low.

    """


class Resource(object):
    """Irods Resource operations """
    _resources = None

    def __init__(self, sess_man: session.Session):
        """ iRODS resource initialization

            Parameters
            ----------
            sess_man : irods session
                instance of the Session class
        """
        self.sess_man = sess_man

    @property
    def resources(self) -> dict:
        """iRODS resources metadata.

        Parameters
        ----------

        Returns
        -------
        dict
            Name, parent, status, context, and free_space of all
            resources.

        NOTE: free_space of a resource is the free_space annotated, if
              so annotated, otherwise it is the sum of the free_space of
              all its children.

        """
        if self._resources is None:
            query = self.sess_man.session.query(
                kw.RESC_NAME, kw.RESC_PARENT, kw.RESC_STATUS, kw.RESC_CONTEXT)
            resc_list = []
            for item in query.get_results():
                name, parent, status, context_ = item.values()
                free_space = 0
                if parent is None:
                    free_space = self.get_free_space(name, multiplier=kw.MULTIPLIER)
                metadata = {
                    'parent': parent,
                    'status': status,
                    'context': context_,
                    'free_space': free_space,
                }
                resc_list.append((name, metadata))
            resc_dict = dict(
                sorted(resc_list, key=lambda item: str.casefold(item[0])))
            self._resources = resc_dict
            # Check for inclusion of default resource.
            resc_names = []
            for name, metadata in self._resources.items():
                context_ = metadata['context']
                if context_ is not None:
                    for kvp in context_.split(';'):
                        if 'write' in kvp:
                            _, val = kvp.split('=')
                            if float(val) == 0.0:
                                continue
                status = metadata['status']
                if status is not None:
                    if 'down' in status:
                        continue
                if metadata['parent'] is None and metadata['free_space'] > 0:
                    resc_names.append(name)
            if self.sess_man.default_resc not in resc_names:
                print('    -=WARNING=-    '*4)
                print(f'The default resource ({self.sess_man.default_resc}) not found in available resources!')
                print('Check "irods_default_resource" and "force_unknown_free_space" settings.')
                print('    -=WARNING=-    '*4)
        return self._resources

    def list_resources(self, attr_names: list = None) -> tuple:
        """Discover all writable root resources available in the current
        system producing 2 lists by default, one with resource names and
        another the value of the free_space annotation.  The parent,
        status, and context values are also available.  When the
        force_unknown_free_space option is set, it returns all root
        resources. A value of 0 indicates no free space annotated.

        Parameters
        ----------
        attr_names : list
            Names of resource attributes to assemble.

        Returns
        -------
        tuple
            Discovered names of writable root resources: (names,
            free_space).

        """
        if not attr_names:
            attr_names = ['name', 'free_space']
        vals, spaces = [], []
        for name, metadata in self.resources.items():
            # Add name to dictionary for convenience.
            metadata['name'] = name
            # Resource is writable?
            _context = metadata['context']
            if _context is not None:
                for kvp in _context.split(';'):
                    if 'write' in kvp:
                        _, val = kvp.split('=')
                        if float(val) == 0.0:
                            continue
            # Resource is up?
            status = metadata['status']
            if status is not None:
                if 'down' in status:
                    continue
            # Is a root resource?
            if metadata['parent'] is None:
                vals.append([metadata.get(attr) for attr in attr_names])
                spaces.append(metadata['free_space'])
        if not IENV.get('force_unknown_free_space', False):
            # Filter for free space annotated resources.
            vals = [val for val, space in zip(vals, spaces) if space != 0]
        return tuple(zip(*vals)) if vals else ([],) * len(attr_names)

    def get_resource(self, resc_name: str) -> irods.resource.Resource:
        """Instantiate an iRODS resource.

        Prameters
        ---------
        resc_name : str
            Name of the iRODS resource.

        Returns
        -------
        iRODSResource
            Instance of the resource with `resc_name`.

        Raises:
            irods.exception.ResourceDoesNotExist

        """
        try:
            return self.sess_man.session.resources.get(resc_name)
        except irods.exception.ResourceDoesNotExist as rdne:
            print(f'Resource with name {resc_name} not found')
            raise rdne

    def resource_space(self, resc_name: str) -> int:
        """Find the available space left on a resource in bytes.

        Parameters
        ----------
        resc_name : str
            Name of an iRODS resource.

        Returns
        -------
        int
            Number of bytes in `resc_name`.

        Throws: ResourceDoesNotExist if resource not known
                FreeSpaceNotSet if 'free_space' not set

        """
        space = self.resources[resc_name]['free_space']
        if space == -1:
            logging.info(
                'RESOURCE ERROR: Resource %s does not exist (typo?).',
                resc_name, exc_info=True)
            raise irods.exception.ResourceDoesNotExist(
                f'RESOURCE ERROR: Resource {resc_name} does not exist (typo?).')
        if space == 0:
            logging.info(
                'RESOURCE ERROR: Resource "free_space" is not set for %s.',
                resc_name, exc_info=True)
            raise FreeSpaceNotSet(
                f'RESOURCE ERROR: Resource "free_space" is not set for {resc_name}.')
        # For convenience, free_space is stored multiplied by MULTIPLIER.
        return int(space / kw.MULTIPLIER)

    def get_free_space(self, resc_name: str, multiplier: int = 1) -> int:
        """Determine free space in a resource hierarchy.

        If the specified resource name has the free space annotated,
        then report that.  If not, search for any resources in the tree
        that have the free space annotated and report the sum all those
        values.

        Parameters
        ----------
        resc_name : str
            Name of monolithic resource or the top of a resource tree.
        multiplier : int
            Factor to convert to desired units (e.g., 1 / 2**30 for
            GiB or 1 / 10**9 for GB).

        Returns
        -------
        int
            Number of bytes free in the resource hierarchy.

        The return can have one of two possible values if not the actual
        free space:

            -1 if the resource does not exists (typo or otherwise)
             0 if the no free space has been annotated in the specified
               resource tree

        """
        try:
            resc = self.sess_man.session.resources.get(resc_name)
        except irods.exception.ResourceDoesNotExist:
            print(f'Resource with name {resc_name} not found')
            return -1
        if resc.free_space is not None:
            return round(int(resc.free_space) * multiplier)
        children = self.get_resource_children(resc)
        free_space = sum((
            int(child.free_space) for child in children
            if child.free_space is not None))
        return round(free_space * multiplier)

    def get_resource_children(self, resc: irods.resource.Resource) -> list:
        """Get all the children for the resource `resc`.

        Parameters
        ----------
        resc : instance
            iRODS resource instance.

        Returns
        -------
        list
            Instances of child resources.

        """
        children = []
        for child in resc.children:
            children.extend(self.get_resource_children(child))
        return resc.children + children
