The Session
===========

.. currentmodule:: ibridges.session

Before we can perform operations on an iRODS server, we need to connect to it using the :class:`Session` object (see also :doc:`API documentation <api/generated/ibridges.session.Session>`).
This object uses your `irods_environment.json` to connect to the iRODS server. All operations that need a connection will use the :class:`Session` object.


Authentication with the iRODS server
------------------------------------

There are two ways to create a :class:`Session`.

- Interactive authentication
  
  The function :func:`ibridges.interactive.interactive_auth` will check in the `.irods` folder for the default `irods_environment.json` and will try to authenticate with the cached password. If the password does not exist, you will be interactively asked for a password. 
  You can also pass a path to a specific `irods_environment.json` with the parameter `irods_env_path` and you can also pass a password with the parameter `password`:
  
  .. code-block:: python
	
		from ibridges.interactive import interactive_auth

		session = interactive_auth()
		# or
		session = interactive_auth(irods_env_path="/some/other/irods_environment.json")

  .. note::
  	Upon successful authentication, the function will store an obfuscated password just like the iRODS icommands. 
  	Once you are authenticated you can create more sessions without providing your password again.
	
- Authentication by environment and password

  If your workflow does not allow you to provide your password interactively, you can instantiate a :class:`Session` object with the following code:

  .. code-block:: python
		
		from ibridges import Session
		session = Session(irods_env="/path/to/irods_environment.json", password="YourPassword")

  The `irods_env` can also be a python dictionary which contains all your connection details.

.. note::
	The :class:`Session` object is a `context manager <https://book.pythontips.com/en/latest/context_managers.html>`__.
	Similar to opening files, we recommend using the :class:`Session` object with a :code:`with` statement.

	.. code-block:: python

		with interactive_auth() as session:
			# Do stuff with the interactive session.
	
		with Session(...) as session:
			# Do stuff with the session

	The advantage is that at the end data operations, connections to the server will be automatically
	closed and not linger, regardless of whether the operations were successful or not.

	Otherwise, you will have to close the connection manually using:

	.. code-block:: python

		session.close()



The Session object
------------------

The :class:`Session` does not only contain the connection to the iRODS server, but also some useful attributes:

.. code-block:: python

	print(session.username)
	print(session.default_resc) # the resource to which data will be uploaded
	print(session.zone)
	print(session.server_version)
	print(session.get_user_info()) # lists user type and groups
	print(session.home) # default home for iRODS /zone/home/username

We will have a closer look at the :class:`Session.home` below.

.. _session home:

The Session home
----------------

The :class:`Session.home` denotes your iRODS working path and can be referred to with :code:`~`. For any relative paths that are created using an
:doc:`IrodsPath <ipath>`, the path will be relative to the :class:`Session.home` that you have set.

There are three ways to set the irods_home:

- You can set the "irods_home" in the configuration file irods_environment.json
- You can pass it as a parameter when creating the session
- You can set it later by session.home = <YOUR_IRODS_PATH>

If you did not set any :class:`Session.home` the home will default to `/<zone_name>/home/<user name>`.

.. note::
	
	If the home collection does not exist, you might get some strange errors. Its existence can be checked with:
	
	.. code-block:: python
			
		IrodsPath(session, session.home).collection_exists()

.. _session cwd:

The Session cwd
---------------

Apart from the home collection, you can also set the current working collection (:class:`Session.cwd`).
By default this is not set, and it will be equal to your :class:`Session.home`.
To directly refer to your current working collection, you can use the :code:`.`
symbol in your :class:`ibridges.path.IrodsPath`.
