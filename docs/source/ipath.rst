iRODS paths
===========


iRODS paths follow a certain pattern just like the local paths of different operating systems.
To allow for similar path operations on iRODS paths, rather than using strings, `iBridges` offers an class with similar `pathlib`-like functionality.

**Why prefer `pathlib.path` and `IrodsPath` over strings?**

.. note::

    - To work with pathlib and IrodsPath is **safer** since it takes care of the correct concatenation of parts of the path according to the operating system and their specific setup.
    - To work with pathlib and IrodsPath is **more convenient** since you can easily determine certain parts of a path, like parent, name and parts and easily check whether a path exists.


A complete tutorial on iRODS paths can be followed `here <https://github.com/UtrechtUniversity/iBridges/tree/main/tutorials>`__.

IrodsPath
---------

In iRODS the `/` is used as separator and all paths on an iRODS server start with `/<zone_name>`.
Users usually have a personal `home` collection in iRODS: `/<zone_name>/home/<user name>`.
Group-based iRODS instances like Yoda will give you access to a group `home` collection: `/<zone_name>/home/<group name>`

iBridges implements a selection of functions which are comparable to their counterparts in `pathlib`.

In the :doc:`Installation <install>` we showed you how to set a default `home`, which we can address by `~` in `IrodsPath`.

.. code-block:: python

    from ibridges import IrodsPath
    home = IrodsPath(session, '~')
    print(home)

This will give you the value which you set in the `irods_environment.json`. If you did not set any `irods_home` the home will default to `/<zone_name>/home/<user name>`.

**Note**, that we still need to verify whether the path exists on the iRODS server. 

.. code-block:: python
   
    home.collection_exists()

Below we present a selection of possible iRODS path manipulations:

.. code-block:: python

    irods_path = IrodsPath(session, session.home)
    print(f'Extend {irods_path}:', irods_path.joinpath('new_collection'))
    print(f'{irods_path} exists:', irods_path.exists())
    print(f'{irods_path} is collection:', irods_path.collection_exists())
    print(f'{irods_path} is data object:', irods_path.dataobject_exists())
    print(f'{irods_path} has parts: {irods_path.parts}') 

Concatenating iRODS paths and local paths
-----------------------------------------

In data transfers often iRODS collections that correspond to a local folder have to be created.
Below we show how you can create an iRODS collection with the same name as an arbitrary local folder.

We create the local path that points to a folder:

.. code-block:: python
    
    from pathlib import Path
    path  = Path.home().joinpath('new_dir')
    print(path)

We will create `new_dir` in our iRODS home collection:

.. code-block:: python
    
    from ibridges import IrodsPath

    name = path.name
    irods_home = IrodsPath(session, '~')
    new_irods_coll_path = irods_home.joinpath(name)
    print(new_irods_coll_path)

    coll = IrodsPath.create_collection(session, new_irods_coll_path)
