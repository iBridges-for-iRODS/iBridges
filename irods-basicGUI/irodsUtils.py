import os
import socket


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
        s.connect(('scomp1461.wur.nl', 22))
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

