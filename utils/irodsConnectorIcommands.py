from irods.session      import iRODSSession
from irods.access       import iRODSAccess
from irods.exception    import CATALOG_ALREADY_HAS_ITEM_BY_THAT_NAME, CAT_NO_ACCESS_PERMISSION
from irods.exception    import CAT_SUCCESS_BUT_WITH_NO_INFO, CAT_INVALID_ARGUMENT, CAT_INVALID_USER
from irods.exception    import CollectionDoesNotExist
from irods.ticket       import Ticket

from irods.models       import Collection, DataObject, Resource, ResourceMeta, CollectionMeta, DataObjectMeta
from irods.models       import User, UserGroup
from irods.column import Like, Between, In
import irods.keywords as kw
from irods.rule import Rule

import subprocess
from subprocess         import Popen, PIPE
import json
import os
from base64 import b64decode
from shutil import disk_usage
import hashlib
import random, string
import logging
from utils.irodsConnector import irodsConnector

RED = '\x1b[1;31m'
DEFAULT = '\x1b[0m'
YEL = '\x1b[1;33m'
BLUE = '\x1b[1;34m'

class irodsConnectorIcommands(irodsConnector):
    def __init__(self, password = ''):
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
        self.__name__="irodsConnectorIcommands"

        envFile = os.environ['HOME']+"/.irods/irods_environment.json"
        envFileExists = os.path.exists(envFile)
        
        try:
            #passwordFileExists = os.path.exists(os.environ['HOME']+"/.irods/.irodsA")
            icommandsExist = False
            icommandsExist = subprocess.call(["which", "iinit"]) == 0
            if icommandsExist == False:
                raise EnvironmentError("icommands not installed")
        except Exception as error:
            logging.info('AUTHENTICATION ERROR', exc_info=True)
            raise 

        if not envFileExists:
            logging.info('AUTHENTICATION ERROR envFile not found: '+envFile)
            raise FileNotFoundError('Environment file not found: '+ envFile)

        if not os.path.exists(os.path.expanduser('~/.irods/.irodsA')):
            logging.info("No password cached, logging in with password:")
            print("No password cached, logging in with password:")
            p = Popen(['iinit'], stdout=PIPE, stdin=PIPE, stderr=PIPE, shell=True)
            outLogin, errLogin = p.communicate(input=(password+"\n").encode())
            if errLogin != b'':
                logging.info("AUTHENTICATION ERROR: Wrong iRODS password provided.")
                raise ConnectionRefusedError('Wrong iRODS password provided.')
            self.session = iRODSSession(irods_env_file=envFile)
        else:
            logging.info("Password cached, trying ils:")
            p = Popen(['ils'], stdout=PIPE, stdin=PIPE, stderr=PIPE, shell=True)
            out, err = p.communicate()
            if err != b'':
                logging.info("Cached password wrong. Logging in with password.")
                p = Popen(
                        ['iinit'], stdout=PIPE, stdin=PIPE, stderr=PIPE, shell=True)
                outLogin, errLogin = p.communicate(input=(password+"\n").encode())
                if errLogin != b'':
                    logging.info('AUTHENTICATION ERROR: Wrong iRODS password provided.')
                    raise ConnectionRefusedError('Wrong iRODS password provided.')
            self.session = iRODSSession(irods_env_file=envFile)
        try:
            colls = self.session.collections.get("/"+self.session.zone+"/home").subcollections
        except CollectionDoesNotExist:
            colls = self.session.collections.get(
                    "/"+self.session.zone+"/home/"+self.session.username).subcollections
        except:
            logging.info('AUTHENTICATION ERROR', exc_info=True)
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

        logging.info(
            'IRODS LOGIN SUCCESS: '+self.session.username+", "+self.session.zone+", "+self.session.host)


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
        logging.info('iRODS UPLOAD: '+source+'-->'+str(destination)+', '+str(resource))
        if not force:
            try:
                space = self.session.resources.get(resource).free_space
                if not space:
                    space = 0
                if int(size) > (int(space)-buff):
                    logging.info('ERROR iRODS upload: Not enough space on resource.')
                    raise ValueError('ERROR iRODS upload: Not enough space on resource.')
                if buff < 0:
                    logging.info('ERROR iRODS upload: Negative resource buffer.')
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
            logging.info('UPLOAD ERROR', exc_info=True)
            raise FileNotFoundError("ERROR iRODS upload: not a valid source path")
       
        logging.info("IRODS UPLOAD: "+cmd)
        p = Popen([cmd], stdout=PIPE, stdin=PIPE, stderr=PIPE, shell=True)
        out, err = p.communicate()
        logging.info('IRODS UPLOAD INFO: out:'+str(out)+'\nerr: '+str(err))


    def downloadData(self, source, destination, size, buff = 1024**3, force = False, diffs = []):
        '''
        Download object or collection.
        source: iRODS collection or data object
        destination: absolut path to download folder
        size: size of data to be downloaded in bytes
        buff: buffer on the filesystem that should be left over
        '''
        
        logging.info('iRODS DOWNLOAD: '+str(source)+'-->'+destination)
        destination = '/'+destination.strip('/')
        if not os.access(destination, os.W_OK):
            logging.info("IRODS DOWNLOAD: No rights to write to destination.")
            raise PermissionError("IRODS DOWNLOAD: No rights to write to destination.")
        if not os.path.isdir(destination):
            logging.info("IRODS DOWNLOAD: Path seems to be directory, but is file.")
            raise IsADirectoryError("IRODS DOWNLOAD: Path seems to be directory, but is file.")

        if not force:
            try:
                space = disk_usage(destination).free
                if int(size) > (int(space)-buff):
                    logging.info('ERROR iRODS download: Not enough space on disk.')
                    raise ValueError('ERROR iRODS download: Not enough space on disk.')
                if buff < 0:
                    logging.info('ERROR iRODS download: Negative disk buffer.')
                    raise BufferError('ERROR iRODS download: Negative disk buffer.')
            except Exception as error:
                logging.info('DOWNLOAD ERROR', exc_info=True)
                raise error()

        if self.session.data_objects.exists(source.path):
            #-f overwrite, -K control checksum, -r recursive (collections)
            cmd = 'irsync -K i:'+source.path+' '+destination+os.sep+os.path.basename(source.path)
        elif self.session.collections.exists(source.path):
            cmd = 'irsync -Kr i:'+source.path+' '+destination+os.sep+os.path.basename(source.path)
        else:
            raise FileNotFoundError("IRODS download: not a valid source.")
        
        logging.info("IRODS DOWNLOAD: "+cmd)
        p = Popen([cmd], stdout=PIPE, stdin=PIPE, stderr=PIPE, shell=True)
        out, err = p.communicate()
        logging.info('IRODS DOWNLOAD INFO: out:'+str(out)+'\nerr: '+str(err))


    def createTicket(self, path, expiryString=""):
        ticket = Ticket(self.session, 
                        ''.join(random.choice(string.ascii_letters) for _ in range(20)))
        ticket.issue("read", path)
        logging.info('IRODS TICKET INFO: ticket created: '+ticket.ticket)

        if expiryString != "":
            cmd = 'iticket mod '+ticket.ticket+' expire '+expiryString

        p = Popen([cmd], stdout=PIPE, stdin=PIPE, stderr=PIPE, shell=True)
        out, err = p.communicate()
        logging.info('IRODS TICKET Expiration date: out:'+str(out)+'\nerr: '+str(err))
        if err == b'':
            return ticket.ticket, expiryString
        else:
            return ticket.ticket, err.decode()
