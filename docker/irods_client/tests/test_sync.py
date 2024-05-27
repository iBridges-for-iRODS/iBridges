from ibridges.data_operations import _calc_checksum, create_collection, sync
from ibridges.path import IrodsPath


def test_sync_dry_run(session, testdata, capsys):

    ipath = IrodsPath(session, "~", "empty")
    coll = create_collection(session=session, coll_path=ipath)
    assert len(coll.data_objects)+len(coll.subcollections)==0, "Dry run starting not empty"

    # upload
    ops = sync(session=session,
               source=testdata,
               target=ipath,
               max_level=None,
               dry_run=True,
               copy_empty_folders=True)

    assert len(ops["create_collection"]) == 1
    assert len(ops["create_dir"]) == 0
    assert len(ops["download"]) == 0
    assert len(ops["upload"]) == 7
    assert len(coll.data_objects)+len(coll.subcollections)==0, "Dry run did sync"


def test_sync_upload_download(session, testdata, tmpdir):
    ipath = IrodsPath(session, "~", "empty")
    coll = create_collection(session=session, coll_path=ipath)

    assert len(coll.data_objects)+len(coll.subcollections)==0, "iRODS folder not empty"

    # upload
    sync(session=session,
         source=testdata,
         target=ipath,
         max_level=None,
         dry_run=False,
         copy_empty_folders=True)

    for cur_file in list(testdata.glob("*")):
        s_ipath = IrodsPath(session, "~", "empty", cur_file.name)
        if cur_file.is_file():
            assert s_ipath.dataobject_exists(), "File not uploaded"
            cur_obj=s_ipath.dataobject
            assert _calc_checksum(cur_file)==(cur_obj.checksum
                if len(cur_obj.checksum)>0
                else cur_obj.chksum()), "Checksums not identical after upload"

    s_ipath = IrodsPath(session, "~/empty/more_data")
    assert s_ipath.collection_exists(), "Subfolder not uploaded"
    s_ipath = IrodsPath(session, "~/empty/more_data/polarbear.txt")
    assert s_ipath.dataobject_exists(), "File in subfolder not uploaded"
    obj = s_ipath.dataobject
    assert _calc_checksum(testdata / "more_data" / "polarbear.txt")== \
        (obj.checksum if len(obj.checksum)>0 else obj.chksum()), \
            "Checksums not identical after upload"

    # download
    sync(session=session,
        source=ipath,
        target=tmpdir,
        max_level=None,
        dry_run=False,
        copy_empty_folders=True)

    for cur_file in list(testdata.glob("*")):
        if cur_file.is_file():
            assert (tmpdir / cur_file.name).exists(), "File not downloaded"
            assert _calc_checksum(tmpdir / cur_file.name)== \
                _calc_checksum(testdata / cur_file.name), "Checksums not identical after download"
        elif cur_file.is_dir():
            assert (tmpdir / cur_file.name).exists(), "Subfolder not downloaded"

    assert (tmpdir / "more_data" / "polarbear.txt").exists(), "File in subfolder not downloaded"
    assert _calc_checksum(tmpdir / "more_data" / "polarbear.txt")== \
        _calc_checksum(testdata  / "more_data" / "polarbear.txt"), \
            "Checksums not identical after download"
