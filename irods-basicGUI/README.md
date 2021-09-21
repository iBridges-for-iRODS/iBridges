# iRODS basic GUI
## Synopsis
## Dependencies
- Python 3
	- Tested on 3.6 and 3.9.6
- pip-21.1.3

- Python packages
	- Cryptography
	- PyQt5
	- python-irodsclient-1.0.0
	- elabjournal

```
pip install -r requirements.txt
```

## Configuration
### iRODS environment.json
- Please create a folder `.irods` in your home
   - Linux: /home/<username>/.irods
   - Mac: /Users/<username>/.irods
   - Windows: C:\\....

- Your iRODS admin will proivide a file `irods_environment.json`. Place that file into the `.irods` folder
   Example:
   ```
   {
	"irods_host": "scomp1461.wur.nl", 
	"irods_port": 1247, 
	"irods_user_name": "cstaiger", 
	"irods_zone_name": "npecZone", 
	"default_resource_name": "disk", 
	"davrods_server": "https://scomp1461.wur.nl", 
	"ui_tabs": [ #Activated tabs for the user
		"tabBrowser", 
		"tabUpDownload",
		"tabELNData", 
		"tabDataCompression" #requires "default_resource_name" (not demoResc!)
	], 
	"ui_ienvFilePath": "/home/christine/.irods/irods_environment.json_npec"
   }
   ```



## Usage
```
python3 irods-basicGui.py
```

## Remarks
### Performance

- When the client is started for the first time it, might take some time to launch.
- Tested on
	- 4cores, 8GB memory: Quick performance. GUI reacts :very quickly.

- Upload performances 
	- icommands: Upload speed is mainly impacted by network speed
	- default: Upload performance is depending on network speed and performance of the iRODS python API: https://github.com/chStaiger/irods-performances
	- 4GB from home network through python API takes about 30 minutes.	

### ELabjournal
- Data Upload to Elabjournal works in an own thread. Hence, you can continue working in other Tabs of the application.
- The laoding of Projects and Experiments takes quite long and depends on the performance of the Elabjournal server and the elabjournal python library.
- After clicking 'Upload' the application also waits for some response of the Elabjournal and seems to 'hang'.
- Before data is uploaded, there is a check whether data fits on th iRODS resource.
- Small hickup after Data upload to Elabjournal finished. The stopping and cleaning up of the thread is done in the main application and affects all Tabs for a short moment. 

## Delete function
- If a lot of data is deleted, the application 'hangs'. 4GB  about 3 minutes
