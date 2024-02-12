import os
from ibridges import Session
from ibridges.utils.path import IrodsPath
from ibridges.irodsconnector.sync import IBridgesSync

session = Session(irods_env_path=os.path.expanduser("~/.irods/irods_environment.json"))

# print(session.username)
# IkLMYhSTgiDlyV86dwipxttk-NCBNsHS

source='/data/ibridges'
target_path='research-test-christine/books/otherbooks'
target_path='research-test-christine/books'


source_path='research-test-christine/books'

#TODO
# does it need to create the remote root folder(s) it's syncing to?



# extend the home path with a new sub collection
target = IrodsPath(session, "~", target_path)
# source = IrodsPath(session, "~", source_path)

# source='/data/ibridges'
# target='/data/ibridges'



# source, target=target, source

# None = recursive
max_level=None
dry_run=True
no_checksum=False

ibs=IBridgesSync(
       source=source,
       target=target,
       session=session,
       max_level=max_level,      
       dry_run=dry_run,
       no_checksum=no_checksum)

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



"""
    max_level: 1 for not-recursive, None for (fully) recursive. test with dry_run
"""