import os
import sys

print("Integration tests start ...")
summary = {}
summary['python_version'] = sys.version
irods_env_path = "/root/.irods/irods_environment.json"

try:
    import irods

    from ibridges import Session
    from ibridges.irodsconnector.data_operations import download, get_collection, upload
    from ibridges.irodsconnector.meta import MetaData
    from ibridges.irodsconnector.resources import Resources
    from ibridges.utils.path import IrodsPath
    summary['import_backend'] = "success"
except Exception as e:
    print(repr(e))
    summary['import_backend'] = "fail"


# move cached password
# os.rename("/root/.irods/.irodsA", "/root/.irods/.irodsA_backup")

print("Connect with password")
try:
    session = Session(irods_env_path=irods_env_path,
                      password = "rods")
    print("Valid iRODS session: ", session.has_valid_irods_session())
    summary['iRODS_server_version'] = session.server_version
    summary['authentication_with_passwd'] = "success"
    session._write_pam_password()
except Exception as e:
    summary['authentication_with_passwd'] = repr(e)

# os.rename("/root/.irods/.irodsA_backup", "/root/.irods/.irodsA")
# print("Connect with cached password:")
# try:
#     del session
#     session = Session(irods_env_path=irods_env_path)
#     print("Valid iRODS session: ", session.has_valid_irods_session())
#     summary['iRODS_server_version'] = session.server_version
#     summary['authentication_cached_passwd'] = "success"
# except Exception as e:
#     summary['authentication_cached_passwd'] = repr(e)

print("Get home collection")
try:
    coll = get_collection(session, IrodsPath("~"))
    assert isinstance(coll, irods.collection.iRODSCollection)
    print(coll.path)
    summary['get_home_coll'] = "success"
except Exception as e:
    summary['get_home_coll'] = repr(e)

print("Get resources")
try:
    summary["resources"] = Resources(session).resources(update=True)
except Exception as e:
    summary["resources"] = repr(e)

print("Upload testdata folder")
try:
    upload_path = IrodsPath(session, "~", "testdata")
except Exception:
    pass
try:
    coll = get_collection(session, IrodsPath("~"))
    upload(session, "/tmp/testdata", IrodsPath("~"), session.default_resc) #, size=0, force=True)
    upload_coll = get_collection(session, upload_path)
    print("Uploaded data objects: ", str(upload_coll.data_objects))
    summary['upload_testdata_folder'] = "success"
except Exception as e:
    summary['upload_testdata_folder'] = repr(e)

print("Add metadata to collection")
try:
    meta = MetaData(upload_coll)
    meta.add('key', 'value')
    print(meta)
    summary['metadata_collection'] = meta
except Exception as e:
    summary['metadata_collection'] = repr(e)

print("Download collection")
try:
    download(session, upload_path, "/tmp") #, 0, force=True)
    files = os.listdir("/tmp/"+upload_coll.name)
    os.system("rm -rf /tmp/"+upload_coll.name)
    summary['download_collecion'] = files
except Exception as e:
    summary['download_collecion'] = repr(e)

print("Remove metadata")
try:
    meta.delete('key', 'value')
    print(meta)
    summary['delete_metadata'] = 'success'
except Exception as e:
    summary['delete_metadata'] = repr(e)

print("Delete collection")
try:
    upload_path.remove()
    # ic.data_op.delete_data(uploadColl)
    subcolls = [c.name for c in coll.subcollections]
    if "testdata" in subcolls:
        summary['delete_collection'] = 'failed'
    else:
        summary['delete_collection'] = 'success'
except Exception as e:
    summary['delete_collection'] = repr(e)

print("Close iBridges session")
try:
    del session
    summary['session_cleanup'] = "success"
except Exception as e:
    summary['session_cleanup'] = repr(e)

print("Integration tests end")
print()
print("Summary")
for key, value in summary.items():
    print(key, ':', value)
