#!/usr/bin/env python3

"""
Commandline client to upload data to a storage service and double-link the storage location with a metadata store.

Implemented for:
    Storage types:
        iRODS
    Metadata stores:
        Elabjournal
"""

from utils.elabConnector import elabConnector
from utils.irodsConnector import irodsConnector
from utils.irodsConnectorIcommands import irodsConnectorIcommands
from irods.exception import ResourceDoesNotExist

import configparser
import os
import sys
import json
import getopt
import getpass
import subprocess
from utils.utils import setup_logger, getSize, ensure_dir

RED = '\x1b[1;31m'
DEFAULT = '\x1b[0m'
YEL = '\x1b[1;33m'
BLUE = '\x1b[1;34m'

def getConfig(path):
    """
    Reads in config file. checks that at least section "iRODS" exists
    """
    config = configparser.ConfigParser()
    config.read_file(open(path))
    args = config._sections
    if not 'iRODS' in args:
        raise AttributeError("iRODS environment not defined.")
    if len(args) == 1:
        print(BLUE+"INFO: No metadata store configured. Only upload data to iRODS."+DEFAULT)
    
    return args


def connectIRODS(config):

    #icommands present and irods_environment file present and user wants to use standard envFile
    standardEnv = os.path.expanduser('~' +os.sep+'.irods'+os.sep+'irods_environment.json')
    if os.path.exists(standardEnv) and \
            (config['iRODS']['irodsenv'] == '' or config['iRODS']['irodsenv'] == standardEnv):
        try:
            ic = irodsConnectorIcommands()
            print(BLUE+"INFO: Icommands and standard environment file are present.")
            print("INFO: Using icommands for data up and download."+DEFAULT)
        except ConnectionRefusedError:
            raise
        except FileNotFoundError:
            raise
        except EnvironmentError:
            print("Connect with python API")
            passwd = getpass.getpass(
                    'Password for '+os.environ['HOME']+'/.irods/irods_environment.json'+': ')
            ic = irodsConnector(standardEnv, passwd)

        except Exception as e:
           raise

    elif os.path.exists(config['iRODS']['irodsenv']):
        passwd = getpass.getpass(
                    'Password for '+os.environ['HOME']+'/.irods/irods_environment.json'+': ')
        ic = irodsConnector(config['iRODS']['irodsenv'], passwd)
        print(BLUE+"INFO: Data up and download by python API."+DEFAULT)

    else:
        raise FileNotFoundError('Environment file not found e.g. '+ standardEnv)

    return ic


def setupIRODS(config, operation):
    """
    Connects to iRODS and sets up the environment.
    """
    ic = connectIRODS(config)
    if operation == 'download':
        return ic

    #set iRODS path
    try:
        coll = ic.ensureColl(config['iRODS']['irodscoll'])
        print(YEL+'Uploading to '+config['iRODS']['irodscoll']+DEFAULT)
    except:
        print(RED+"Collection path not set in config or invalid: "+ config['iRODS']['irodscoll']+DEFAULT)
        success = False
        while not success:
            iPath = input('Choose iRODS collection: ')
            try:
                coll = ic.ensureColl(iPath)
                config['iRODS']['irodscoll'] = iPath
                print(YEL+'Uploading to '+config['iRODS']['irodscoll']+DEFAULT)
                success = True
            except:
                print(RED+"Collection path not valid: "+ config['iRODS']['irodscoll']+DEFAULT)

    #set iRODS resource, can be located in ibridges config or in irods_environment, ibridges gets priority
    try:
        resource = ic.getResource(config['iRODS']['irodsresc'])
        if ic.resourceSize(resource.name) is None:
            print(config['iRODS']['irodsresc']+ " upload capacity, free space: No  inofrmation")
        else:
            print(config['iRODS']['irodsresc']+ " upload capacity, free space: "+ \
                str(round(int(ic.resourceSize(resource.name))/1000**3))+'GB')

    except ResourceDoesNotExist:
        print(RED+'iRODS resource does not exist: '+config['iRODS']['irodsresc']+DEFAULT)
        try:
            resource = ic.getResource(ic.defaultResc)
            config['iRODS']['irodsresc'] = ic.defaultResc
        except:
            print(RED+"No resource set in environment file either ('default_resource_name')"+DEFAULT)
            print(RED+"ERROR: No resource set"+DEFAULT)
            sys.exit(2)
        if ic.resourceSize(ic.defaultResc) is None:
            print(ic.defaultResc+ " upload capacity, free space: No  inofrmation")
        else:
            print(ic.defaultResc+ " upload capacity, free space: "+ \
                str(round(int(ic.resourceSize(resource.name))/1000**3))+'GB')

    return ic
    

def setupELN(config):
    md = elabConnector(config['ELN']['token'])
    if config['ELN']['group'] != '' and config['ELN']['experiment'] != '':
        try:
            md.updateMetadataUrl(group = config['ELN']['group'], 
                                 experiment = config['ELN']['experiment'])
        except:
            print(RED+'ELN groupID or experimentID not set or valid.'+DEFAULT)
            md.showGroups()
            md.updateMetadataUrlInteractive(group = True)
    else:
        md.showGroups()
        md.updateMetadataUrlInteractive(group = True)

    if config['ELN']['title'] == '':
        config['ELN']['title'] = input('ELN paragraph title: ')

    print(BLUE+('Link Data to experiment: '))
    print(md.metadataUrl)
    config['ELN']['experiment'] = md.experiment.id()
    config['ELN']['group'] = md.elab.group().id()
    print('with title: '+config['ELN']['title']+DEFAULT)

    return md, config['ELN']['title']

def prepareUpload(dataPath, ic, config):
    if not os.path.exists(dataPath):
        print(RED+'Data path does not exist'+DEFAULT)
        menu = input('Do you want to specify a new path? (Y/N)')
        if menu in ['YES', 'Yes', 'Y', 'y', '']:
            success = False
            while not success:
                dataPath = input('Full data path: ')
                success = os.path.exists(dataPath)
        else:
            print('Aborted: Data path not given')
            return False
    else:
        pass 

    size = getSize([dataPath])
    try:
        freeSpace = int(ic.getResource(config['iRODS']['irodsresc']).free_space)
        print('Checking storage capacity for '+dataPath+', '+str(float(size)/(1000**3))+'GB')
    except:
        print(YEL+'No information how much storage is left on the resource')
        res = input('Do you want to force the upload (Y/N): '+DEFAULT)
        freeSpace = None
    
    if freeSpace != None and int(freeSpace)-1000**3 < size:
        print(RED+'Not enough space left on iRODS resource.'+DEFAULT)
        res = input('Do you want to force the upload (Y/N): ')
        if res != 'Y':
            print('Aborted: Not enough space left.')
            return False
        else:
            return True
    else:
        return True


def prepareDownload(irodsItemPath, ic, config):
    if not ic.session.data_objects.exists(irodsItemPath) or \
       not ic.session.collections.exists(irodsItemPath):
        print(RED+'iRODS path does not exist'+DEFAULT)
        menu = input('Do you want to specify a new iRODS path? (Y/N)')
        if menu in ['YES', 'Yes', 'Y', 'y', '']:
            success = False
            while not success:
                irodsItemPath = input('Full data path: ')
                success = ic.session.data_objects.exists(irodsItemPath) or \
                          ic.session.collections.exists(irodsItemPath)
            config["iRODS"]["downloadItem"] = irodsItemPath
        else:
            print('Aborted: iRODS path not given')
            return False
    else:
        pass

    if config['DOWNLOAD']['path'] == '' or os.path.isfile(config['DOWNLOAD']['path']):
        print(RED+'No download directory given'+DEFAULT)
        menu = input('Do you want to specify a new iRODS path? (Y/N)')
        if menu in ['YES', 'Yes', 'Y', 'y', '']:
            success = False
            while not success:
                dataPath = input('Download directory: ')
                success = ensure_dir(dataPath)
            config["DOWNLOAD"]["path"] = dataPath
        else:
            print('Aborted: download directory not given')
            return False
    else:
        return ensure_dir(config['DOWNLOAD']['path'])
    
    return True

def printHelp():
    print('Data upload client')
    print('Uploads local data to iRODS, and, if specified, links dat to an entry in a metadata store (ELN).')
    print('Usage: ./iUpload.py -c, --config= \t config file')
    print('\t\t    -d, --data= \t datapath')
    print('\t\t    -i, --irods= \t irodspath (download)')
    print('Examples:')
    print('Downloading: ./irods-iBridgesCli.py -c <yourConfigFile> --irods=/npecZone/home')
    print('Uploading: ./irods-iBridgesCli.py -c <yourConfigFile> --data=/my/data/path')

def main(argv):
    
    irodsEnvPath = os.path.expanduser('~')+ os.sep +".irods"
    #setup_logger(irodsEnvPath, "iBridgesCli")

    try:
        opts, args = getopt.getopt(argv,"hc:d:i:",["config=", "data=", "irods="])
    except getopt.GetoptError:
        print(RED+"ERROR: incorrect usage."+DEFAULT)
        printHelp()
        sys.exit(2)

    config = None
    operation = None
        
    for opt, arg in opts:
        if opt == '-h':
            printHelp()
            sys.exit(2)
        elif opt in ['-c', '--config']:
            try:
               config  = getConfig(arg)
            except:
                try:
                    config = getConfig('iUpload.config')
                except:
                    print(RED+'No config file found.'+DEFAULT)
                    sys.exit(2)
        elif opt in ['-i', '--irods']:
            operation = 'download'
            if arg.endswith("/"):
                irodsPath = arg[:-1]
            else:
                irodsPath = arg
        elif opt in ['-d', '--data']:
            operation = 'upload'
            if arg.endswith("/"):
                dataPath = arg[:-1]
            else:
                dataPath = arg
        else:
            printHelp()
            sys.exit(2)

    #initialise iRODS
    if operation == None:
        print(RED+"ERROR: missing parameter."+DEFAULT)
        printHelp()
        sys.exit(2)        
        
    ic = setupIRODS(config, operation)
    #initialise medata store connetcions
    if 'ELN' in config and operation == 'upload':
        md, title = setupELN(config)
    else:
        md = None

    #check files for upload
    if operation == 'upload':
        if prepareUpload(dataPath, ic, config):
            if md != None:
                iPath = config['iRODS']['irodscoll']+'/'+md.__name__+'/'+ \
                    str(config['ELN']['group'])+'/'+str(config['ELN']['experiment'])
            #elif os.path.isdir(dataPath):
            #    iPath = config['iRODS']['irodscoll']+'/'+os.path.basename(dataPath)
            else:
                iPath = config['iRODS']['irodscoll']
            #ic.ensureColl(iPath)
            #print('DEBUG: Created/Ensured iRODS collection '+iPath)
            iColl = ic.session.collections.get(iPath)
            ic.uploadData(dataPath, iColl, config['iRODS']['irodsresc'], getSize([dataPath]), force=True)
        else:
            sys.exit(2)
        #tag data in iRODS and metadata store
        if md != None:
            coll = ic.session.collections.get(iPath)
            items = []
            for c, _, o in coll.walk():
                items.extend([c]+o)
            ic.addMetadata(items, 'PROVENANCE', md.metadataUrl)
            if config['iRODS']['webdav']!='':
                md.addMetadata(config['iRODS']['webdav']+iPath, title)
            else:
                md.addMetadata(ic.session.host+', '+iPath, title)
        print()
        print(BLUE+'Upload complete with the following parameters:')
        print(json.dumps(config, indent=4))
        print(DEFAULT)
    elif operation == 'download':
        print(json.dumps(config, indent=4))
        if prepareDownload(irodsPath, ic, config):
            downloadDir = config['DOWNLOAD']['path']
            irodsDataPath = config["iRODS"]["downloadItem"]
            print(YEL, 
                  'Downloading: '+irodsDataPath+', '+str(ic.getSize([irodsDataPath])/1000**3)+'GB', 
                  DEFAULT)
            try:
                item = ic.session.collections.get(irodsDataPath)
            except:
                item = ic.session.data_objects.get(irodsDataPath)
            ic.downloadData(item, downloadDir, ic.getSize([irodsDataPath]), force = False)
            print()
            print(BLUE+'Download complete with the following parameters:')
            print(json.dumps(config, indent=4))
            print(DEFAULT)
        else:
            sys.exit(2)
    else:
        print('Not an implemented operation.')
        sys.exit(2)


if __name__ == "__main__":
   main(sys.argv[1:])    
    
