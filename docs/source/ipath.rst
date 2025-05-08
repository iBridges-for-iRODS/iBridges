iRODS paths
===========

.. currentmodule:: ibridges.path

iRODS paths follow a certain pattern just like the local paths of different operating systems.
All iBridges operations support passing iRODS paths as strings. iBridges provides an alternative way
to describe the location of collections and data objects: :class:`IrodsPath`, which is analogous to a :code:`Path`
from `pathlib <https://docs.python.org/3/library/pathlib.html>`__.

We strongly recommend using :class:`IrodsPath` over using strings for the following reasons:

- :class:`IrodsPath` is **safer** since it takes care of the correct concatenation of parts of the path.
- :class:`IrodsPath` is **more convenient** since there are many methods and attributes available such as: the name, size and parent of the iRODS path.
- The string representation of the :class:`IrodsPath` is available through :code:`str(ipath)`.

A complete tutorial on iRODS paths can be followed `here <https://github.com/iBridges-for-iRODS/iBridges/tree/main/tutorials>`__. For an overview of
all functionality connected to the :class:`IrodsPath`, see the :doc:`API documentation <api/generated/ibridges.path.IrodsPath>`. 

IrodsPath
---------

In iRODS the :code:`/` is used as separator and all paths on an iRODS server start with `/<zone_name>`.
Users usually have a personal `home` collection in iRODS: `/<zone_name>/home/<user name>`.
Group-based iRODS instances such as Yoda will give you access to a group `home` collection: `/<zone_name>/home/<group name>`

iBridges implements a selection of functions which are comparable to their counterparts in :code:`pathlib`.

Apart from absolute paths, :class:`IrodsPath` supports relative paths. Relative paths are always
defined with respect to the session :ref:`home <session home>`. The session home is marked by the :code:`~``:

.. code-block:: python

    from ibridges import IrodsPath
    home = IrodsPath(session, '~')
    print(home)

Another form or relative path is defined with respect to the session :ref:`working collection <session cwd>`.
This is denoted by the :code:`.` symbol or the absence of the :code:`/` or :code:`.`:

.. code-block:: python

    IrodsPath(session)  # Current working directory
    IrodsPath(session, ".") # Same
    IrodsPath(session, session.cwd) # Same

    IrodsPath(session, "sub")  # session.cwd / sub
    IrodsPath(session, ".", "sub")  # Same
    IrodsPath(session "./sub")  # Same

Below we present a selection of possible iRODS path manipulations, some of which are similar to those in pathlib:

.. code-block:: python

    irods_path = IrodsPath(session, session.home)
    irods_path / "new_collection"  # Concatenate IrodsPaths
    irods_path.exists()  # True if the path is either a collection or data object.
    irods_path.size  # Size of the collection (and subcollections) or data object.
    irods_path.checksum  # Sha-256 checksum of the data object.
