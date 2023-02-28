# iBridges - Upload client

## Dependencies

- Python3
- Dependencies for elabJournal:

```sh
# sudo apt-get install build-essential libssl-dev libffi-dev python3-dev cargo
pip install elabjournal
```

- Dependencies for iRODS:

```sh
pip install python-irodsclient
```

## Configuration

- Minimal configuration file for uploading data to iRODs:

```ini
[iRODS]
irodsenv = /<path to>/irods_environment.json
irodscoll = 
irodsresc = 
webdav = 
```

- Configuration file for downloading data from iRODS:

```ini
[iRODS]
irodsenv = /<path to>/irods_environment.json
irodscoll = 
irodsresc = 
webdav = 

[DOWNLOAD]
path = /path/to/download/directory
```

- Configuration files for uploading data to iRODS and linking them to ElabJournal experiment:

```
  [iRODS]
  irodsenv = /<path to>/irods_environment.json
  irodscoll = 
  irodsresc = bigstore
  webdav = http://scomp1486.wurnet.nl
  
  [ELN]
  token = wur.elabjournal.com;<some hash>
  group =
  experiment =
  title =
  ```

## Usage

```sh
./irods-iBridgesCli.py -h
./irods-iBridgesCli -c </path/to/config> -d </path/to/folder/or/file/to/upload>
./irods-iBridgesCli.py -c </path/to/config> -i </zone/home/path/to/coll/or/obj>
```
