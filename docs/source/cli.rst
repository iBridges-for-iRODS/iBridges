Command Line Interface
======================

iBridges also has a Command Line Interface (CLI). The CLI provides an even more simplified
interface for uploading, downloading and synchronizing. It does not provide (or intends to) all the features
that are available in the iBridges API library. It is mainly there for users that are not familiar with Python
and still want to download or upload their data using the interface, or if you need a simple iBridges operation
in your shell script without having to create a new python script.


Setting up
----------

To use the ibridges CLI, you will have to create an irods environment file and put it in the default location:
`~/.irods/irods_environment.json`. Then, you should log into your irods server once with the following command:

.. code:: shell

    ibridges init

This will most likely ask for your password. After filling this in, iBridges will cache your password, so that
you will not have to type it in every time you use an iBridges operation. This is especially useful if you want
to execute scripts that run in the background. Note that the time your cached password is valid depends on the
administrator settings of your iRods server.


Downloading data
----------------

The basic command to download a data object or collection is `ibridges download`:

.. code:: shell

    ibridges download "irods:~/some_collection/some_object.json" [download_dir]

There are two more options: `--overwrite` to allow the download command to overwrite a local file and
`--resource` to set the resource to download the data from. See `ibridges download --help` for more details.

.. note::

    Note that all data objects and collections on the iRods server are always preceded with "irods:". This is
    done to distinguish local and remote files.

Uploading data
--------------

The command to upload files and directories to an iRods server is similar to the `download` command:

.. code:: shell

    ibridges upload my_file.json "irods:~/some_collection"

.. note::

    In contrast to the `download`` command, the `upload`` command always needs a desination collection or data
    object.


Synchronizing data
------------------

In some cases, instead of downloading/uploading your data, you might want to synchronize data between local
folders and collections. The `sync` command does this synchronization and only transfers files/directories 
that are missing or have a different checksum (content).

.. code:: shell

    ibridges sync some_local_directory "irods:~/remote_collection"

.. note::

    There are no CLI commands to add/change metadata, instead use the iBridges API for this.
