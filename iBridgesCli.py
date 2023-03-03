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
from utils.IrodsConnector import IrodsConnector
from utils.IrodsConnector import FreeSpaceNotSet
from utils.IrodsConnectorIcommands import IrodsConnectorIcommands
from irods.exception import ResourceDoesNotExist, NoResultFound

import configparser
import os
import sys
import json
import getopt
import getpass
from utils.utils import setup_logger, get_local_size, ensure_dir

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
    if 'iRODS' not in args:
        raise AttributeError("iRODS environment not defined.")

    return args


def annotateElab(annotation, ic, elab, coll, title='Data in iRODS'):
    """
    Example annotation
    annotation = {
            "Data size": f'{size} Bytes',
            "iRODS path": coll.path,
            "iRODS server": ic.session.host,
            "iRODS user": ic.session.username,
        }
    """
    # YODA: webdav URL does not contain "home", but iRODS path does!
    if ic.davrods and ("yoda" in ic.session.host or "uu.nl" in ic.session.host):
        elab.addMetadata(
            ic.davrods+'/'+coll.path.split('home/')[1].strip(),
            meta=annotation,
            title=title)
    elif ic.davrods and "surfsara.nl" in ic.session.host:
        elab.addMetadata(
            ic.davrods+'/'+coll.path.split(ic.session.zone)[1].strip('/'),
            meta=annotation,
            title=title)
    elif ic.davrods:
        elab.addMetadata(
            ic.davrods+'/'+coll.path.strip('/'),
            meta=annotation,
            title=title)
    else:
        host = ic.session.host
        zone = ic.session.zone
        name = ic.session.username
        port = ic.session.port
        path = coll.path
        conn = f'{{{host}\n{zone}\n{name}\n{port}\n{path}}}'
        elab.addMetadata(conn, meta=annotation, title='Data in iRODS')


def connectIRODS(config):

    # icommands present and irods_environment file present and user wants to use standard envFile
    standardEnv = os.path.expanduser('~' + os.sep+'.irods' + os.sep + 'irods_environment.json')
    if os.path.exists(standardEnv) and \
            (config['iRODS']['irodsenv'] == '' or config['iRODS']['irodsenv'] == standardEnv):
        try:
            ic = IrodsConnectorIcommands()
            print(BLUE+"INFO: Icommands and standard environment file are present.")
            print("INFO: Using icommands for data up and download."+DEFAULT)
        except ConnectionRefusedError:
            raise
        except FileNotFoundError:
            raise
        except EnvironmentError:
            print("INFO: Connect with python API")
            success = False
            while not success:
                passwd = getpass.getpass(
                    'Password for '+os.environ['HOME']+'/.irods/irods_environment.json'+': ')
                ic = IrodsConnector(config['iRODS']['irodsenv'], passwd)
                try:
                    ic.session.pool.get_connection
                    success = True
                except Exception as e:
                    print(RED+"AUTHENTICATION failed. "+repr(e)+DEFAULT)
                    res = input('Try again (Y/N): ')
                    if res not in ['Y', 'y']:
                        sys.exit(2)
        except Exception:
            raise

    elif os.path.exists(config['iRODS']['irodsenv']):
        print("INFO: Connect with python API")
        success = False
        while not success:
            passwd = getpass.getpass(
                    'Password for '+config['iRODS']['irodsenv']+': ')
            ic = IrodsConnector(config['iRODS']['irodsenv'], passwd)
            try:
                ic.session.pool.get_connection()
                success = True
            except Exception as e:
                print(RED+"AUTHENTICATION failed. "+repr(e)+DEFAULT)
                res = input('Try again (Y/N): ')
                if res not in ['Y', 'y']:
                    sys.exit(2)

        print(BLUE+"INFO: Data up and download by python API."+DEFAULT)

    else:
        raise FileNotFoundError('Environment file not found e.g. ' + standardEnv)

    return ic


def setupIRODS(config, operation):
    """
    Connects to iRODS and sets up the environment.
    """
    ic = connectIRODS(config)
    if operation == 'download':
        return ic

    # set iRODS path
    try:
        ic.ensure_coll(config['iRODS']['irodscoll'])
        print(YEL+'Uploading to '+config['iRODS']['irodscoll']+DEFAULT)
    except Exception:
        print(RED+"Collection path not set in config or invalid: " + config['iRODS']['irodscoll']+DEFAULT)
        success = False
        while not success:
            iPath = input('Choose iRODS collection: ')
            try:
                ic.ensure_coll(iPath)
                config['iRODS']['irodscoll'] = iPath
                print(YEL+'Uploading to '+config['iRODS']['irodscoll']+DEFAULT)
                success = True
            except Exception:
                print(RED+"Collection path not valid: " + config['iRODS']['irodscoll']+DEFAULT)

    # Set iRODS resource
    # Look in config, then in ienv

    print(YEL+"Confirming resource in config: " + config['iRODS']['irodsresc'])
    try:
        resource = ic.get_resource(config['iRODS']['irodsresc'])
        try:
            print(config['iRODS']['irodsresc'] + " upload capacity, free space: " + \
                  str(round(int(ic.resource_space(resource.name) * ic.multiplier)) + 'GB'))
        except FreeSpaceNotSet:
            ic.ienv.setdefault('force_unknown_free_space', 'True')
            print(config['iRODS']['irodsresc'] + " upload capacity, free space: No  inofrmation")
    except (NoResultFound, ResourceDoesNotExist):
        print(RED+'iRODS resource does not exist: '+config['iRODS']['irodsresc']+DEFAULT)
        try:
            print(YEL+'Checking env-file: '+ic.default_resc)
            resource = ic.get_resource(ic.default_resc)
            config['iRODS']['irodsresc'] = ic.default_resc
            try:
                print(config['iRODS']['irodsresc'] + " upload capacity, free space: " + \
                      str(round(int(ic.resource_space(resource.name) * ic.multiplier)) + 'GB'))
            except FreeSpaceNotSet:
                ic.ienv.setdefault('force_unknown_free_space', 'True')
                print(config['iRODS']['irodsresc'] + " upload capacity, free space: No  inofrmation")
        except Exception:
            print(RED+"No resource set in environment file either ('irods_resource_name')"+DEFAULT)
            print(RED+"ERROR: No resource set"+DEFAULT)
            ic.session.cleanup()
            sys.exit(2)
    except Exception:
        print(RED+'iRODS resource not found: '+config['iRODS']['irodsresc']+DEFAULT)
        print(RED+'No valid resource set.')
        ic.session.cleanup()
        sys.exit(2)

    return ic


def setupELN(config):
    md = elabConnector(config['ELN']['token'])
    if config['ELN']['group'] != '' and config['ELN']['experiment'] != '':
        try:
            md.updateMetadataUrl(group=config['ELN']['group'],
                                 experiment=config['ELN']['experiment'])
        except Exception:
            print(RED+'ELN groupID or experimentID not set or valid.'+DEFAULT)
            md.showGroups()
            md.updateMetadataUrlInteractive(group=True)
    else:
        md.showGroups()
        md.updateMetadataUrlInteractive(group=True)

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
    # store verified dataPath
    config["iRODS"]["uploadItem"] = dataPath

    size = get_local_size([dataPath])
    freeSpace = int(ic.get_free_space(config['iRODS']['irodsresc']))
    print('Checking storage capacity for ' + dataPath + ', ' + str(float(size) * ic.multiplier) + 'GB')

    if freeSpace is not None and int(freeSpace)-1000**3 < size:
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
    if not ic.session.data_objects.exists(irodsItemPath) and \
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
        config["iRODS"]["downloadItem"] = irodsItemPath

    if 'DOWNLOAD' not in config.keys():
        config['DOWNLOAD'] = {'path': ''}

    if config['DOWNLOAD']['path'] == '' or os.path.isfile(config['DOWNLOAD']['path']):
        print(RED+'No download directory given'+DEFAULT)
        success = False
        while not success:
            dataPath = input('Download directory: ')
            success = ensure_dir(dataPath)
            if not success:
                abort = input('Abort download? (Y/N): ')
                if abort == "Y":
                    ic.session.cleanup()
                    sys.exit(2)
            else:
                config["DOWNLOAD"]["path"] = dataPath
                return ensure_dir(config['DOWNLOAD']['path'])
    else:
        return ensure_dir(config['DOWNLOAD']['path'])

    return True


def printHelp():
    print('Data upload client')
    print('Uploads local data to iRODS, and, if specified, links dat to an entry in a metadata store (ELN).')
    print('Usage: ./iBridgesCli.py -c, --config= \t config file')
    print('\t\t    -d, --data= \t datapath')
    print('\t\t    -i, --irods= \t irodspath (download)')
    print('Examples:')
    print('Downloading: ./iBridgesCli.py -c <yourConfigFile> --irods=/npecZone/home')
    print('Uploading: ./iBridgesCli.py -c <yourConfigFile> --data=/my/data/path')


def main(argv):

    irodsEnvPath = os.path.expanduser('~') + os.sep + ".irods"
    setup_logger(irodsEnvPath, "iBridgesCli")

    try:
        opts, args = getopt.getopt(argv, "hc:d:i:", ["config=", "data=", "irods="])
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
                config = getConfig(arg)
            except Exception:
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

    # initialise iRODS
    if operation is None:
        print(RED+"ERROR: missing parameter."+DEFAULT)
        printHelp()
        sys.exit(2)
    ic = setupIRODS(config, operation)
    # initialise medata store connetcions
    if 'ELN' in config and operation == 'upload':
        md, title = setupELN(config)
    else:
        md = None

    # check files for upload
    if operation == 'upload':
        if len(config) == 1:
            print(BLUE+"INFO: No metadata store configured. Only upload data to iRODS."+DEFAULT)
        if prepareUpload(dataPath, ic, config):
            if md is not None:
                iPath = config['iRODS']['irodscoll'] + '/' + md.__name__ + '/' + \
                    str(config['ELN']['group']) + '/'+str(config['ELN']['experiment'])
            # elif os.path.isdir(dataPath):
            #     iPath = config['iRODS']['irodscoll']+'/'+os.path.basename(dataPath)
            else:
                iPath = config['iRODS']['irodscoll']
            iColl = ic.session.collections.get(iPath)
            dataPath = config["iRODS"]["uploadItem"]
            ic.upload_data(dataPath, iColl, config['iRODS']['irodsresc'],
                           get_local_size([dataPath]), force=True)
        else:
            ic.session.cleanup()
            sys.exit(2)
        # tag data in iRODS and metadata store
        if md is not None:
            coll = ic.session.collections.get(iPath)
            metadata = {
                "iRODS path": coll.path,
                "iRODS server": ic.session.host,
                "iRODS user": ic.session.username,
            }
            if config["ELN"]["title"] == '':
                annotateElab(metadata, ic, md, coll, title='Data in iRODS')
            else:
                annotateElab(metadata, ic, md, coll, title=config["ELN"]["title"])

            if os.path.isfile(dataPath):
                item = ic.session.data_objects.get(
                    coll.path+'/'+os.path.basename(dataPath))
                ic.addMetadata([item], 'ELN', md.metadataUrl)
            elif os.path.isdir(dataPath):
                upColl = ic.session.collections.get(
                            coll.path+'/'+os.path.basename(dataPath))
                items = [upColl]
                for c, _, objs in upColl.walk():
                    items.append(c)
                    items.extend(objs)
                ic.addMetadata(items, 'ELN', md.metadataUrl)

        print()
        print(BLUE+'Upload complete with the following parameters:')
        print(json.dumps(config, indent=4))
        print(DEFAULT)
        ic.session.cleanup()
    elif operation == 'download':
        if prepareDownload(irodsPath, ic, config):
            downloadDir = config['DOWNLOAD']['path']
            irodsDataPath = config["iRODS"]["downloadItem"]
            print(YEL,
                  'Downloading: ' + irodsDataPath + ', ' + \
                  str(ic.get_irods_size([irodsDataPath]) * ic.multiplier) + 'GB',
                  DEFAULT)
            try:
                item = ic.session.collections.get(irodsDataPath)
            except Exception:
                item = ic.session.data_objects.get(irodsDataPath)
            print(item, downloadDir)
            ic.download_data(item, downloadDir, ic.get_irods_size([irodsDataPath]), force=False)
            print()
            print(BLUE+'Download complete with the following parameters:')
            print(json.dumps(config, indent=4))
            print(DEFAULT)
            ic.session.cleanup()
        else:
            ic.session.cleanup()
            sys.exit(2)
    else:
        print('Not an implemented operation.')
        sys.exit(2)


if __name__ == "__main__":
    main(sys.argv[1:])
