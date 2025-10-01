How to use the CLI
==================

iBridges also has a Command Line Interface (CLI). The CLI provides a simplified
interface for uploading, downloading and synchronising compared to the Python API. It does not provide (nor intends to) all the features
that are available in the iBridges API library. It is mainly there for users that are not familiar with Python
and still want to download or upload their data using the interface, or if you need a simple iBridges operation
in your shell script without having to create a new python script.

.. note::

    All of the subcommands mentioned below have a :code:`--help` flag to explain
    how the subcommand works:

    .. code:: shell

        ibridges <subcommand> --help

.. note::

    There are no CLI commands to add/change metadata, instead use the iBridges API for this.


.. _cli-setup:

Setup
-----


Create your environment file
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

As with the ibridges API, you will need to create an `irods_environment.json`. We have created a plugin system to automatically
create the environment file for you. Below are the currently (known) plugins, see the links for installation instructions:

.. list-table:: Server configuration plugins
    :widths: 50 50
    :header-rows: 1

    * - Organization
      - Link
    * - Utrecht University
      - https://github.com/iBridges-for-iRODS/ibridges-servers-uu

After installation, you will be able to create an `irods_environment.json` by simply answering questions such as which email-address
you have. First find the server name with:

.. code:: shell

    ibridges setup --list

Then finish the setup using the server name you just found:

.. code:: shell

    ibridges setup server_name

If you want to create in a different location, you can use the :code:`--output` flag:

.. code:: shell

    ibridges setup server_name --output path/to/some/file.json


If your organization does not provide a plugin, then you will have to create the `irods_environment.json` yourself (with 
the help of your iRODS administrator).

It is the easiest if you put this file
in the default location: `~/.irods/irods_environment.json`, because then it will be automatically detected.



Initialize connection to iRODS
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Before you start working with your data, you should select and test your connection with
the iRODS server. This can be done with the :code:`ibridges init` command

.. code:: shell

    ibridges init path/to/some_irods_env_file.json


If you have your iRODS environment file in the default location, then you can simply:

.. code:: shell

    ibridges init

This will most likely ask for your password. After filling this in, iBridges will cache your password, so that
you will not have to type it in every time you use an iBridges operation. This is especially useful if you want
to execute scripts that run in the background. Note that the time your cached password is valid depends on the
administrator settings of your iRODS server.

iBridges stores the location of your iRODS environment file in `~/.ibridges/ibridges_cli.json`. You can safely delete
this file if somehow it gets corrupted. If you have the iRODS environment in the default location, it can still be
useful to cache the password so that the next commands will no longer ask for your password until the cached password expires.

Multiple iRODS environment files
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When you have access to multiple iRODS servers or otherwise need to use multiple environment
files, switching between them can become cumbersome. For that purpose, there is the :code:`ibridges alias`
command:

.. code:: shell

    ibridges alias env1 some/irods_environment_file.json
    ibridges alias env2 other/irods_environment_file.json

Now you can easily switch between different environment files with :code:`ibridges init`:

.. code:: shell

    ibridges init env1 # Now some/irods_environment_file.json is selected
    ibridges init env2 # Now the other environment file is selected.

To see which irods environment file is currently selected:

.. code:: shell

    ibridges alias

This will list all your aliases and used environment files, where the one with the `*`
is the environment currently selected.

To delete an alias, use:

.. code:: shell

    ibridges alias --delete env1


.. _ibridges shell:

The iBridges shell
------------------

After setting up the connection to your iRODS server, you can use the iBridges CLI directly as will
be shown below. There is also another way, which is by using the :code:`ibridges shell` command.
This is a subshell, where instead of typing for example :code:`ibridges ls`, you would type :code:`ls`.
Apart from that, the commands do basically the same as in the CLI. Advantages of using the shell instead
of the CLI are:

- Autocompletion of remote and local paths: use the :code:`TAB` key to complete the path. Unfortunately, this is not available on Windows.
- Short commands such as :code:`ls` are much faster, since the session can be maintained between commands.
- You can look through your iBridges shell history with :code:`up` and :code:`down` key.
- You don't have to type :code:`ibridges` for every command.

More tips and tricks:

- The command :code:`cd` in the :code:`shell` has no effect on the CLI, but the CLI does affect your starting collection in the :code:`shell`.
- Type :code:`?` and :code:`?command` for help on how to use a command.
- Type :code:`!` run something in the bash/zsh shell. For example :code:`!cd some_dir` and :code:`!ls` can be very useful to navigate locally.
- Type :code:`ctrl+d`, :code:`ctrl+c` or :code:`quit` to quit the shell.
- Similarly to the normal shell, use quotes (:code:`''` or :code:`""`) for locations with spaces: :code:`ls "some col with spaces"`.
- The :code:`shell`, :code:`alias`, :code:`init` and :code:`setup` commands are not available.


Navigation
----------

Listing remote data
^^^^^^^^^^^^^^^^^^^


To list the data objects and collections that are available on the iRODS server, you can use the :code:`ibridges list` (or :code:`ibridges ls`) command:

.. code:: shell

    ibridges list "irods:/path/to/some_collection"

If you don't supply a collection to display, it will list the data objects and collections in your `irods_home` directory which you can specify in your `~/.irods/irods_environment.json`.

If you want to list a collection relative to your `irods_home`, you can use `~` as an abbreviation:

.. code:: shell

    ibridges list "irods:~/collection_in_home"

It is generally best to avoid spaces in collection and data object names. If you really need them, you must enclose the path with `"`. That also holds true for local paths.

If you want to have a list that is easier to parse with other command line tools, you can use:

.. code:: shell

    ibridges list --short

You can also see the checksums and sizes of data objects with the long format:

.. code:: shell

    ibridges list --long

.. note::
    Note that all data objects and collections on the iRODS server are always preceded with "irods:". This is done to distinguish local and remote files.

Change working collection
^^^^^^^^^^^^^^^^^^^^^^^^^

With the iBridges CLI you can change your working collection. This is equivalent to
the command line tool :code:`cd`:

.. code:: shell

    ibridges cd some/path/to/collection
    ibridges list  # This will list some/path/to/collection
    ibridges list "./sub" # This will list some/path/to/collection/sub
    ibridges list "sub" # Same as above

To return the current working directory to the home collection simply type :code:`ibridges cd`.

Print current working collection
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This command is equivalent to the Unix `pwd` command and will show the current working collection:

.. code:: shell

    ibridges pwd

Show collection and data object tree
------------------------------------

Sometimes it can be convenient to not only see subcollections and data objects directly under a collection, but
also subsubcollections, etc. deeper in the tree. This works similar to the Unix :code:`tree` command and can be shown as follows:

.. code:: shell

    ibridges tree "irods:~/collection_in_home"

Creating a new collection
-------------------------

To create a new collection in you iRODS home simply type:

.. code:: shell

	ibridges mkcoll "irods:~/new_collection"	

Or:

.. code:: shell
  	
  	ibridges mkcoll "irods:/full/path/to/new_collection"


Downloading data
----------------

The basic command to download a data object or collection is :code:`ibridges download`:

.. code:: shell

    ibridges download "irods:~/some_collection/some_object" download_dir

The download_dir argument is optional. If it is left out, it will be put in the current working directory.

There are two more options: :code:`--overwrite` to allow the download command to overwrite a local file and
:code:`--resource` to set the resource to download the data from. On many iRODS systems you will not need to set
the resource yourself: the server will decide for you. In this case, you should not specify the resource.
Type :code:`ibridges download --help` for more details.


Uploading data
--------------

The command to upload files and directories to an iRODS server is similar to the :code:`download` command:

.. code:: shell

    ibridges upload my_file "irods:~/some_collection"

.. note::

    In contrast to the :code:`download` command, the :code:`upload` command always needs a 
    destination collection or data object.


Synchronising data
------------------

In some cases, instead of downloading/uploading your data, you might want to synchronise data between local
folders and collections. The :code:`sync` command does this synchronisation and only transfers files/directories 
that are missing or have a different checksum (content). 

.. code:: shell

    ibridges sync some_local_directory "irods:~/remote_collection"


.. warning::

    The order of the directory/collection that you supply to :code:`ibridges sync` matters. The first argument is the `source`
    directory/collection, while the second argument is the `destination` directory/collection. Transfers will only happen
    from `source` to `destination`, so extra or updated files in the `destination` directory will not be transferred.


Removing data
-------------

You can remove data objects and collections with the :code:`ibridges rm` command:

.. code:: shell

    ibridges rm irods:some_data_object

.. warning::

    Needless to say, removing data has the potential of data loss. Be careful to check the path before you remove anything.

Collections with underlying subcollections and data objects can also be removed, but similarly to the Unix `rm` you will have to
supply the `-r` flag for recursive removal:

.. code:: shell

    ibridges rm -r irods:some_collection


Searching for data
------------------

It can be helpful to search for data if the exact location is not known. This is done
using the :code:`search` subcommand. There are four different criteria types for searching:
path pattern, checksum, metadata and item type. By default, the search is conducted in the home directory,
but this can be modified by supplying a remote path:

.. code:: shell

    ibridges search irods:some_collection # Search criteria after this

.. note::

    The different matching criteria can be combined. If they are combined all of the
    criteria must be true for the item to show up in the list.

Searching by path pattern
^^^^^^^^^^^^^^^^^^^^^^^^^

Searching by path pattern can search for full or partial names of objects and collections.
For example, to find all :code:`.txt` data objects:

.. code:: shell

    ibridges search --path-pattern "%.txt"
    
Find all :code:`.txt` data objects in a collection :code:`demo`

.. code:: shell

    ibridges search --path-pattern "%/demo/%.txt"


Searching by checksum
^^^^^^^^^^^^^^^^^^^^^

Searching for checksum can be useful to find duplicates of data objects:

.. code:: shell

    ibridges search --checksum "5dfasd%"


Searching by metadata
^^^^^^^^^^^^^^^^^^^^^

Metadata can make data more findable. For example, to find all data objects and
collections that have a metadata entry "key":


.. code:: shell

    ibridges search --metadata "key"

The same can be done for finding metadata with a certain key/value pair:

.. code:: shell

    ibridges search --metadata "key" "value"

Wildcards (:code:`%`) can be particularly useful. For example if we want to
find items with units "kg", we can do:

.. code:: shell

    ibridges search --metadata "%" "%" "kg"

The metadata criterium can be used multiple times:

.. code:: shell

    ibridges search --metadata "key" "value" --metadata "key2" "value2"

Note that in the above example, it is not sufficient for the item to contain
the keys "key" and "key2", and the values "value" and "value2": the entries
must have the key/value pairs as indicated in the command.


Searching by item type
^^^^^^^^^^^^^^^^^^^^^^

By default, the search will return both data objects and collections.
Sometimes it might be useful to only search for collections or data objects.
In this case, you can use the :code:`--item_type` flag:


.. code:: shell

    ibridges search --metadata "key" --item_type collection

or

.. code:: shell

    ibridges search --metadata "key" --item_type data_object


Metadata commands
-----------------

Listing metadata
^^^^^^^^^^^^^^^^

Listing metadata entries for a single collection or data object can be done with the :code:`meta-list`
subcommand:

.. code:: shell

    ibridges meta-list "irods:some_collection"

Adding new metadata
^^^^^^^^^^^^^^^^^^^

To add new metadata for a single collection or data object, you can use the :code:`meta-add` subcommand:

.. code:: shell

    ibridges meta-add "irods:some_collection" some_key some_value, some_units

The :code:`some_units` argument can be left out, in which case the units will be set to the empty string.

Deleting metadata
^^^^^^^^^^^^^^^^^

Metadata can also again be deleted with the CLI using the :code:`meta-del` subcommand:

.. code:: shell

    ibridges meta-del "irods:some_collection" --key some_key --value some_value --units some_units

All of the :code:`--key`, :code:`--value` and :code:`--units` are optional. They serve to constrain
which metadata items will be deleted. For example, if you only set the key:

.. code:: shell

    ibridges meta-del "irods:some_collection" --key some_key

then **all** metadata items with that key will be deleted. You can delete all metadata for a single
collection or data object with:

.. code:: shell

    ibridges meta-del "irods:some_collection"

You will be asked to confirm this operation.


Plugins
-------

The iBridges CLI is modular: users and developers can create their own sub commands so that
they can be used inside the CLI with :code:`ibridges {new_command}` or inside the :ref:`shell <ibridges shell>`
with :code:`{new_command}`.
Since this feature is relatively new, there are currently no plugins available, but an example can be found on
`GitHub <https://github.com/iBridges-for-iRODS/ibridges-cli-plugin-example>`__. If you have created a plugin that
has general use, contact and we will list it here.

Color Customization
-------------------

The command `ibridges tree` highlights the iRODS collections by default in blue. It uses the Linux `LS_COLORS` which are set
when you choose your terminal colors. On Mac can alter that by this color with
.. code:: shell

	LS_COLORS=$LS_COLORS:'di=1;44:' ; export LS_COLORS

Please have a look [here](https://gist.github.com/thomd/7667642#ls_colors) for possible color and highlighting settings.
