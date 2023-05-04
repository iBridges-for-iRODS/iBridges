"""IrodsConnector for iCommands
"""
import logging
import os
import platform
import shutil
import subprocess
from subprocess import Popen, PIPE
from typing import Union, Tuple, List
from pathlib import Path
from irods.collection import iRODSCollection, iRODSDataObject
from utils.sync_result import SyncResult
import irodsConnector.keywords as kw
from irodsConnector.resource import Resource
from irodsConnector.session import Session


class IrodsConnectorIcommands:
    """Connection to an iRODS server while using iCommands.
    """

    base_command_irsync = 'irsync {flags} {source} {target} {arguments}'
    irods_environment_file_key = 'IRODS_ENVIRONMENT_FILE'

    def __init__(self, res_man: Resource, ses_man: Session) -> None:
        """ iRODS icommands initialization
            Parameters
            ----------
            res_man : irods resource
                Instance of the Resource class
            ses_man : irods session
                instance of the Session class
        """
        self._res_man = res_man
        self._ses_man = ses_man

        # icommands can be made to use a different env file than the default
        # by setting the environment var IRODS_ENVIRONMENT_FILE
        # the var's original value is reset in the destructor
        self.prev_irods_environment_file = os.getenv(self.irods_environment_file_key)

        if str(self._ses_man.context.irods_env_file) != self.prev_irods_environment_file:
            os.environ[self.irods_environment_file_key] = str(self._ses_man.context.irods_env_file)

    def __del__(self) -> None:
        """
        Reset original value of IRODS_ENVIRONMENT_FILE
        """
        if self.prev_irods_environment_file is None:
            del os.environ[self.irods_environment_file_key]
        else:
            os.environ[self.irods_environment_file_key] = self.prev_irods_environment_file

    @property
    def has_icommands(self) -> bool:
        """
        Availability of icommands.
        Starts with OS check as icommands available for Linux only.
        Returns:
            bool
        """
        return 'linux' in platform.platform().lower() and \
            len(subprocess.check_output(['which', 'iinit']))>0

    @staticmethod
    def _execute_command(cmd: str) -> Tuple[str, str]:
        """
        Executes external process
        Returns:
            output: str
            error:  str
        """
        logging.debug(cmd)

        with Popen([cmd], stdout=PIPE, stdin=PIPE, stderr=PIPE, shell=True) as proc:
            output, error = proc.communicate()

        return output.decode('utf-8'), error.decode('utf-8')

    @staticmethod
    def _parse_output(output) -> List[Tuple[str, int]]:
        """
        Parses screen output of dry run irsync command
        Returns:
            List of filepath, bytesize tuples
        """
        def parse_line(line):
            """"
            raw line format (path, bytes, N):
            /path/to/file.txt   1000   N
            """
            line = line[:line.strip().rfind(" ")].strip()
            return (line[:line.rfind(" ")].strip(), int(line[line.rfind(" "):].strip()))

        lines: List[str] = list(filter(None, output.splitlines(False)))
        header = [x for x in lines if x.find("Running") == 0]
        files = list(set(lines) ^ set(header))
        return list(map(parse_line, files))

    def _resolve_irods_path(self, path: Union[iRODSDataObject, iRODSCollection,
                                              str]) -> Union[iRODSDataObject, iRODSCollection]:
        if isinstance(path, str):
            if self._ses_man.session.collections.exists(path):
                return self._ses_man.session.collections.get(path)
            if self._ses_man.session.data_objects.exists(path):
                return self._ses_man.session.data_objects.get(path)
            raise ValueError(f"iRODSCollection or iRODSDataObject '{path}' does not exist")

        return path

    def upload_data(self,                               # pylint: disable=too-many-arguments
                    source: Union[Path, str],
                    destination: iRODSCollection,
                    res_name: str,
                    size: int,
                    buff: int = kw.BUFF_SIZE,
                    force: bool = False) -> None:
        """Upload files or folders to an iRODS collection.
        Parameters
        ----------
        source: str
            absolute path to file or folder
        destination: iRODS collection to upload to
        res_name: str
            name of the iRODS storage resource to use
        size: int
            size of data to be uploaded in bytes
        buf: int
            buffer on resource that should be left over
        force: bool
            upload without checking the available space
        """

        if not force:
            if buff < 0:
                raise BufferError('icommands upload: Negative resource buffer.')
            if int(size) > (int(self._res_man.resource_space(self._ses_man, res_name)) - buff):
                raise ValueError('icommands upload: Not enough space on resource.')

        if isinstance(source, Path):
            source = source.as_posix()

        if os.path.isfile(source):
            self._ses_man.session.collections.create(destination.path)
            dest = destination.path
            flags = '-K'
        elif os.path.isdir(source):
            self._ses_man.session.collections.create(f"{destination.path}/{os.path.basename(source)}")
            dest = self._ses_man.session.collections.get(f"{destination.path}/{os.path.basename(source)}").path
            flags = '-Kr'
        else:
            raise FileNotFoundError('icommands upload: not a valid source path')

        cmd = self.base_command_irsync.format(flags=flags,
                                              source=source,
                                              target=f"i:{dest}",
                                              arguments=f"-R {res_name}")
        _, err = self._execute_command(cmd)
        if err:
            raise ValueError(err)

    def download_data(self,                                             # pylint: disable=too-many-arguments
                      source: Union[iRODSDataObject, iRODSCollection],
                      destination: Union[Path, str],
                      size: int,
                      buff: int = kw.BUFF_SIZE,
                      force: bool = False) -> None:
        """Download object or collection.
        Parameters
        ----------
        source: iRODS collection or data object
        destination: str
            absolut path to download folder
        size: int
            size of data to be downloaded in bytes
        buff: int
            buffer on the filesystem that should be left over
        """
        if not isinstance(destination, Path):
            destination = Path(destination)

        if not os.access(destination, os.W_OK):
            raise PermissionError('icommands download: No rights to write to destination.')

        if not os.path.isdir(destination):
            raise IsADirectoryError('icommands download: Destination is not a directory.')

        if not force:
            if buff < 0:
                raise BufferError('icommands download: Negative disk buffer.')
            if int(size) > (int(shutil.disk_usage(destination).free) - buff):
                raise ValueError('icommands download: Not enough space on disk.')

        flags = '-K' if isinstance(source, iRODSDataObject) else '-Kr'
        dest = (destination / os.path.basename(source.path)).as_posix()
        cmd = f"irsync {flags} i:{source.path} {dest}"
        _, err = self._execute_command(cmd)
        if err:
            raise ValueError(err)

    def get_diff_upload(self,
                        source: Union[str, Path],
                        target: Union[iRODSDataObject, iRODSCollection, str],
                        arguments: str = None) -> list[SyncResult]:
        """
        Performs upload dry run, captures and parses output.
        Returns:
            List of SyncResult-objects, each containing remote and local path, and size.
        """
        if not isinstance(source, Path):
            source = Path(source)

        if not source.exists():
            raise ValueError(f"Source {source.as_posix()} does not exist.")

        if source.is_dir():
            flags = '-Klr'
        elif source.is_file():
            flags = '-Kl'
        else:
            raise ValueError("Requires file or folder as source")

        target = self._resolve_irods_path(target)
        cmd = self.base_command_irsync.format(source=source,
                                       target=f"i:{target.path}",
                                       flags=flags,
                                       arguments=arguments if arguments else '')
        output, err = self._execute_command(cmd)
        if err:
            raise ValueError(err)

        out = []
        for file in self._parse_output(output):
            t_target = file[0].replace(f"{source.as_posix()}/", target.path)
            out.append(SyncResult(source=file[0], target=t_target, filesize=file[1]))

        return out

    def get_diff_download(self,
                          source: Union[iRODSDataObject, iRODSCollection, str],
                          target: Union[str, Path],
                          arguments: str = None) -> list[SyncResult]:
        """
        Performs download dry run, captures and parses output.
        Returns:
            List of SyncResult-objects, each containing remote and local path, and size.
        """
        source = self._resolve_irods_path(source)
        if isinstance(source, iRODSCollection):
            flags = '-Klr'
        elif isinstance(source, iRODSDataObject):
            flags = '-Kl'
        else:
            raise ValueError("Require iRODSCollection or iRODSDataObject as source")

        if not isinstance(target, Path):
            target = Path(target)

        if not target.exists():
            raise ValueError(f"Target {target.as_posix()} does not exist.")

        cmd = self.base_command_irsync.format(source=f"i:{source.path}",
                                      target=target.as_posix(),
                                      flags=flags,
                                      arguments=arguments if arguments else '')
        output, err = self._execute_command(cmd)
        if err:
            raise ValueError(err)

        out = []
        for file in self._parse_output(output):
            f_target = file[0].replace(str(source), f"{target.as_posix()}/")
            out.append(SyncResult(source=file[0], target=f_target, filesize=file[1]))

        return out

    def get_diff_both(self,
                      local: Union[str, Path],
                      remote: Union[iRODSDataObject, iRODSCollection],
                      arguments: str = None) -> dict:
        """
        Wraps get_diff_upload and get_diff_download.
        Returns:
            Dict with two lists.
        """
        return {
            'diff_download': self.get_diff_download(source=remote,
                                                    target=local,
                                                    arguments=arguments),
            'diff_upload': self.get_diff_upload(source=local,
                                                target=remote,
                                                arguments=arguments)}
