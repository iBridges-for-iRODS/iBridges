from irods.session      import iRODSSession
from irods.access       import iRODSAccess
from irods.exception    import CATALOG_ALREADY_HAS_ITEM_BY_THAT_NAME, CAT_NO_ACCESS_PERMISSION
from irods.exception    import CAT_SUCCESS_BUT_WITH_NO_INFO, CAT_INVALID_ARGUMENT, CAT_INVALID_USER

from irods.models       import Collection, DataObject, Resource, ResourceMeta, CollectionMeta, DataObjectMeta
import irods.keywords as kw

import subprocess
from subprocess         import Popen, PIPE
import json
import os
from base64 import b64decode
import hashlib

RED = '\x1b[1;31m'
DEFAULT = '\x1b[0m'
YEL = '\x1b[1;33m'
BLUE = '\x1b[1;34m'

class irodsConnectorIcommands():
    def __init__(self, password, logger = None):
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
        self.logger = logger
        if logger != None:
            print("DEBUG: TODO Print all to file")

        envFile = os.environ['HOME']+"/.irods/irods_environment.json"
        envFileExists = os.path.exists(os.environ['HOME']+"/.irods/irods_environment.json")
        
        try:
            passwordFileExists = os.path.exists(os.environ['HOME']+"/.irods/.irodsA")
            icommandsExist = False
            icommandsExist = subprocess.call(["which", "iinit"]) == 0
            if icommandsExist == False:
                raise EnvironmentError("icommands not installed")
        except Exception as error:
            raise 

        if not envFileExists:
            raise FileNotFoundError('Environment file not found: '+ envFile)
        else:
            p = Popen(['iinit'], stdout=PIPE, stdin=PIPE, stderr=PIPE, shell=True)
            out, err = p.communicate(input=(password+"\n").encode())
            if err != b'':
                raise ConnectionRefusedError('Wrong iRODS password provided.')
            else:
                self.session = iRODSSession(irods_env_file=envFile)

        with open(envFile) as f:
                ienv = json.load(f)

        if "default_resource_name" in ienv:
            self.defaultResc = ienv["default_resource_name"]
        else:
            self.defaultResc = "demoResc"

        print("Welcome to iRODS (icommands):")
        print("iRODS Zone: "+self.session.zone)
        print("You are: "+self.session.username)
        print("Default resource: "+self.defaultResc)
        print("You have access to: ")
        print(''.join([coll.path+'\n' for coll 
            in self.session.collections.get("/"+self.session.zone+"/home").subcollections]))


    def getPermissions(self, iPath):
        '''
        iPath: Can be a string or an iRODS collection/object
        Throws:
            irods.exception.CollectionDoesNotExist
        '''
        try:
            return self.session.permissions.get(iPath)
        except:
            try:
                coll = self.session.collections.get(iPath)
                return self.session.permissions.get(coll)
            except:
                try:
                    obj = self.session.data_objects.get(iPath)
                    return self.session.permissions.get(obj)
                except:
                    raise


    def setPermissions(self, rights, user, path, zone, recursive = False):
        '''
        Sets permissions to an iRODS collection or data object.
        path: string
        rights: string, [own, read, write, null]
        '''
        acl = iRODSAccess(rights, path, user, zone)

        try:
            if recursive and self.session.collections.exists(path):
                self.session.permissions.set(acl, recursive=True)
            else:
                self.session.permissions.set(acl, recursive=False)
        except CAT_INVALID_USER:
            raise CAT_INVALID_USER("ACL ERROR: user unknown ")
        except CAT_INVALID_ARGUMENT:
            raise CAT_INVALID_ARGUMENT("ACL ERROR: rights or path not known")


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
                TypeError if 'free_space' not set
        """
        try:
            size = self.session.resources.get(resource).free_space
            if size == None:
                raise AttributeError("RESOURCE ERROR: size not set.")
            else:
                return size
        except Exception as error:
            raise error("RESOURCE ERROR: Either resource does not exist or size not set.")
        
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

    def uploadData(self, source, destination, resource, size, buff = 1024**3, force = False):
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
        
        if not force:
            try:
                space = self.session.resources.get(resource).free_space
                if int(size) > (int(space)-buff):
                    raise ValueError('ERROR iRODS upload: Not enough space on resource.')
                if buff < 0:
                    raise BufferError('ERROR iRODS upload: Negative resource buffer.')
            except Exception as error:
                raise

        if os.path.isfile(source):
            print("CREATE", destination.path+"/"+os.path.basename(source))
            self.session.collections.create(destination.path)
            if resource:
                cmd = 'iput -fK '+source+' '+destination.path+' -R '+resource
            else:
                cmd = 'iput -fK '+source+' '+destination.path
        elif os.path.isdir(source):
            if resource:
                cmd = 'iput -brfK '+source+' '+destination.path+' -R '+resource
            else:
                cmd = 'iput -brfK '+source+' '+destination.path
        else:
            raise FileNotFoundError("ERROR iRODS upload: not a valid source path")
       
        print(cmd)
        p = Popen([cmd], stdout=PIPE, stdin=PIPE, stderr=PIPE, shell=True)
        out, err = p.communicate()


    def downloadData(self, source, destination):
        '''
        Download object or collection.
        source: iRODS collection or data object
        destination: absolut path to download folder
        '''

        destination = '/'+destination.strip('/')
        if not os.access(destination, os.W_OK):
            raise PermissionError("IRODS DOWNLOAD: No rights to write to destination.")
        if not os.path.isdir(destination):
            raise IsADirectoryError("IRODS DOWNLOAD: Path seems to be directory, but is file.")

        if self.session.data_objects.exists(source.path):
            #-f overwrite, -K control checksum, -r recursive (collections)
            cmd = 'iget -fK '+source.path+' '+destination
        elif self.session.collections.exists(source.path):
            cmd = 'iget -fKr '+source.path+' '+destination
        else:
            raise FileNotFoundError("IRODS download: not a valid source.")

        p = Popen([cmd], stdout=PIPE, stdin=PIPE, stderr=PIPE, shell=True)
        out, err = p.communicate()


    def diffIrodsLocalfs(self, collPath, dirPath, scope="size"):
        '''
        Compares and iRODS tree to a directory and lists files that are not in sync.
        Syncing scope can be 'size' or 'checksum'
        Returns: zip([dataObjects][files]) where ther is a difference
        collection: collection path
        '''

        if not os.access(dirPath, os.R_OK):
            raise PermissionError("IRODS FS DIFF: No rights to write to destination.")
        if not os.path.isdir(dirPath):
            raise IsADirectoryError("IRODS FS DIFF: directory is a file.")
        if not self.session.collections.exists(collPath):
            raise CollectionDoesNotExist("IRODS FS DIFF: collection path unknwn")

        listDir = []
        for root, dirs, files in os.walk(dirPath, topdown=False):
            for name in files:
                listDir.append(os.path.join(root.split(dirPath)[1], name).strip('/'))

        listColl = []
        for root, subcolls, obj in self.session.collections.get(collPath).walk():
            for o in obj:
                listColl.append(os.path.join(root.path.split(collPath)[1], o.name).strip('/'))

        diff = []
        for partialPath in set(listDir).intersection(listColl):
            if scope == "size":
                objSize = self.session.data_objects.get(collPath+'/'+partialPath).size
                fSize = os.path.getsize(dirPath+'/'+partialPath)
                if objSize != fSize:
                    diff.append((collPath+'/'+partialPath, dirPath+'/'+partialPath))
            elif scope == "checksum":
                objCheck = self.session.data_objects.get(collPath+'/'+partialPath).checksum
                if objCheck.startswith("sha2"):
                    sha2Obj = b64decode(objCheck.split('sha2:')[1])
                    with open(dirPath+'/'+partialPath,"rb") as f:
                        stream = f.read()
                        sha2 = hashlib.sha256(stream).digest()
                    if sha2Obj != sha2:
                        diff.append((collPath+'/'+partialPath, dirPath+'/'+partialPath))
                elif objCheck:
                    #md5
                    with open(dirPath+'/'+partialPath,"rb") as f:
                        stream = f.read()
                        md5 = hashlib.md5(stream).hexdigest();
                    if objCheck != md5:
                        diff.append((collPath+'/'+partialPath, dirPath+'/'+partialPath))
            else: # same paths no scope
                diff.append((collPath+'/'+partialPath, dirPath+'/'+partialPath))

        return diff


    def addMetadata(self, items, key, value, units = None):
        """
        Adds metadata to all items
        items: list of iRODS data objects or iRODS collections
        key: string
        value: string
        units: (optional) string 

        Throws:
            AttributeError
        """
        for item in items:
            try:
                item.metadata.add(key.upper(), value, units)
            except CATALOG_ALREADY_HAS_ITEM_BY_THAT_NAME:
                print(RED+"METADATA ADD FAILED: Metadata already present"+DEFAULT)

    def updateMetadata(self, items, key, value, units = None):
        """
        Updates a metadata entry to all items
        items: list of iRODS data objects or iRODS collections
        key: string
        value: string
        units: (optional) string

        Throws:
        """

        for item in items:
            if key in item.metadata.keys():
                meta = item.metadata.get_all(key)
                valuesUnits = [(m.value, m.units) for m in meta]
                if (value, units) not in valuesUnits:
                    #remove all iCAT entries with that key
                    for m in meta:
                        item.metadata.remove(m)
                    #add key, value, units
                    self.addMetadata(items, key, value, units)

            else:
                self.addMetadata(items, key, value, units)
                

    def deleteMetadata(self, items, key, value, units):
        """
        Deletes a metadata entry of all items
        items: list of iRODS data objects or iRODS collections
        key: string
        value: string
        units: (optional) string

        Throws:
            CAT_SUCCESS_BUT_WITH_NO_INFO: metadata did not exist
        """
        for item in items:
            try:
                item.metadata.remove(key, value, units)
            except CAT_SUCCESS_BUT_WITH_NO_INFO:
                print(RED+"METADATA ADD FAILED: Metadata never existed"+DEFAULT)



