from irods.session import iRODSSession
from irods.ticket import Ticket
from irods.exception import CollectionDoesNotExist, CAT_SQL_ERR
import irods.keywords as kw
import irods
import uuid

from utils.irodsConnector import irodsConnector
from utils.utils import ensure_dir

import os
from base64 import b64decode
from shutil import disk_usage
import hashlib
import logging
import subprocess
from subprocess         import Popen, PIPE
from utils.utils        import saveIenv

RED = '\x1b[1;31m'
DEFAULT = '\x1b[0m'
YEL = '\x1b[1;33m'
BLUE = '\x1b[1;34m'

class irodsConnectorAnonymous(irodsConnector):
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
        
        self.tempEnv = None
        self.tempIrodsA = None

        zone = path.split('/')[1]
        self.session = iRODSSession(user='anonymous',
                                    password='',
                                    zone=zone,
                                    port=1247,
                                    host=host)
        self.token = ticket
        self.path = path
        self.icommands = False
        self.icommands = subprocess.call(["which", "iinit"]) == 0
        if self.icommands:
            ensure_dir(os.path.expanduser('~'+os.sep+'.irods'))
            #move previous iRODS sessions to tmp file (envFile and .irodsA file)
            self.__movePrevSessionConfigs(False)
            env = {"irods_host": self.session.host, 
                    "irods_port": 1247, 
                    "irods_user_name": "anonymous", 
                    "irods_zone_name": self.session.zone}
            saveIenv(env)
            logging.info('Anonymous Login: '+self.session.host+', '+self.session.zone)
            p = Popen(['iinit'], stdout=PIPE, stdin=PIPE, stderr=PIPE, shell=True)
            outLogin, errLogin = p.communicate()
            if errLogin != b'':
                logging.info('AUTHENTICATION ERROR: Anonymous login failed.')
                self.icommands = False

    def closeSession(self):
        self.__movePrevSessionConfigs(True)


    def __movePrevSessionConfigs(self, restore):
        if restore:
            if self.tempEnv:
                os.rename(self.tempEnv, 
                        os.path.expanduser('~'+os.sep+'.irods'+os.sep+'irods_environment.json'))
            if self.tempIrodsA:
                os.rename(self.tempIrodsA, 
                        os.path.expanduser('~'+os.sep+'.irods'+os.sep+'.irodsA'))
        else:
            uid = str(uuid.uuid1())
            envPath = os.path.expanduser('~'+os.sep+'.irods'+os.sep+'irods_environment.json')
            irodsAPath = os.path.expanduser('~'+os.sep+'.irods'+os.sep+'.irodsA')
            if os.path.exists(envPath):
                os.rename(envPath, envPath+uid)
                self.tempEnv = envPath+uid
            if os.path.exists(irodsAPath):
                os.rename(irodsAPath, irodsAPath+uid)
                self.tempIrodsA = irodsAPath+uid


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
    
    def downloadIcommands(self, source, destination):
        if type(source) == irods.data_object.iRODSDataObject:
            #-f overwrite, -K control checksum, -r recursive (collections)
            cmd = 'iget -Kft '+self.token+' '+ \
                    source.path+' '+destination+os.sep+os.path.basename(source.path)
        elif self.session.collections.exists(source.path):
            cmd = 'iget -Kfrt '+self.token+' '+ \
                    source.path+' '+destination+os.sep+os.path.basename(source.path)
        else:
            raise FileNotFoundError("IRODS download: not a valid source.")

        logging.info("IRODS DOWNLOAD: "+cmd)
        p = Popen([cmd], stdout=PIPE, stdin=PIPE, stderr=PIPE, shell=True)
        out, err = p.communicate()
        logging.info('IRODS DOWNLOAD INFO: out:'+str(out)+'\nerr: '+str(err))


    def download(self, source, destination, diffs):
        (diff, onlyFS, onlyIrods, same) = diffs
        if type(source) == irods.data_object.iRODSDataObject and len(diff+onlyIrods) > 0:
            try:
                logging.info("IRODS DOWNLOADING object:"+ source.path+
                                "to "+ destination)
                self.__get(source, os.path.join(destination, source.name))
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
                _subcoll = self.session.collections.get(os.path.dirname(d[0]))
                obj = [o for o in _subcoll.data_objects if o.path == d[0]][0]
                self.__get(obj, d[1])
                #self.session.data_objects.get(d[0], local_path=d[1], **options)

            for IO in onlyIrods: #can contain files and folders
                #Create subcollections and upload
                sourcePath = source.path + "/" + IO
                locO = IO.replace("/", os.sep)
                destPath = os.path.join(subdir, locO)
                if not os.path.isdir(os.path.dirname(destPath)):
                    os.makedirs(os.path.dirname(destPath))
                logging.info('INFO: Downloading '+sourcePath+" to "+destPath)
                _subcoll = self.session.collections.get(os.path.dirname(sourcePath))
                obj = [o for o in _subcoll.data_objects if o.path == sourcePath][0]
                self.__get(obj, destPath)
                #self.session.data_objects.get(sourcePath, local_path=destPath, **options)
        except:
            logging.info('DOWNLOAD ERROR', exc_info=True)
            raise


    def downloadData(self, source, destination, size, buff = 1024**3, force = False, diffs=[]):
        '''
        Download object or collection.
        source: iRODS collection or data object
        destination: absolute path to download folder
        size: size of data to be downloaded in bytes
        buff: buffer on resource that should be left over
        force: If true, do not calculate storage capacity on destination
        diffs: output of diff functions

        Since the data_object.get function does not work for anonymous sessions, we need to stream
        '''
        logging.info('iRODS DOWNLOAD: '+str(source)+'-->'+destination) 
        #options = {kw.FORCE_FLAG_KW: '', kw.REG_CHKSUM_KW: ''}

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
            if self.session.collections.exists(source.path):
                subdir = os.path.join(destination, source.name)
                if not os.path.isdir(os.path.join(destination, source.name)):
                    os.mkdir(os.path.join(destination, source.name))
                diffs = self.diffIrodsLocalfs(source, subdir, scope="checksum")
            elif type(source) == irods.data_object.iRODSDataObject:
                _subcoll = self.session.collections.get(os.path.dirname(source.path))
                valObjs = [o for o in _subcoll.data_objects if o.path == source.path]
                if len(valObjs) > 0:
                    diffs = self.diffObjFile(source.path,
                                                    os.path.join(
                                                    destination, os.path.basename(source.path)),
                                                    scope="checksum")
            else:
                raise FileNotFoundError("ERROR iRODS upload: not a valid source path")

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
        
        if self.icommands:
            self.downloadIcommands(source, destination)
        else:
            self.download(source, destination, diffs)
    

    def __get(self, obj, filename):
        """
        Workaround for bug in the irods_data_objects get function:
        https://github.com/irods/python-irodsclient/issues/294
        """
        options = {kw.FORCE_FLAG_KW: '', kw.REG_CHKSUM_KW: '', kw.TICKET_KW: self.token}
        #with obj.open('r') as stream:
        #    tmp = stream.read()
        #with open(filename, 'wb') as f:
        #    f.write(tmp)
        #    f.close()

        try:
            self.session.data_objects.get(obj.path, local_path=filename, **options)
        except CAT_SQL_ERR:
            pass
        except:
            raise


    def diffObjFile(self, objPath, fsPath, scope="size"):
        """
        Compares and iRODS object to a file system file.
        We do not have the function session.data_objects.exists or .get for anonymous users
        returns ([diff], [onlyIrods], [onlyFs], [same])
        Implements workaround to
        https://github.com/irods/python-irodsclient/issues/294
        """
        if os.path.isdir(fsPath) and not os.path.isfile(fsPath):
            raise IsADirectoryError("IRODS FS DIFF: file is a directory.")
        if self.session.collections.exists(objPath):
            raise IsADirectoryError("IRODS FS DIFF: object exists already as collection. "+objPath)

        coll = self.session.collections.get(os.path.dirname(objPath))
        obj = [o for o in coll.data_objects if o.path == objPath][0]
        if not os.path.isfile(fsPath) and obj:
            return ([], [], [obj.path], [])

        elif not obj and os.path.isfile(fsPath):
            return ([], [fsPath], [], [])

        #both, file and object exist
        if scope == "size":
            objSize = obj.size
            fSize = os.path.getsize(fsPath)
            if objSize != fSize:
                return ([(objPath, fsPath)], [], [], [])
            else:
                return ([], [], [], [(objPath, fsPath)])
        elif scope == "checksum":
            objCheck = obj.checksum
            if objCheck == None:
                #obj.chksum()
                #objCheck = obj.checksum
                logging.info('No checksum available: '+obj.path)
                return([(objPath, fsPath)], [], [], [])
            if objCheck.startswith("sha2"):
                sha2Obj = b64decode(objCheck.split('sha2:')[1])
                with open(fsPath, "rb") as f:
                    stream = f.read()
                    sha2 = hashlib.sha256(stream).digest()
                if sha2Obj != sha2:
                    return([(objPath, fsPath)], [], [], [])
                else:
                    return ([], [], [], [(objPath, fsPath)])
            elif objCheck:
                #md5
                with open(fsPath, "rb") as f:
                    stream = f.read()
                    md5 = hashlib.md5(stream).hexdigest()
                if objCheck != md5:
                    return([(objPath, fsPath)], [], [], [])
                else:
                    return ([], [], [], [(objPath, fsPath)]) 


    def diffIrodsLocalfs(self, coll, dirPath, scope="size"):
        '''
        Compares and iRODS tree to a directory and lists files that are not in sync.
        Syncing scope can be 'size' or 'checksum'
        Returns: zip([dataObjects][files]) where ther is a difference
        collection: iRODS collection
        Implements workaround to
        https://github.com/irods/python-irodsclient/issues/294
        '''

        listDir = []
        if not dirPath == None:
            if not os.access(dirPath, os.R_OK):
                raise PermissionError("IRODS FS DIFF: No rights to write to destination.")
            if not os.path.isdir(dirPath):
                raise IsADirectoryError("IRODS FS DIFF: directory is a file.")
            for root, dirs, files in os.walk(dirPath, topdown=False):
                for name in files:
                    listDir.append(os.path.join(root.split(dirPath)[1], name).strip(os.sep))

        listColl = []
        if not coll == None:
            for root, subcolls, obj in coll.walk():
                for o in obj:
                    listColl.append(os.path.join(root.path.split(coll.path)[1], o.name).strip('/'))

        diff = []
        same = []
        for locPartialPath in set(listDir).intersection(listColl):
            iPartialPath = locPartialPath.replace(os.sep, "/")
            _subcoll = self.session.collections.get(os.path.dirname(coll.path + '/' + iPartialPath))
            obj = [o for o in _subcoll.data_objects if o.path == coll.path + '/' + iPartialPath][0]
            if scope == "size":
                objSize = obj.size
                fSize = os.path.getsize(os.path.join(dirPath, iPartialPath))
                if objSize != fSize:
                    diff.append((coll.path + '/' + iPartialPath, os.path.join(dirPath, locPartialPath)))
                else:
                    same.append((coll.path + '/' + iPartialPath, os.path.join(dirPath, locPartialPath)))
            elif scope == "checksum":
                objCheck = obj.checksum
                if objCheck == None:
                    #Anonymous user cannot calculate checksums
                    #obj.chksum()
                    #objCheck = obj.checksum
                    diff.append((coll.path + '/' + iPartialPath, 
                                 os.path.join(dirPath, locPartialPath)))
                    continue
                if objCheck.startswith("sha2"):
                    sha2Obj = b64decode(objCheck.split('sha2:')[1])
                    with open(os.path.join(dirPath, locPartialPath), "rb") as f:
                        stream = f.read()
                        sha2 = hashlib.sha256(stream).digest()
                    if sha2Obj != sha2:
                        diff.append((coll.path + '/' + iPartialPath, os.path.join(dirPath, locPartialPath)))
                    else:
                        same.append((coll.path + '/' + iPartialPath, os.path.join(dirPath, locPartialPath)))
                elif objCheck:
                    #md5
                    with open(os.path.join(dirPath, locPartialPath), "rb") as f:
                        stream = f.read()
                        md5 = hashlib.md5(stream).hexdigest();
                    if objCheck != md5:
                        diff.append((coll.path + '/' + iPartialPath, os.path.join(dirPath, locPartialPath)))
                    else:
                        same.append((coll.path + '/' + iPartialPath, os.path.join(dirPath, locPartialPath)))
            else: #same paths, no scope
                diff.append((coll.path + '/' + iPartialPath, os.path.join(dirPath, locPartialPath)))

        #adding files that are not on iRODS, only present on local FS
        #adding files that are not on local FS, only present in iRODS
        #adding files that are stored on both devices with the same checksum/size
        irodsOnly = list(set(listColl).difference(listDir))
        for i in range(0, len(irodsOnly)):
            irodsOnly[i] = irodsOnly[i].replace(os.sep, "/")
        return (diff, list(set(listDir).difference(listColl)), irodsOnly, same)


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


    def getSize(self, itemPaths):
        '''
        Compute the size of the iRods dataobject or collection
        Returns: size in bytes.
        itemPaths: list of irods paths pointing to collection or object
        Implementing workaround for bug
        '''
        size = 0
        for path in itemPaths:
            #remove possible leftovers of windows fs separators
            path = path.replace("\\", "/")
            
            if self.session.collections.exists(path):
                coll = self.session.collections.get(path)
                walk = [coll]
                while walk:
                    try:
                        coll = walk.pop()
                        walk.extend(coll.subcollections)
                        for obj in coll.data_objects:
                            size = size + obj.size
                    except:
                        logging.info('DATA SIZE', exc_info=True)
                        raise
            else:
                _subcoll = self.session.collections.get(os.path.dirname(path))
                obj = [o for o in _subcoll.data_objects if o.path == path][0]
                size = size + obj.size

        return size

