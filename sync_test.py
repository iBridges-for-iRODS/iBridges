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


# now just doing folder --> collection (and vv), not files, --> collection. do that too?

# not doing:
#   --link - ignore symlink --> can we make that default?
#   -a   synchronize to all replicas if the target is an iRODS dataobject/collection.
#   --age age_in_minutes - The maximum age of the source copy in minutes for sync.

