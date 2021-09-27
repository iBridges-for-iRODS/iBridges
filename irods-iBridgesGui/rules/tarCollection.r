tarCollection{

    msiGetObjType(*coll, *objType);
    *s = size(split(*coll, "/")); #path level needs to be deeper than /zone/home/user
    msiGetObjType(*resource, *rescType)
    *run = true;

    *size1 = 0;
    *size2 = 0;
    *size = 0;
    *rescSize = 0;

    if(*objType != "-c"){
        writeLine("stderr", "ERROR tarCollection: *coll not a collection.");
        *run = false;
    }
    else{
    	foreach(*row in SELECT sum(DATA_SIZE) where COLL_NAME like "*coll/%"){
            *size1 = double(*row.DATA_SIZE);
        }
        foreach(*row in SELECT sum(DATA_SIZE) where COLL_NAME like "*coll"){
            *size2 = double(*row.DATA_SIZE);
	}
	*size = *size1+*size2;
	if(*size==0){
            *run = false;
	    writeLine("stderr", "ERROR tarCollection: *coll empty: Size *size.");
	}
    }

    if(int(*s) < 4){
        writeLine("stderr", "ERROR tarCollection: cannot bundle root or home of users.");
        *run = false;
    }

    if(*rescType != "-r"){
        writeLine("stderr", "ERROR tarCollection: *resource not a resource.");
        *run = false;
    }
    else{
        foreach(*row in SELECT RESC_FREE_SPACE where RESC_NAME like *resource){
            *rescSize = double(*row.RESC_FREE_SPACE);
        }
        if(*rescSize < *size*2-*rescSize/10){
            writeLine("stderr", "ERROR tarCollection: Not enough space on *resource");
	    *run = false;
        }
    }

    if(*run== true){
        msiSplitPath(*coll, *parentColl, *collName);
        if(bool(*compress)){
            *tarFile = "*parentColl/*collName.irods.zip"
        }
        else {*tarFile = "*parentColl/*collName.irods.tar"}
        writeLine("stdout", "*tarFile");
        msiArchiveCreate(*tarFile, *coll, *resource, *outTar);
        if(bool(*delete) && *outTar == 0){
            writeLine("stdout", "DEBUG tarCollection: Delete *coll")
	    msiRmColl(*coll, "forceFlag=", *out);
            #writeLine("stdout", *out);
        }
	if(*outTar!=0){writeLine("stderr", "Tar failed.")}
    }
    else{writeLine("stdout", "DEBUG tarCollection: no action.")}
}

input *coll="/npecZone/home/cstaiger/Uploads/ACES", *resource="disk", *compress="false", *delete="false"
output ruleExecOut
