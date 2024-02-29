# iBridges

## Development status
|    | |
| -------- | ------- |
| [![Run integration tests against iRODS](https://github.com/UtrechtUniversity/iBridges/actions/workflows/integration-tests-irods.yml/badge.svg?branch=develop)](https://github.com/UtrechtUniversity/iBridges/actions/workflows/integration-tests-irods.yml)  | [![Python package](https://github.com/UtrechtUniversity/iBridges/actions/workflows/main.yml/badge.svg?branch=develop)](https://github.com/UtrechtUniversity/iBridges/actions/workflows/main.yml)    |
| [![Run integration tests against Yoda](https://github.com/UtrechtUniversity/iBridges/actions/workflows/integration-tests-yoda.yml/badge.svg)](https://github.com/UtrechtUniversity/iBridges/actions/workflows/integration-tests-yoda.yml) | ![Docs](https://readthedocs.org/projects/ibridges/badge/?version=latest&style=flat-default)     |


## About

iBridges is library for scientific programmers who are working with data in iRODS. We provide a wrapper arount the [python-irodsclient] to facilitate easy interaction with the iRODS server.

Since iBridges is solely based on python it works on all operating systems.

### Documenation
[ReadTheDocs](https://ibridges.readthedocs.io/en/latest/)

## Dependencies

### Supported iRODS versions

- 4.2.11, 4.2.12
- 4.3.0, 4.3.1

### Python

- Python 3 (>= 3.9)
  - Tested with python versions 3.11 on Windows, Ubuntu20.22 and MacOS
- Python packages
	- python-irodsclient>=1.1.6
	- tqdm	

### icommands (optional)
If the icommands are installed, the users can choose them as backend for up and downloads.

## Installation
### From Github repository
```
git clone git@github.com:UtrechtUniversity/iBridges.git
cd iBridges
pip install pip install .
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

**Raoul Schramm (Maintainer) [ORCID](https://orcid.org/my-orcid?orcid=0000-0001-6616-230X)**. 
*Utrecht University* 2024

## Contributors

**J.P. Mc Farland**,
*University of Groningen, Center for Information Technology*, 2022

## License
This project is licensed under the GPL-v3 license.
The full license can be found in [LICENSE](LICENSE).
