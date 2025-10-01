import hashlib
import json
import subprocess
from pathlib import Path

import pytest
from pytest import mark

from ibridges import IrodsPath
from ibridges.meta import MetaData


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
        pass_opts = {"input": config["password"]+"\n"}
    pass_opts["text"] = True
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
    ipath.remove()

    # Upload a directory and check if the dataobjects and collections are created.
    ipath = IrodsPath(session, "~", "test")
    ipath.remove()
    ipath.create_collection()
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
    ipath.remove()


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

    # Check uploading metadata with upload
    subprocess.run(["ibridges", "upload", tmpdir / "meta_test", "irods:",
                    "--metadata"], **pass_opts)
    assert ("some_key", "some_val") in ipath_collection.meta

    # Check uploading metadata with sync
    ipath_collection.meta.delete("some_key", "some_val")
    subprocess.run(["ibridges", "sync", tmpdir / "meta_test", "irods:meta_test",
                    "--metadata"], **pass_opts)
    assert ("some_key", "some_val") in ipath_collection.meta

    ipath_collection.remove()


def test_list_cli(config, pass_opts, irods_env_file, collection):
    # Check if the listing works without any errors.
    subprocess.run(["ibridges", "init", irods_env_file], **pass_opts)
    subprocess.run(["ibridges", "list"], **pass_opts)
    subprocess.run(["ibridges", "list", f"irods:{collection.path}"], **pass_opts)
    subprocess.run(["ibridges", "list", "-i"], **pass_opts)
    subprocess.run(["ibridges", "list", "-l"], **pass_opts)


@mark.parametrize(
    "search,nlines",
    [
        (["--path-pattern", "test_search"], 1),
        (["--path-pattern", "test_search2"], 0),
        (["--path-pattern", "test_search/%"], 6),
        (["--path-pattern", "test_search/%/%"], 1),
        (["--path-pattern", "%.rtf"], 4),
        (["--checksum", "sha2:uJzC+gqi59rVJu8PoBAaTstNUUnFMxW9HsJzsJUb1ao="], 1),
        (["--checksum", "sha2:uJzC+gqi5%"], 1),
        (["--path-pattern", "%", "--item_type", "data_object"], 6),
        (["--path-pattern", "%", "--item_type", "collection"], 2),
        (["--path-pattern", "%/%", "--item_type", "collection"], 2),
        (["--metadata", "search"], 1),
        (["--metadata", "search", "sval", "kg"], 1),
        (["--metadata", "search", "--metadata", "search2"], 1),
        (["--metadata", "search", "--metadata", "does not exist"], 0),
    ]
)
def test_search_cli(session, config, pass_opts, irods_env_file, testdata, search, nlines):
    subprocess.run(["ibridges", "init", irods_env_file], **pass_opts)
    ipath_coll = IrodsPath(session, "test_search_x", "test_search")
    ipath_coll.create_collection()
    subprocess.run(["ibridges", "sync", testdata, "irods:test_search_x/test_search"], **pass_opts)
    assert ipath_coll.collection_exists()
    ipath_coll.meta.clear()
    ipath_coll.meta.add("search", "sval", "kg")
    ipath_coll.meta.add("search2", "small")

    ret = subprocess.run(["ibridges", "search", "irods:test_search_x", *search], capture_output=True,
                         **pass_opts)
    stripped_str = ret.stdout.strip("\n")
    if stripped_str == "":
        assert nlines == 0
    else:
        assert len([x for x in stripped_str.split("\n") if not x.startswith("Your iRODS")]) == nlines
    ipath_coll.remove()

@mark.parametrize("item_name", ["collection", "dataobject"])
def test_meta_cli(item_name, request, pass_opts):
    item = request.getfixturevalue(item_name)
    meta = MetaData(item)
    meta.clear()
    cli_path = f"irods:{item.path}"

    ret = subprocess.run(["ibridges", "meta-list", cli_path], capture_output=True, **pass_opts)
    assert len(ret.stdout.strip("\n").split("\n")) == 1

    subprocess.run(["ibridges", "meta-add", cli_path, "key", "value", "units"], **pass_opts)
    meta.refresh()
    assert ("key", "value", "units") in meta

    subprocess.run(["ibridges", "meta-del", cli_path, "--key", "key"], **pass_opts)
    meta.refresh()
    meta = MetaData(item)
    assert ("key", "value", "units") not in meta



def test_aliases(pass_opts, irods_env_file, tmpdir, collection, session):
    coll_ipath = IrodsPath(session, collection.path)
    base_path = IrodsPath(session, "~")
    irods_env_file_2 = f"{tmpdir}/{Path(irods_env_file).name}"
    subprocess.run(["cp", irods_env_file, f"{irods_env_file_2}"], **pass_opts)
    subprocess.run(["ibridges", "init", irods_env_file], **pass_opts)
    subprocess.run(["ibridges", "init", irods_env_file_2], **pass_opts)
    subprocess.run(["ibridges", "alias", "first", irods_env_file], **pass_opts)
    subprocess.run(["ibridges", "alias", "second", irods_env_file_2], **pass_opts)
    subprocess.run(["ibridges", "init", "first"], **pass_opts)
    subprocess.run(["ibridges", "init", "second"], **pass_opts)
    ret = subprocess.run(["ibridges", "alias"], **pass_opts, capture_output=True)
    assert f"first -> {Path(irods_env_file).absolute()}" in ret.stdout
    assert f"second -> {Path(irods_env_file_2).absolute()}" in ret.stdout
    # assert len(ret.stdout.strip("\n").split("\n")) == 2
    subprocess.run(["ibridges", "cd", str(coll_ipath)], **pass_opts)
    ret = subprocess.run(["ibridges", "pwd"], **pass_opts, capture_output=True)
    assert ret.stdout.strip("\n").split("/")[-1] == coll_ipath.name
    subprocess.run(["ibridges", "init", "first"], **pass_opts)
    ret = subprocess.run(["ibridges", "pwd"], **pass_opts, capture_output=True)
    assert ret.stdout.strip("\n").split("/")[-1] == base_path.name

    subprocess.run(["ibridges", "init", "second"], **pass_opts)
    subprocess.run(["ibridges", "cd"], **pass_opts)
    ret = subprocess.run(["ibridges", "pwd"], **pass_opts, capture_output=True)
    assert ret.stdout.strip("\n").split("/")[-1] == base_path.name

    subprocess.run(["ibridges", "alias", "--delete", "first"], **pass_opts)
    subprocess.run(["ibridges", "alias", "--delete", "second"], **pass_opts)

    # ret = subprocess.run(["ibridges", "pwd"], **pass_opts, capture_output=True)
    # assert ret.stdout.strip("\n").split("/")[-1] == base_path.name

def test_shell(pass_opts):
    input_str = pass_opts.get("input", "")
    input_str += "\n?\n?ls\n!ls\n!cd\nls\nquit\n"
    new_pass_opts = {k: v for k, v in pass_opts.items() if k != "input"}
    subprocess.run(["ibridges", "shell"], **new_pass_opts, input=input_str,
                   capture_output=True)


def test_rm(pass_opts, testdata, session, irods_env_file):
    if IrodsPath(session, "rm_test").exists():
        IrodsPath(session, "rm_test").remove()
    subprocess.run(["ibridges", "init", irods_env_file], **pass_opts, capture_output=True)
    subprocess.run(["ibridges", "mkcoll", "rm_test"], **pass_opts, capture_output=True)
    subprocess.run(["ibridges", "upload", str(testdata), "irods:rm_test"], **pass_opts)
    assert IrodsPath(session, "rm_test").exists()
    subprocess.run(["ibridges", "rm", "-r", "rm_test"], **pass_opts)
    assert not IrodsPath(session, "rm_test").exists()
