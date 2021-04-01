# iBridges - Upload client

## Dependencies

- Python3
- Dependencies for elabJournal:

```
sudo apt-get install build-essential libssl-dev libffi-dev python3-dev cargo
pip install cryptography
pip install elabjournal
```

- Dependencies for iRODS:

```
pip install python-irodsclient
```

## Usage

- Configuration file:
  - Default

```
[iRODS]
irodsenv = <path to>/irods_environment.json
irodscoll = 
irodsresc = 
webdav = 
```

- Configuration files for the iRODS-Elab instance

  - The iRODS instance is SSL encrypted to allow for interactions with LDAP, you can use your WUR-account and password to login.
  - You need an irods.crt file (contact iRODS admin)
  - iRODS environment file:

  ```
  {
      "irods_host": "scomp1486.wurnet.nl",
      "irods_port": 1247,
      "irods_zone_name": "elabZone",
      "irods_user_name": "<WUR-account>", 
      "irods_client_server_negotiation": "request_server_negotiation",
      "irods_client_server_policy": "CS_NEG_REQUIRE",
      "irods_encryption_key_size": 32,
      "irods_encryption_salt_size": 8,
      "irods_encryption_num_hash_rounds": 16,
      "irods_encryption_algorithm": "AES-256-CBC",
      "irods_ssl_ca_certificate_file": "<path to>/irods.crt",
      "irods_authentication_scheme": "PAM"
  }
  ```

  - Config file for the upload client

  ```
  [iRODS]
  irodsenv = /<path to>/irods_environment.json
  irodscoll = 
  irodsresc = 
  webdav = http://scomp1486.wurnet.nl
  
  [ELN]
  token = wur.elabjournal.com;<some hash>
  group =
  experiment =
  title =
  ```

  - In the iRODS instance there are two iRODS resources available:
    - bigstore: ~300GB
    - demoResc: ~5GB

## Usage

```
./iUpload -c </path/to/config> -d </path/to/folder/or/file/to/upload>
```



