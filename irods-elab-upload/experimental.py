from elabjournal import elabjournal
from irods.session import iRODSSession
import irods.keywords as kw
import os
import ssl
import platform

def getSize(path):
    size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for i in filenames:
            f = os.path.join(dirpath, i)
            size += os.path.getsize(f)
    return float(size)/(1024**3)

def iRODSupload(source, destination, resource = "bigstore"):
    """
    source: absolute path to file or folder
    destination: iRODS collection where data is uploaded to
    resource: name of the iRODS storage resource to use

    The function uploads the contents of a folder with all subfolders to an iRODS collection.
    If source is the path to a file, the file will be uploaded.
    """
    options = {kw.RESC_NAME_KW: resource, 
               kw.REG_CHKSUM_KW: ''}

    if os.path.isfile(source):
        session.collections.create(destination.path)
        session.data_objects.put(source, destination.path+"/"+os.path.basename(source), **options)
    elif os.path.isdir(source):
        for directory, _, files in os.walk(source):
            subColl = directory.split(source)[1]
            iColl = destination.path+subColl
            session.collections.create(iColl)
            for fname in files:
                print("CREATE", iColl+'/'+fname)
                session.data_objects.put(directory+'/'+fname, iColl+'/'+fname, **options) 
    else:
        print("ERROR iRODS upload: not a valid source path")


RED = '\x1b[1;31m'
DEFAULT = '\x1b[0m'
YEL = '\x1b[1;33m'
BLUE = '\x1b[1;34m'

# PARAMETERS
eLABKey = "wur.elabjournal.com;6d91b9e86f7016a195f326262100fe24"
title = "New paragraph section."
envFile = os.environ["HOME"]+"/.irods/irods_environment.json"
webDav = "http://scomp1486.wurnet.nl"

eLAB = elabjournal.api(key=eLABKey)
groupID = eLAB.group().id()
userID = eLAB.user().id()
title = "New paragraph section."

#### Information from ELN
print("Your current group:")
print(eLAB.group().name())

menu = input("Do you want to change your current group? (Y(es) or enter to skip)")
while menu in ["Y", "y", "yes", "YES", "Yes"]:
    print(eLAB.groups().all(["name", "description"]))
    groupID = input("For which groupID do you want to upload data: ")
    if int(groupID) in eLAB.groups().all().index:
        eLAB.set_group(groupID)
        print(BLUE+"Group changed: "+eLAB.group().name()+DEFAULT)
        menu = "N"
    else:
        print(YEL+"\nNot a valid groupID"+DEFAULT)

experiments = eLAB.experiments()
expFrames = eLAB.experiments().all()
print("Your experiments:")
print(expFrames.loc[expFrames["userID"] == userID, ["name", "projectID"]])
print("\n")
print("Other experiments:")
print(expFrames.loc[expFrames["userID"] != userID, ["name", "projectID"]])
menu = input("To which experiment does the data belong? (experimentID):")
while int(menu) not in expFrames.index:
    print(YEL+"\nNot a valid experimentID"+DEFAULT)
    menu = input("To which experiment does the data belong? (experimentID):")
experimentID = int(menu)
print(BLUE+"Data will be uploaded to:")
print(expFrames.iloc[[expFrames.index.get_loc(int(experimentID))]][["studyID", "name"]])
print(DEFAULT+"\n")
experiment = experiments.get(experimentID)

#### Information from iRODS
# For the elabjournal instance we use PAM authentication
# Authentication by irods_environment.json
webDav = "http://scomp1486.wurnet.nl"
session = iRODSSession(irods_env_file=envFile)
homeColl = session.collections.get("/"+session.zone+"/home/"+session.username)

# Ensure that the path ELN/groupname/experimentname is present
#the create method ensures that the path exists andcreates folder if necessary
session.collections.create(
    (homeColl.path+"/ELN/"+eLAB.group().name()+"/"+experiment.name()).replace(" ", "_"))
uploadColl = session.collections.get((homeColl.path+"/ELN/"+eLAB.group().name()+"/"+experiment.name()).replace(" ", "_"))

#### Data upload to iRODS
menu = input("Upload data: (Path to file or folder)")
while not os.path.exists(menu):
    print(YEL+"\nNot a valid Path"+DEFAULT)
    menu = input("Upload data: (Path to file or folder)")
size = getSize(menu)
print(BLUE+"Uploading data in "+ menu)
print(str(size)+"GB")
iRODSupload(menu, uploadColl)

metaValue = "https://"+eLABKey.split(";")[0]+"/members/experiments/browser/#view=experimentID="+str(experimentID)
metaKey = "PROVENANCE"
uploadColl.metadata.add(metaKey, metaValue)

#### Create new section in ELN with iRODS path
webdavLink = webDav+uploadColl.path
experiment.add("Data uploaded to iRODS: "+webdavLink, title)

