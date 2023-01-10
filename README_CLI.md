# iBridges - Upload client

## Dependencies

- Python3
- Dependencies for elabJournal:

```
#sudo apt-get install build-essential libssl-dev libffi-dev python3-dev cargo
pip install elabjournal
```

- Dependencies for iRODS:

```
pip install python-irodsclient
```

## Configuration

- Minimal configuration file for uploading data to iRODs:

```
[iRODS]
irodsenv = /<path to>/irods_environment.json
irodscoll = 
irodsresc = 
webdav = 
```

- Configuration file for downloading data from iRODS:

```
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

  
  ```
Uploads local data to iRODS, and, if specified, links dat to an entry in a metadata store (ELN).
Usage: ./iUpload.py -c, --config= 	 config file
		    -d, --data= 	 datapath
		    -i, --irods= 	 irodspath (download)
Examples:
Downloading: ./irods-iBridgesCli.py -c <yourConfigFile> --irods=/npecZone/home
Uploading: ./irods-iBridgesCli.py -c <yourConfigFile> --data=/my/data/path
  ```



  
