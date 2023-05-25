"""IrodsConnector for iCommands
"""
import logging
import os
import platform
import shutil
import subprocess
import re
from subprocess import Popen, PIPE
from typing import Union, Tuple, List
from pathlib import Path
from irods.collection import iRODSCollection, iRODSDataObject
from utils.sync_result import SyncResult
import irodsConnector.keywords as kw


class IrodsConnectorIcommands:
    """Connection to an iRODS server while using iCommands.
    """

    icmd_irsync = 'irsync {flags} {source} {target} {arguments}'
    icmd_free_space = 'iquest "SELECT RESC_FREE_SPACE where RESC_NAME = \'{resource}\'"'
    icmd_imkdir = 'imkdir -p {collection}'
    icmd_ils = 'ils {coll_or_object}'
    irods_environment_file_key = 'IRODS_ENVIRONMENT_FILE'

    def __init__(self) -> None:
        """ IrodsConnectorIcommands initialization
        """
        self.prev_irods_environment_file = None

    def __del__(self) -> None:
        """
        Reset original value of IRODS_ENVIRONMENT_FILE
        """
        if self.irods_environment_file_key in os.environ:
            if self.prev_irods_environment_file is None:
                del os.environ[self.irods_environment_file_key]
            else:
                os.environ[self.irods_environment_file_key] = self.prev_irods_environment_file

    def set_irods_env_file(self, irods_env_file: Union[Path, str]):
        """
        Set specific iRods env file
        """
        # icommands can be made to use a different env file than the default
        # by setting the environment var IRODS_ENVIRONMENT_FILE
        # the var's original value is reset in the destructor
        if isinstance(irods_env_file, Path):
            irods_env_file = irods_env_file.as_posix()

        if irods_env_file != os.getenv(self.irods_environment_file_key):
            self.prev_irods_environment_file = os.getenv(self.irods_environment_file_key)
            os.environ[self.irods_environment_file_key] = irods_env_file

    @property
    def has_icommands(self) -> bool:
        """
        Availability of icommands.
        Starts with OS check as icommands available for Linux only.
        Returns:
            bool
        """
        is_linux = 'linux' in platform.platform().lower()
        if is_linux:
            # Do not use check_output().  It raises an exception.
            return subprocess.call(['which', 'iinit']) == 0
        return False

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
    def _parse_diff_output(output) -> List[Tuple[str, int]]:
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

    @staticmethod
    def _extract_icommands_error(string):
        return re.sub(r'^(.*)failed with error', '',
                      list(filter(lambda x: 'failed with error' in x, string.splitlines()))[0]).strip()

    def resolve_irods_path(self, path: Union[iRODSDataObject, iRODSCollection,
                                             str]) -> Union[None, Tuple[str, Union[iRODSDataObject, iRODSCollection]]]:
        """
        Consumes a string or iRods object or collection and returns the correct type and its path as a string
        """
        if isinstance(path, iRODSDataObject):
            return Path(path.path).as_posix(), iRODSDataObject

        if isinstance(path, iRODSCollection):
            return Path(path.path).as_posix(), iRODSCollection

        if isinstance(path, str):
            path = Path(path)
        else:
            raise ValueError("Require string, iRODSDataObject, or iRODSCollection")

        parent = path.parent.absolute()

        output, error = self._execute_command(self.icmd_ils.format(coll_or_object=parent.as_posix()))

        if error:
            raise ValueError(self._extract_icommands_error(error))

        coll_flag = "C- "
        out_lines = output.splitlines()[1:]
        collections = [x.strip()[len(coll_flag):] for x in out_lines if x.strip()[:len(coll_flag)] == coll_flag]
        objects = [x.strip() for x in out_lines if x.strip()[:len(coll_flag)] != coll_flag]

        if path.as_posix() in collections:
            return path.as_posix(), iRODSCollection(None)

        if path.parts[-1:][0] in objects:
            return path.as_posix(), iRODSDataObject(None)

        return None

    def get_resource_free_space(self, res_name: str):
        """
        Queries and returns the available free space on an iRods resource.
        """
        cmd = self.icmd_free_space.format(resource=res_name)
        output, err = self._execute_command(cmd)
        if err:
            raise ValueError(err)

        key = "RESC_FREE_SPACE ="
        lines = list(filter(lambda a: key in a, output.splitlines(False)))

        if len(lines) == 1:
            n_bytes = lines[0].strip()[len(key):].strip()
            if len(n_bytes) > 1:
                return int(''.join(filter(str.isdigit, n_bytes)))

        return -1

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

            free_space = self.get_resource_free_space(res_name)
            if (free_space > -1) and (int(size) > (free_space - buff)):
                raise ValueError('icommands upload: Not enough space on resource.')

        if isinstance(source, Path):
            source = source.as_posix()

        if os.path.isfile(source):
            cmd = self.icmd_imkdir.format(collection=destination.path)
            _, err = self._execute_command(cmd)
            if err:
                raise ValueError(err)

            dest = destination.path
            flags = '-K'

        elif os.path.isdir(source):
            dest = f"{destination.path}/{os.path.basename(source)}"
            cmd = self.icmd_imkdir.format(collection=dest)
            _, err = self._execute_command(cmd)
            if err:
                raise ValueError(err)

            flags = '-Kr'

        else:
            raise FileNotFoundError('icommands upload: not a valid source path')

        cmd = self.icmd_irsync.format(flags=flags,
                                              source=source,
                                              target=f"i:{dest}",
                                              arguments=f"-R {res_name}")

        _, err = self._execute_command(cmd)
        if err:
            raise ValueError(err)

    def download_data(self,                             # pylint: disable=too-many-arguments
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

        target, _ = self.resolve_irods_path(target)
        cmd = self.icmd_irsync.format(source=source,
                                       target=f"i:{target}",
                                       flags=flags,
                                       arguments=arguments if arguments else '')
        output, err = self._execute_command(cmd)
        if err:
            raise ValueError(err)

        out = []
        for file in self._parse_diff_output(output):
            t_target = file[0].replace(f"{source.as_posix()}/", target)
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
        source, source_type = self.resolve_irods_path(source)

        if isinstance(source_type, iRODSCollection):
            flags = '-Klr'
        elif isinstance(source_type, iRODSDataObject):
            flags = '-Kl'
        else:
            raise ValueError(f"{source} is not a valid iRODSCollection or iRODSDataObject")

        if not isinstance(target, Path):
            target = Path(target)

        if not target.exists():
            raise ValueError(f"Target {target.as_posix()} does not exist.")

        cmd = self.icmd_irsync.format(source=f"i:{source}",
                                      target=target.as_posix(),
                                      flags=flags,
                                      arguments=arguments if arguments else '')
        output, err = self._execute_command(cmd)
        if err:
            raise ValueError(err)

        out = []
        for file in self._parse_diff_output(output):
            f_target = file[0].replace(str(source), f"{target.as_posix()}/")
            out.append(SyncResult(source=file[0], target=f_target, filesize=file[1]))

        return out

    def get_diff_both(self,
                      local: Union[str, Path],
                      remote: Union[str, iRODSDataObject, iRODSCollection],
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
