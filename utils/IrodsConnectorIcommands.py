"""IrodsConnector for iCommands
"""
import logging
import os
import shutil
import subprocess

import utils


class IrodsConnectorIcommands(utils.IrodsConnector.IrodsConnector):
    """Connection to an iRODS server while using iCommands.

    """

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
        logging.info('iRODS UPLOAD: ' + source + '-->' + str(destination) + ', ' + str(resource))
        if not force:
            try:
                space = self.resource_space(resource)
                if int(size) > (int(space) - buff):
                    logging.info('ERROR iRODS upload: Not enough space on resource.')
                    raise ValueError('ERROR iRODS upload: Not enough space on resource.')
                if buff < 0:
                    logging.info('ERROR iRODS upload: Negative resource buffer.')
                    raise BufferError('ERROR iRODS upload: Negative resource buffer.')
            except Exception as error:
                raise

        if os.path.isfile(source):
            print('CREATE', destination.path + '/' + os.path.basename(source))
            self.session.collections.create(destination.path)
            if resource:
                cmd = 'irsync -aK ' + source + ' i:' + destination.path + ' -R ' + resource
            else:
                cmd = 'irsync -aK ' + source + ' i:' + destination.path
        elif os.path.isdir(source):
            self.session.collections.create(destination.path + '/' + os.path.basename(source))
            subColl = self.session.collections.get(destination.path + '/' + os.path.basename(source))
            if resource:
                cmd = 'irsync -aKr ' + source + ' i:' + subColl.path + ' -R ' + resource
            else:
                cmd = 'irsync -aKr ' + source + ' i:' + subColl.path
        else:
            logging.info('UPLOAD ERROR', exc_info=True)
            raise FileNotFoundError('ERROR iRODS upload: not a valid source path')
        logging.info('IRODS UPLOAD: ' + cmd)
        p = subprocess.Popen([cmd], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = p.communicate()
        logging.info('IRODS UPLOAD INFO: out:' + str(out) + '\nerr: ' + str(err))

    def download_data( self, source, destination, size, buff=1024**3, force=False, diffs=None):
        """
        Download object or collection.
        source: iRODS collection or data object
        destination: absolut path to download folder
        size: size of data to be downloaded in bytes
        buff: buffer on the filesystem that should be left over
        """
        logging.info('iRODS DOWNLOAD: ' + str(source) + '-->' + destination)
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
        logging.info('IRODS DOWNLOAD: ' + cmd)
        p = subprocess.Popen([cmd], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = p.communicate()
        logging.info('IRODS DOWNLOAD INFO: out:' + str(out) + '\nerr: ' + str(err))
