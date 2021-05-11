from irods.session import iRODSSession
from irods.exception import CATALOG_ALREADY_HAS_ITEM_BY_THAT_NAME
import irods.keywords as kw
from subprocess import Popen, PIPE
import json
import os
from getpass import getpass

RED = '\x1b[1;31m'
DEFAULT = '\x1b[0m'
YEL = '\x1b[1;33m'
BLUE = '\x1b[1;34m'

class irodsConnectorIcommands():
    def __init__(self):
        """
        iRODS authentication.
        Input:
            Works only for linux with installed icommands
            envFile: expects and ~/.irods/irods_enviornment.json

        Throws errors:
            ConnectionRefusedError: password incorrect
            FileNotFoundError: /home/<user>/.irods/irods_environment.json not found
            All other errors refer to having the envFile not setup properly
        """
        envFile = os.environ['HOME']+"/.irods/irods_environment.json"
        if os.path.exists(envFile):
            p = Popen(['ils'], stdout=PIPE, stdin=PIPE, stderr=PIPE, shell=True)
            out, err = p.communicate()
            if err != b'':
                password = getpass("Please enter your password: ")
                p = Popen(['iinit'], stdout=PIPE, stdin=PIPE, stderr=PIPE, shell=True)
                out, err = p.communicate(input=(password+"\n").encode())
                if err != b'':
                    raise ConnectionRefusedError('Wrong iRODS password provided.')
                else:
                    self.session = iRODSSession(irods_env_file=envFile)
            else:
                self.session = iRODSSession(irods_env_file=envFile)
        else:
            raise FileNotFoundError('Environment file not found: '+ envFile)
        
        print("Welcome to iRODS:")
        print("iRODS Zone: "+self.session.zone)
        print("You are: "+self.session.username)
        print("You have access to: ")
        print(''.join([coll.path+'\n' for coll 
            in self.session.collections.get("/"+self.session.zone+"/home").subcollections]))

    def getPermissions(self, iPath):
        try:
            coll = self.session.collections.get(iPath)
            return self.session.permissions.get(coll)
        except:
            try:
                obj = self.session.data_objects.get(iPath)
                return self.session.permissions.get(obj)
            except:
                raise

    def getSubcollections(self, iPath):
        return self.session.collections.get(iPath)

    def getDataObj(self, objPath):
        return self.session.data_objects.get(objPath)

    def getDataObjs(self, collPath):
        if self.session.collections.exists(collPath):
            coll = self.session.collections.get(collPath)
            return coll.data_objects
        else:
            raise Error('Not a valid collection path')

    def ensureColl(self, collPath):
        try:
            self.session.collections.create(collPath)
            return self.session.collections.get(collPath)
        except:
            raise

    def getResource(self, resource):
        return self.session.resources.get(resource)

    def resourceSize(self, resource):
        """
        Returns the available space left on a resource in bytes
        resource: Name of the resource
        Throws: ResourceDoesNotExist if resource not known
                TypeError if 'free_space' not set
        """
        try:
            size = self.session.resources.get(resource).free_space
            if size == None:
                raise AttributeError("RESOURCE ERROR: size not set.")
            else:
                return size
        except Exception as error:
            print(RED+"RESOURCE ERROR: Either resource does not exist or size not set.")
            raise
        

    def uploadData(self, source, destination, resource, size, buff = 1024**3):
        """
        source: absolute path to file or folder
        destination: iRODS collection where data is uploaded to
        resource: name of the iRODS storage resource to use
        size: size of data to be uploaded in bytes
        buf: buffer on resource that should be left over

        The function uploads the contents of a folder with all subfolders to 
        an iRODS collection.
        If source is the path to a file, the file will be uploaded.

        Throws:
        ResourceDoesNotExist
        ValueError (if resource too small or buffer is too small)
        
        """
        try:
            space = self.session.resources.get(resource).free_space
            if int(size) > (int(space)-buff):
                raise ValueError('ERROR iRODS upload: Not enough space on resource.')
            if buff < 0:
                raise BufferError('ERROR iRODS upload: Negative resource buffer.')
        except Exception as error:
            print(RED+"ERROR iRODS upload: "+repr(error)+DEFAULT)
            raise

        if os.path.isfile(source):
            print("CREATE", destination.path+"/"+os.path.basename(source))
            self.session.collections.create(destination.path)
            p = Popen(['iput -f', source, destination.path], 
                    stdout=PIPE, stdin=PIPE, stderr=PIPE, shell=True)
            out, err = p.communicate()
        elif os.path.isdir(source):
            p = Popen(['iput -brf '+source+' '+destination.path], 
                    stdout=PIPE, stdin=PIPE, stderr=PIPE, shell=True)
            out, err = p.communicate()
        else:
            raise FileNotFoundError("ERROR iRODS upload: not a valid source path")

    def addMetadata(self, items, key, value):
        """
        Adds metadata to all items
        items: list of iRODS data objects or iRODS collections
        key: string
        value: string

        Throws:
            AttributeError
        """
        for item in items:
            try:
                item.metadata.add(key.upper(), value)
            except CATALOG_ALREADY_HAS_ITEM_BY_THAT_NAME:
                print(RED+"METADATA ADD FAILED: Metadata already present"+DEFAULT)
                


