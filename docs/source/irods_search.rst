iRODS Search
============

`iBridges` offers an easy way to search for data. You can pass a combination of path, metadata,
item type and checksum. The output will be a list of :class:`ibridges.path.CachedIrodsPath`, which contain information where to find the item on the iRODS server.

.. note::

	The collection to search within is by default your home collection. You can change this
	by supplying the :code:`path` argument. Note that this :code:`path` itself will not show
	up in the results.

Search data by path pattern
---------------------------

In the example below we search for a data object by its path pattern.
The path is a string:
 	
.. code-block:: python
    
    from ibridges import search_data
    search_data(session, path="/", path_pattern="dataobj_name")
	
The result is a list of iRODS paths that indicate the locations of the found collections and data objects.
	
To find all subcollections and dataobjects in a collection use the `%` as wildcard:
  	
.. code-block:: python

    search_data(session, path_pattern="subcoll/%")
  	
.. note::

    The output of a search is a :class:`ibridges.path.CachedIrodsPath`. It contains the information about the data object or collection at the time of the search.
    This information is not refetched from the server, i.e. the size of the path will always remain the size at the time of the search. 


Search data by metadata
-----------------------

We can also use the metadata we generated above to search for data.


To search by metadata we need to create a :class:`ibridges.search.MetaSearch` for each key, value, units triple:

.. code-block:: python

	MetaSearch(key="my_key", value="my_value", units="my_units")

The above statement means: find all data objects and collections which are annotated with a key "my_key" where the value is "my_value" and the units is "my_units".

You can also omit any of the three items which will be interpreted as "anything". E.g.

.. code-block:: python

	MetaSearch(value="my_value")

This translates to: find all data which are labeled with any key where the value is "my_value" and the units can also be anything. Here again you can also use wild cards.

A query with metadata will look like:

.. code-block:: python

	# Search for items with an entry that has key=="key" and any value or units.
	search_data(session, metadata=MetaSearch(key="key"))

	# Search for items with an entry that has key=="key" and value=="value"
	search_data(session, metadata=MetaSearch(key="key", value="value"))

	# Different from above! Search for items with one metadata entry that has key=="key"
	# and one metadata entry that has value=="value", but they do not have to be
	# for the same entry as in the above.
	search_data(session, metadata=[MetaSearch(key="key"), MetaSearch(value="value")])

Use the `%` as a wild card again to match any combination of characters.
	

Search data by checksum
-----------------------

The search by checksum is handy to find duplicate data. In *iBridges* we always create checksums when data is uploaded. The checksum is unique for the file we uploaded and can be used to identify the files. E.g. when you uploaded the same file twice, once as `file.txt` and once as `file1.txt` you can find the two duplicates by their checksum:

.. code-block:: python

	obj = IrodsPath(session, "~", "dataobj_name").dataobject
	search_data(session, checksum = obj.checksum)

Search data by item type
------------------------

Sometimes you might want to only look for data objects or collections. In
this case you can select for that:

.. code-block:: python

	search_data(session, path_pattern="sta%", item_type="data_object")
	search_data(session, path_pattern="sta%", item_type="collection")
