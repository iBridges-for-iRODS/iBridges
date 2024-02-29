# iBridges
[![](https://github.com/UtrechtUniversity/iBridges/actions/workflows/integration-tests-irods.yml/badge.svg?branch=develop)](https://github.com/UtrechtUniversity/iBridges/actions/workflows/integration-tests-irods.yml) [![](https://github.com/UtrechtUniversity/iBridges/actions/workflows/main.yml/badge.svg?branch=develop)](https://github.com/UtrechtUniversity/iBridges/actions/workflows/main.yml) 
[![](https://github.com/UtrechtUniversity/iBridges/actions/workflows/integration-tests-yoda.yml/badge.svg)](https://github.com/UtrechtUniversity/iBridges/actions/workflows/integration-tests-yoda.yml) ![](https://readthedocs.org/projects/ibridges/badge/?version=latest&style=flat-default)


## About

iBridges is library for scientific programmers who are working with data in iRODS. We provide a wrapper around the [python-irodsclient](https://pypi.org/project/python-irodsclient/) to facilitate easy interaction with the iRODS server.

Since iBridges is solely based on python it works on all operating systems.

- Runs on Python 3.8 or higher.
- Supported iRODS server versions: 4.2.11 or higher and 4.3.0 or higher.

## Installation
### From Github repository
```
git clone git@github.com:UtrechtUniversity/iBridges.git
cd iBridges
pip install .
```

### Pypi install
```
pip install ibridges
```

## Usage
```py
# Create an iRODS session
from ibridges import Session

session = Session(irods_env_path="~/.irods/irods_environment.json", password="mypassword")

# Upload data
from ibridges import upload

upload(session, "/your/local/path", "/irods/path")

# Download data
from ibridges import download

download(session, "/irods/path", "/other/local/path")

```

## Tutorials
### Documentation
- **[ReadTheDocs](https://ibridges.readthedocs.io/en/latest/)**

### Guides
- [QuickStart](Tutorials/QuickStart.ipynb)
- [iRODS Paths](Tutorials/iRODS_paths.ipynb)
- [Data synchronisation](Tutorials/Data_sync.ipynb)

### Beginners tutorials
- [Setup client configuration](Tutorials/01-Setup-and-connect.ipynb)
- [Working with data](Tutorials/02-Working-with-data.ipynb)
- [iRODS and local Paths](Tutorials/03-iRODS-Paths.ipynb)
- [Metadata](Tutorials/04-Metadata.ipynb)
- [Sharing data](Tutorials/05-Data-Sharing.ipynb)

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
This project is licensed under the GPL-v3 license.
The full license can be found in [LICENSE](LICENSE).
