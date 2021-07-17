from irods.session import iRODSSession
from irods.exception import CATALOG_ALREADY_HAS_ITEM_BY_THAT_NAME, CAT_NO_ACCESS_PERMISSION
from irods.models import Collection, DataObject, Resource, ResourceMeta, CollectionMeta, DataObjectMeta
import irods.keywords as kw
import json
import os

RED = '\x1b[1;31m'
DEFAULT = '\x1b[0m'
YEL = '\x1b[1;33m'
BLUE = '\x1b[1;34m'

class irodsConnector():
    def __init__(self, envFile, password, logger = None):
        """
        iRODS authentication with python.
        Input:
            envFile: json document with iRODS connection parameters
            password: string

        If you like to overwrite one or both parameters, use the envFile and password.

        Throws errors:
            irods.exception.CAT_INVALID_USER: password no longer properly cached
            irods.exception.PAM_AUTH_PASSWORD_FAILED: wrong password
            NetworkException: No conection could be established
            All other errors refer to having the envFile not setup properly
        """
        self.logger = logger
        if logger != None:
            print("DEBUG: TODO Print all to file")
        
        try:
            with open(envFile) as f:
                ienv = json.load(f)
            self.session = iRODSSession(**ienv, password=password)
            self.session.collections.get("/"+self.session.zone+"/home")
        except Exception as error:
            print(RED+"AUTHENTICATION ERROR: "+repr(error)+DEFAULT)
            raise

        print("Welcome to iRODS:")
        print("iRODS Zone: "+self.session.zone)
        print("You are: "+self.session.username)
        print("You have access to: ")
        print(''.join([coll.path+'\n' for coll 
            in self.session.collections.get("/"+self.session.zone+"/home").subcollections]))

    def getPermissions(self, iPath):
        '''
        Throws:
            irods.exception.CollectionDoesNotExist
        '''
        try:
            coll = self.session.collections.get(iPath)
            return self.session.permissions.get(coll)
        except:
            try:
                obj = self.session.data_objects.get(iPath)
                return self.session.permissions.get(obj)
            except:
                raise

    def getSubcollections(self, collPath):
        return self.session.collections.get(collPath)

    def getDataObj(self, objPath):
        '''
        Raises:
            irods.exception.CollectionDoesNotExist
            irods.exception.DataObjectDoesNotExist
        '''
        return self.session.data_objects.get(objPath)

    def getDataObjs(self, collPath):
        if self.session.collections.exists(collPath):
            coll = self.session.collections.get(collPath)
            return coll.data_objects
        else:
            raise Exception('Not a valid collection path')

    def ensureColl(self, collPath):
        '''
        Raises:
            irods.exception.CAT_NO_ACCESS_PERMISSION
        '''
        try:
            self.session.collections.create(collPath)
            return self.session.collections.get(collPath)
        except:
            raise

    def listResources(self):
        query = self.session.query(Resource.name)
        resources = []
        for item in query.get_results():
            for key in item.keys():
                resources.append(item[key])
        return resources


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
        options = {kw.RESC_NAME_KW: resource,
               kw.REG_CHKSUM_KW: ''}
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
            self.session.data_objects.put(source, 
                    destination.path+"/"+os.path.basename(source), **options)
        elif os.path.isdir(source):
            for directory, _, files in os.walk(source):
                subColl = directory.split(source)[1]
                iColl = destination.path+subColl
                self.session.collections.create(iColl)
                for fname in files:
                    print("CREATE", iColl+'/'+fname)
                    self.session.data_objects.put(directory+'/'+fname, 
                            iColl+'/'+fname, **options)
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
                


