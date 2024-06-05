The Session
===========

When connecting to iRODS a `Session` object is created, which stores information from your `irods_environment.json` and provides you with more information about the iRODS you are connected to and it is needed for all interactions with iRODS.

Authentication with the iRODS server
------------------------------------

There are two ways to create a `Session`.

- Interactive authentication
  
  The function `interactive_auth` will check in the `.irods` folder for the default `irods_environment.json` and will try to authenticate with the cached password. If the password does not exist, you will be interactively asked for a password. 
  You can also pass a path to a specific `irods_environment.json` with the parameter `irods_env_path` and you can also pass a password with the parameter `password`
  
  .. code-block:: python
	
		from ibridges.interactive import interactive_auth
		session = interactive_auth()

		# or
		session = interactive_auth(irods_env_path="/some/other/irods_environment.json")

  Upon successful authentication, the function will store an obfuscated password just like the iRODS icommands.
	I.e. once you are authenticated you can create more sessions without providing your password again.
	
- Authentication by environment and password

  If your workflow does not allow you to provide your password interactively, you can instantiate a `Session` object with the following code:

  .. code-block:: python
		
		from ibridges import Session
		session = Session(irods_env="/path/to/irods_environment.json", password="YourPassword")

  The `irods_env` can also be a python dictionary which contains all your connection details.

The Session object
------------------

The `Session` does not only contain the connection to the iRODS server, but also some useful attributes:

.. code-block:: python

	print(session.username)
	print(session.default_resc) # the resource to which data will be uploaded
	print(session.zone)
	print(session.server_version)
	print(session.get_user_info()) # lists user type and groups
	print(session.home) # default home for iRODS /zone/home/username

We will have a closer look at the `session.home` below.

The `Session` object is necessary for all interactions with the iRODS server and you will have to provide the object to most of the functions in `iBridges`.


The Session home
----------------

The `session.home` denotes your iRODS working path. If you do not specify a full path, all paths you create with `IrodsPath` (see :doc:`IrodsPath <ipath>` ) will be prefixed with your `session.home`.

There are three ways to set the irods_home:

- You can set the "irods_home" in the configuration file irods_environment.json
- You can pass it as a parameter when creating the session
- You can set it later by session.home = <YOUR_IRODS_PATH>

.. note::
	
	It is not automatically checked during the connection, if the `session.home` really exists. Please always check:
	
.. code-block:: python
		
    IrodsPath(session, session.home).collection_exists()
		
Closing the Session
-------------------

When you do not need the `Session` any longer, close the connection to the iRODS server:

.. code-block:: python

    session.close()

The `Session` will automatically be closed when you open it in a `with` statement:

.. code-block:: python

    with Session("irods_environment.json") as session:
        # Do things on the iRODS server


		
		
