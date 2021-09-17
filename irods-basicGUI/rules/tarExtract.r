tarExtract{

    msiGetObjType(*obj, *objType);

    writeLine("stdout", "*obj, *objType");
    msiSplitPath(*obj, *parentColl, *objName);
    *suffix = substr(*obj, strlen(*obj)-9, strlen(*obj));
    *objName = substr(*objName, 0, strlen(*objName)-10);
    writeLine("stdout", "DEBUG tarExtract *parentColl");
    writeLine("stdout", "DEBUG tarExtract *objName, *suffix");
    *run = true;

    if(*objType != '-d'){
        *run = false;
        writeLine("stderr", "ERROR tarExtract: not a data object, *path")
    }
    if(*suffix != "irods.tar" && *suffix != "irods.zip"){
        *run = false;
        writeLine("stderr", "ERROR tarExtract: not an irods.tar file, *path")
    }

    if(*run== true){
        writeLine("stdout", "STATUS tarExtract: Create collection *parentColl/*objName");
        msiCollCreate("*parentColl/*objName", 1, *collCreateOut);
        if(*collCreateOut == 0){
            writeLine("stdout", "STATUS tarExtract: Extract *obj to *parentColl/*objName");
            msiArchiveExtract(*obj, "*parentColl/*objName", *resource, *outTarExtract);
            if(*outTarExtract != 0){
                writeLine("stderr", "ERROR tarExtract: Failed to extract data");
            }
        }
        else{
            writeLine("stderr", "ERROR tarExtract: Failed to create *parentColl/*objName")
        }
    }
    else{writeLine("stdout", "DEBUG tarExtract: no action.")}
}

input *obj="/npecZone/home/cstaiger/Uploads/ACES.irods.zip", *resource="disk"
output ruleExecOut

