import os
import sys
import socket
import logging
from datetime import datetime
from json import dump


def ensure_dir(path):
    try:
        if not os.path.exists(path):
            os.makedirs(path)
        return True
    except:
        return False 


def getSize(pathList):
    size = 0
    for p in pathList:
        if os.path.isdir(p):
            for dirpath, dirnames, filenames in os.walk(p):
                for i in filenames:
                    f = os.path.join(dirpath, i)
                    size += os.path.getsize(f)
        elif os.path.isfile(p):
            size = size + os.path.getsize(p)
    return size


def can_connect(hostname):
    """Check connectivity to an iRODS server.

    Parameters
    ----------
    hostname : str
        FQDN/IP of an iRODS server.

    Returns
    -------
    bool
        Connection to `hostname` possible.

    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.settimeout(10.0)
            sock.connect((hostname, 1247))
            return True
        except socket.error:
            return False


def walkToDict(root):
    #irods collection
    items = []
    for collection, subcolls, _ in root.walk():
        items.append(collection.path)
        items.extend([s.path for s in subcolls])
    walkDict = {key: None for key in sorted(set(items))}
    for collection, _,  objs in root.walk():
        walkDict[collection.path] = [o.name for o in objs]

    return walkDict


def getDownloadDir():
    if os.name == 'nt':
        import winreg
        sub_key = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders'
        downloads_guid = '{374DE290-123F-4565-9164-39C4925E467B}'
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key) as key:
            location = winreg.QueryValueEx(key, downloads_guid)[0]
        return location
    else:
        return os.path.join(os.path.expanduser('~'), 'Downloads')


def saveIenv(ienv):
    if "ui_ienvFilePath" in ienv:
        envFile = ienv["ui_ienvFilePath"]
    else:
        envFile = os.path.join(os.path.expanduser("~"), ".irods"+os.sep+"irods_environment.json")
        ienv["ui_ienvFilePath"] = envFile
    with open(envFile, 'w') as f:
        dump(ienv, f, indent=4)
    return envFile


# needed to get the workdir for executable & normal operation
def get_filepath():
    if getattr(sys, 'frozen', False):
        file_path = os.path.dirname(sys.executable)
    elif __file__:
        file_path = os.path.dirname(__file__)
    return file_path

# check if a given directory exists on the drive
def check_direxists(dir):
    if _check_exists(dir):
        return os.path.isdir(dir)
    return False

def check_fileexists(file):
    if _check_exists(file):
        return os.path.isfile(file)
    return False

def _check_exists(fname):
    if fname is None:
        return False
    if not os.path.exists(fname):
        return False
    return True


def setup_logger(logdir, appname):
    """Initialize the application logging service.

    Parameters
    ----------
    logdir : str
        Path to logging location.
    appname : str
        Base name for the log file.

    """
    logfile = logdir.joinpath(f'{appname}.log')
    log_format = '[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s'
    handlers = [
        logging.handlers.RotatingFileHandler(logfile, 'a', 100000, 1),
        logging.StreamHandler(sys.stdout),
    ]
    logging.basicConfig(
        format=log_format, level=logging.INFO, handlers=handlers)
    # Indicate start of a new session
    with open(logfile, 'a', encoding='utf-8') as logfd:
        logfd.write('\n\n')
        underscores = f'{"_"*50}\n'
        logfd.write(underscores)
        logfd.write(underscores)
        logfd.write(f'\t\t{datetime.now().isoformat()}\n')
        logfd.write(underscores)
        logfd.write(underscores)
