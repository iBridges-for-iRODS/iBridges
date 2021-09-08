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
            *size1 = int(*row.DATA_SIZE);
        }
        foreach(*row in SELECT sum(DATA_SIZE) where COLL_NAME like "*coll"){
            *size2 = int(*row.DATA_SIZE);
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
            *rescSize = int(*row.RESC_FREE_SPACE);
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
        writeLine("stdout", "Create *tarFile");
        msiArchiveCreate(*tarFile, *coll);
        if(bool(*delete)){
            msiRmColl(*coll, "forceFlag=", *out);
            writeLine("stdout", *out);
        }
    }
    else{writeLine("stdout", "DEBUG tarCollection: no action.")}
}

input *coll="/npecZone/home/cstaiger/TEST", *resource="disk", *compress="false", *delete="false"
output ruleExecOut
