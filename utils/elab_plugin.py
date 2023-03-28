import logging
from utils.elabConnector import elabConnector

class ElabPlugin():

    def setup(self, calling_class):

        config = calling_class.get_config('ELN')

        if not config:
            logging.info('Skipping ELN (no config)')
            return

        self.elab = elabConnector(config['token'])

        if 'group' in config and 'experiment' in config \
            and len(config['group']) > 0 and len(config['experiment']) > 0:
            try:
                self.elab.updateMetadataUrl(group=config['group'], experiment=config['experiment'])
            except Exception:
                logging.error(f"ELN groupID {config['group']} or experimentID {config['experiment']} not set or valid.")
                self.elab.showGroups()
                self.elab.updateMetadataUrlInteractive(group=True)
        else:
            self.elab.showGroups()
            self.elab.updateMetadataUrlInteractive(group=True)

        # TODO: while loop to ensure title? : is it actually mandatory? maybe lose interactivity altogether.
        if not 'title' in config or len(config['title']) == 0:
            self.title = input('ELN paragraph title: ')
        else:
            self.title = config['title']

        logging.info('Link Data to experiment: ')
        logging.info(self.elab.metadataUrl)
        logging.info(f'with title: {self.title}')

        calling_class.target_path = f"{calling_class.irods_path}/{self.elab.__name__}/{str(self.elab.group.index[0])}/{str(self.elab.experiment.id())}"

    def annotate(self, calling_class):

        if not self.elab:
            return
       
        irods_conn = calling_class.irods_conn
        coll = irods_conn.get_collection(calling_class.target_path)

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

        self.elab.addMetadata(url=url, meta=annotation, title=self.title)

        # if os.path.isfile(source):
        #     item = irods_conn.get_dataobject(f"{coll.path}/{os.path.basename(source)}")
        #     irods_conn.add_metadata([item], 'ELN', elab.metadataUrl)
        # elif os.path.isdir(source):
        #     uploaded_coll = irods_conn.get_collection(f"{coll.path}/{os.path.basename(source)}")
        #     items = [uploaded_coll]
        #     for this_coll, _, objs in uploaded_coll.walk():
        #         items.append(this_coll)
        #         items.extend(objs)

        #     irods_conn.add_metadata(items, 'ELN', elab.metadataUrl)


