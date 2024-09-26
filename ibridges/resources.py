"""resource operations."""

from __future__ import annotations

from typing import Optional

import irods.exception
import irods.resource

from ibridges import icat_columns as icat
from ibridges.session import Session


class Resources:
    """iRODS Resource operations.

    On many systems, the selection and management of resources
    is done completely server side. In this case, the user will not need
    to worry about using the Resources class.

    Parameters
    ----------
    session : Session
        Instance of the Session class

    """

    def __init__(self, session: Session):
        """iRODS resource initialization."""  # noqa: D403
        self._resources: Optional[dict] = None
        self.session = session

    def get_resource(self, resc_name: str) -> irods.resource.iRODSResource:
        """Instantiate an iRODS resource.

        Prameters
        ---------
        resc_name : str
            Name of the iRODS resource.

        Returns
        -------
        iRODSResource
            Instance of the resource with `resc_name`.

        Raises
        ------
        irods.exception.ResourceDoesNotExist:
            If the resource does not exist.

        """
        return self.session.irods_session.resources.get(resc_name)

    def get_free_space(self, resc_name: str) -> int:
        """Determine free space in a resource hierarchy.

        Parameters
        ----------
        resc_name:
            Name of monolithic resource or the top of a resource tree.

        Returns
        -------
            Number of bytes free in the resource hierarchy.
            On some iRODS servers, the server does not report the available storage space,
            but instead will return: -1 if the resource does not exists (typo or otherwise), or
            0 if no free space has been set in the whole resource tree starting at node resc_name.

        """
        try:
            resc = self.session.irods_session.resources.get(resc_name)
        except irods.exception.ResourceDoesNotExist:
            return -1
        if resc.free_space is not None:
            return int(resc.free_space)
        children = self.get_resource_children(resc)
        free_space = sum(
            (int(child.free_space) for child in children if child.free_space is not None)
        )
        return free_space

    def get_resource_children(self, resc: irods.resource.iRODSResource) -> list:
        """Get all the children for the resource `resc`.

        Parameters
        ----------
        resc:
            iRODS resource instance.

        Returns
        -------
            Instances of child resources.

        """
        children = []
        for child in resc.children:
            children.extend(self.get_resource_children(child))
        return resc.children + children

    def resources(self, update: bool = False) -> dict:
        """iRODS resources and their metadata.

        Parameters
        ----------
        update
            Fetch information from iRODS server and overwrite _resources

        Returns
        -------
            Name, parent, status, context, and free_space of all
            resources.

        NOTE: free_space of a resource is the free_space annotated, if
              so annotated, otherwise it is the sum of the free_space of
              all its children.

        """  # noqa: D403
        if self._resources is None or update:
            query = self.session.irods_session.query(
                icat.RESC_NAME, icat.RESC_PARENT, icat.RESC_STATUS, icat.RESC_CONTEXT
            )
            resc_list = []
            for item in query.get_results():
                name, parent, status, context = item.values()
                if name == "bundleResc":
                    continue
                free_space = 0
                if parent is None:
                    free_space = self.get_free_space(name)
                metadata = {
                    "parent": parent,
                    "status": status,
                    "context": context,
                    "free_space": free_space,
                }
                resc_list.append((name, metadata))
            resc_dict = dict(sorted(resc_list, key=lambda item: str.casefold(item[0])))
            self._resources = resc_dict
        return self._resources

    @property
    def root_resources(self) -> list[tuple]:
        """Filter resources for all root resources.

        Data can only be written to root resources.
        Return their names, their status and their free space.

        Returns
        -------
        List  containing [(resource_name, status, free_space, context)]

        """
        parents = [(key, val) for key, val in self.resources().items() if not val["parent"]]
        return [
            (resc[0], resc[1]["status"], resc[1]["free_space"], resc[1]["context"])
            for resc in parents
        ]
