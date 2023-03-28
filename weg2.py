#!/usr/bin/env python3

"""
Commandline client to upload data to a storage service and double-link the storage location with a metadata store.

Implemented for:
    Storage types:
        iRODS
    Metadata stores:
        Elabjournal
"""
import argparse
import logging
import configparser
import os
import sys
import json
import getpass
from pathlib import Path
from irods.exception import ResourceDoesNotExist
import irodsConnector.keywords as kw
from irodsConnector.manager import IrodsConnector
from utils.elabConnector import elabConnector
from utils.utils import setup_logger, get_local_size


class Hooks:

    def __init__(self) -> None:
        self.hooks = {}

    def register_hook(self, hook, function):        
        self.hooks[hook] = function

    def call_hook(self, calling_class, hook, **kwargs):
        if not hook in self.hooks:
            raise ValueError(f"unknown hook: {hook}")
        self.hooks[hook](calling_class=calling_class, **kwargs)

class iBridgesCli():                          # pylint: disable=too-many-instance-attributes
    """
    Class for up- and downloading to YODA/iRODS via the command line.
    """
    def __init__(self,                      # pylint: disable=too-many-arguments
                 config_file: str,
                 local_path: str,
                 irods_path: str,
                 irods_env: str,
                 irods_resc: str,
                 operation: str,
                 logdir: str,
                 hooks: dict = None) -> None:

        if hooks:
            self.hooks = hooks

        self.irods_env = None
        self.irods_path = None
        self.irods_resc = None
        self.local_path = None
        self.config_file = None

        # reading optional config file
        if config_file:
            if not os.path.exists(config_file):
                self._clean_exit(f"{config_file} does not exist")

            self.config_file = os.path.expanduser(config_file)
            if not self.get_config('iRODS'):
                self._clean_exit(f"{config_file} misses iRODS section")

        # CLI parameters override config-file
        self.irods_env = irods_env or self.get_config('iRODS', 'irodsenv') \
                         or self._clean_exit("need iRODS environment file", True)
        self.irods_path = irods_path or self.get_config('iRODS', 'irodscoll') \
                          or self._clean_exit("need iRODS path", True)
        self.local_path = local_path or self.get_config('LOCAL', 'path') \
                          or self._clean_exit("need local path", True)

        self.irods_env = Path(os.path.expanduser(self.irods_env))
        self.local_path = Path(os.path.expanduser(self.local_path))
        self.irods_path = self.irods_path.rstrip("/")
        logdir = Path(logdir)

        # checking if paths actually exist
        for path in [self.irods_env, self.local_path, logdir]:
            if not path.exists():
                self._clean_exit(f"{path} does not exist")

        # reading default irods_resc from env file if not specified otherwise
        self.irods_resc = irods_resc or self.get_config('iRODS', 'irodsresc') or None
        if not self.irods_resc:
            with open(self.irods_env,'r',encoding='utf-8') as file:
                cfg = json.load(file)
                if 'default_resource_name' in cfg:
                    self.irods_resc = cfg['default_resource_name']

        if not self.irods_resc:
            self._clean_exit("need an iRODS resource", True)

        self.operation = operation
        setup_logger(logdir, "iBridgesCli")
        # self.run()

    def hook(func):
        
        def wrapper(self, **kwargs):
            print(func.__name__)
            print("Something is happening before the function is called.")
            func(self, **kwargs)
            print("Something is happening after the function is called.")
        return wrapper

    def _clean_exit(self, message=None, show_help=False, exit_code=1):
        if message:
            print_message(message) if exit_code==0 else print_error(message)
        if show_help:
            iBridgesCli.parser.print_help()
        if self.irods_conn and self.irods_conn.session:
            self.irods_conn.cleanup()
        sys.exit(exit_code)

    def get_config(self, section: str, option: str=None):
        """
        Reads config file.
        """
        if not self.config_file:
            return False

        config = configparser.ConfigParser()
        with open(self.config_file, encoding='utf-8') as file:
            config.read_file(file)

            if section not in config.sections():
                return False

            if not option:
                return dict(config.items(section))

            if option in [x[0] for x in config.items(section)]:
                return config.get(section, option)

        return False

    @classmethod
    def from_arguments(cls):
        cls.parser = argparse.ArgumentParser(
            prog='python iBridgesCli.py',
            description="",
            epilog=""
            )

        default_logdir = os.path.join(str(os.getenv('HOME')), '.irods')
        default_irods_env = os.path.join(str(os.getenv('HOME')), '.irods', 'irods_environment.json')

        cls.parser.add_argument('--config', '-c',
                            type=str,
                            help='Config file')
        cls.parser.add_argument('--local_path', '-l',
                            help='Local path to download to, or upload from',
                            type=str)
        cls.parser.add_argument('--irods_path', '-i',
                            help='iRods path to upload to, or download from',
                            type=str)
        cls.parser.add_argument('--operation', '-o',
                            type=str,
                            choices=['upload', 'download'],
                            required=True)
        cls.parser.add_argument('--env', '-e', type=str,
                            help=f'iRods environment file. (example: {default_irods_env})')
        cls.parser.add_argument('--irods_resc', '-r', type=str,
                            help='iRods resource. If omitted default will be read from iRods env file.')
        cls.parser.add_argument('--logdir', type=str,
                            help=f'Directory for logfile. Default: {default_logdir}',
                            default=default_logdir)

        args = cls.parser.parse_args()

        return cls(config_file=args.config,
                   irods_env=args.env,
                   irods_resc=args.irods_resc,
                   local_path=args.local_path,
                   irods_path=args.irods_path,
                   operation=args.operation,
                   logdir=args.logdir
                   )

    @classmethod
    def connect_irods(cls, irods_env):
        attempts = 0
        while True:
            secret = getpass.getpass(f'Password for {irods_env} (leave empty to use cached): ')
            try:
                irods_conn = IrodsConnector(irods_env, secret)
                _ = irods_conn.session
                break
            except Exception as exception:
                # print_error(f"AUTHENTICATION failed. {repr(exception)}")
                print_error(f"Failed to connect")
                attempts += 1
                if attempts >= 3 or input('Try again (Y/n): ').lower() == 'n':
                    return False

        return irods_conn

    def download(self, irods_conn, source, target_folder):
        # checks if remote object exists and if it's an object or a collection
        if irods_conn.collection_exists(source):
            item = irods_conn.get_collection(source)
        elif irods_conn.dataobject_exists(source):
            item = irods_conn.get_dataobject(source)
        else:
            print_error(f'iRODS path {source} does not exist')
            return False

        # get its size to check if there's enough space
        download_size = irods_conn.get_irods_size([source])
        print_message(f"Downloading '{source}' (approx. {round(download_size * kw.MULTIPLIER, 2)}GB)")

        # download
        irods_conn.download_data(src_obj=item, dst_path=target_folder, size=download_size, force=False)

        print_success('Download complete')
        return True

    @hook
    def upload(self, irods_conn, irods_resc, source, target_path):

        # check if intended upload target exists
        try:
            irods_conn.ensure_coll(target_path)
            print_warning(f"Uploading to {target_path}")
        except Exception:
            print_error(f"Collection path invalid: {target_path}")
            return False

        # check if there's enough space left on the resource
        upload_size = get_local_size([source])

        # TODO: does irods_conn.get_free_space() work yet?
        # free_space = int(irods_conn.get_free_space(resc_name=irods_resc))
        free_space = None
        if free_space is not None and free_space-1000**3 < upload_size:
            print_error('Not enough space left on iRODS resource to upload.')
            return False

        irods_conn.upload_data(
            source=source,
            destination=irods_conn.get_collection(target_path),
            res_name=irods_resc,
            size=upload_size,
            force=True)
        
        return True

    def run(self):

        self.irods_conn = self.connect_irods(irods_env=self.irods_env)

        if not self.irods_conn or not self.irods_conn.session:
            self._clean_exit("Connection failed")

        if self.operation == 'download':

            # self.hooks.call_hook(hook='pre_download', calling_class=self)

            if not self.download(irods_conn=self.irods_conn, source=self.irods_path, target_folder=self.local_path):
                self._clean_exit()

            # self.hooks.call_hook(hook='post_download', calling_class=self)

        elif self.operation == 'upload':

            # check if specified iRODS resource exists
            try:
                _ = self.irods_conn.session.resources.get(self.irods_resc)
            except AttributeError:
                self._clean_exit(f"iRODS resource '{self.irods_resc}' not found")

            self.target_path = self.irods_path

            # self.hooks.call_hook(hook='pre_upload', calling_class=self)

            if not self.upload(irods_conn=self.irods_conn,
                               irods_resc=self.irods_resc,
                               source=self.local_path,
                               target_path=self.target_path):
                self._clean_exit()

            # self.hooks.call_hook(hook='post_upload', calling_class=self)

        else:
            print_error(f'Unknown operation: {self.operation}')

        self._clean_exit(message="Done", exit_code=0)

if __name__ == "__main__":

    elab = ElabConnector()

    hooks = Hooks()
    hooks.register_hook(hook='pre_upload', function=elab.setup_elab)
    hooks.register_hook(hook='post_upload', function=elab.annotate_elab)

    # cli = iBridgesCli.from_arguments()
    # # or
    # # cli = iBridgesCli(input_csv='/data/ibridges/test.csv', transfer_config='...', output_folder='...')
    cli.run()
