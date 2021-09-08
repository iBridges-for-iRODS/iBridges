import os
import sys
import socket
import logging
from datetime import datetime
from json import dump


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

def getSizeList(folder, files):
    size = 0
    for file in files:
        size += os.path.getsize(folder + os.sep + file)
    return size


def networkCheck(hostname):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.settimeout(10.0)
        s.connect((hostname, 1247))
        return True
    except socket.error as e:
        return False

    s.close()


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
    envFile = ienv["ui_ienvFilePath"]
    with open(envFile, 'w') as f:
        dump(ienv, f)


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


# Create logger, it is important to note that it either writes prints to the console or the logfile! 
def setup_logger(log_stdout = False):
    log_folder = get_filepath() + os.sep + "logs"
    if not check_direxists(log_folder):
        os.makedirs(log_folder)
    #current_imestamp = datetime.now().strftime("%y-%m-%dT%H_%M_%S")
    #file_path = log_folder + "/log_" + current_imestamp + ".log"
    file_path = log_folder + "/current_session.log"

    log_format = '[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s'
    handlers = [logging.FileHandler(file_path, 'a'), logging.StreamHandler(sys.stdout)]#, logging.StreamHandler()
    logging.basicConfig(format = log_format, level = logging.INFO, handlers = handlers)
    logger = logging.getLogger()
    if log_stdout == True:
        sys.stderr.write = logger.error
        sys.stdout.write = logger.info

