"""IrodsConnector for iCommands
"""
import logging
import os
import shutil
from subprocess import call, Popen, PIPE


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

    def upload_data(self, source, destination, resource, size, buff=1024**3,
                    force=False, diffs=None):
        """
        source: absolute path to file or folder
        destination: iRODS collection where data is uploaded to
        resource: name of the iRODS storage resource to use
        size: size of data to be uploaded in bytes
        buf: buffer on resource that should be left over
        diffs: Leave empty, placeholder to be in sync with IrodsConnector class function

        The function uploads the contents of a folder with all subfolders to 
        an iRODS collection.
        If source is the path to a file, the file will be uploaded.

        Throws:
        ResourceDoesNotExist
        ValueError (if resource too small or buffer is too small)

        """
        logging.info('iRODS UPLOAD: %s --> %s, %s', source, str(destination), str(resource))
        if not force:
            try:
                space = self.resource_space(resource)
                if int(size) > (int(space) - buff):
                    raise ValueError('ERROR iRODS upload: Not enough space on resource.')
                if buff < 0:
                    raise BufferError('ERROR iRODS upload: Negative resource buffer.')
            except Exception as error:
                logging.error(error)
                raise error

        if os.path.isfile(source):
            print('CREATE', destination.path + '/' + os.path.basename(source))
            self.session.collections.create(destination.path)
            if resource:
                cmd = 'irsync -aK ' + source + ' i:' + destination.path + ' -R ' + resource
            else:
                cmd = 'irsync -aK ' + source + ' i:' + destination.path
        elif os.path.isdir(source):
            self.session.collections.create(destination.path + '/' + os.path.basename(source))
            sub_coll = self.session.collections.get(destination.path + '/' + os.path.basename(source))
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

    def download_data(self, source, destination, size, buff=1024**3, force=False, diffs=None):
        """
        Download object or collection.
        source: iRODS collection or data object
        destination: absolut path to download folder
        size: size of data to be downloaded in bytes
        buff: buffer on the filesystem that should be left over
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

        if self.session.data_objects.exists(source.path):
            # -f overwrite, -K control checksum, -r recursive (collections)
            cmd = 'irsync -K i:' + source.path + ' ' + destination + os.sep + os.path.basename(source.path)
        elif self.session.collections.exists(source.path):
            cmd = 'irsync -Kr i:' + source.path + ' ' + destination + os.sep + os.path.basename(source.path)
        else:
            raise FileNotFoundError('IRODS download: not a valid source.')
        logging.info('IRODS DOWNLOAD: %s', cmd)
        pros = Popen([cmd], stdout=PIPE, stdin=PIPE, stderr=PIPE, shell=True)
        out, err = pros.communicate()
        logging.info('IRODS DOWNLOAD INFO: out:%s \nerr: %s', str(out), str(err))
