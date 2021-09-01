#!/usr/bin/env python3

"""
Commandline client to upload data to a storage service and double-link the storage location with a metadata store.

Implemented for:
    Storage types:
        iRODS
    Metadtaa stores:
        Elabjournal
"""

from elabConnector import elabConnector
from irodsConnector import irodsConnector
from irodsConnectorIcommands import irodsConnectorIcommands
from irods.exception import ResourceDoesNotExist

import configparser
import os
import sys
import json
import getopt
import getpass
import subprocess

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
    standardEnv = os.path.expanduser('~' +os.sep+'.irods/irods_environment.json')
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
        except Exception as e:
           raise

    elif os.path.exists(config['iRODS']['irodsenv']):
        passwd = getpass.getpass(
                    'Password for '+os.environ['HOME']+'/.irods/irods_environment.json'+': ')
        ic = irodsConnector(config['iRODS']['irodsenv'], passwd)
        print(BLUE+"INFO: Data up and download by python API."+DEFAULT)

    else:
        raise FileNotFoundError('Environment file not found: '+ envFile)

    return ic


def setupIRODS(config):
    """
    Connects to iRODS and sets up the environment.
    """
    ic = connectIRODS(config)

    #set iRODS path
    try:
        coll = ic.ensureColl(config['iRODS']['irodscoll'])
        print(YEL+'Uploading to '+config['iRODS']['irodscoll']+DEFAULT)
    except:
        print(RED+"Collection path not set or invalid: "+ config['iRODS']['irodscoll']+DEFAULT)
        success = False
        print(''.join([coll.path+'\n' for coll
            in ic.session.collections.get("/"+ic.session.zone+"/home").subcollections]))
        while not success:
            iPath = input('Choose iRODS collection: ')
            try:
                coll = ic.ensureColl(iPath)
                config['iRODS']['irodscoll'] = iPath
                print(YEL+'Uploading to '+config['iRODS']['irodscoll']+DEFAULT)
                success = True
            except:
                print(RED+"Collection path not valid: "+ config['iRODS']['irodscoll']+DEFAULT)

    #set iRODS resource
    try:
        resource = ic.getResource(config['iRODS']['irodsresc'])
        print(config['iRODS']['irodsresc']+ " upload capacity, free space: "+ \
                str(round(int(ic.resourceSize(resource.name))/1024**3))+'GB')
    except ResourceDoesNotExist:
        print(RED+'iRODS resource does not exist: '+config['iRODS']['irodsresc']+DEFAULT)
        resources  = ic.listResources()
        sizes = list(map(ic.resourceSize, resources))
        largestResc = resources[sizes.index(max(sizes))]
        menu = input('Choose '+largestResc+' ('\
                +str(round(int(ic.resourceSize(largestResc))/1024**3))+'GB free)? (Yes/No) ')
        if menu in ['Yes', 'yes', 'Y', 'y']:
            config['iRODS']['irodsresc'] = largestResc
        else:
            print("Aborted: no iRODS reosurce set.")
            sys.exit(2)

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
        print(RED+'Data path odes not exist'+DEFAULT)
        menu = input('Do you want to specify a new path? (Y/N)')
        if menu in ['YES', 'Yes', 'Y', 'y']:
            success = False
            while not success:
                dataPath = input('Full data path: ')
                success = os.path.exists(dataPath)
        else:
            print('Aborted: Data path not given')
    else:
        pass 

    size = getSize(dataPath)
    freeSpace = ic.getResource(config['iRODS']['irodsresc']).free_space

    print('Checking storage capacity for '+dataPath+', '+str(float(size)/(1024**3))+'GB')

    if int(freeSpace)-1024**3 < size:
        print(RED+'Not enough space left on iRODS resource.'+DEFAULT)
        print('Aborted: Not enough space left.')
        return False
    else:
        return True


def getSize(path):
    size = 0
    if os.path.isdir(path):
        for dirpath, dirnames, filenames in os.walk(path):
            for i in filenames:
                f = os.path.join(dirpath, i)
                size += os.path.getsize(f)
    elif os.path.isfile(path):
        size = os.path.getsize(path)

    return size

def main(argv):

    try:
        opts, args = getopt.getopt(argv,"hc:d:",["config="])
    except getopt.GetoptError:
        print('iUpload -h')
        sys.exit(2)

    config = None
    operation = None

    for opt, arg in opts:
        if opt == '-h':
            print('Data upload client')
            print('Uploads local data to iRODS, and, if specified, links dat to an entry in a metadata store (ELN).')
            print('Usage: ./iUpload.py -c, --config= \t config file') 
            print('\t\t    -d, --data= \t datapath')
            sys.exit(2)
        elif opt in ['-c', '--config']:
            try:
               config  = getConfig(arg)
            except:
                print(RED+'No config file found.'+DEFAULT)
                sys.exit(2)
        elif opt in ['-d', '--data']:
            operation = 'upload'
            if arg == '':
                print(RED+'Data upload: No file or directory given.'+DEFAULT)
                sys.exit(2)
            if arg.endswith(os.sep):
                dataPath = arg[:-1]
            else:
                dataPath = arg
        else:
            print('Data upload client')
            print('Uploads local data to iRODS, and, if specified, links dat to an entry in a metadata store (ELN).')
            print('Usage: ./iUpload.py -c, --config= \t config file')
            print('\t\t    -d, --data= \t datapath')
            sys.exit(2)

    #initialise iRODS
    ic = setupIRODS(config)
    #initialise medata store connetcions
    if 'ELN' in config:
        md, title = setupELN(config)
    else:
        md = None

    #check files for upload
    if operation == 'upload':
        if prepareUpload(dataPath, ic, config):
            if md != None:
                iPath = config['iRODS']['irodscoll']+'/'+md.__name__+'/'+ \
                    str(config['ELN']['group'])+'/'+str(config['ELN']['experiment'])
            else:
                iPath = config['iRODS']['irodscoll']
            iColl = ic.ensureColl(iPath)
            print('DEBUG: Created/Ensured iRODS collection '+iPath)
            ic.uploadData(dataPath, iColl, config['iRODS']['irodsresc'], getSize(dataPath))
            diff = ic.diffIrodsLocalfs(
                    config['iRODS']['irodscoll']+os.sep+os.path.basename(dataPath), dataPath)
            if diff == []:
                print(YEL+'Upload complete and checked'+DEFAULT)
            else:
                print(RED+'Upload failed'+DEFAULT)
                print(diff)

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
    else:
        print('Not an implemented operation.')
        sys.exit(2)


if __name__ == "__main__":
   main(sys.argv[1:])    
    
