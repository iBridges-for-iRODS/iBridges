Metadata 
=========

iRODS offers metadata as key, value, units triplets. The type is always string. Below we show how to create an `ibridges.Metadata` object from a dataobject or collection.

The Metadata object
--------------------

.. code-block:: python

	from ibridges.interactive import interactive_auth
	from ibridges import Metadata
	from ibridges import IrodsPath
    
    session = interactive_auth()
	obj = IrodsPath(session, "~", "dataobj_name").dataobject
	meta = Metadata(obj)
	
With the object `meta` we can now access and manipulate the metadata of the data object.

Add, set and delete metadata
----------------------------

- Add metadata to a collection or data object:

	.. code-block:: python

		meta.add('NewKey', 'NewValue', 'NewUnit')
		print(meta)
	
	- You always need to provide a key and a value, the unit is optional and can be left out.
	
	- You can have several metadata entries with the same key but different values and units, i.e. metadata keys are not unique in iRODS but the combination of key, value and unit must be unique.
	
- Set metadata:

	.. code-block:: python
	
		meta.set('ExistingKey', 'Value', 'Unit')
	
	The `set` function is a special function. It sets all metadata items with the key `ExistingKey` to the value and unit. It is the implementation of the *icommands* `imeta set`.
	
- Delete metadata of a collection or data object:

	.. code-block:: python
	
		meta.delete('NewKey', 'NewValue', 'NewUnit')
	
Export Metadata
---------------

The function `Metadata.to_dict` will provide you with a python dictionary containing the user-defined metadata:

.. code-block:: python

   meta.to_dict()

.. code-block:: python

    {
    'name': '<obj_name>',
    'irods_id': 24490075,
    'checksum': 'sha2:XGiECYZOtUfP9lnCGyZaBBkBGLaJJw1p6eoc0GxLeKU=',
    'metadata': [('Key', 'Value', 'Unit'), ('Key', 'Value', 'Unit1')]
    }

The dictionary contains the name of the data object or collection and its iRODS identifier.
For data objects the checksum is also listed under the key `checksum`. The checksum is not calculated, but extracted from the iRODS database.

The user-defined metadata can be accessed with the key `metadata`.

Export metadata of all member of a collection
---------------------------------------------

Above we showed how to export the metadata of one collection or data object. In case you want to export
metadata of all memebers of a collection you can use:

.. code-block:: python

    from ibridges.export_metadata import export_metadata_to_dict
   
    coll = IrodsPath(session, <coll_path>).collection
    meta = Metadata(coll)
    export_metadata_to_dict(meta, session)

The resulting dictionary is built like above and contains two additional keys `subcollections` and `dataobjects`.

Under `subcollections` we will find the extracted  metadata of all subcollection and under `dataobjects` the extracted metadata for all data objects. 
Those extracted metadata are also represented by dictionaries as shown above, they only  contain one extra key `rel_path` which denotes the path relative to the collection which we gave as input to the function.

.. code-block:: python

    {
    'ibridges_metadata_version': 1.0,
    'name': 'Demo',
    'irods_id': 24484787,
    'metadata': [('Key', 'very_important', None)],
    'subcollections': [
        {
            'name': 'subDemo',
            'irods_id': 24490064,
            'rel_path': 'Demo',
            'metadata': []
            },
        {
            'name': 'my_books',
            'irods_id': 24502538,
            'rel_path': 'my_books',
            'metadata': []}
        ],
    'dataobjects': [
        {
            'name': 'AliceInWonderland.txt',
            'irods_id': 24484789,
            'checksum': 'sha2:TQzOrHuw1qRQ6zh8xm5GEuVKGjs22STdgQCdezv8LY4=',
            'rel_path': 'my_books/AliceInWonderland.txt',
            'metadata': [('author', 'Lewis Carroll', None)]
            }
        ]
    }
