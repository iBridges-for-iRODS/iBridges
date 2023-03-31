"""
Plugin for IBridgesCli for annotating eLab Journal.
"""

import logging
import os
from irods.exception import CollectionDoesNotExist, CAT_NO_ACCESS_PERMISSION
from utils.elabConnector import elabConnector


class ElabPlugin():
    """
    Clas containing functions called before and after upload to iRods.
    """

    def __init__(self) -> None:
        self.elab = None
        self.title = None

    def setup(self, calling_class):
        """
        Setup, called before upload to iRods.
        """
        config = calling_class.get_config('ELN')

        if not config:
            logging.info('Skipping ELN (no config)')
            return

        self.elab = elabConnector(config['token'])

        if 'group' in config and 'experiment' in config \
                and len(config['group']) > 0 and len(config['experiment']) > 0:
            try:
                self.elab.updateMetadataUrl(group=config['group'], experiment=config['experiment'])
            except ValueError as exception:
                logging.error("ELN groupID %s or experimentID %s not set or invalid. (%s)",
                              config['group'], config['experiment'], str(exception))
                self.elab.showGroups()
                self.elab.updateMetadataUrlInteractive(group=True)
        else:
            self.elab.showGroups()
            self.elab.updateMetadataUrlInteractive(group=True)

        if 'title' not in config or len(config['title']) == 0:
            self.title = input('ELN paragraph title: ')
        else:
            self.title = config['title']

        logging.info("Link Data to experiment: %s", self.elab.metadataUrl)
        logging.info("with title: %s", self.title)

        calling_class.target_path = f"{calling_class.irods_path}/{self.elab.__name__}/" + \
                                    f"{str(self.elab.group.index[0])}/{str(self.elab.experiment.id())}"

    def annotate(self, calling_class):
        """
        Setup, called after upload to iRods.
        """

        if not self.elab:
            return

        if not calling_class.upload_finished:
            logging.warning("Upload unsuccesful, aborting eLab annotation")
            return

        irods_conn = calling_class.irods_conn

        try:
            coll = irods_conn.get_collection(calling_class.target_path)
        except CollectionDoesNotExist as exception:
            logging.error("Could not get collection: %s (%s)", calling_class.target_path, str(exception))
            return

        annotation = {
            "iRODS path": coll.path,
            "iRODS server": irods_conn.host,
            "iRODS user": irods_conn.username,
        }

        # YODA: webdav URL does not contain "home", but iRODS path does!
        if irods_conn.davrods and ("yoda" in irods_conn.host or "uu.nl" in irods_conn.host):
            url = f"{irods_conn.davrods}/{coll.path.split('home/')[1].strip()}"
        elif irods_conn.davrods and "surfsara.nl" in irods_conn.host:
            url = f"{irods_conn.davrods}/{coll.path.split(irods_conn.zone)[1].strip('/')}"
        elif irods_conn.davrods:
            url = f"{irods_conn.davrods}/{coll.path.strip('/')}"
        else:
            url = '{' + "\n".join([irods_conn.host, irods_conn.zone,
                                   irods_conn.username, str(irods_conn.port), coll.path]) + '}'

        try:
            self.elab.addMetadata(url=url, meta=annotation, title=self.title)
        except ValueError as exception:
            logging.error("Could not add eLab-metadata: %s", str(exception))

        try:
            if os.path.isfile(calling_class.local_path):
                item = irods_conn.get_dataobject(f"{coll.path}/{os.path.basename(calling_class.local_path)}")
                irods_conn.add_metadata([item], 'ELN', self.elab.metadataUrl)
            elif os.path.isdir(calling_class.local_path):
                uploaded_coll = irods_conn.get_collection(f"{coll.path}/{os.path.basename(calling_class.local_path)}")
                items = [uploaded_coll]
                for this_coll, _, objs in uploaded_coll.walk():
                    items.append(this_coll)
                    items.extend(objs)

                irods_conn.add_metadata(items, 'ELN', self.elab.metadataUrl)
        except CAT_NO_ACCESS_PERMISSION as exception:
            logging.error("Could not add iRods-metadata: %s", str(exception))
