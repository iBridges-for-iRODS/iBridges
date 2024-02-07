import os
from ibridges import Session
from ibridges.utils.path import IrodsPath
from ibridges.irodsconnector.sync import IBridgesSync

session = Session(irods_env_path=os.path.expanduser("~/.irods/irods_environment.json"))

print(session.username)

source='/data/ibridges'
target_path='research-test-christine/books/otherbooks'
target_path='research-test-christine/books'

#TODO
# does it need to create the remote root folder(s) it's syncing to?


# extend the home path with a new sub collection
target = IrodsPath(session, "~", target_path)
ibs=IBridgesSync(source=source, target=target, session=session)

exit()

files, folders=ibs.get_irods_tree(path=ibs.target)

for folder in folders:
    print(folder.path)


print()

for file in files:
    print(file.name, file.path, file.size, file.checksum)

print()

files, folders=ibs.get_filesystem_tree(path=source)

for file in files:
    print(file.name, file.path, file.size, file.checksum)

for folder in folders:
    print(folder.path)


