# iBridges
## About

The git repository contains a generic *iRODS* graphical user interface and the corresponding command-line interface clients.  The GUI and CLI work with any *iRODS* instance.  However, for user and data security we depend on some *iRODS* event hooks that need to be installed on the *iRODS* server.  Please refer to the documentation below.

[Explore the documentation](https://chstaiger.github.io/iBridges-Gui/)

## Authors

Tim van Daalen, Christine Staiger

Wageningen University & Research 2021

## Contributors

J.P. Mc Farland

University of Groningen, Center for Information Technology, 2022

## Dependencies

### Python

- Python 3 (>= 3.6)
  - Tested on versions up to 3.10 on multiple platforms
- pip-22.2.2
- Python packages (see install via `requirements.txt` below)

Install dependencies with, for example:

```sh
python3.10 -m pip install -r requirements.txt
```

## Configuration

### iRODS environment.json

- Please create a directory/folder named `.irods` in your home directory/folder (`~/.irods/` in Linux shorthand).
  - Linux: `/home/\<username\>/.irods/irods_environment.json`
  - Mac: `/Users/\<username\>/.irods/irods_environment.json`
  - Windows: `C:\\\\....\\\<username\>\\.irods\\irods_environment.json`

- Your *iRODS* admin will provide an `irods_environment.json` file, its contents, or instructions on how to create it.  Place that file into the `.irods` directory/folder.  Here it an example that can be created with the `iinit` iCommand on Linux:

```json
{
    "irods_host": "server.fqdn.nl", 
    "irods_port": 1247, 
    "irods_user_name": "username", 
    "irods_zone_name": "myZone", 
    "irods_default_resource": "myResc" 
}
```

### iBridges config.json

*iBridges* will create its own configuration file in `~/.ibridges/` containing the name of the last *iRODS* environment file used.  This `config.json` file can be updated to control other aspects of *iBridges*.  For example:

```json
{
    "last_ienv": "irods_environment.json", 
    "davrods_server": "https://server.fqdn.nl", 
    "ui_tabs": [ 
        "tabUpDownload", 
        "tabELNData", 
        "tabDataBundle", 
        "tabCreateTicket" 
    ], 
    "force_unknown_free_space": false 
}
```
Options:
- `davrods_server`: for annotation of eLabJournal data
- `ui_tabs`: configure which tabs are shown (Browser and Info tabs always are)
  - `tabUpDownload`: a two-pane upload/download tab
  - `tabELNData`: for the Electronic Lab Notebook, eLabJournal
  - `tabDataBundle`: (un)bundle datasets from/to four supported formats
  - `tabCreateTicket`: create iRODS tickets for anonymous access
- `force_unknown_free_space`: ignore if resources' free space is unannotated

The `force_unknown_free_space` option is *REQUIRED* to be set to `true` if your default resource does not yet have its free space annotated.  It makes unannotated top-level resources visible in the drop-downs allowing selection of them.  In addition, it sets the `force` flag for uploads overriding resource overflow protection.

The logs for both GUI and CLI clients can be found in the `~/.ibridges/` directory/folder.

## Usage

```bash
export PYTHON_IRODSCLIENT_DEFAULT_XML=QUASI_XML
./irods-iBridgesGui.py
```

## Contributing
### Code
Instructions on how to extend the GUI or contribute to the code base can be found in the [documentation](https://chstaiger.github.io/iBridges-Gui/).

## License
This project is licensed under the GPL-v3 license.
The full license can be found in [LICENSE](LICENSE).
