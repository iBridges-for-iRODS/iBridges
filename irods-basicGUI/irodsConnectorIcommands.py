from irods.session      import iRODSSession
from irods.access       import iRODSAccess
from irods.exception    import CATALOG_ALREADY_HAS_ITEM_BY_THAT_NAME, CAT_NO_ACCESS_PERMISSION
from irods.exception    import CAT_SUCCESS_BUT_WITH_NO_INFO, CAT_INVALID_ARGUMENT, CAT_INVALID_USER
from irods.exception    import CollectionDoesNotExist

from irods.models       import Collection, DataObject, Resource, ResourceMeta, CollectionMeta, DataObjectMeta
from irods.models       import User, UserGroup
from irods.column import Like, Between, In
import irods.keywords as kw

import subprocess
from subprocess         import Popen, PIPE
import json
import os
from base64 import b64decode
from shutil import disk_usage
import hashlib

RED = '\x1b[1;31m'
DEFAULT = '\x1b[0m'
YEL = '\x1b[1;33m'
BLUE = '\x1b[1;34m'

class irodsConnectorIcommands():
    def __init__(self, password = '', logger = None):
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

        envFile = os.environ['HOME']+"/.irods/irods_environment.json"
        envFileExists = os.path.exists(envFile)
        
        try:
            #passwordFileExists = os.path.exists(os.environ['HOME']+"/.irods/.irodsA")
            icommandsExist = False
            icommandsExist = subprocess.call(["which", "iinit"]) == 0
            if icommandsExist == False:
                raise EnvironmentError("icommands not installed")
        except Exception as error:
            raise 

        if not envFileExists:
            print(envFile)
            raise FileNotFoundError('Environment file not found: '+ envFile)

        if not os.path.exists(os.path.expanduser('~/.irods/.irodsA')):
            print("No password cached, logging in with password:")
            p = Popen(['iinit'], stdout=PIPE, stdin=PIPE, stderr=PIPE, shell=True)
            outLogin, errLogin = p.communicate(input=(password+"\n").encode())
            if errLogin != b'':
                print("Login failed.")
                raise ConnectionRefusedError('Wrong iRODS password provided.')
            self.session = iRODSSession(irods_env_file=envFile)
        else:
            print("Password cached, trying ils:")
            p = Popen(['ils'], stdout=PIPE, stdin=PIPE, stderr=PIPE, shell=True)
            out, err = p.communicate()
            if err != b'':
                print("Cached password wrong. Logging in with password.")
                p = Popen(
                        ['iinit'], stdout=PIPE, stdin=PIPE, stderr=PIPE, shell=True)
                outLogin, errLogin = p.communicate(input=(password+"\n").encode())
                if errLogin != b'':
                    print("Login failed")
                    raise ConnectionRefusedError('Wrong iRODS password provided.')
            self.session = iRODSSession(irods_env_file=envFile)
        try:
            colls = self.session.collections.get("/"+self.session.zone+"/home").subcollections
        except CollectionDoesNotExist:
            colls = self.session.collections.get(
                    "/"+self.session.zone+"/home/"+self.session.username).subcollections
        except:
            raise

        collnames = [c.path for c in colls]

        with open(envFile) as f:
            ienv = json.load(f)
        if "default_resource_name" in ienv:
            self.defaultResc = ienv["default_resource_name"]
        else:
            self.defaultResc = "demoResc"
        if "davrods_server" in ienv:
            self.davrods = ienv["davrods_server"].strip('/')
        else:
            self.davrods = None

        print("Welcome to iRODS:")
        print("iRODS Zone: "+self.session.zone)
        print("You are: "+self.session.username)
        print("Default resource: "+self.defaultResc)
        print("You have access to: \n")
        print('\n'.join(collnames))


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
            raise CAT_INVALID_ARGUMENT("ACL ERROR: rights or path not known")


    def ensureColl(self, collPath):
        '''
        Raises:
            irods.exception.CAT_NO_ACCESS_PERMISSION
        '''
        try:
            if not self.session.collections.exists(collPath):
                self.session.collections.create(collPath)
            return self.session.collections.get(collPath)
        except:
            raise


    def search(self, keyVals = None):
        '''
        Given a dictionary with keys and values, searches for collections and 
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
        collBatch = []
        objBatch = []
        if collQuery:
            results[0] = ["Collections found: "+str(sum(1 for _ in collQuery)),'', '']
            collBatch = [b for b in collQuery.get_batches()]
        if objQuery:
            results[1] = ["Objects found: "+str(sum(1 for _ in objQuery)), '', '']
            objBatch = [b for b in objQuery.get_batches()]

        if 'checksum' in keyVals or 'object' in keyVals:
            for res in objBatch[0][:50]:
                results.append([res[list(res.keys())[0]],
                                res[list(res.keys())[1]],
                                res[list(res.keys())[2]]])
        if 'path' in keyVals:
            for res in collBatch[0][:50]:
                results.append([res[list(res.keys())[0]], '', ''])

        return results


    def listResources(self):
        """
        Returns list of all root resources, that accept data.
        """
        query = self.session.query(Resource.name, Resource.parent)
        resources = []
        for item in query.get_results():
            rescName, parent = item.values()
            if parent == None:
                resources.append(rescName)

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


    def uploadData(self, source, destination, resource, size, buff = 1024**3, 
                    force = False, diffs = []):
        """
        source: absolute path to file or folder
        destination: iRODS collection where data is uploaded to
        resource: name of the iRODS storage resource to use
        size: size of data to be uploaded in bytes
        buf: buffer on resource that should be left over
        diffs: Leave empty, placeholder to be in sync with irodsConnector class function

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
                if not space:
                    space = 0
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
                cmd = 'irsync -aK '+source+' i:'+destination.path+' -R '+resource
            else:
                cmd = 'irsync -aK '+source+' i:'+destination.path
        elif os.path.isdir(source):
            self.session.collections.create(destination.path+'/'+os.path.basename(source))
            subColl = self.session.collections.get(destination.path+'/'+os.path.basename(source))
            if resource:
                cmd = 'irsync -aKr '+source+' i:'+subColl.path+' -R '+resource
            else:
                cmd = 'irsync -aKr '+source+' i:'+subColl.path
        else:
            raise FileNotFoundError("ERROR iRODS upload: not a valid source path")
       
        print("IRODS UPLOAD: "+cmd)
        p = Popen([cmd], stdout=PIPE, stdin=PIPE, stderr=PIPE, shell=True)
        out, err = p.communicate()
        print('IRODS UPLOAD INFO: out:'+str(out)+'\nerr: '+str(err))


    def downloadData(self, source, destination, size, buff = 1024**3, force = False, diffs = []):
        '''
        Download object or collection.
        source: iRODS collection or data object
        destination: absolut path to download folder
        size: size of data to be downloaded in bytes
        buff: buffer on the filesystem that should be left over
        '''

        destination = '/'+destination.strip('/')
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
            #-f overwrite, -K control checksum, -r recursive (collections)
            cmd = 'irsync -K i:'+source.path+' '+destination+os.sep+os.path.basename(source.path)
        elif self.session.collections.exists(source.path):
            cmd = 'irsync -Kr i:'+source.path+' '+destination+os.sep+os.path.basename(source.path)
        else:
            raise FileNotFoundError("IRODS download: not a valid source.")
        
        print("IRODS DOWNLOAD: "+cmd)
        p = Popen([cmd], stdout=PIPE, stdin=PIPE, stderr=PIPE, shell=True)
        out, err = p.communicate()
        print('IRODS DOWNLOAD INFO: out:'+str(out)+'\nerr: '+str(err))


    def diffObjFile(self, objPath, fsPath, scope="size"):
        """
        Compares and iRODS object to a file system file.
        returns ([diff], [onlyIrods], [onlyFs], [same])
        """

        if os.path.isdir(fsPath) and not os.path.isfile(fsPath):
            raise IsADirectoryError("IRODS FS DIFF: file is a directory.")
        if self.session.collections.exists(objPath):
            raise IsADirectoryError("IRODS FS DIFF: object is a collection.")

        if not os.path.isfile(fsPath) and self.session.data_objects.exists(objPath):
            return ([], [objPath], [], [])

        elif not self.session.data_objects.exists(objPath) and os.path.isfile(fsPath):
            return ([], [], [fsPath], [])

        #both, file and object exist
        obj = self.session.data_objects.get(objPath)
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
                obj.chksum()
                objCheck = obj.checksum
            if objCheck.startswith("sha2"):
                sha2Obj = b64decode(objCheck.split('sha2:')[1])
                with open(fsPath) as f:
                    stream = f.read()
                    sha2 = hashlib.sha256(stream).digest()
                if sha2Obj != sha2:
                    return([(objPath, fsPath)], [], [], [])
                else:
                    return ([], [], [], [(objPath, fsPath)])
            elif objCheck:
                #md5
                with open(fsPath) as f:
                    stream = f.read()
                    md5 = hashlib.md5(stream).hexdigest();
                if objCheck != md5:
                    return([(objPath, fsPath)], [], [], [])
                else:
                    return ([], [], [], [(objPath, fsPath)])

    def diffIrodsLocalfs(self, coll, dirPath, scope="size"):
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
        if not self.session.collections.exists(coll.path):
            raise CollectionDoesNotExist("IRODS FS DIFF: collection path unknwn")

        listDir = []
        for root, dirs, files in os.walk(dirPath, topdown=False):
            for name in files:
                listDir.append(os.path.join(root.split(dirPath)[1], name).strip('/'))

        listColl = []
        for root, subcolls, obj in coll.walk():
            for o in obj:
                listColl.append(os.path.join(root.path.split(coll.path)[1], o.name).strip('/'))

        diff = []
        same = []
        for partialPath in set(listDir).intersection(listColl):
            if scope == "size":
                objSize = self.session.data_objects.get(coll.path+'/'+partialPath).size
                fSize = os.path.getsize(dirPath+'/'+partialPath)
                if objSize != fSize:
                    diff.append((coll.path+'/'+partialPath, dirPath+'/'+partialPath))
                else:
                    same.append((coll.path+'/'+partialPath, os.path.join(dirPath, partialPath)))
            elif scope == "checksum":
                objCheck = self.session.data_objects.get(coll.path+'/'+partialPath).checksum
                if objCheck == None:
                    self.session.data_objects.get(coll.path+'/'+partialPath).chksum()
                    objCheck = self.session.data_objects.get(coll.path+'/'+partialPath).checksum
                if objCheck.startswith("sha2"):
                    sha2Obj = b64decode(objCheck.split('sha2:')[1])
                    with open(dirPath+'/'+partialPath,"rb") as f:
                        stream = f.read()
                        sha2 = hashlib.sha256(stream).digest()
                    if sha2Obj != sha2:
                        diff.append((coll.path+'/'+partialPath, dirPath+'/'+partialPath))
                    else:
                        same.append((coll.path+'/'+partialPath, os.path.join(dirPath, partialPath)))
                elif objCheck:
                    #md5
                    with open(dirPath+'/'+partialPath,"rb") as f:
                        stream = f.read()
                        md5 = hashlib.md5(stream).hexdigest();
                    if objCheck != md5:
                        diff.append((coll.path+'/'+partialPath, dirPath+'/'+partialPath))
                    else:
                        same.append((coll.path+'/'+partialPath, os.path.join(dirPath, partialPath)))
            else: # same paths no scope
                diff.append((coll.path+'/'+partialPath, dirPath+'/'+partialPath))

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
            AttributeError
        """
        for item in items:
            try:
                item.metadata.add(key.upper(), value, units)
            except CATALOG_ALREADY_HAS_ITEM_BY_THAT_NAME:
                print(RED+"METADATA ADD FAILED: Metadata already present"+DEFAULT)
            except CAT_NO_ACCESS_PERMISSION:
                raise CAT_NO_ACCESS_PERMISSION("ERROR UPDATE META: no permissions: "+item.path)


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
            except CAT_NO_ACCESS_PERMISSION:
                raise CAT_NO_ACCESS_PERMISSION("ERROR UPDATE META: no permissions "+item.path)




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
        params: depending on rule, 
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
                stderr = [o.decode
                    for o in (out.MsParam_PI[0].inOutStruct.stderrBuf.buf.strip(b'\x00')).split(b'\n')]
            except AttributeError:
                return stdout, stderr

        return stdout, stderr


    def getSize(self, itemPaths):
        '''
        Compute the size of the iRods dataobject or collection
        Returns: size in bytes.
        itemPaths: list of irods paths pointing to collection or object
        '''
        size = 0
        for path in itemPaths:
            #remove possible leftovers of windows fs separators
            path = path.replace("\\", "/")
            if self.session.data_objects.exists(path):
                size = size + self.session.data_objects.get(path).size

            elif self.session.collections.exists(path):
                coll = self.session.collections.get(path)
                walk = [coll]
                while walk:
                    try:
                        coll = walk.pop()
                        walk.extend(coll.subcollections)
                        for obj in coll.data_objects:
                            size = size + obj.size
                    except:
                        raise
            else:
                pass

        return size

