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
