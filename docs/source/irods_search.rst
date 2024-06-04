iRODS Search
============

`iBridges` offers an easy way to search for data. You can pass a combination of path, metadata keys and values and checksum. The output will be a list of dictionaries, one dictionary for each found item, which contain information where to find the item on the iRODS server.


Search data by Path
--------

In the example below we search for a data object by ites path.
The path can be an IrodsPath or a string:
 	
.. code-block:: python
		
        from ibridges import search_data
	    search_data(session, path=IrodsPath(session, "dataobj_name"))
	
The result is a list of dictionaries.
	
.. code-block:: python
	
		[{'COLL_NAME': '/you/irods/home',
  		'DATA_NAME': 'dataobj_name',
  		'D_DATA_CHECKSUM': 'sha2:XGiECYZOtUfP9lnCGyZaBBkBGLaJJw1p6eoc0GxLeKU='}]
  		
For collections the dictionary only contains the entry `COLL_NAME`.
  	
To find all subcollections and dataobjects in a collection use the `%` as wildcard:
  	
.. code-block:: python
  	
  		search_data(session, path=IrodsPath(session, "subcoll/%"))
  	

Search data by metadata
--------------------

We can also use the metadata we generated above to search for data.
We need to create a python dictionary which contains the metadata keys ad their values. The values are again optional.

.. code-block:: python

	key_vals = {'key': 'value'}
	search_data(session, key_vals = key_vals)
	key_vals = {'key': ''}
	search_data(session, key_vals = key_vals)
	
Use the `%` as a wild card again to match any combination of characters.
	

Search data by checksum
------

The search by checksum is handy to find duplicate data. in *iBridges* we always create checksums when data is uploaded. The checksum is unique for the file we uploaded and can be used to identify the files. E.g. when you uploaded the same file twice, once as `file.txt` and once as `file1.txt` you can find the two duplicates by their checksum:

.. code-block:: python

	obj = IrodsPath(session, "~", "dataobj_name").dataobject
	search_data(session, checksum = obj.checksum)
