import os
import socket
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
    