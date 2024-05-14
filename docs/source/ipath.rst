iRODS paths
===========

iRODS paths follow a certain pattern just like the local paths of different operatings systems.

In iRODS the `/` is used as separator and all paths on an iRODS server start with `/<zone_name>`.

Users usually have a personal `home` collection in iRODS: `/<zone_name>/home/<user name>`.
Group-based iRODS instances like Yoda will give you access to a group `home` collection: `/<zone_name>/home/<group name>`

IrodsPath
---------

iBridges offers an `IrodsPath` class to conveniently work with those paths. It implements a selection of functions which are comparable to their counterparts in `pathlib`.

In the installation we showed you how to set a default `home`, for which we can address by `~` in `IrodsPath`.

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

Assume we would like to create a counter part collection to our local path:

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

Summary
-------

To work with pathlib and IrodsPath is safer since it takes care of the correct concatenation of parts of the path according to the operating system and their specific setup.

