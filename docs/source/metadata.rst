Metadata 
=========

.. currentmodule:: ibridges.meta

iRODS offers metadata as key, value, units triplets. The type of the keys, values and units is always a string.
Below we show how to create a :doc:`Metadata <api/generated/ibridges.meta.MetaData>` object from a data object or collection.

The MetaData class
------------------

.. code-block:: python

    from ibridges.interactive import interactive_auth
    from ibridges import IrodsPath

    session = interactive_auth()
    meta = IrodsPath(session, "~", "collection_or_dataobject").meta

    # Show all metadata entries with print.
    print(meta)

With the object :code:`meta` we can now access and manipulate the metadata of the data object.

The MetaDataItem class
----------------------

As explained above, the metadata of a collection or dataobject can have multiple entries. You can iterate over
these entries as follows:

.. code-block:: python

    for item in meta:
        print(item.key, item.value, item.units)


Add metadata
------------
To add metadata, you always need to provide a key and a value, the units are optional and can be left out.

.. code-block:: python

    meta.add('NewKey', 'NewValue', 'NewUnit')
	
.. note::
    You can have several metadata entries with the same key but different values and units,
    i.e. metadata keys are not unique in iRODS but the combination of key,
    value and units must be unique.

Set metadata
------------

You can use the brackets ``[]`` to set a key or key/value pair. The following code creates two entries:
(ExistingKey, Value, Unit) and (ExistingKey, NewValue, NewUnit). 


.. code-block:: python

    meta["ExistingKey"] = "Value", "Unit"
    meta["ExistingKey", "New_Value"] = "New_Unit"

The single assignment notation will only change/set one triplet at the same time. So, for example the following will throw an error:

.. code-block:: python

    meta["ExistingKey"] = "Other_Value", "Other_Unit"

If you want to remove all entries with the key ``ExistingKey`` and set it to one or more new entries, then you can use the double bracket notation:

.. code-block:: python

    meta["ExistingKey"] = [["Other_Value", "Other_Unit"]]


This notation mirrors the implementation of the `iCommands <https://rdm-docs.icts.kuleuven.be/mango/clients/icommands.html#adding-metadata>`__
:code:`imeta set`.

Find metadata items
-------------------

If you want to find all items with a certain key/value/units, you can use the ``find_all`` method
which returns a list of items:

.. code-block:: python


    # Find all metadata items with key "some_key".
    items = meta.find_all(key="some_key")

    # Find all metadata items with value "some_value".
    items = meta.find_all(value="some_value")

    # Find all metadata items with some units "some_units".
    items = meta.find_all(units="some_units")

    # Find all metadata items with key == "some_key" and value == "some_value"
    items = meta.find_all(key="some_key", value="some_value")

If you are searching for one specific metadata item, then you can also use the following notation,
which will either give back one metadata item, raise a ``KeyError`` if no item matches the criteria, or
a ``ValueError`` if more than one value matches the criteria:

.. code-block:: python

    item = meta["some_key"]
    item = meta["some_key", "some_value", "some_units"]

Modify metadata items
---------------------

You can also rename the ``key``, ``value`` and ``units`` of a metadata item, by setting it to a new value:

.. code-block:: python

    item = metadata["some_key"]
    item.key = "new_key"
    item.value = "new_value"
    item.units = "new_units"

If you are trying to rename the metadata item so that it would overwrite an existing metadata item,
ibridges will throw an error.

Delete metadata
---------------
Below are examples on how to delete metadata entries:

.. code-block:: python

    # Delete all entries with key 'NewKey'
    meta.delete('NewKey')

    # Delete all entries with key 'NewKey' and value 'NewValue'
    meta.delete('NewKey', 'NewValue')

    # Delete all entries with key 'NewKey' and units 'NewUnit'
    meta.delete('NewKey', units='NewUnit')

    # Delete a single entry with exactly that triplet.
    meta.delete('NewKey', 'NewValue', 'NewUnit')

Export Metadata
---------------

The method :meth:`MetaData.to_dict` will provide you with a python dictionary containing the user-defined metadata:

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
For data objects the checksum is also listed under the key :code:`checksum`. The checksum is not calculated, but extracted from the iRODS database.

The user-defined metadata can be accessed with the key :code:`metadata`.
