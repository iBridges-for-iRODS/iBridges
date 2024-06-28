.. iBridges documentation master file, created by
   sphinx-quickstart on Wed Feb 28 14:42:06 2024.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to the iBridges documentation!
======================================

`iBridges <https://github.com/UtrechtUniversity/iBridges>`__ is a Python library to connect to iRods servers in a simplified and safe manner.

.. admonition:: Warning

   The project is in active development, current features are stable and the documentation is complete. However, we are still actively developing new features and improving the existing ones. We appreciate help, suggestions, issues and bug reports in our issue tracker on `github <https://github.com/UtrechtUniversity/iBridges>`__.


iBridges is a wrapper around the `python-irodsclient <https://github.com/irods/python-irodsclient>`__. While the
python-irodsclient is very powerful and feature rich, we aim to provide an easier API for users (mainly researchers)
that do not have any technical knowledge of iRods.

We provide extensive tutorials on how to work with data in iRODS. Please consult our `iBridges <https://github.com/UtrechtUniversity/iBridges/tree/main/tutorials>`__.

.. toctree::
   :hidden:
   :maxdepth: 2
   :caption: Contents:

   quickstart

   install

   session
   ipath
   data_transfers
   sync
   metadata
   irods_search
   cli
   faq
   api/main


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
