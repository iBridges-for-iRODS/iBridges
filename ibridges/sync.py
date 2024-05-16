"""Synchronize data between local and remote copies.

'sync' synchronizes the data between a local copy (local file system) and the copy stored in
iRODS. The command can be in one of the two modes: synchronization of data from the client's
local file system to iRODS, or from iRODS to the local file system. It broadly mirros the
behaviour of the irsync module of the icommands command line tool.
"""

from __future__ import annotations

import base64
import os
from hashlib import sha256
from pathlib import Path
from typing import NamedTuple, Optional, Union

from irods.collection import iRODSCollection
from tqdm import tqdm

from ibridges.data_operations import perform_operations
from ibridges.path import IrodsPath
from ibridges.session import Session
from ibridges.util import get_collection, get_dataobject


def sync_data(session: Session,
         source: Union[str, Path, IrodsPath],
         target: Union[str, Path, IrodsPath],
         max_level: Optional[int] = None,
         dry_run: bool = False,
         ignore_err: bool = False,
         copy_empty_folders: bool = False) -> dict:
    """Synchronize the data between a local copy (local file system) and the copy stored in iRODS.

    The command can be in one of the two modes: synchronization of data from the client's local file
    system to iRODS, or from iRODS to the local file system. The mode is determined by the type of
    the values for `source` and `target` (IrodsPath or str/Path).

    The command considers the file size and the checksum to determine whether a file should be
    synchronized.


    Parameters
    ----------
    session : ibridges.Session
        An authorized iBridges session.
    source : str or Path or IrodsPath
        Existing local folder or iRODS collection. An exception will be raised if it doesn't exist.
    target : str or Path or IrodsPath
        Existing local folder or iRODS collection. An exception will be raised if it doesn't exist.
    max_level : int, default None
        Controls the depth up to which the file tree will be synchronized. A max level of 1
        synchronizes only the source's root, max level 2 also includes the first set of
        subfolders/subcollections and their contents, etc. Set to None, there is no limit
        (full recursive synchronization).
    dry_run : bool, default False
        List all source files and folders that need to be synchronized without actually
        performing synchronization.
    ignore_err : If an error occurs during the transfer, and ignore_err is set to True,
        any errors encountered will be transformed into warnings and iBridges will continue
        to transfer the remaining files.
    copy_empty_folders : bool, default False
        Controls whether folders/collections that contain no files or  subfolders/subcollections
        will be synchronized.


    Returns
    -------
        A dict object containing two keys: 'changed_folders' and 'changed_files'.
        These contain lists of changed folders and files, respectively
        (or of to-be-changed folders and files, when in dry-run mode).

    """
    _param_checks(source, target)

    if isinstance(source, IrodsPath):
        if not source.collection_exists():
            raise ValueError(f"Source collection '{source.absolute_path()}' does not exist")
    else:
        if not Path(source).is_dir():
            raise ValueError(f"Source folder '{source}' does not exist")

    if isinstance(source, IrodsPath):
        ops = _down_sync_operations(session, source, target, copy_empty_folders=copy_empty_folders,
                                    depth=max_level)
    else:
        ops = _up_sync_operations(session, source, target, copy_empty_folders=copy_empty_folders,
                                    depth=max_level)

    if not dry_run:
        perform_operations(session, ops)
    return ops

def _param_checks(source, target):
    if not isinstance(source, IrodsPath) and not isinstance(target, IrodsPath):
        raise TypeError("Either source or target should be an iRODS path.")

    if isinstance(source, IrodsPath) and isinstance(target, IrodsPath):
        raise TypeError("iRODS to iRODS copying is not supported.")

def _calc_checksum(filepath):
    if isinstance(filepath, IrodsPath):
        dataobj = filepath.dataobject
        return dataobj.checksum if dataobj.checksum else dataobj.chksum()
    f_hash=sha256()
    memv=memoryview(bytearray(128*1024))
    with open(filepath, 'rb', buffering=0) as file:
        for item in iter(lambda : file.readinto(memv), 0):
            f_hash.update(memv[:item])
    return f"sha2:{str(base64.b64encode(f_hash.digest()), encoding='utf-8')}"

def _down_sync_operations(session, isource_path, ldest_path, copy_empty_folders=True, depth=None):
    operations = {
        "create_dir": set(),
        "create_collection": set(),
        "upload": [],
        "download": [],
    }
    for ipath in isource_path.walk(depth=depth):
        lpath = ldest_path.joinpath(*ipath.relative_to(isource_path)._parts)
        if ipath.dataobject_exists():
            if lpath.is_file():
                l_chksum = _calc_checksum(lpath)
                i_chksum = _calc_checksum(ipath)
                if i_chksum != l_chksum:
                    operations["download"].append((ipath, lpath))
            else:
                operations["download"].append((ipath, lpath))
            if not lpath.parent.exists():
                operations["create_dir"].add(str(lpath.parent))
        elif ipath.collection_exists() and copy_empty_folders:
            if not lpath.exists():
                operations["create_dir"].add(str(lpath))
    return operations

def _up_sync_operations(session, lsource_path, idest_path, copy_empty_folders=True, depth=None):
    operations = {
        "create_dir": set(),
        "create_collection": set(),
        "upload": [],
        "download": [],
    }
    for root, folders, files in os.walk(lsource_path):
        root_part = Path(root).relative_to(lsource_path)
        root_ipath = idest_path.joinpath(*root_part.parts)
        for cur_file in files:
            ipath = root_ipath / cur_file
            lpath = lsource_path / root_part / cur_file
            if ipath.dataobject_exists():
                l_chksum = _calc_checksum(lpath)
                i_chksum = _calc_checksum(ipath)
                if i_chksum != l_chksum:
                    operations["upload"].append((lpath, ipath))
            else:
                operations["upload"].append((lpath, ipath))
        for fold in folders:
            operations["create_collection"].add(str(root_ipath / fold))
        operations["create_collection"].add(str(root_ipath))
    return operations
