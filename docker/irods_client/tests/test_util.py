from copy import deepcopy

from pytest import mark

from ibridges import IrodsPath, Session, download, upload
from ibridges.util import calc_checksum, checksums_equal


@mark.parametrize(
    "check_type,checksum", [
        # There seems some PRC issue with dynamically switching checksums
        # ("md5", "e313c75f6de6e7cea6c641a99adb18d9"),
        ("sha2", "sha2:Ys0LhUZdm4jCp83Zy//9Jojs74BzKDrnYYPqqv0MqeU=")]
)
def test_calc_checksum(irods_env, config, check_type, checksum, testdata, tmp_path):
    ienv = deepcopy(irods_env)
    ienv["irods_default_hash_scheme"] = check_type.upper()
    with Session(irods_env=ienv, password=config["password"]) as session:
        ipath_coll = IrodsPath(session, "test_check")
        ipath_coll.remove()
        ipath_coll.create_collection()
        upload(testdata / "bunny.rtf", ipath_coll)
        ipath = ipath_coll / "bunny.rtf"
        download(ipath, tmp_path)
        assert calc_checksum(ipath, checksum_type=check_type) == checksum
        assert calc_checksum(tmp_path / "bunny.rtf", checksum_type=check_type) == checksum
        assert checksums_equal(ipath, tmp_path / "bunny.rtf")
        ipath_coll.remove()

