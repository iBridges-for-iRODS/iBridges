"""IrodsConnector for iCommands
"""
import logging
import os
import shutil
from subprocess import call, Popen, PIPE
import irodsConnector.keywords as kw
from irodsConnector.resource import Resource
from irodsConnector.session import Session


class IrodsConnectorIcommands():
    """Connection to an iRODS server while using iCommands.

    """

    @staticmethod
    def icommands():
        """

        Returns
        -------
        bool
            Are the iCommands available?
        """
        return call(['which', 'iinit'], shell=True, stderr=PIPE) == 0

    def upload_data(self, ses_man: Session, res_man: Resource, source: str, destination: None, resource: str,
                    size: int, buff: int = kw.BUFF_SIZE, force: bool = False):
        """Upload files or folders to an iRODS collection.

        Parameters
        ----------
        ses_man : irods session
            Instance of the Session class
        source: str
            absolute path to file or folder
        destination: iRODS collection to upload to

        resource: str
            name of the iRODS storage resource to use
        size: int
            size of data to be uploaded in bytes
        buf: int
            buffer on resource that should be left over
        force: bool
            upload without checking the available space

        """
        logging.info('iRODS UPLOAD: %s --> %s, %s', source, str(destination), str(resource))
        if not force:
            try:
                space = res_man.resource_space(ses_man, resource)
                if int(size) > (int(space) - buff):
                    raise ValueError('ERROR iRODS upload: Not enough space on resource.')
                if buff < 0:
                    raise BufferError('ERROR iRODS upload: Negative resource buffer.')
            except Exception as error:
                logging.error(error)
                raise error

        if os.path.isfile(source):
            print('CREATE', destination.path + '/' + os.path.basename(source))
            ses_man.session.collections.create(destination.path)
            if resource:
                cmd = 'irsync -aK ' + source + ' i:' + destination.path + ' -R ' + resource
            else:
                cmd = 'irsync -aK ' + source + ' i:' + destination.path
        elif os.path.isdir(source):
            ses_man.session.collections.create(destination.path + '/' + os.path.basename(source))
            sub_coll = ses_man.session.collections.get(destination.path + '/' + os.path.basename(source))
            if resource:
                cmd = 'irsync -aKr ' + source + ' i:' + sub_coll.path + ' -R ' + resource
            else:
                cmd = 'irsync -aKr ' + source + ' i:' + sub_coll.path
        else:
            logging.info('UPLOAD ERROR', exc_info=True)
            raise FileNotFoundError('ERROR iRODS upload: not a valid source path')
        logging.info('IRODS UPLOAD: %s', cmd)
        p = Popen([cmd], stdout=PIPE, stdin=PIPE, stderr=PIPE, shell=True)
        out, err = p.communicate()
        logging.info('IRODS UPLOAD INFO: out:%s \nerr: %s', str(out), str(err))

    def download_data(self, ses_man: Session, source: None, destination: str,
                      size: int, buff: int = kw.BUFF_SIZE, force: bool = False):
        """Download object or collection.

        Parameters
        ----------
        ses_man : irods session
            Instance of the Session class
        source: iRODS collection or data object

        destination: str
            absolut path to download folder
        size: int
            size of data to be downloaded in bytes
        buff: int
            buffer on the filesystem that should be left over
        """
        logging.info('iRODS DOWNLOAD: %s --> %s', str(source), destination)
        destination = '/' + destination.strip('/')
        if not os.access(destination, os.W_OK):
            logging.info('IRODS DOWNLOAD: No rights to write to destination.')
            raise PermissionError('IRODS DOWNLOAD: No rights to write to destination.')
        if not os.path.isdir(destination):
            logging.info("IRODS DOWNLOAD: Path seems to be directory, but is file.")
            raise IsADirectoryError("IRODS DOWNLOAD: Path seems to be directory, but is file.")

        if not force:
            try:
                space = shutil.disk_usage(destination).free
                if int(size) > (int(space) - buff):
                    logging.info('ERROR iRODS download: Not enough space on disk.')
                    raise ValueError('ERROR iRODS download: Not enough space on disk.')
                if buff < 0:
                    logging.info('ERROR iRODS download: Negative disk buffer.')
                    raise BufferError('ERROR iRODS download: Negative disk buffer.')
            except Exception as error:
                logging.info('DOWNLOAD ERROR', exc_info=True)
                raise error

        if ses_man.session.data_objects.exists(source.path):
            cmd = 'irsync -K i:' + source.path + ' ' + destination + os.sep + os.path.basename(source.path)
        elif ses_man.session.collections.exists(source.path):
            cmd = 'irsync -Kr i:' + source.path + ' ' + destination + os.sep + os.path.basename(source.path)
        else:
            raise FileNotFoundError('IRODS download: not a valid source.')
        logging.info('IRODS DOWNLOAD: %s', cmd)
        pros = Popen([cmd], stdout=PIPE, stdin=PIPE, stderr=PIPE, shell=True)
        out, err = pros.communicate()
        logging.info('IRODS DOWNLOAD INFO: out:%s \nerr: %s', str(out), str(err))

    def irods_put(self, local_path: str, irods_path: str, resc_name: str = ''):
        """Upload `local_path` to `irods_path` following iRODS `options`.

        Parameters
        ----------
        ses_man : irods session
            Instance of the Session class
        local_path : str
            Path of local file or directory/folder.
        irods_path : str
            Path of iRODS data object or collection.
        resc_name : str
            Optional resource name.

        """
        commands = [f'iput -aK -N {kw.NUM_THREADS}']
        if resc_name:
            commands.append(f'-R {resc_name}')
        commands.append(f'{local_path} {irods_path}')
        call(' '.join(commands), shell=True)

    def irods_get(self, irods_path: str, local_path: str):
        """ Download `irods_path` to `local_path` following iRODS `options`.

        Parameters
        ----------
        ses_man : irods session
            Instance of the Session class
        irods_path : str
            Path of iRODS data object or collection.
        local_path : str
            Path of local file or directory/folder.

        """
        commands = [f'iget -K -N {kw.NUM_THREADS} {irods_path} {local_path}']
        call(' '.join(commands), shell=True)
