# iBridges <img src="https://github.com/iBridges-for-iRods/iBridges/blob/main/docs/logo.png?raw=true" width="150" align="right">
iBridges is a library for scientific programmers who are working with data in iRODS. We provide a wrapper around the [python-irodsclient](https://pypi.org/project/python-irodsclient/) to facilitate easy interaction with the iRODS server. iBridges is currently still in very active development.

[![PyPI version](https://badge.fury.io/py/ibridges.svg)](https://badge.fury.io/py/ibridges)
[![Run integration tests against iRODS](https://github.com/iBridges-for-iRods/iBridges/actions/workflows/integration-tests-irods.yml/badge.svg)](https://github.com/iBridges-for-iRods/iBridges/actions/workflows/integration-tests-irods.yml)
[![Run integration tests against Yoda](https://github.com/iBridges-for-iRods/iBridges/actions/workflows/integration-tests-yoda.yml/badge.svg)](https://github.com/iBridges-for-iRods/iBridges/actions/workflows/integration-tests-yoda.yml)
[![Python package](https://github.com/iBridges-for-iRods/iBridges/actions/workflows/main.yml/badge.svg)](https://github.com/iBridges-for-iRods/iBridges/actions/workflows/main.yml)
![](https://readthedocs.org/projects/ibridges/badge/?version=latest&style=flat-default)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.12583187.svg)](https://doi.org/10.5281/zenodo.12583187)

## Highlights

- Works on Windows, Mac OS and Linux
- Runs on Python 3.8 or higher.
- Supported iRODS server versions: 4.2.11 or higher and 4.3.0 or higher.
- **Interactive connection** to your iRODS server.
- **Upload** and **Download** your data.
- Manipulate the **metadata** on the iRODS server.
- **Synchronise** your data between your local computer and the iRODS server.
- Create and manipulate **Tickets** to temporarily grant access to outside users.
- **Search** through all metadata for your dataset or collection.
- Small number of dependencies (`python-irodsclient` and `tqdm`)
- Safe default options when working with your data.

**iBridges** also has a graphical user interface, which you can install [here](https://github.com/iBridges-for-iRods/iBridges-GUI).

 <p align="center">
    <a href="https://github.com/iBridges-for-iRods/iBridges/issues/new?assignees=&labels=&projects=&template=bug_report.md&title=%5BBUG%5D">Report Bug</a>
    .
    <a href="https://github.com/iBridges-for-iRods/iBridges/issues/new?assignees=&labels=&projects=&template=feature_request.md&title=%5BFEATURE%5D">Request Feature</a>
    .
    <a href="https://github.com/iBridges-for-iRods/iBridges/discussions/categories/ideas">Share an idea</a>
    .
    <a href="https://github.com/iBridges-for-iRods/iBridges/discussions/categories/general">Leave some feedback</a>
    .
    <a href="https://github.com/iBridges-for-iRods/iBridges/discussions/categories/q-a">Ask a question</a>
  </p>
</p>

## Installation

There are two main ways to install iBridges. The recommended way is to use the stable version that is available on PyPi:

```bash
pip install ibridges
```

If you want to install the unstable version to test out new features, you can install the development branch:

```bash
pip install git+https://github.com/iBridges-for-iRods/iBridges.git@develop
```

## Configuration

You will need to have a so-called `irods_environment.json`. Please follow the [documentation](https://ibridges.readthedocs.io/en/latest/cli.html) how to set it up. 

## Usage

Below are some basic examples of the features in iBridges.

```py
# Create an iRODS session
from ibridges.interactive import interactive_auth

session = interactive_auth()

# Upload data
from ibridges import upload

upload(session, "/your/local/path", "/irods/path")

# Download data
from ibridges import download

download(session, "/irods/path", "/other/local/path")

```

## Command line interface

To simply upload or download data you do not need to write full python program, we offer a command line interface (see also [the documentation](https://ibridges.readthedocs.io/en/latest/)).

- Establish a connection

  ```bash
  ibridges init
  ```

- List a collection
  
  ```bash
  # list your home collection
  ibridges list
  
  # list a different collection in your home
  ibridges list "irods:~/<collection>"
  
  # list a collection on a different path than your home

  ibridges list "irods:/full/irods/path"
  ```

- Upload data

  ```bash
  ibridges upload my_file.json "irods:~/some_collection"
  ```

- Download data

  ```bash
  ibridges download "irods:~/some_collection/some_object" download_dir
  ```

- Synchronise data

  ```bash

  ibridges sync some_local_directory "irods:~/some_collection"


## Tutorials
### Documentation
- **[ReadTheDocs](https://ibridges.readthedocs.io/en/latest/)**

### Guides

- [Manual with examples](tutorials/00-FirstSteps.ipynb)

### Beginners tutorials
- [Setup client configuration](tutorials/01-Setup-and-connect.ipynb)
- [iRODS Paths](tutorials/02-iRODS-paths.ipynb)
- [Working with data](tutorials/03-Working-with-data.ipynb)
- [Metadata](tutorials/04-Metadata.ipynb)
- [Sharing data](tutorials/05-Data-Sharing.ipynb)
- [Synchronising data](tutorials/06-Data-sync.ipynb)


## Do I have to choose between the *python-irodsclient* and *iBridges*?
No. *iBridges* itself is based on the *python-irodsclient*. When you connect to iRODS a *python-irodsclient* `irods.iRODSSession` is automatically created with which you can access all functionality of the *python-irodsclient*.

<p align="center">
<img src="docs/ibridges-prc.png" alt="ibridges and prc" style="width:75%;"/>
</p>

## Authors

**Christine Staiger (Maintainer) [ORCID](https://orcid.org/0000-0002-6754-7647)**

- *Wageningen University & Research* 2021 - 2022
- *Utrecht University* 2022

**Tim van Daalen**, *Wageningen University & Research* 2021

**Maarten Schermer (Maintainer) [ORCID](https://orcid.org/my-orcid?orcid=0000-0001-6770-3155)**, *Utrecht University* 2023

**Raoul Schram (Maintainer) [ORCID](https://orcid.org/my-orcid?orcid=0000-0001-6616-230X)**. 
*Utrecht University* 2023

## Contributors

**J.P. Mc Farland**,
*University of Groningen, Center for Information Technology*, 2022

## License
This project is licensed under the MIT license.
The full license can be found in [LICENSE](LICENSE).
