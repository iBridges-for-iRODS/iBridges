Metadata 
=========

.. currentmodule:: ibridges.meta

iRODS offers metadata as key, value, units triplets. The type of the keys, values and units is always a string.
Below we show how to create a :doc:`Metadata <api/generated/ibridges.meta.MetaData>` object from a dataobject or collection.

The Metadata object
--------------------

.. code-block:: python

    from ibridges.interactive import interactive_auth
    from ibridges import IrodsPath

    session = interactive_auth()
    meta = IrodsPath(session, "~", "collection_or_dataobject").meta

With the object :code:`meta` we can now access and manipulate the metadata of the data object.

Add metadata
------------
To add metadata, you always need to provide a key and a value, the unit is optional and can be left out.

.. code-block:: python

    meta.add('NewKey', 'NewValue', 'NewUnit')
    print(meta)

	
.. note::
    You can have several metadata entries with the same key but different values and units,
    i.e. metadata keys are not unique in iRODS but the combination of key,
    value and unit must be unique.

Set metadata
------------

The :meth:`ibridges.meta.MetaData.set` method differs from the add method in that it removes all other entries with the
same key first. This mirrors the implementation of the `iCommands <https://rdm-docs.icts.kuleuven.be/mango/clients/icommands.html#adding-metadata>`__
:code:`imeta set`.

.. code-block:: python

    meta.set('ExistingKey', 'Value', 'Unit')


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
