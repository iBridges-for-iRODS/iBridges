.. iBridges documentation master file, created by
   sphinx-quickstart on Wed Feb 28 14:42:06 2024.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to the iBridges documentation!
======================================

`iBridges <https://github.com/iBridges-for-iRODS/iBridges>`__ is a Python library to connect to iRODS servers in a simplified and safe manner.
iBridges consists of three major components: a Python API for Python programmers, a Command Line Interface and a Graphical user interface.
The documentation presented here is for the Python API and Command Line Interface. The documentation for the Graphical User Interface is
located on a separate `page <https://ibridges-for-irods.github.io/iBridges-GUI/>`__.

.. note::
   The project is in active development, current features are stable and the documentation is complete. However, we are still actively developing new features and improving the existing ones. We appreciate help, suggestions, issues and bug reports in our issue tracker on `GitHub <https://github.com/iBridges-for-iRODS/iBridges>`__.


iBridges is a wrapper around the `python-irodsclient <https://github.com/irods/python-irodsclient>`__. While the
python-irodsclient is very powerful and feature rich, we aim to provide an easier API for users (mainly researchers)
that do not have any technical knowledge of iRods.

We provide extensive tutorials on how to work with data in iRODS. Please consult our `tutorials <https://github.com/iBridges-for-iRODS/iBridges/tree/main/tutorials>`__ page.

.. toctree::
   :hidden:
   :maxdepth: 2
   :caption: Contents:

   quickstart
   ibridges_python
   cli
   faq


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
