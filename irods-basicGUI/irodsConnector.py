from irods.session import iRODSSession
from irods.access import iRODSAccess
from irods.exception import CATALOG_ALREADY_HAS_ITEM_BY_THAT_NAME, CAT_NO_ACCESS_PERMISSION 
from irods.exception import CAT_SUCCESS_BUT_WITH_NO_INFO, CAT_INVALID_ARGUMENT, CAT_INVALID_USER
from irods.exception import CollectionDoesNotExist
from irods.models import Collection, DataObject, Resource, ResourceMeta, CollectionMeta, DataObjectMeta
from irods.models import User, UserGroup
from irods.column import Like, Between, In
import irods.keywords as kw
from irods.rule import Rule

import json
import os
from base64 import b64decode
from shutil import disk_usage
import hashlib

RED = '\x1b[1;31m'
DEFAULT = '\x1b[0m'
YEL = '\x1b[1;33m'
BLUE = '\x1b[1;34m'

class irodsConnector():
    def __init__(self, envFile, password = "", logger = None):
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
            if password == "": # requires a valid .irods/.irodsA (linux/mac only)
                print("EnvFile only")
                self.session = iRODSSession(irods_env_file=envFile)
            else:
                print("EnvFile, password")
                self.session = iRODSSession(**ienv, password=password)
            self.session.collections.get("/"+self.session.zone+"/home")
        except Exception as error:
            print(RED+"AUTHENTICATION ERROR: "+repr(error)+DEFAULT)
            raise

        if "default_resource_name" in ienv:
            self.defaultResc = ienv["default_resource_name"]
        else:
            self.defaultResc = "demoResc"

        if "davrods_server" in ienv:
            self.davrods = ienv["davrods_server"]
        else:
            self.davrods = None

        print("Welcome to iRODS:")
        print("iRODS Zone: "+self.session.zone)
        print("You are: "+self.session.username)
        print("Default resource: "+self.defaultResc)
        print("You have access to: ")
        print(''.join([coll.path+'\n' for coll 
            in self.session.collections.get("/"+self.session.zone+"/home").subcollections]))


    def getUserInfo(self):
        userGroupQuery = self.session.query(UserGroup).filter(Like(User.name, self.session.username))
        userTypeQuery = self.session.query(User.type).filter(Like(User.name, self.session.username))
        
        userType = []
        for t in userTypeQuery.get_results():
            userType.extend(list(t.values()))
        userGroups = []
        for g in userGroupQuery.get_results():
            userGroups.extend(list(g.values()))

        return(userType, userGroups)

        
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
            print(RED+"ACL ERROR: rights or path not known"+DEFAULT)
            raise


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


    def search(self, keyVals = None):
        '''
        Given a dictionary with keys and values, searches for colletions and 
        data objects that fullfill the criteria.
        The key 'checksum' will be mapped to DataObject.checksum, the key 'path'
        will be mapped to Collection.name and the key 'object' will be mapped to DataObject.name.
        Default: if no keyVals are given, all accessible colletcins and data objects will be returned

        keyVals: dict; {'checksum': '', 'key1': 'val1', 'key2': 'val2', 'path': '', 'object': ''}

        Returns:
        list: [[Collection name, Object name, checksum]]
        '''
        collQuery = None
        objQuery = None
        if set(keyVals.keys()).intersection(['checksum', 'object', 'path']) == set():
            collQuery = self.session.query(Collection.name)
            objQuery = self.session.query(Collection.name,
                                          DataObject.name,
                                          DataObject.checksum)
        if 'path' in keyVals: 
            collQuery = self.session.query(Collection.name).\
                                           filter(Like(Collection.name, keyVals['path']))
        if 'object' in keyVals or 'checksum' in keyVals:
            objQuery = self.session.query(Collection.name,
                                DataObject.name,
                                DataObject.checksum)
            if 'object' in keyVals:
                if keyVals['object']:
            	    objQuery = objQuery.filter(Like(DataObject.name, 
                                                keyVals['object']))
            if 'checksum' in keyVals: 
                if keyVals['checksum']:
                    objQuery = objQuery.filter(Like(DataObject.checksum, 
                                                keyVals['checksum']))
        
        for key in keyVals:
            if key not in ['checksum', 'path', 'object']:
                if objQuery:
                    objQuery.filter(DataObjectMeta.name == key)
                if collQuery:
                    collQuery.filter(CollectionMeta.name == key)
                if keyVals[key]:
                    if objQuery:
                        objQuery.filter(DataObjectMeta.value == keyVals[key])
                    if collQuery:
                        collQuery.filter(CollectionMeta.value == keyVals[key])

        results = [['', '', ''], ['', '', ''], ['', '', '']]
        collBatch = [[]]
        objBatch = [[]]
        #return only 100 results
        if collQuery:
            results[0] = ["Collections found: "+str(sum(1 for _ in collQuery)),'', '']
            collBatch = [b for b in collQuery.get_batches()]
        if objQuery:
            results[1] = ["Objects found: "+str(sum(1 for _ in objQuery)), '', '']
            objBatch = [b for b in objQuery.get_batches()]
       
        for res in objBatch[0][:50]:
            results.append([res[list(res.keys())[0]],
                            res[list(res.keys())[1]],
                            res[list(res.keys())[2]]])
        for res in collBatch[0][:50]:
            results.append([res[list(res.keys())[0]], '', ''])

        return results


    def listResources(self):
        query = self.session.query(Resource.name)
        resources = []
        for item in query.get_results():
            for key in item.keys():
                resources.append(item[key])

        if 'bundleResc' in resources:
            resources.remove('bundleResc')
        if 'demoResc' in resources:
            resources.remove('demoResc')

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
            raise error("RESOURCE ERROR: Either resource does not exist or size not set.")
        

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
        if resource:
            options = {kw.RESC_NAME_KW: resource,
                        kw.REG_CHKSUM_KW: ''}
        else:
            options = {kw.REG_CHKSUM_KW: ''}

        if not force:
            try:
                space = self.session.resources.get(resource).free_space
                if not space:
                    space = 0
                if int(size) > (int(space)-buff):
                    raise ValueError('ERROR iRODS upload: Not enough space on resource.')
                if buff < 0:
                    raise BufferError('ERROR iRODS upload: Negative resource buffer.')
            except Exception as error:
                raise error
        try: 
            if source.endswith(os.sep):
                source = source[:len(source)-1]
            if os.path.isfile(source):
                print("CREATE", destination.path+"/"+os.path.basename(source))
                self.session.collections.create(destination.path)
                self.session.data_objects.put(source, 
                    destination.path+"/"+os.path.basename(source), **options)
            elif os.path.isdir(source):
                iPath = destination.path+'/'+os.path.basename(source)
                for directory, _, files in os.walk(source):
                    subColl = directory.split(source)[1].replace(os.sep, '/')
                    iColl = iPath+subColl
                    self.session.collections.create(iColl)
                    for fname in files:
                        print("CREATE", iColl+'/'+fname)
                        self.session.data_objects.put(directory+'/'+fname, 
                            iColl+'/'+fname, **options)
            else:
                raise FileNotFoundError("ERROR iRODS upload: not a valid source path")
        except:
            raise
    

    def downloadData(self, source, destination, size, buff = 1024**3, force = False):
        '''
        Download object or collection.
        source: iRODS collection or data object
        destination: absolute path to download folder
        size: size of data to be downloaded in bytes
        buf: buffer on the filesystem that should be left over
        '''
        
        options = {kw.FORCE_FLAG_KW: '', kw.REG_CHKSUM_KW: ''}
        
        if destination.endswith(os.sep):
            destination = destination[:len(destination)-1]

        if not os.access(destination, os.W_OK):
            raise PermissionError("IRODS DOWNLOAD: No rights to write to destination.")
        if not os.path.isdir(destination):
            raise IsADirectoryError("IRODS DOWNLOAD: Path seems to be directory, but is file.")

        if not force:
            try:
                space = disk_usage(destination).free
                if int(size) > (int(space)-buff):
                    raise ValueError('ERROR iRODS download: Not enough space on disk.')
                if buff < 0:
                    raise BufferError('ERROR iRODS download: Negative disk buffer.')
            except Exception as error:
                raise error()

        if self.session.data_objects.exists(source.path):
            try:
                print("INFO Downloading:", source.path, "to \n\t", destination)
                self.session.data_objects.get(source.path, 
                            local_path=os.path.join(destination, source.name), **options)
            except:
                raise

        elif self.session.collections.exists(source.path):
            walk = [source]
            while walk:
                try:
                    coll = walk.pop()
                    suffix = os.path.join(os.path.basename(source.path), 
                                          coll.path.split(source.path)[1].strip('/'))
                    if suffix.endswith(os.sep):
                        suffix = suffix[:len(suffix)-1]
                    directory = os.path.join(destination, suffix)
                    walk.extend(coll.subcollections)
                    if not os.path.exists(directory):
                        os.makedirs(directory)
                    for obj in coll.data_objects:
                        print(DEFAULT+"INFO: Downloading "+obj.path+" to \n\t", 
                                os.path.join(directory, obj.name))
                        self.session.data_objects.get(obj.path, 
                                                      local_path=os.path.join(directory, obj.name), 
                                                      **options)
                except:
                    raise 
        else:
            raise FileNotFoundError("IRODS DOWNLOAD: not a valid source path")


    def diffIrodsLocalfs(self, coll, dirPath, scope="size"):
        '''
        Compares and iRODS tree to a directory and lists files that are not in sync.
        Syncing scope can be 'size' or 'checksum'
        Returns: zip([dataObjects][files]) where ther is a difference
        collection: iRODS collection
        '''

        if not os.access(dirPath, os.R_OK):
            raise PermissionError("IRODS FS DIFF: No rights to write to destination.")
        if not os.path.isdir(dirPath):
            raise IsADirectoryError("IRODS FS DIFF: directory is a file.")
        if not self.session.collections.exists(coll.path):
            raise CollectionDoesNotExist("IRODS FS DIFF: collection path unknwn")

        listDir = []
        for root, dirs, files in os.walk(dirPath, topdown=False):
            for name in files:
                listDir.append(os.path.join(root.split(dirPath)[1], name).strip(os.sep))

        listColl = []
        for root, subcolls, obj in self.session.collections.get(coll.path).walk():
            for o in obj:
                listColl.append(os.path.join(root.path.split(coll.path)[1], o.name).strip('/'))

        diff = []
        same = []
        for partialPath in set(listDir).intersection(listColl):
            if scope == "size":
                objSize = self.session.data_objects.get(coll.path+'/'+partialPath).size
                fSize = os.path.getsize(os.path.join(dirPath, partialPath))
                if objSize != fSize:
                    diff.append((coll.path+'/'+partialPath, os.path.join(dirPath, partialPath)))
                else:
                    same.append((coll.path+'/'+partialPath, os.path.join(dirPath, partialPath)))
            elif scope == "checksum":
                objCheck = self.session.data_objects.get(coll.path+'/'+partialPath).checksum
                if objCheck == None:
                    self.session.data_objects.get(coll.path+'/'+partialPath).chksum()
                    objCheck = self.session.data_objects.get(coll.path+'/'+partialPath).checksum
                if objCheck.startswith("sha2"):
                    sha2Obj = b64decode(objCheck.split('sha2:')[1])
                    with open(os.path.join(dirPath, partialPath), "rb") as f:
                        stream = f.read()
                        sha2 = hashlib.sha256(stream).digest()
                    if sha2Obj != sha2:
                        diff.append((coll.path+'/'+partialPath, os.path.join(dirPath, partialPath)))
                    else:
                        same.append((coll.path+'/'+partialPath, os.path.join(dirPath, partialPath)))
                elif objCheck:
                    #md5
                    with open(os.path.join(dirPath, partialPath), "rb") as f:
                        stream = f.read()
                        md5 = hashlib.md5(stream).hexdigest();
                    if objCheck != md5:
                        diff.append((coll.path+'/'+partialPath, os.path.join(dirPath, partialPath)))
                    else:
                        same.append((coll.path+'/'+partialPath, os.path.join(dirPath, partialPath)))
            else: #same paths, no scope
                diff.append((coll.path+'/'+partialPath, os.path.join(dirPath, partialPath)))

        #adding files that are not on iRODS, only present on local FS
        #adding files that are not on local FS, only present in iRODS
        #adding files that are stored on both devices with the same checksum/size
        return (diff, list(set(listDir).difference(listColl)), list(set(listColl).difference(listDir)), same)


    def addMetadata(self, items, key, value, units = None):
        """
        Adds metadata to all items
        items: list of iRODS data objects or iRODS collections
        key: string
        value: string
        units: (optional) string 

        Throws:
            CATALOG_ALREADY_HAS_ITEM_BY_THAT_NAME
        """
        for item in items:
            try:
                item.metadata.add(key.upper(), value, units)
            except CATALOG_ALREADY_HAS_ITEM_BY_THAT_NAME:
                print(RED+"ERROR ADD META: Metadata already present"+DEFAULT)
            except CAT_NO_ACCESS_PERMISSION:
                raise CAT_NO_ACCESS_PERMISSION("ERROR UPDATE META: no permissions")

            

    def updateMetadata(self, items, key, value, units = None):
        """
        Updates a metadata entry to all items
        items: list of iRODS data objects or iRODS collections
        key: string
        value: string
        units: (optional) string

        Throws: CAT_NO_ACCESS_PERMISSION
        """
        try:
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
        except CAT_NO_ACCESS_PERMISSION:
            raise CAT_NO_ACCESS_PERMISSION("ERROR UPDATE META: no permissions")


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
                print(RED+"ERROR DELETE META: Metadata never existed"+DEFAULT)
            except CAT_NO_ACCESS_PERMISSION:
                raise CAT_NO_ACCESS_PERMISSION("ERROR UPDATE META: no permissions")



    def deleteData(self, item):
        """
        Delete a data object or a collection recursively.
        item: iRODS data object or collection
        """

        if self.session.collections.exists(item.path):
            try:
                item.remove(recurse = True, force = True)
            except CAT_NO_ACCESS_PERMISSION:
                raise CAT_NO_ACCESS_PERMISSION("ERROR IRODS DELETE: no permissions")
        elif self.session.data_objects.exists(item.path):
            try:
                item.unlink(force = True)
            except CAT_NO_ACCESS_PERMISSION:
                raise CAT_NO_ACCESS_PERMISSION("ERROR IRODS DELETE: no permissions")


    def executeRule(self, ruleFile, params, output='ruleExecOut'):
        """
        Executes and interactive rule. Returns stdout and stderr.
        params: Depending on rule,
                dictionary of variables for rule, will overwrite the default settings.
        params format example:
        params = {  # extra quotes for string literals
            '*obj': '"/zone/home/user"',
            '*name': '"attr_name"',
            '*value': '"attr_value"'
        }
        """
        rule = Rule(self.session, ruleFile, params=params, output=output)
        out = rule.execute()
        stdout = []
        stderr = []
        if len(out.MsParam_PI) > 0:
            try:
                stdout = [o.decode() 
                    for o in (out.MsParam_PI[0].inOutStruct.stdoutBuf.buf.strip(b'\x00')).split(b'\n')]
                stderr = [o.decode() 
                    for o in (out.MsParam_PI[0].inOutStruct.stderrBuf.buf.strip(b'\x00')).split(b'\n')]
            except AttributeError:
                return stdout, stderr
        
        return stdout, stderr


    def getSize(self, coll):
        '''
        Compute the size of the iRods dataobject or collection
        Returns: size in bytes.
        collection: iRODS collection
        '''
        if self.session.data_objects.exists(coll.path):
            return coll.size

        elif self.session.collections.exists(coll.path):
            size = 0
            walk = [coll]
            while walk:
                try:
                    coll = walk.pop()
                    walk.extend(coll.subcollections)
                    for obj in coll.data_objects:
                        size = size + obj.size
                except:
                    raise
            return size
        else:
            raise FileNotFoundError("IRODS getSize: not a valid source path")


    def getSizeList(self, coll, ojbList):
        '''
        Compute the size of a list of dataobjects in a collection
        Returns: size in bytes.
        collection: base iRODS collection
        ojbList: list of object to get size off
        '''
        size = 0
        for objpath in ojbList:
            path = coll.path + '/' + objpath.replace("\\", "/")
            if self.session.data_objects.exists(path):
                size = size + self.session.data_objects.get(path).size
            else:
                raise FileNotFoundError("IRODS getSize: not a valid source path")
        return size
