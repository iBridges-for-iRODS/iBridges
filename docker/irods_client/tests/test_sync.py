from ibridges.data_operations import create_collection
from ibridges.path import IrodsPath
from ibridges.sync import _calc_checksum, sync_data


def test_sync_dry_run(session, testdata, capsys):

    ipath = IrodsPath(session, "~", "empty")
    coll = create_collection(session=session, coll_path=ipath)

    # upload
    ops = sync_data(session=session,
                    source=testdata,
                    target=ipath,
                    max_level=None,
                    dry_run=True,
                    copy_empty_folders=True)

    assert len(ops["create_collection"]) == 0
    assert len(ops["create_dir"]) == 0
    assert len(ops["download"]) == 0
    assert len(ops["upload"]) == 7

    # captured = capsys.readouterr()
    # lines=sorted([x.strip() for x in captured.out.split("\n") if len(x.strip())>0])

    # assert lines == ['/tempZone/home/rods/empty/more_data',
    #     'Will create collection(s):',
    #     "Will upload from '/tmp/testdata' to '/tempZone/home/rods/empty':",
    #     'beach.rtf  727',
    #     'bunny.rtf  10150',
    #     'example.r  182',
    #     'more_data/polarbear.txt  2717',
    #     'plant.rtf  992',
    #     'plant.rtf.copy  992',
    #     'sun.rtf  661']

    assert len(coll.data_objects)+len(coll.subcollections)==0, "Dry run did sync"

def test_sync_upload_download(session, testdata, tmpdir):
    ipath = IrodsPath(session, "~", "empty")
    coll = create_collection(session=session, coll_path=ipath)

    assert len(coll.data_objects)+len(coll.subcollections)==0, "iRODS folder not empty"

    # upload
    sync_data(session=session,
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
    sync_data(session=session,
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
