"""Operations to be performed for upload/download/sync."""
from __future__ import annotations

import warnings
from inspect import signature
from pathlib import Path
from typing import Any, Optional, Union

import irods.collection
import irods.data_object
import irods.exception
import irods.keywords as kw
from irods.exception import CollectionDoesNotExist
from tqdm import tqdm
from tqdm.std import tqdm as tqdm_type

from ibridges.exception import FileTransferFailedError, ObjectTransferFailedError
from ibridges.path import IrodsPath
from ibridges.session import Session

NUM_THREADS = 4
NUM_TRANSFER_RESET = 3000


class Operations():  # pylint: disable=too-many-instance-attributes
    """Storage for all data and metadata operations.

    This class should generally not be used directly by the user to create and execute
    the data and metadata operations. Instead, the user should use the upload/download/sync
    operations from the :mod:`ibridges.data_operations` module. The return value of these functions
    is an Operations instance. This can be useful in the case of a dry-run, since the user can
    print the to be performed operations with :meth:`print_summary` and execute them if
    necessary with :meth:`execute`.

    Examples
    --------
    >>> ops = upload(session, "some_directory", ipath, dry_run=True)
    >>> ops.print_summary()  # Check what which basic operations will be performed.
    >>> ops.execute(session)  # Execute the upload operation.

    """

    def __init__(self, resc_name: Optional[str] = None, options: Optional[dict] = None):
        """Initialize and empty Operations object.

        The operations should be added separately, which is usually done by higher
        level functions.

        Parameters
        ----------
        resc_name:
            Name of the resource to perform the operations on.
        options:
            Options to transfer data with.

        """
        self.create_dir: set[str] = set()
        self.create_collection: set[str] = set()
        self.upload: list[tuple[Path, IrodsPath]] = []
        self.download: list[tuple[IrodsPath, Path]] = []
        self.meta_download: list[dict[str, Any]] = []
        self.meta_upload: list[tuple[IrodsPath, Union[str, Path, dict]]] = []
        self.resc_name: str = "" if resc_name is None else resc_name
        self.options: Optional[dict] = {} if resc_name is None else options
        self.download_unchanged = 0
        self.upload_unchanged = 0

    def add_meta_download(self, root_ipath: IrodsPath, meta_fp: Union[str, Path]):
        """Add operation for downloading metadata archives.

        This basic operation adds one IrodsPath point to either a collection or data object for
        metadata archiving.

        Parameters
        ----------
        root_ipath
            Root irods path to which all paths are relative to.
        ipath
            Irods path for which the metadata needs to be downloaded.
        meta_fp
            File to store the metadata in.

        """
        self.meta_download.append({"root_ipath": root_ipath, "meta_fp": meta_fp})

    def add_meta_upload(self, root_ipath: IrodsPath, meta_fp: Union[str, Path, dict]):
        """Add operation to use a metadata archive.

        This basic operation adds one metadata archive to be applied to a collection
        and its subcollections and data objects. It assumes that the data tree structure
        is the same for the metadata archive as for the destination iRODS path. If this is not the
        case, you will get errors during the execution of the operation.

        Parameters
        ----------
        root_ipath
            Root irods path to which all paths are relative to.
        meta_fp
            File that contains the metadata.

        """
        self.meta_upload.append((root_ipath, meta_fp))

    def add_download(self, ipath: IrodsPath, lpath: Path):
        """Add operation to download a data object.

        Parameters
        ----------
        ipath
            IrodsPath for the data object to download.
        lpath
            Local path for the data to be stored in.

        """
        self.download.append((ipath, lpath))

    def add_create_dir(self, new_dir: Path):
        """Add operation to create a new directory.

        Parameters
        ----------
        new_dir
            Directory to be created.

        """
        self.create_dir.add(str(new_dir))

    def add_upload(self, lpath: Path, ipath: IrodsPath):
        """Add operation to upload a data object.

        Parameters
        ----------
        lpath
            Local path for the file to be uploaded.
        ipath
            Destination IrodsPath for the data object to be created.

        """
        self.upload.append((lpath, ipath))

    def add_create_coll(self, new_col: IrodsPath):
        """Add operation to create a new collection.

        Parameters
        ----------
        new_col
            IrodsPath that points to the new collection to be created.

        """
        self.create_collection.add(str(new_col))

    def execute(self, session: Session, on_error: str = "fail",
                progress_bar: bool = True, print_summary: bool = True):
        """Execute all added operations.

        This also creates a progress bar to see the status updates.

        Parameters
        ----------
        session
            Session to perform the operations with.
        on_error, optional
            Decides what happens when an error occurs.
            There are three options: 'fail', 'warn' and 'skip'.
        progress_bar
            Whether to turn on the progress bar. The progress bar will be disabled
            if the total download + upload size is 0 regardless.
        print_summary:
            Whether to print a summary about how many files have been uploaded, downloaded,
            directories created, and more.

        """
        up_sizes = [lpath.stat().st_size for lpath, _ in self.upload]
        down_sizes = [ipath.size for ipath, _ in self.download]
        disable = len(up_sizes) + len(down_sizes) == 0 or not progress_bar
        pbar = tqdm(
            total=sum(up_sizes) + sum(down_sizes),
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
            disable=disable,
        )
        n_dir = self.execute_create_dir()
        n_coll = self.execute_create_coll(session)
        n_download = self.execute_download(session, pbar, on_error=on_error)
        n_upload = self.execute_upload(session, pbar, on_error=on_error)
        n_meta_down = self.execute_meta_download()
        n_meta_up = self.execute_meta_upload()

        download_error = len(self.download) - n_download
        upload_error = len(self.upload) - n_upload

        msg_dict = {
            "Downloaded": n_download,
            "Download errors": download_error,
            "Uploaded": n_upload,
            "Upload errors": upload_error,
            "Skipped unchanged": self.download_unchanged + self.upload_unchanged,
            "Directories created": n_dir,
            "Collections created": n_coll,
            "Metadata download": n_meta_down,
            "Metadata upload": n_meta_up,
        }
        messages = [f"{msg}: {count}" for msg, count in msg_dict.items() if count > 0]
        pbar.close()
        if print_summary:
            print(", ".join(messages))

    def execute_download(self, session: Session,
                         pbar: Optional[tqdm_type], on_error: str = "fail"):
        """Execute all download operations.

        Parameters
        ----------
        session
            Session to perform the downloads with.
        down_sizes
            Sizes of the data objects to be downloaded.
        pbar
            The progress bar to be updated.
        on_error, optional
            Decides what happens when an error occurs.
            There are three options: 'fail', 'warn' and 'skip'.

        """
        n_transfer = 0
        for ipath, lpath in self.download:
            if n_transfer % NUM_TRANSFER_RESET == NUM_TRANSFER_RESET-1:
                session.close()
                session.irods_session = session.connect()

            n_transfer += _obj_get(
                session,
                ipath,
                lpath,
                overwrite=True,
                on_error=on_error,
                options=self.options,
                resc_name=self.resc_name,
                pbar=pbar,
            )
        return n_transfer

    def execute_upload(self, session: Session,
                       pbar: Optional[tqdm_type], on_error: str = "fail"):
        """Execute all upload operations.

        Parameters
        ----------
        session
            Session to perform the downloads with.
        up_sizes
            Sizes of the files to be uploaded.
        pbar
            Progress bar to be updated while uploading.
        on_error, optional
            Decides what happens when an error occurs.
            There are three options: 'fail', 'warn' and 'skip'.

        """
        n_transfer = 0
        for lpath, ipath in self.upload:
            if n_transfer % NUM_TRANSFER_RESET == NUM_TRANSFER_RESET-1:
                session.close()
                session.irods_session = session.connect()

            n_transfer += _obj_put(
                session,
                lpath,
                ipath,
                overwrite=True,
                on_error=on_error,
                options=self.options,
                resc_name=self.resc_name,
                pbar=pbar,
            )
        return n_transfer

    def execute_meta_download(self):
        """Execute all metadata download operations."""
        for item in self.meta_download:
            root_ipath = item["root_ipath"]
            meta_fp = item["meta_fp"]
            root_ipath.create_meta_archive(meta_fp)
        return len(self.meta_download)

    def execute_meta_upload(self):
        """Execute all metadata upload operations.

        Parameters
        ----------
        session
            Session to use with uploading the operations.

        """
        n_ops = 0
        for root_ipath, meta_fp in self.meta_upload:
            n_ops += len(root_ipath.apply_meta_archive(meta_fp)["items"])
        return n_ops

    def execute_create_dir(self):
        """Execute all create directory operations.

        Raises
        ------
        PermissionError
            If the path to the directory already exists and is not a directory.

        """
        for curdir in self.create_dir:
            try:
                Path(curdir).mkdir(parents=True, exist_ok=True)
            except NotADirectoryError as error:
                raise PermissionError(f"Cannot create {error.filename}") from error
        return len(self.create_dir)

    def execute_create_coll(self, session: Session):
        """Execute all create collection operations.

        Parameters
        ----------
        session
            Session to create the collections with.

        """
        for col in self.create_collection:
            IrodsPath(session, col).create_collection()
        return len(self.create_collection)

    def print_summary(self):
        """Print a summary of all the operations added to the object."""
        summary_strings = []
        if len(self.create_collection) > 0:
            summary = "Create collections:\n\n"
            # for coll in self.create_collection:
            summary += "\n".join(self.create_collection)
            summary_strings.append(summary)

        if len(self.create_dir) > 0:
            summary = "Create directories:\n\n"
            # for cur_dir in self.create_dir:
            summary += "\n".join(self.create_dir)
            summary_strings.append(summary)

        if len(self.upload) > 0:
            summary = "Upload files:\n\n"
            for lpath, ipath in self.upload:
                summary += f"{lpath} -> {ipath}\n"
            summary_strings.append(summary)

        if len(self.download) > 0:
            summary = "Download files:\n\n"
            for ipath, lpath in self.download:
                summary += f"{ipath} -> {lpath}\n"
            summary_strings.append(summary)

        if len(self.meta_download) > 0:
            summary = "Metadata to download:\n\n"
            for meta_item in self.meta_download:
                summary += f"{meta_item['meta_fp']} -> {meta_item['root_ipath']}\n"
            summary_strings.append(summary)

        if len(self.meta_upload) > 0:
            summary = "Metadata to upload:\n\n"
            for (ipath, meta_fp) in self.meta_upload:
                summary += f"{meta_fp} -> {ipath}\n"
            summary_strings.append(summary)
        print("\n\n".join(summary_strings))


def _warn_ignored_keywords(options: Optional[dict]):
    if options is None:
        return

    all_ignored_set = set((kw.FORCE_FLAG_KW, kw.RESC_NAME_KW, kw.NUM_THREADS_KW, kw.REG_CHKSUM_KW,
                           kw.VERIFY_CHKSUM_KW))
    cur_ignored_set = set(options).intersection(all_ignored_set)
    if len(cur_ignored_set) > 0:
        warnings.warn(f"Some options will be ignored: {cur_ignored_set}", UserWarning)


def _raise_transfer_errors(on_error: str,
                           msg: str,
                           throw_error,
                           error: Optional[Exception] = None):
    if on_error == "fail":
        if error:
            raise throw_error(msg) from error
        raise throw_error(msg)
    if on_error == "warn":
        warnings.warn(msg)


def _obj_put(  # pylint: disable=too-many-branches
    session: Session,
    local_path: Union[str, Path],
    irods_path: Union[str, IrodsPath],
    overwrite: bool = False,
    resc_name: str = "",
    options: Optional[dict] = None,
    on_error: str = "fail",
    pbar: Optional[tqdm_type] = None,
) -> int:
    """Upload `local_path` to `irods_path` following iRODS `options`.

    Parameters
    ----------
    session :
        Session to upload the object.
    local_path : str or Path
        Path of local file.
    irods_path : str or IrodsPath
        Path of iRODS data object or collection.
    resc_name : str
        Optional resource name.
    overwrite :
        Whether to overwrite the object if it exists.
    options :
        Extra options to the python irodsclient put method.
    on_error:
        'fail': fail with an exception; 'warn': turn error into warning and continue;
        'skip': simply continue.
    pbar:
        Optional progress bar.

    """
    transfers = 0

    if on_error and on_error.lower() not in ['fail', 'warn', 'skip']:
        raise ValueError(f"'on_error' {on_error} not a valid value. Choose fail, warn or skip.")

    local_path = Path(local_path)
    irods_path = IrodsPath(session, irods_path)

    if not local_path.is_file():
        err_msg = f"local_path '{local_path}' must be a file."
        _raise_transfer_errors(on_error, err_msg, ValueError)
        return 0

    # Check if irods object already exists
    obj_exists = (
        IrodsPath(session, irods_path / local_path.name).dataobject_exists()
        or irods_path.dataobject_exists()
    )

    _warn_ignored_keywords(options)

    if options is None:
        options = {}
    options.update({kw.NUM_THREADS_KW: NUM_THREADS, kw.REG_CHKSUM_KW: "", kw.VERIFY_CHKSUM_KW: ""})

    if pbar is not None:
        upd_put = "updatables" in signature(session.irods_session.data_objects.put).parameters
        if upd_put:
            options["updatables"] = [pbar.update]

    if overwrite:
        options[kw.FORCE_FLAG_KW] = ""
    if resc_name not in ["", None]:
        options[kw.RESC_NAME_KW] = resc_name
    if overwrite or not obj_exists:
        try:
            session.irods_session.data_objects.put(local_path, str(irods_path), **options)
            transfers += 1
        except (PermissionError, OSError) as error:
            err_msg = f"Cannot read {error.filename}."
            _raise_transfer_errors(on_error, err_msg, error, error)
        except irods.exception.CAT_NO_ACCESS_PERMISSION as error:
            err_msg = f"Cannot write iRODS path {str(irods_path)}."
            _raise_transfer_errors(on_error, err_msg, PermissionError, error)
        except irods.exception.OVERWRITE_WITHOUT_FORCE_FLAG as error:
            # This should generally not occur, but a race condition might trigger this.
            # obj does not exist -> someone else writes to object -> overwrite error
            err_msg = (f"Dataset {irods_path} already exists. "
                       "Use overwrite=True to overwrite the existing file."
                       "This error might be the result of simultaneous writing "
                       "to the same data object.")
            _raise_transfer_errors(on_error, err_msg, FileExistsError, error)
        except Exception as error: # pylint: disable=W0718
            err_msg = f"Cannot transfer {local_path} to {irods_path}, {repr(error)}"
            _raise_transfer_errors(on_error, err_msg, FileTransferFailedError, error)
    else:
        err_msg = (f"Dataset {irods_path} already exists. "
                    "Use overwrite=True to overwrite the existing file.")
        _raise_transfer_errors(on_error, err_msg, FileExistsError)
    if pbar is not None and not upd_put:
        pbar.update(IrodsPath(session, irods_path).size)
    return transfers


def _obj_get(
    session: Session,
    irods_path: IrodsPath,
    local_path: Path,
    overwrite: bool = False,
    resc_name: Optional[str] = "",
    options: Optional[dict] = None,
    on_error: str = "fail",
    pbar: Optional[tqdm_type] = None,
 ) -> int:
    # pylint: disable=W0718,R0915,R0912
    """Download `irods_path` to `local_path` following iRODS `options`.

    Parameters
    ----------
    session :
        Session to get the object from.
    irods_path : str or IrodsPath
        Path of iRODS data object.
    local_path : str or Path
        Path of local file or directory/folder.
    overwrite :
        Whether to overwrite the local file if it exists.
    resc_name:
        Name of the resource to get the object from.
    options : dict
        Extra options to the python irodsclient get method.
    on_error:
        'fail': fail with an exception; 'warn': turn error into warning and continue
        'skip': simply continue.
    pbar:
        Optional progress bar.

    """
    if on_error and on_error.lower() not in ["fail", "warn", "skip"]:
        raise ValueError(f"'on_error' {on_error} not a valid value. Choose fail, warn or skip.")
    _warn_ignored_keywords(options)

    if options is None:
        options = {}
    options.update(
        {
            kw.NUM_THREADS_KW: NUM_THREADS,
            kw.VERIFY_CHKSUM_KW: "",
        }
    )
    if overwrite:
        options[kw.FORCE_FLAG_KW] = ""
    if resc_name not in ["", None]:
        options[kw.RESC_NAME_KW] = resc_name

    # Compatibility with PRC<2.1
    if pbar is not None:
        upd_put = "updatables" in signature(session.irods_session.data_objects.put).parameters
        if upd_put:
            options["updatables"] = [pbar.update]

    transfers = 0

    # Quick fix for #126
    if Path(local_path).is_dir():
        local_path = Path(local_path).joinpath(irods_path.name)

    try:
        session.irods_session.data_objects.get(str(irods_path), local_path, **options)
        transfers += 1
    except (OSError, irods.exception.CAT_NO_ACCESS_PERMISSION) as error:
        msg = f"Cannot write to {local_path}."
        _raise_transfer_errors(on_error, msg, PermissionError, error)
    except irods.exception.CUT_ACTION_PROCESSED_ERR as error:
        msg = f"During download operation from '{irods_path}': iRODS server forbids action."
        _raise_transfer_errors(on_error, msg, PermissionError, error)
    except irods.exception.CollectionDoesNotExist:
        msg = f"{irods_path} does not exist."
        exception = CollectionDoesNotExist(msg)
        _raise_transfer_errors(on_error, msg, ObjectTransferFailedError, exception)
    except Exception as error:
        msg = f"Cannot transfer {irods_path} to {local_path}, {repr(error)}"
        _raise_transfer_errors(on_error, msg, ObjectTransferFailedError, error)
    if pbar is not None and not upd_put:
        pbar.update(IrodsPath(session, irods_path).size)
    return transfers
