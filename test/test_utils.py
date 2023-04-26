"""Test iBridges utilities.

"""
import json
import os
import pathlib
import sys

import utils


class TestUtils:
    """

    """

    def test_is_posix(self):
        orig_platform = sys.platform
        sys.platform = 'win32'
        assert not utils.utils.is_posix()
        sys.platform = 'linux'
        assert utils.utils.is_posix()
        sys.platform = orig_platform

    def test_pure_path(self):
        path = utils.path.PurePath('.')
        assert isinstance(path.path, pathlib.PurePath)

    def test_irods_path(self):
        path = utils.path.IrodsPath('.')
        assert isinstance(path.path, pathlib.PurePath)
        not_norm = '/zone/./home/./user/../user'
        is_norm = '/zone/home/user'
        path = utils.path.IrodsPath(not_norm)
        norm_path = utils.path.IrodsPath(is_norm)
        assert path == norm_path

    def test_local_path(self):
        path = utils.path.LocalPath('.')
        assert isinstance(path.path, pathlib.Path)

    def test_json_config(self):
        filename = './config.json'
        if os.path.exists(filename):
            os.remove(filename)
        config = utils.json_config.JsonConfig(filename)
        test_config = {'test_key': 'test_val'}
        config.config = test_config
        config.save()
        assert os.path.exists(filename)
        with open(filename) as confd:
            assert json.load(confd) == test_config

    def test_ensure_dir(self):
        dirname = 'ensure.dir'
        assert not os.path.isdir(dirname)
        assert utils.utils.ensure_dir(dirname)
        assert os.path.isdir(dirname)
        assert utils.utils.ensure_dir(dirname)
        os.rmdir(dirname)

    def test_get_local_size(self):
        size = 1024
        dirname = 'size.dir'
        filename = 'size.file'
        os.mkdir(dirname)
        with open(os.path.join(dirname, filename), 'w') as sizefd:
            sizefd.seek(size - 1)
            sizefd.write('\0')
        assert utils.utils.get_local_size([dirname]) == size
        os.unlink(os.path.join(dirname, filename))
        os.rmdir(dirname)

    def test_get_data_size(self):
        pass

    def test_get_coll_size(self):
        pass

    def test_can_connect(self):
        pass

    def test_get_coll_dict(self):
        pass

    def test_get_downloads_dir(self):
        if sys.platform not in ['win32', 'cygwin']:
            downname = os.path.expanduser('~/Downloads')
            assert utils.utils.get_downloads_dir() == downname

    def test_save_irods_env(self):
        pass

    def test_get_working_dir(self):
        pass

    def test_dir_exists(self):
        dirname = os.path.abspath('.')
        assert utils.utils.dir_exists(dirname)

    def test_file_exists(self):
        filename = 'test.file'
        with open(filename, 'w'):
            pass
        assert utils.utils.file_exists(filename)
        os.unlink(filename)

    def test_setup_logger(self):
        pass

    def test_bytes_to_str(self):
        value = 2**30
        assert utils.utils.bytes_to_str(value) == '1.074 GB'
        value = 2**40
        assert utils.utils.bytes_to_str(value) == '1.100 TB'
