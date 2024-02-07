from ibridges import Session
from  ibridges.irodsconnector.data_operations import is_collection, get_collection
from ibridges.utils.path import IrodsPath
import os, json
import os
from pathlib import Path
from os import walk


# with open(os.path.expanduser("~/.irods/irods_environment.json"), "r") as f:
#     ienv = json.load(f)
# password = 'TXweOC4VVLNVFwKhpC8eG-8XLHY0papB'
session = Session(irods_env_path=os.path.expanduser("~/.irods/irods_environment.json"))


# print(session.username)
# print(session.default_resc) # the resource to which data will be uploaded
# print(session.zone) # default home for iRODS /zone/home/username
# print(session.server_version)


source='/data/ibridges'
target='research-test-christine/books/otherbooks'
target='research-test-christine/books'


# how to judge what is local and what is remote?

class IBridgesSync:

    def __init__(self, source, target) -> None:
        #TODO
        # make sure both exist (or should we create the root as well?)
        self.source=source
        self.target=target

    def get_local(self):
        local_files=[]
        local_folders=[]
        for root, dirs, files in Path(self.source).walk(on_error=print):
            for file in files:
                local_files.append(root / file)
                local_folders.extend([root / dir for dir in dirs])
        return local_files, sorted(local_folders, key=lambda x: len(str(x)))

    def get_remote(self):
        if not is_collection(self.target):
            raise ValueError("%s is not a collection" % self.target)



# extend the home path with a new sub collection
irods_path = IrodsPath(session, "~", target)

print(irods_path)

print(irods_path.collection_exists())


def fuck(session, path, paths):
    coll=get_collection(session=session, path=path)
    for col in coll.subcollections:
        print(col)


fuck(session, irods_path)

exit()

ibs=IBridgesSync(source=source, target=target)

# files, folders=ibs.get_local()

# for item in files:
#     print(item, item.name, item.stat().st_size)



ibs.get_remote()

# for item in files:
#     print(item, item.name, item.stat().st_size)

#TODO
# auto determine local/remote which is which
# does it need to create the remote root folder(s) it's syncing to?


# get file tree SOURCE
# get file tree TARGET
