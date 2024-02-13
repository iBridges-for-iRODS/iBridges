import os
from ibridges import Session
from ibridges.utils.path import IrodsPath
from ibridges.irodsconnector.sync import sync

session = Session(irods_env_path=os.path.expanduser("~/.irods/irods_environment.json"))

# print(session.username)
# IkLMYhSTgiDlyV86dwipxttk-NCBNsHS

source='/data/ibridges'
target_path='research-test-christine/books/otherbooks'
target_path='research-test-christine/books'


source_path='research-test-christine/books'


# extend the home path with a new sub collection
target = IrodsPath(session, "~", target_path)
# source = IrodsPath(session, "~", source_path)

# source='/data/ibridges'
# target='/data/ibridges'



source, target=target, source

# None = recursive
max_level=1
max_level=None

dry_run=False
# dry_run=True
ignore_checksum=False
# ignore_checksum=True
copy_empty_folders=True
verify_checksum=True



sync(
    source=source,
    target=target,
    session=session,
    max_level=max_level,      
    dry_run=dry_run,
    ignore_checksum=ignore_checksum,
    verify_checksum=verify_checksum,
    copy_empty_folders=copy_empty_folders)



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