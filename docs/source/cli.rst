Command Line Interface
======================

iBridges also has a Command Line Interface (CLI). The CLI provides an even more simplified
interface for uploading, downloading and synchronising. It does not provide (nor intends to) all the features
that are available in the iBridges API library. It is mainly there for users that are not familiar with Python
and still want to download or upload their data using the interface, or if you need a simple iBridges operation
in your shell script without having to create a new python script.

.. note::

    There are no CLI commands to add/change metadata, instead use the iBridges API for this.


.. _cli-setup:

Setup
-----

As with the ibridges API, you will need to create an `irods_environment.json`. We have created a plugin system to automatically
create the environment file for you. Below are the currently (known) plugins, see the links for installation instructions:

.. list-table:: Server configuration plugins
    :widths: 50 50
    :header-rows: 1

    * - Organization
      - Link
    * - Utrecht University
      - https://github.com/UtrechtUniversity/ibridges-servers-uu

After installation, you will be able to create an `irods_environment.json` by simply answering questions like which email-address
you have. First find the server name with:

.. code:: shell

    ibridges setup --list

Then finish the setup using the server name you just found:

.. code:: shell

    ibridges setup server_name

If your organization does not provide a plugin, then you will have to create the `environment.json` yourself (with 
the help of your iRODS administrator).

It is the easiest if you put this file
in the default location: `~/.irods/irods_environment.json`, because then it will be automatically detected. However,
if you have it in another location for some reason (let's say you have multiple environments), then you can tell the
ibridges CLI where it is:

.. code:: shell

    ibridges init path/to/some_irods_env_file.json

This will most likely ask for your password. After filling this in, iBridges will cache your password, so that
you will not have to type it in every time you use an iBridges operation. This is especially useful if you want
to execute scripts that run in the background. Note that the time your cached password is valid depends on the
administrator settings of your iRODS server.

iBridges stores the location of your iRODS environment file in `~/.ibridges/ibridges_cli.json`. You can safely delete
this file if somehow it gets corrupted. If you have the iRODS environment in the default location, it can still be
useful to cache the password so that the next commands do not ask for your password anymore:

.. code:: shell

    ibridges init


Listing remote files
--------------------

To list the dataobjects and collections that are available on the iRODS server, you can use the `ibridges list` command:

.. code:: shell

    ibridges list "irods:/path/to/some_collection"

If you don't supply a collection to display, it will list the data objects and collections in your `irods_home` directory which you can specify in your `~/.irods/irods_environment.json`.

If you want to list a collection in your `irods_home`, you can use `~` as an abbreviation:

.. code:: shell

    ibridges list "irods:~/collection_in_home"


Please try to avoid spaces in collection and data object names! If you really need them, you must enclose the path with `"`. That also holds true for local paths.


.. note::


    Note that all data objects and collections on the iRODS server are always preceded with "irods:". This is done to distinguish local and remote files.
    
    
Creating a new collection
--------------------

To create a new collection in you iRODS home simply type:

.. code:: shell

	ibridges mkcoll "irods:~/new_collection"	

Or:

.. code:: shell
  	
  	ibridges mkcoll "irods:/full/path/to/new_collection"


Downloading data
----------------

The basic command to download a data object or collection is `ibridges download`:

.. code:: shell

    ibridges download "irods:~/some_collection/some_object" download_dir

The download_dir argument is optional. If it is left out, it will be put in the current working directory.

There are two more options: `--overwrite` to allow the download command to overwrite a local file and
`--resource` to set the resource to download the data from. See `ibridges download --help` for more details.


Uploading data
--------------

The command to upload files and directories to an iRODS server is similar to the `download` command:

.. code:: shell

    ibridges upload my_file "irods:~/some_collection"

.. note::

    In contrast to the `download`` command, the `upload`` command always needs a 
    destination collection or data object.


Synchronising data
------------------

In some cases, instead of downloading/uploading your data, you might want to synchronise data between local
folders and collections. The `sync` command does this synchronisation and only transfers files/directories 
that are missing or have a different checksum (content). 

.. code:: shell

    ibridges sync some_local_directory "irods:~/remote_collection"


.. note::

    The order of the directory/collection that you supply to `ibridges sync` matters. The first argument is the `source`
    directory/collection, while the second argument is the `destination` directory/collection. Transfers will only happen
    from `source` to `destination`, so extra or updated files in the `destination` directory will not be transferred.
