Quick Start Guide
=================


Installation
------------

iBridges requires Python version 3.8 or higher. You can install iBridges with pip:

.. code:: bash

    pip install ibridges


Getting your iRODS environment file
-----------------------------------

To connect to an iRods server you need an iRods environment file (`irods_environment.json`).
If your organization provides automatic setup, you can create this file yourself using the :ref:`CLI <cli-setup>`.
Otherwise, you can obtain this by asking your local iRods administrator. An example of an environment file:

.. code:: json

    {
        "irods_host": "provider.yoda",
        "irods_port": 8247,
        "irods_user_name": "technicaladmin",
        "irods_home": "/tempZone/home/rods",
        "irods_cwd": "/tempZone/home/rods",
        "irods_zone_name": "tempZone",
        "irods_client_server_negotiation": "request_server_negotiation",
        "irods_client_server_policy": "CS_NEG_REQUIRE",
        "irods_default_hash_scheme": "SHA256",
        "irods_default_resource": "irodsResc",
        "irods_encryption_algorithm": "AES-256-CBC",
        "irods_encryption_key_size": 32,
        "irods_encryption_num_hash_rounds": 16,
        "irods_encryption_salt_size": 8,
        "irods_ssl_verify_server": "none"
    }

Normally this file is stored in `~/.irods/irods_environment.json`. It is recommended to store it in the default location,
but if needed (if you need access to more than one iRods instance for example) you can also store it elsewhere. Simply
replace that path in this quick start guide with the path you have chosen.


Connecting to your iRODS server
-------------------------------

To connect to your iRods server, we will create a session. The session is the central object in the iBridges library;
almost all functionality is enabled with this connection to your server. Generally you will create a session,
perform your data operations, and then delete/close the session. To create a new session, open Python:

.. code:: python

    from ibridges import Session

    session = Session(irods_env_path="~/.irods/irods_environment.json", password="mypassword")


Upload data
-----------

You can easily upload your data with the previously created session:

.. code:: python

    from ibridges import upload

    upload(session, "/your/local/path", "/irods/path")

This upload function can upload both directories (collections in iRods) and files (data objects in iRods)


Add metadata
------------

One of the powerful features of iRODS is its ability to store metadata with your data in a consistent manner.
Let's add some metadata to a collection or data object:

.. code:: python

    from ibridges import MetaData, get_collection

    collection = get_collection("/irods/path")
    meta = MetaData(collection)
    meta.add("some_key", "some_value", "some_units")


Download data
-------------

Naturally, we also want to download the data back to our local machine. This is done with the download function:

.. code:: python

    from ibridges import download

    download(session, "/irods/path", "/other/local/path")


Closing the session
-------------------
When you are done with your session, you should generally close it:

.. code:: python

    session.close()

