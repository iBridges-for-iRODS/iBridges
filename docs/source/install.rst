Installation and configuration
===============================


Installation
------------

iBridges requires Python version 3.8 or higher. You can install iBridges with pip:

.. code:: bash

    pip install ibridges


Configure iBridges
-------------------

iBridges connects to an iRODS server. To do so it needs an iRODS client configuration file, the `irods_nevironment.json`.
It is the same file which is also used with other iRODS clients e.g. the (`icommands`).
  
Below we give an example of such a file

.. code:: json

    {
        "irods_host": "<iRODS servername or IP address>",
        "irods_port": 8247,
        "irods_user_name": "<irods username>",
        "irods_home": "/<irods_zone>/home/<irods username>",
        "irods_zone_name": "<iRODS zone name>",
        "irods_client_server_negotiation": "request_server_negotiation",
        "irods_client_server_policy": "CS_NEG_REQUIRE",
        "irods_default_hash_scheme": "SHA256",
        "irods_default_resource": "irodsResc",
        "irods_encryption_algorithm": "AES-256-CBC",
        "irods_encryption_key_size": 32,
        "irods_encryption_num_hash_rounds": 16,
        "irods_encryption_salt_size": 8
    }

It is recommended to store this file in the default location `~/.irods/irods_environment.json`. 
However, if needed you can point iBridges also to a different location.

Ensure that the file is saved as `.json`.

Configuration of your `home` collection
----------------------------------------

iBridges makes use of the configuration setting `"irods_home"`. The `"irods_home"` is your default path on the iRODS server which in iBridges you can address with `~` when creating paths.

In a default iRODS instance you have a personal location on the iRODS server with the path

.. code:: bash

    /<zone_name>/home/<username>

However, this can differ. E.g. on Yoda instances you will belong to a research group and hence your iRODS home will be:

.. code:: bash
    
    /<zone_name>/home/research-<group name>

Please ask your iRODS admin or service provider how to set up the `irods_environment.json` such that it matches your iRODS instance.
