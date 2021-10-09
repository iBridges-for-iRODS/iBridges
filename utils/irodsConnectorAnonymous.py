from irods.session import iRODSSession
from irods.ticket import Ticket
from irods.exception import CollectionDoesNotExist

import os
from base64 import b64decode
from shutil import disk_usage
import hashlib
import logging

RED = '\x1b[1;31m'
DEFAULT = '\x1b[0m'
YEL = '\x1b[1;33m'
BLUE = '\x1b[1;34m'

class irodsConnectorAnonymous():
    def __init__(self, host, ticket, path):
        """
        iRODS anonymous login.
        Input:
            server: iRODS server
            ticket: string
            path: iRODS path the ticket grants access to

        """
        self.__name__="irodsConnectorAnonymous"
        if path.endswith('/'):
            path = path[:-1]
        if not path.startswith("/"):
            raise Exception("Not a valid iRODS path.")
        zone = path.split('/')[1]
        self.session = iRODSSession(user='anonymous',
                                    password='',
                                    zone=zone,
                                    port=1247,
                                    host=host)
        self.token = ticket
        self.path = path

    def getData(self):
        ticket = Ticket(self.session, self.token)
        ticket.supply()
        try:
            item = self.session.collections.get(self.path)
            return item
        except:
            raise

    def getUserInfo(self):
        pass

    def getPermissions(self, iPath):
        pass

    def setPermissions(self, rights, user, path, zone, recursive = False):
        pass

    def ensureColl(self, collPath):
        pass

    def search(self, keyVals = None):
        pass

    def listResources(self):
        pass

    def getResource(self, resource):
        '''
        Raises:
            irods.exception.ResourceDoesNotExist
        '''
        return self.session.resources.get(resource)

    def resourceSize(self, resource):
        """
        Returns the available space left on a resource in bytes
        resource: Name of the resource
        Throws: ResourceDoesNotExist if resource not known
                AttributeError if 'free_space' not set
        """
        try:
            size = self.session.resources.get(resource).free_space
            return size
        except Exception as error:
            logging.info('RESOURCE ERROR: Either resource does not exist or size not set.',
                            exc_info=True)
            raise error("RESOURCE ERROR: Either resource does not exist or size not set.")
        

    def uploadData(self, source, destination, resource, size, buff = 1024**3, 
                         force = False, diffs = []):
        pass 

    def downloadData(self, source, destination, size, buff = 1024**3, force = False, diffs=[]):
        '''
        Download object or collection.
        source: iRODS collection or data object
        destination: absolute path to download folder
        size: size of data to be downloaded in bytes
        buff: buffer on resource that should be left over
        force: If true, do not calculate storage capacity on destination
        diffs: output of diff functions
        '''
        logging.info('iRODS DOWNLOAD: '+str(source)+'-->'+destination) 
        options = {kw.FORCE_FLAG_KW: '', kw.REG_CHKSUM_KW: ''}

        if destination.endswith(os.sep):
            destination = destination[:len(destination)-1]
        if not os.path.isdir(destination):
            logging.info('DOWNLOAD ERROR: destination path does not exist or is not directory', 
                    exc_info=True)
            raise FileNotFoundError(
                "ERROR iRODS download: destination path does not exist or is not directory")
        if not os.access(destination, os.W_OK):
            logging.info('DOWNLOAD ERROR: No rights to write to destination.', 
                exc_info=True)
            raise PermissionError("ERROR iRODS download: No rights to write to destination.")

        if diffs == []:#Only download if not present or difference in files
            if self.session.data_objects.exists(source.path):
                (diff, onlyFS, onlyIrods, same) = self.diffObjFile(source.path,
                                                    os.path.join(
                                                    destination, os.path.basename(source.path)),
                                                    scope="checksum")
            elif self.session.collections.exists(source.path):
                subdir = os.path.join(destination, source.name)
                if not os.path.isdir(os.path.join(destination, source.name)):
                    os.mkdir(os.path.join(destination, source.name))

                (diff, onlyFS, onlyIrods, same) = self.diffIrodsLocalfs(
                                                    source, subdir, scope="checksum")
            else:
                raise FileNotFoundError("ERROR iRODS upload: not a valid source path")
        else:
            (diff, onlyFS, onlyIrods, same) = diffs

        if not force:#Check space on destination
            try:
                space = disk_usage(destination).free
                if int(size) > (int(space)-buff):
                    logging.info('DOWNLOAD ERROR: Not enough space on disk.', 
                            exc_info=True)
                    raise ValueError('ERROR iRODS download: Not enough space on disk.')
                if buff < 0:
                    logging.info('DOWNLOAD ERROR: Negative disk buffer.', exc_info=True)
                    raise BufferError('ERROR iRODS download: Negative disk buffer.')
            except Exception as error:
                logging.info('DOWNLOAD ERROR', exc_info=True)
                raise error()

        if self.session.data_objects.exists(source.path) and len(diff+onlyIrods) > 0:
            try:
                logging.info("IRODS DOWNLOADING object:"+ source.path+
                                "to "+ destination)
                self.session.data_objects.get(source.path, 
                            local_path=os.path.join(destination, source.name), **options)
                return
            except:
                logging.info('DOWNLOAD ERROR: '+source.path+"-->"+destination, 
                        exc_info=True)
                raise

        try: #collections/folders
            subdir = os.path.join(destination, source.name)
            logging.info("IRODS DOWNLOAD started:")
            for d in diff:
                #upload files to distinct data objects
                logging.info("REPLACE: "+d[1]+" with "+d[0])
                self.session.data_objects.get(d[0], local_path=d[1], **options)

            for IO in onlyIrods: #can contain files and folders
                #Create subcollections and upload
                sourcePath = source.path + "/" + IO
                locO = IO.replace("/", os.sep)
                destPath = os.path.join(subdir, locO)
                if not os.path.isdir(os.path.dirname(destPath)):
                    os.makedirs(os.path.dirname(destPath))
                logging.info('INFO: Downloading '+sourcePath+" to "+destPath)
                self.session.data_objects.get(sourcePath, local_path=destPath, **options)
        except:
            logging.info('DOWNLOAD ERROR', exc_info=True)
            raise


    def addMetadata(self, items, key, value, units = None):
        pass
            
    def updateMetadata(self, items, key, value, units = None):
        pass

    def deleteMetadata(self, items, key, value, units):
        pass

    def deleteData(self, item):
        pass

    def executeRule(self, ruleFile, params, output='ruleExecOut'):
        pass


    def createTicket(self, path, expiryString=""):
        pass
