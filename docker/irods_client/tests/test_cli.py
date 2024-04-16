import hashlib
import subprocess
from pathlib import Path

from ibridges import IrodsPath
from ibridges.data_operations import create_collection


def _get_digest(obj_or_file):
    with open(obj_or_file, "rb") as handle:
        digest = hashlib.sha1(handle.read()).digest()
    return digest


def _check_files_equal(*files):
    if all(Path(f).is_dir() for f in files):
        for fname in files[0].glob("*"):
            if not _check_files_equal(*[d/fname.name for d in files]):
                 return False
        return True
    assert len(files) > 0
    digests = [_get_digest(f) for f in files]

    for dig in digests[1:]:
        if digests[0] != dig:
            return False
    return True


def test_upload_download_cli(session, config, testdata, tmpdir, irods_env_file):
    ipath = IrodsPath(session, "~", "plant.rtf")
    ipath.remove()
    subprocess.run(["ibridges", "init", irods_env_file],
                   check=True, input=config["password"].encode())
    subprocess.run(["ibridges", "upload", testdata/"plant.rtf", "irods:" + str(ipath),
                    "--overwrite"],
                   check=True)
    assert ipath.dataobject_exists()
    subprocess.run(["ibridges", "download", "irods:~/plant.rtf", testdata/"plant2.rtf"])
    _check_files_equal(testdata/"plant2.rtf", testdata/"plant.rtf")
    (testdata/"plant2.rtf").unlink()

    ipath = IrodsPath(session, "~", "test")
    ipath.remove()
    create_collection(session, ipath)
    subprocess.run(["ibridges", "upload", testdata, "irods:~/test", "--overwrite"], check=True)
    for fname in testdata.glob("*"):
        assert ((ipath / "testdata" / fname.name).dataobject_exists()
                or (ipath / "testdata" / fname.name).collection_exists())

    subprocess.run(["ibridges", "download", "irods:~/test/testdata", tmpdir], check=True)

    for fname in testdata.glob("*"):
        assert _check_files_equal(testdata/fname.name, tmpdir/"testdata"/fname.name)
    Path(tmpdir/"testdata").unlink

    print(list(testdata.glob("*")))
    print(list(Path(tmpdir).glob("*")))
    subprocess.run(["ibridges", "sync", "irods:~/test/testdata", tmpdir], check=True)
    for fname in testdata.glob("*"):
        assert _check_files_equal(testdata/fname.name, tmpdir/fname.name)


def test_ls_cli(config):
    subprocess.run(["ibridges", "init"], check=True, input=config["password"].encode())
    subprocess.run(["ibridges", "ls"], check=True)
    subprocess.run(["ibridges", "ls", "test"], check=True)
