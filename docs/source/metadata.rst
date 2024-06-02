Metadata 
=========

iRODS offers metadata as key, value, units triplets. The type is always string. Below we shoe how to create an `ibridges.Metadata` object from a dataobject or collection.

The Metadata object
--------------------

.. code-block:: python

	deom ibridges.interactive import interactive_auth
	from ibridges import Metadata
	from ibridges import IrodsPath
	
	session = interactive_auth()
	obj = IrodsPath(session, "~", "dataobj_name").dataobject
	meta = Metadata(obj)
	
With the object `meta` we can now access the metadata of the data object and manipulate the metadata.

Add, set and delete metadata
-----------------------------

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
	