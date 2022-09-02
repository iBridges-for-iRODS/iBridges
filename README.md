# iBridges

## Authors

Tim van Daalen, Christine Staiger

Wageningen University & Research 2021

## Contributors

J.P. Mc Farland

University of Groningen, Center for Information Technology, 2022

## Synopsis

The git repository contains a generic *iRODS* graphical user interface and the corresponding command-line interface clients.  The GUI and CLI work with any *iRODS* instance.  However, for user and data security we depend on some *iRODS* event hooks that need to be installed on the *iRODS* server.  Please refer to the documentation below.

## Dependencies

### iRODS server

To protect the *iRODS* resources from overflowing you should install an event hook on the *iRODS* servers that fill the resources' `RESC_FREE_SPACE` attribute in the iCAT.  These can be either *catalog* or *resource* servers.  Please add the following to the `/etc/irods/core.re` or another rule engine file:

```py
######################################################
# Storage capacity policies.
# Update the metadata field free_space of the resource
# when data is moved there or deleted from it.
#
# Author: Christine Staiger (2021)
#######################################################

acPostProcForParallelTransferReceived(*leaf_resource) {
    msiWriteRodsLog("LOGGING: acPostProcForParallelTransferReceived", *Status);
    msi_update_unixfilesystem_resource_free_space(*leaf_resource);
}

acPostProcForDataCopyReceived(*leaf_resource) {
    msiWriteRodsLog("LOGGING: acPostProcForDataCopyReceived", *Status);
    msi_update_unixfilesystem_resource_free_space(*leaf_resource);
}

# for iput
acPostProcForPut {
    msi_update_unixfilesystem_resource_free_space($KVPairs.rescName);
}

# for storage update after irmtrash
acPostProcForDelete {
    msi_update_unixfilesystem_resource_free_space($KVPairs.rescName);
}
```

For very busy systems, updating this value for every upload or delete can be prevented by commenting out or removing the last two stanzas if performance is being hampered.

For more complex resource hierarchies, the top of the resource tree (the _root_ node) will usually not be updated with the free space values, but if it is (the sum of all _leaf_ nodes is asssumed), the value in any _leaf_ nodes will be ignored.  If the _root_ node has no free space value, the sum of the _leaf_ nodes will be used instead.  If none of the resource nodes are annotated, an error will occur.  This feature can be overridden by annotating the _root_ node's free space value with an arbitrarily large value.  _*Please note, that this action disables the built-in protection offered by this client.*_

### Python

- Python 3 (>= 3.6)
  - Tested on 3.6 and 3.9.6
- pip-21.1.3
- Python packages
  - Cryptography
  - PyQt5
  - python-irodsclient (>=1.0.0)
  - elabjournal
  - watchdog

```
pip install -r requirements.txt
```

### Operating system

The client works on Mac, Windows and Linux distributions.  On Mac and Windows it makes use solely of the *iRODS* Python API.  On Linux, we implemented a switch: if the *iRODS* icommands are installed, you can choose at the login page to up and download data through the icommand `irsync`. This is recommended for large data transfers.

- Install the *iBridges* GUI on a Linux (sub)system
- [Install the icommands](https://git.wur.nl/rdm-infrastructure/irods-training/-/blob/master/04-Training-Setup.md#icommands). 
- Start the *iBridges* GUI in the mode (icommands) on the Login screen.
<img src="gui/icons/irods-basicGUI_Login.png" width="500">

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
    "ui_tabs": [  # Activated tabs for the user beyond just the Browser and Info tabs
        "tabBrowser",  # default
        "tabUpDownload",  # requires "irods_default_resource" (not demoResc!)
        "tabELNData", 
        "tabDataCompression"  # requires "irods_default_resource" (not demoResc!)
    ]
}
```

*PLEASE NOTE: the comments denoted by the hashes `#` will need to be removed as they will cause a JSON error.*

The logs for both GUI and CLI clients can be found in the `~/.ibridges/` directory/folder.

## Usage

```bash
...]$ ./irods-iBridgesGui.py
```

## Remarks

### Performance

- When the client is started for the first time it, might take some time to launch.
- Tested on
  - 4/2cores, 8/4GB memory: Quick performance.  GUI reacts very quickly.  Data transfers with default python API perform okay.  For large data we recommend to move to a linux system, install the icommands and use the GUI with icommands settings upon login.

- Upload performances
  - icommands: Upload speed is mainly impacted by network speed
  - default: Upload performance is depending on network speed and performance of the iRODS python API: https://github.com/chStaiger/irods-performances
  - 4GB from home network through python API takes about 30 minutes.

### Elabjournal

- Data Upload to Elabjournal works in an own thread.  Hence, you can continue working in other Tabs of the application.
- The laoding of Projects and Experiments takes quite long and depends on the performance of the Elabjournal server and the Elabjournal python library.
- After clicking 'Upload' the application also waits for some response of the Elabjournal and seems to 'hang'.
- Before data is uploaded, there is a check whether data fits on th iRODS resource.
- Small hickup after Data upload to Elabjournal finished.  The stopping and cleaning up of the thread is done in the main application and affects all Tabs for a short moment.

## Delete function

- If a lot of data is deleted, the application 'hangs'.

