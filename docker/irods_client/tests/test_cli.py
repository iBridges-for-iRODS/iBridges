import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from ibridges import IrodsPath
from ibridges.data_operations import create_collection


@pytest.fixture(scope="module")
def pass_opts(config):
    """Return input for CLI.

    This fixture ensures that if there is a cached password, we do not provide it to the CLI
    for every command, only to the `ibridges init` command.
    """
    if (config.get("can_write_pam_pass", True)
            or config.get("has_cached_pw", False)):
        pass_opts = {}
    else:
        pass_opts = {"input": config["password"].encode()}
    pass_opts["check"] = True
    return pass_opts

def _get_digest(obj_or_file):
    with open(obj_or_file, "rb") as handle:
        digest = hashlib.sha256(handle.read()).digest()
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


def test_upload_download_cli(session, config, testdata, tmpdir, irods_env_file, pass_opts):
    # Test the upload function by uploading a single file.
    ipath = IrodsPath(session, "~", "plant.rtf")
    ipath.remove()
    subprocess.run(["ibridges", "init", irods_env_file], **pass_opts)

    if "resc2" in config["resources"]:
        subprocess.run(["ibridges", "upload", testdata/"plant.rtf", "irods:" + str(ipath),
                        "--overwrite", "--resource", "resc2"], **pass_opts)
    else:
        subprocess.run(["ibridges", "upload", testdata/"plant.rtf", "irods:" + str(ipath),
                        "--overwrite"], **pass_opts)
    assert ipath.dataobject_exists()

    # Download the same file and check if they are equal.
    assert isinstance(testdata, Path)
    if "resc2" in config["resources"]:
        subprocess.run(["ibridges", "download", "irods:~/plant.rtf", testdata/"plant2.rtf",
                        "--resource", "resc2"], **pass_opts)
    else:
        subprocess.run(["ibridges", "download", "irods:~/plant.rtf", testdata/"plant2.rtf"],
                        **pass_opts)
    assert Path(testdata/"plant2.rtf").is_file()

    _check_files_equal(testdata/"plant2.rtf", testdata/"plant.rtf")
    (testdata/"plant2.rtf").unlink()

    # Upload a directory and check if the dataobjects and collections are created.
    ipath = IrodsPath(session, "~", "test")
    ipath.remove()
    create_collection(session, ipath)
    subprocess.run(["ibridges", "upload", testdata, "irods:~/test", "--overwrite"], **pass_opts)
    for fname in testdata.glob("*"):
        assert ((ipath / "testdata" / fname.name).dataobject_exists()
                or (ipath / "testdata" / fname.name).collection_exists())

    # Download the created collection and check whether the files are the same.
    subprocess.run(["ibridges", "download", "irods:~/test/testdata", tmpdir], **pass_opts)
    for fname in testdata.glob("*"):
        assert _check_files_equal(testdata/fname.name, tmpdir/"testdata"/fname.name)
    Path(tmpdir/"testdata").unlink

    # Synchronize a collection to a temporary directory and check if they are the same.
    subprocess.run(["ibridges", "sync", "irods:~/test/testdata", tmpdir], **pass_opts)
    for fname in testdata.glob("*"):
        assert _check_files_equal(testdata/fname.name, tmpdir/fname.name)

def test_upload_download_metadata(session, config, testdata, tmpdir, irods_env_file, pass_opts):
    ipath_collection = IrodsPath(session, "meta_test")
    ipath_collection.remove()
    subprocess.run(["ibridges", "upload", testdata, f"irods:{ipath_collection}"],
                   **pass_opts)
    assert ipath_collection.exists()
    meta = ipath_collection.meta
    meta.add("some_key", "some_val")
    subprocess.run(["ibridges", "download", f"irods:{ipath_collection}", tmpdir, "--metadata"],
                   **pass_opts)
    meta_fp = tmpdir / "meta_test" / ".ibridges_metadata.json"
    assert meta_fp.isfile()
    with open(meta_fp, "r", encoding="utf-8") as handle:
        metadata = json.load(handle)
        assert metadata["items"][0]["name"] == "meta_test"
        assert metadata["items"][0]["metadata"][0][0] == "some_key"
        assert metadata["items"][0]["metadata"][0][1] == "some_val"
    ipath_collection.remove()
    subprocess.run(["ibridges", "upload", tmpdir / "meta_test", "irods:",
                    "--metadata"], **pass_opts)
    assert ("some_key", "some_val") in ipath_collection.meta
    ipath_collection.remove()


def test_list_cli(config, pass_opts, irods_env_file):
    # Check if the listing works without any errors.
    subprocess.run(["ibridges", "init", irods_env_file], **pass_opts)
    subprocess.run(["ibridges", "list"], **pass_opts)
    subprocess.run(["ibridges", "list", "irods:test"], **pass_opts)
