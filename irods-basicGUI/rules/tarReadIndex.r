tarReadIndexFile{
    msiGetObjType(*path, *objType);
    *suffix = substr(*path, strlen(*path)-9, strlen(*path)); 
    *run = true;

    writeLine("stdout", "DEBUG tarReadIndex: *suffix");
    
    if(*suffix != "irods.tar" && *suffix != "irods.zip"){
        *run = false;
        writeLine("stderr", "ERROR tarReadIndex: not an irods.tar file, *path")
    }
    
    if(*run == true){
        msiArchiveIndex(*path, *out);
        writeLine("stdout", *out)
    }
    else{writeLine("stdout", "DEBUG tarReadIndex: no action.")}

}

input *path="/bobZone/home/bob/test.irods.tar"
output ruleExecOut
