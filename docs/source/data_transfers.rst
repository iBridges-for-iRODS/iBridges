Data Transfers
==============

Upload
------
To upload data from your local file system to iRODS simply use the `upload` function.
To determine paths, we recommend to use `pathlib.Path` for local paths and `ibridges.IrodsPath` for iRODS paths.

In the example below we transfer a file or a folder to a new collection *new_coll*. The new collection will be created on the fly.

.. note::
    
    If you transfer data to a destination folder or collection for which the path does not already exist, the missing folders or collections will NOT be created and the command will fail with the respective error message.
    Please use `IrodsPath.create_collection` or `pathlib.Path.mkdir(parents=True, exist_ok=True)` to create the destination before the upload or download.

.. code-block:: python

    from ibridges import upload
    from ibridges import IrodsPath
    from pathlib import Path
 
    local_path = Path("/path/to the/data/to/upload")
    irods_path = IrodsPath(session, '~', 'new_coll')
    upload(session, local_path, irods_path)

The new collection will be created on the fly. Please note, that this is not true for new nested collections. Please note that the automatic creation of new collections does not work when they are nested. I.e.
you will receive the following exception.

.. code-block:: python
	
	irods_path = IrodsPath(session, '~', 'new_coll', 'new_subcoll', 'new')

	CAT_UNKNOWN_COLLECTION: collection '/nluu12p/home/research-test-christine/new_coll1/new_subcoll' is unknown


The output of a successful upload is:

.. code-block:: python

    {
        'create_dir': set(),
 	    'create_collection': set(),
 	    'upload': [(PosixPath('/Users/christine/demofile.txt'),
                    IrodsPath(/, <zone_name>, home, <user or group>, new_coll1))],
        'download': [],
 	    'resc_name': '',
 		'options': None
    }

.. note::

	All of the data transfer functions return a python dictionary summarising the changes. 
	With the option `dry_run=True` you can retrieve them before the actual data transfer.
	
The dictionary above summarises the changes. In case of an upload, it will list the created collections, in case you upload a directory with subdirectories; and it 	will list which file was uploaded to which iRODS path.

If you want to explicitly overwrite existing data, you need to set the `overwrite=True` parameter. **By default no existing data will be overwritten.**


Download
--------

The download function works similar to the upload function. Simply define your iRODS path you would like to download and a local destination path.

.. code-block:: python

    from ibridges import download
    from ibridges import IrodsPath
    from pathlib import Path
   
    local_path = Path("/destination/location/for/the/data")
    irods_path = IrodsPath(session, '~', 'new_coll')
    download(session, irods_path, local_path)


Again you will receive a dictionary with changes, which you can also retrieve beforehand with the option `dry_run=True`.

As above, existing local data will not be overwritten. Please use the option `overwrite=True` if you want to overwrite your local data.


Synchronisation
---------------
Please see: :doc:`Synchronisation <sync>`.

Streaming data objects
----------------------

With the `python-irodsclient` which `iBridges` is built on, we can open the file inside of a data object as a stream and process the content without downloading the data. 
That works without any problems for textual data. 

.. code-block:: python
  
    from ibrigdes import IrodsPath
  
  	obj_path = IrodsPath(session, "path", "to", "object")
  	
  	content = ''
  	with obj_path.dataobject.open('r') as stream:
  	    content = stream.read().decode()
	
	
Some python libraries allow to be instantiated directly from such a stream. This is supported by e.g. `pandas`, `polars` and `whisper`.

.. code-block:: python

	from io import StringIO
    imort pandas as pd

	df = None
	with obj_path.dataobject.open('r') as stream:
		df = pd.read_csv(StringIO(stream.read().decode()))
	print(df)
