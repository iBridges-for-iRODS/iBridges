"""Data transfer dialog.

"""
import datetime
import logging
import os
import sys

from PyQt6.QtWidgets import QDialog
from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6 import QtCore
from PyQt6.QtGui import QMovie
from PyQt6.uic import loadUi

from gui.ui_files.dataTransferState import Ui_dataTransferState
import utils


class dataTransfer(QDialog, Ui_dataTransferState, utils.context.ContextContainer):
    """

    """
    finished = pyqtSignal(bool, object)

    def __init__(self, upload, localFsPath, irodsColl, irodsTreeIdx=None, resource=None):
        """

        Parameters
        ----------
        upload
        localFsPath
        irodsColl
        irodsTreeIdx
        resource
        """
        super().__init__()
        if getattr(sys, 'frozen', False):
            super().setupUi(self)
        else:
            loadUi("gui/ui_files/dataTransferState.ui", self)
        self.setWindowFlags(QtCore.Qt.WindowType.WindowStaysOnTopHint)
        self.localFsPath = localFsPath
        self.coll = irodsColl
        self.TreeInd = irodsTreeIdx
        self.upload = upload
        self.resource = resource
        self.addFiles = []
        self.addSize = 0
        self.diff = []
        self.updateFiles = []
        self.updateSize = 0
        self.force = self.conf.get('force_transfers', False)
        self.statusLbl.setText("Loading")
        self.cancelBtn.clicked.connect(self.cancel)
        self.confirmBtn.clicked.connect(self.confirm)
        # Upload
        if self.upload:
            self.confirmBtn.setText("Upload")
        else:
            self.confirmBtn.setText("Download")
        self.confirmBtn.setEnabled(False)

        self.loading_movie = QMovie("gui/icons/loading_circle.gif")
        self.loadingLbl.setMovie(self.loading_movie)
        self.loading_movie.start()

        # Get information in separate thread
        self.thread = QThread()
        self.worker = getDataState(localFsPath, irodsColl, upload)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.updLabels.connect(self.updLabels)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.updateUiWithDataState)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()
        self.show()

    def cancel(self):
        logging.debug('Thread stopped')
        self.finished.emit(False, None)
        # if thread is still running
        try:
            self.thread.exit(1)
        except:
            pass
        self.close()

    def closeAfterUpDownl(self):
        self.finished.emit(True, self.TreeInd)
        self.close()

    def confirm(self):
        total_size = self.updateSize + self.addSize
        self.loading_movie.start()
        self.loadingLbl.setHidden(False)
        self.confirmBtn.setEnabled(False)
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        if self.upload:
            self.statusLbl.setText(
                f'Uploading... this might take a while. \nStarted {now}')
        else:
            self.statusLbl.setText(
                f'Downloading... this might take a while. \nStarted {now}')
        self.thread = QThread()
        if len(self.diff)+len(self.addFiles) == 0:
            self.statusLbl.setText("Nothing to update.")
            self.loading_movie.stop()
            self.loadingLbl.setHidden(True)
        else:
            self.worker = UpDownload(
                self.upload, self.localFsPath, self.coll, total_size,
                self.resource, self.diff, self.addFiles, self.force)
            self.worker.moveToThread(self.thread)
            self.thread.started.connect(self.worker.run)
            self.worker.finished.connect(self.thread.quit)
            self.worker.finished.connect(self.upDownLoadFinished)
            self.worker.finished.connect(self.worker.deleteLater)
            self.thread.finished.connect(self.thread.deleteLater)
            self.thread.start()

    def updLabels(self, numAdd, numDiff):
        """Callback for the getDataSize worker

        Parameters
        ----------
        numAdd
        numDiff

        """
        self.numDiffLabel.setText(f"{numDiff}")
        self.numAddLabel.setText(f"{numAdd}")

    def updateUiWithDataState(self, addFiles, diff, addSize, updateSize):
        """Callback for the getDataSize worker

        Parameters
        ----------
        addFiles
        diff
        addSize
        updateSize

        Returns
        -------

        """
        # TODO fix handling of updateSize and addSize as ints
        self.updateSize = updateSize
        logging.debug('%s %s', addSize, updateSize)
        # checksumSizeStr = self.bytesToStr(updateSize)
        self.ChecksumSizeLbl.setText(utils.utils.bytes_to_str(int(updateSize)))
        self.diff = diff

        self.addSize = addSize
        # newSizeStr = self.bytesToStr(addSize)
        self.newFSizeLbl.setText(utils.utils.bytes_to_str(int(addSize)))
        self.addFiles = addFiles

        self.loading_movie.stop()
        self.loadingLbl.setHidden(True)
        self.statusLbl.setText("")
        self.confirmBtn.setEnabled(True)

    def upDownLoadFinished(self, status, statusmessage):
        """

        Parameters
        ----------
        status
        statusmessage

        Returns
        -------

        """
        self.loading_movie.stop()
        self.loadingLbl.setHidden(True)
        if status:
            # remove callback
            self.confirmBtn.disconnect()
            self.confirmBtn.setText("Close")
            self.confirmBtn.setEnabled(True)
            self.confirmBtn.clicked.connect(self.closeAfterUpDownl)
            self.statusLbl.setText("Update complete.")
        else:
            self.statusLbl.setText(statusmessage)
            logging.debug(statusmessage)
            self.confirmBtn.setText("Retry")
            self.confirmBtn.setEnabled(True)
            if "No size set on iRODS resource" in statusmessage:
                self.force = True
                self.confirmBtn.setText("Retry and force upload?")


class getDataState(QObject, utils.context.ContextContainer):
    """Background worker to load the menu.

    """
    # Number of files
    updLabels = pyqtSignal(int, int)
    # Lists with size in bytes
    finished = pyqtSignal(list, list, str, str)

    def __init__(self, localFsPath, coll, upload):
        """

        Parameters
        ----------
        localFsPath
        coll
        upload
        """
        super().__init__()
        self.localFsPath = localFsPath
        self.coll = coll
        self.upload = upload

    def run(self):
        # Diff
        diff, onlyFS, onlyIrods, same = [], [], [], []
        try:
            if self.upload:
                # Data is placed inside of coll, check if dir or file is inside
                newPath = self.coll.path + "/" + os.path.basename(self.localFsPath)
                if os.path.isdir(self.localFsPath):
                    if self.conn.collection_exists(newPath):
                        subColl = self.conn.get_collection(newPath)
                    else:
                        subColl = None
                    (diff, onlyFS, onlyIrods, same) = self.conn.diff_irods_localfs(
                                                  subColl, self.localFsPath, scope="checksum")
                elif os.path.isfile(self.localFsPath):
                    (diff, onlyFS, onlyIrods, same) = self.conn.diff_obj_file(
                                                        newPath,
                                                        self.localFsPath, scope="checksum")
                self.updLabels.emit(len(onlyFS), len(diff))
            else:
                # Data is placed inside fsDir, check if obj or coll is inside
                newPath = os.path.join(self.localFsPath, self.coll.name)
                if self.conn.collection_exists(self.coll.path):
                    if not os.path.isdir(newPath):
                        FsPath = None
                    else:
                        FsPath = newPath
                    (diff, onlyFS, onlyIrods, same) = self.conn.diff_irods_localfs(
                        self.coll, FsPath, scope="checksum")
                # elif self.conn.dataobject_exists(self.coll.path):
                else:
                    (diff, onlyFS, onlyIrods, same) = self.conn.diff_obj_file(
                                                   self.coll.path, newPath, scope="checksum")
                self.updLabels.emit(len(onlyIrods), len(diff))
        except:
            logging.exception('dataTransfer.py: Error in getDataState')

        # Get size
        if self.upload:
            fsDiffFiles = [d[1] for d in diff]
            updateSize = utils.utils.get_local_size(fsDiffFiles)
            fullOnlyFsPaths = [self.localFsPath+os.sep+d for d in onlyFS
                               if not d.startswith('/') or ':' not in d]
            fullOnlyFsPaths.extend(
                [d for d in onlyFS if d.startswith('/') or ':' in d])
            addSize = utils.utils.get_local_size(fullOnlyFsPaths)
            logging.debug('%s %s', fsDiffFiles, updateSize)
            logging.debug('%s %s', onlyFS, addSize)
            self.finished.emit(onlyFS, diff, str(addSize), str(updateSize))
        else:
            irodsDiffFiles = [d[0] for d in diff]
            updateSize = self.conn.get_irods_size(irodsDiffFiles)
            onlyIrodsFullPath = onlyIrods.copy()
            for i in range(len(onlyIrodsFullPath)):
                if not onlyIrods[i].startswith(self.coll.path):
                    onlyIrodsFullPath[i] = f'{self.coll.path}/{onlyIrods[i]}'
            addSize = self.conn.get_irods_size(onlyIrodsFullPath)
            self.finished.emit(onlyIrods, diff, str(addSize), str(updateSize))


class UpDownload(QObject, utils.context.ContextContainer):
    """Background worker for the up/download

    """
    finished = pyqtSignal(bool, str)

    def __init__(self, upload, localFS, Coll, totalSize, resource, diff, addFiles, force):
        """

        Parameters
        ----------
        upload
        localFS
        Coll
        totalSize
        resource
        diff
        addFiles
        force
        """
        super().__init__()
        self.upload = upload
        self.localFS = localFS
        self.Coll = Coll
        self.totalSize = totalSize
        self.resource = resource
        self.diff = diff
        self.addFiles = addFiles
        # TODO prefer setting here?
        self.force = self.conf.get('force_transfers', force)

    def run(self):
        try:
            if self.upload:
                diffs = (self.diff, self.addFiles, [], [])
                self.conn.upload_data(
                    self.localFS, self.Coll, self.resource,
                    int(self.totalSize), buff=1024**3,
                    force=self.force, diffs=diffs)
                self.finished.emit(True, "Upload finished")
            else:
                diffs = (self.diff, [], self.addFiles, [])
                logging.info('UpDownload Diff: %s', diffs)
                self.conn.download_data(
                    self.Coll, self.localFS, int(self.totalSize),
                    buff=1024**3, force=False, diffs=diffs)
                self.finished.emit(True, "Download finished")
        except Exception as error:
            logging.error('%r', error)
            self.finished.emit(False, str(error))
