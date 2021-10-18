# iBRIDGES GUI
### Authors 
Tim van Daalen, Christine Staiger

Wageningen University & Research 2021

## Synopsis
The git repository contains a generic iRODS graphical userinterface and the corresponding commandline client.
The GUI and CLI work with any iRODS instance. However, for user and data security we depend on some iRODS event hooks that need to be installed on the iRODS server. Please refer to the documentation below.

## Dependencies

### iRODS server

To protect the iRODS resources from overflowing you need to install an event hook on the iRODS server that fills the resources' `RESC_FREE_SPACE` attribute in the iCAT. Please add the following to the `/etc/irods/core.re` or another rule engine file:

```py
######################################################
# Storage capacity policies. 
# Update the metadtaa field free_space of the resource 
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

acPostProcForPut { }

# for storage update after irmtrash
acPostProcForDelete {
    msi_update_unixfilesystem_resource_free_space($KVPairs.rescName);
}

acPostProcForDelete { }
```



### Python

- Python 3
	- Tested on 3.6 and 3.9.6
- pip-21.1.3
- Python packages
	- Cryptography
	- PyQt5
	- python-irodsclient-1.0.0
	- elabjournal
	- watchdog

```
pip install -r requirements.txt
```

### Operating system

The client works on  Mac, Windows and Linux distributions. On Mac and Windows it makes use solely of the iRODS python API. On Linux, we implemented a switch: If the iRODS icommands are installed, you can choose at the login page to up and download data through the icommand `irsync`. This is recommended for large data transfers.

- Install the iBridges GUI on a linux (sub)system
- [Install the icommands](https://git.wur.nl/rdm-infrastructure/irods-training/-/blob/master/04-Training-Setup.md#icommands). 
- Start the iBridges GUI in the mode (icommands) on the Login screen.
<img src="gui/icons/irods-basicGUI_Login.png" width="500">

## Configuration
### iRODS environment.json
- Please create a folder `.irods` in your home
   - Linux: /home/\<username\>/.irods/irods_environment.json
   - Mac: /Users/\<username\>/.irods/irods_environment.json
   - Windows: C:\\\\....\\\<username\>\\.irods\\irods_environment.json

- Your iRODS admin will proivide a file `irods_environment.json`. Place that file into the `.irods` folder
   Example:
   
```py
{
	"irods_host": "server.fqdn.nl", 
	"irods_port": 1247, 
	"irods_user_name": "cstaiger", 
	"irods_zone_name": "npecZone", 
	"default_resource_name": "disk", 
	"davrods_server": "https://server.fqdn.nl", 
	"ui_tabs": [ #Activated tabs for the user
		"tabBrowser", 
		"tabUpDownload", #requires "default_resource_name" (not demoResc!)
		"tabELNData", 
		"tabDataCompression" #requires "default_resource_name" (not demoResc!)
	]
}
```


## Usage
```
./irods-iBridgesGui.py
```

## Remarks
### Performance

- When the client is started for the first time it, might take some time to launch.
- Tested on
	- 4/2cores, 8/4GB memory: Quick performance. GUI reacts very quickly. Data transfers with default python API perform ok. For large data we recommend to move to a linux system, install the icommands and use the GUI with icommands settings upon login. 

- Upload performances 
	- icommands: Upload speed is mainly impacted by network speed
	- default: Upload performance is depending on network speed and performance of the iRODS python API: https://github.com/chStaiger/irods-performances
	- 4GB from home network through python API takes about 30 minutes.	

### Elabjournal
- Data Upload to Elabjournal works in an own thread. Hence, you can continue working in other Tabs of the application.
- The laoding of Projects and Experiments takes quite long and depends on the performance of the Elabjournal server and the Elabjournal python library.
- After clicking 'Upload' the application also waits for some response of the Elabjournal and seems to 'hang'.
- Before data is uploaded, there is a check whether data fits on th iRODS resource.
- Small hickup after Data upload to Elabjournal finished. The stopping and cleaning up of the thread is done in the main application and affects all Tabs for a short moment. 

## Delete function
- If a lot of data is deleted, the application 'hangs'. 4GB  about 3 minutes
