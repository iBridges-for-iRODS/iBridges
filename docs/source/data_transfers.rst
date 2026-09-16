Data Transfers
==============

.. currentmodule:: ibridges.data_operations

There are three main data transfer operations: :func:`download`, :func:`upload`, and :func:`sync`. These
functions take very similar arguments.

.. currentmodule:: ibridges.path

In the following examples we assume that local directories and remote collections have
already been created. Otherwise the operations will fail with an error message. To create
local directories, use :code:`pathlib.Path.mkdir(parents=True, exist_ok=True)`. For remote
collections, :meth:`IrodsPath.create_collection` can be used.

.. currentmodule:: ibridges.data_operations

.. note::
    By default, no data will be overwritten. If you want to overwrite data, you
    can set :code:`overwrite=True`. Beware that you can also overwrite newer data with older data this way.
    If a file and a dataobject are exactly the same, iBridges will skip the transfer and print a warning,
    thereby saving time.

For all operations, iBridges will check that the transfer has been completed without
error. If a local file is different from a remote file, you will get an error message.
If this occurs, you can transfer the file again. If the problem persists, you should contact
your local iRODS administrator.

Upload
------
To upload files or folders from your local file system to iRODS use the :func:`upload` function.

In the example below we transfer a file or a folder to a new collection *new_coll*. 
If the transfer concerned a folder, a new collection with the folder name will be created.

.. code-block:: python

    from ibridges import upload
    from ibridges import IrodsPath
    from pathlib import Path
 
    local_path = Path("/path/to/the/data/to/upload")
    irods_path = IrodsPath(session, '~', 'new_coll')
    upload(local_path, irods_path)

.. currentmodule:: ibridges.executor

.. note::

	All of the data transfer functions return an :class:`Operations` object, which can be used to execute all operations.
	With the option :code:`dry_run=True` you can retrieve these operations before executing them. This enables you to check what will be transferred before the actual transfer using the :meth:`Operations.print_summary` method.

.. currentmodule:: ibridges.data_operations

Download
--------

The :func:`download` function works similar to the :func:`upload` function. Simply define your iRODS path you would like to download and a local destination path.

.. code-block:: python

    from ibridges import download
    from ibridges import IrodsPath
    from pathlib import Path
   
    local_path = Path("/destination/location/for/the/data")
    irods_path = IrodsPath(session, '~', 'new_coll')
    download(irods_path, local_path)

Synchronisation
---------------

The iBridges function :doc:`sync <api/generated/ibridges.data_operations.sync>` synchronises data between your local file system and the iRODS server.

The function works in both directions: synchronisation of data from the client's local file system to iRODS,
or from iRODS to the local file system. The direction is given by the type of path and the order. This is a
case where remote paths **have** to be encoded using :class:`ibridges.path.IrodsPath`, since iBridges
otherwise has no way of knowing which of the two paths is remote and which is local.

Synchronise from local to remote
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The code below shows how to synchronise from your local file system to iRODS. The data in iRODS will be updated. 

.. code-block:: python

    from pathlib import Path
    from ibridges.path import IrodsPath
    from ibridges.data_operations import sync

    target = IrodsPath(session, "~", "<irods path>")
    source = Path.home() / "<local path>"

    # Synchronise the data
    sync(source=source, target=target)


Synchronize from remote to local
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The code below shows how to synchronise from your iRODS instance to your local file system. Your local data will be updated.

.. code-block:: python

    from pathlib import Path
    from ibridges.path import IrodsPath
    from ibridges.data_operations import sync
    target = Path.home() / "<local path>"
    source = IrodsPath(session, "~", "<irods path>")

    # call the synchronisation
    sync(source=source, target=target)


Streaming data objects
----------------------

With the `python-irodsclient` which `iBridges` is built on, we can open the file inside of a data object as a stream and process the content without downloading the data. 
That works without any problems for textual data. 

.. code-block:: python

    from ibridges import IrodsPath

    obj_path = IrodsPath(session, "path", "to", "object")
    with obj_path.open('r') as stream:
        content = stream.read().decode()
	
	
Some python libraries allow to be instantiated directly from such a stream. This is supported by e.g. `pandas`, `polars` and `whisper`.

.. code-block:: python

    import pandas as pd

    with obj_path.open('r') as stream:
        df = pd.read_csv(stream)
	
    print(df)


Parallel transfers
------------------

The transfers can also be parallelized in different ways. By default iBridges will not parallelize your transfers,
except for large transfers, where the underlying python-irodsclient will perform the parallelization. For small transfers,
large performance increases can be observed when parallization is used. There are two methods of parallelization:
``thread`` (for multi-threading) and ``process`` (for multi-processing). These methods have both advantages compared to one another.
The advantage of using threads is that it will more efficiently use memory and cpu power on your machine. It will also
be less demanding on the iRODS server. On the other hand using processes can be faster in some cases, and it does not
rely on thread-safety of the ``python-irodsclient`` session. In general we recommend using threads, unless processes are
much faster for your usecase, or the threads method is not working as expected.

Choosing the amount of parallelism
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can adjust two parameters that determine how much iBridges will try to parallelize
your transfers: 

- ``n_workers``: The maximum number of worker threads/processes that can run in parallel
- ``threads_per_worker``: The number of threads used by one thread/process for large transfers.

One might expect then that the total number of threads that will be used could be as high as
``n_workers*threads_per_worker``. This is not the case. Instead the queue will continue serving
new jobs until the total number of threads in flight equals the number of workers. For example,
let's assume ``n_workers=10`` and ``threads_per_worker=4``. Then if we have two large transfers + 1 small
in flight, this will consume 9 slots (2*4+1). This is less than the number of workers, so another
operation will be run, regardless of whether it is a large or small transfer. After this operation
has been assigned to a worker, there are no slots left and the scheduler will wait until new
slots become available when the running workers finish their operation. 
