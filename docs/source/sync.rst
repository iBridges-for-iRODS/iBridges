Synchronise your Data
=====================

The iBridges function `sync` synchronises data between your local file system and the iRODS server.
It compares path, size and optionally checksum of local and remote files to determine whether they have changed and should be synchronized. It creates files or overwrites older copies, but does not delete files from the target location when they have been deleted from the source.

The function works in both directions: synchronization of data from the client's local file system to iRODS, or from iRODS to the local file system. The direction is given by the type of path and the order.

Update your data in iRODS
-------------------------

The code below shows how to synchronise from your local file system to iRODS. The data in iRODS will be updated. 

.. code-block:: python

    from pathlib import Path
    from ibridges.path import IrodsPath
    from ibridges.sync import sync_data

    target = IrodsPath(session, "~", "<irods path>")
    source = Path(os.path.expanduser("~"), "<local path>")

    # call the synchronisation
    changes = sync_data(session=session, source=source, target=target)

The changes are tracked in `changes`. `changes["changed_folders"]` contains the added folders on 
the local file system, `changes["changed_files"]` contains the updated or added  files.

Update your local data
----------------------

the code below shows hot to synchronise from your iRODS instance to your local file system. Your local data will be updated.

.. code-block:: python

    from pathlib import Path
    from ibridges.path import IrodsPath
    from ibridges.sync import sync_data
    target = Path("~").expanduser(), "<local path>")
    source = IrodsPath(session, "~", "<irods path>")

    # call the synchronisation
    changes = sync_data(session=session, source=source, target=target)

Dry run
-------

The `dry-run` option will only list what would be changed without actually executing the changes:

.. code-block:: python

    from pathlib import Path
    from ibridges.path import IrodsPath
    from ibridges.sync import sync_data
    target = Path("~").expanduser(), "<local path>")
    source = IrodsPath(session, "~", "<irods path>")

    # call the synchronisation
    changes = sync_data(session=session, source=source, target=target, dry_run=True)

The potential updates are listed in the prompt and in the `changes` dictionary as shown above.

Options
-------

`sync` takes various options:

- The `max_level` option controls the depth up to which the file tree will be synchronized. With max_level set to None (default), there is no limit (full recursive synchronization). A max level of 1 synchronizes only the source's root, max level 2 also includes the first set of subfolders/subcollections and their contents, etc.

- The `copy_empty_folders` (default `False`) option controls whether folders/collections that contain no files or subfolders/subcollections will be synchronized.

- The `dry_run` option lists all the source files and folders that need to be synchronized without actually performing the synchronization.

By default, checksums of all transferred files will be calculated and verified after up- or downloading. A checksum mismatch will generate an error, aborting the synchronization process. Should this happen, it is possible some hiccup occurred during the transfer process. Check both copies of the offending file, and retain the correct one.
