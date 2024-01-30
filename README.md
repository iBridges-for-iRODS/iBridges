# iBridges
[![Python package](https://github.com/UtrechtUniversity/iBridges/actions/workflows/main.yml/badge.svgi?branch=develop)](https://github.com/UtrechtUniversity/iBridges/actions/workflows/main.yml)

## About

This git repo contains some wrapping classes and functions around the *python-irodsclient* 
to ease the connection and meta/data handling in iRODS.

We offer two main classes

- irodsConnector: basic iRODS functionality
- ibridges: extra fuctionality and presets for scientific programmers to safely wirk with data on an iRODS server.

## Authors

Tim van Daalen, Christine Staiger

Wageningen University & Research 2021

## Contributors

J.P. Mc Farland

University of Groningen, Center for Information Technology, 2022

Raoul Schram, Maarten Schermer

Utrecht University, 2023

## Dependencies

### Supported iRODS versions

- 4.2.11, 4.2.12
- 4.3.0

### Python

- Python 3 (>= 3.9)
  - Tested with python versions 3.11 on Windows, Ubuntu20.22 and MacOs
- pip-22.2.2
- Python packages (see install via `requirements.txt` below)

Install dependencies with, for example:

```sh
python3.11 -m pip install -r requirements.txt
```
### icommands (optional)
If the icommands are installed, the users can choose them as backend for up and downloads.

## Usage

[irodsConnector](Tutorial_irodsConnector.ipynb)

[iRODS paths](Tutorial_iRODS_paths.ipynb)

## License
This project is licensed under the GPL-v3 license.
The full license can be found in [LICENSE](LICENSE).
