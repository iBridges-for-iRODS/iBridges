from typing import ClassVar
from PyQt5.uic import loadUi
from PyQt5.QtWidgets import QDialog, QMessageBox
from PyQt5.QtCore import QObject, QThread, pyqtSlot, pyqtSignal, QModelIndex
from PyQt5.QtGui import QMovie
import logging

from utils import getSizeList


# Loading symbol generator
# http://www.ajaxload.info/#preview


class UpDownloadCheck(QDialog):
    finished = pyqtSignal(bool ,QModelIndex)

    def __init__(self, ic, localFS, Coll, TreeInd, upload = True):
        super(UpDownloadCheck, self).__init__()
        loadUi("ui-files/upDownloadCheck.ui", self)
        QMessageBox.information(self, "status", "test")

        self.ic = ic
        self.localFS = localFS
        self.Coll = Coll
        self.TreeInd = TreeInd
        self.upload = upload
        self.newFiles = []
        self.checksumFiles = []

        self.cancelBtn.clicked.connect(self.cancel)
        self.confirmBtn.clicked.connect(self.confirm)

        # Upload
        if self.upload == True:
            self.confirmBtn.setText("Upload")
            self.newCB.setText("Upload")
        else:
            self.confirmBtn.setText("Download")
            self.newCB.setText("Download")           
        self.confirmBtn.setEnabled(False)

        self.loading_movie = QMovie("icons/loading_circle.gif")
        #loading_movie.setScaledSize(size)
        self.loadingLbl.setMovie(self.loading_movie)
        self.loading_movie.start()

        # Get information in seperate thread
        self.thread = QThread()
        self.worker = GetInfo(self.ic, localFS, Coll, upload)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.updLabels.connect(self.updLabels)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.updateUIFinished)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()
        self.show()


    def cancel(self):
        self.finished.emit(False, self.TreeInd)
        self.close()


    def confirm(self):
        to_process = []
        total_size = 0
        if self.diffCB.isChecked():
            to_process = self.checksumFiles
            total_size = self.checksumSize
        if self.newCB.isChecked():
            to_process = to_process + self.newFiles
            total_size = total_size + self.newSize

        self.thread = QThread()
        self.worker = UpDownload(self.ic, self.upload, self.localFS, self.Coll, to_process, total_size)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.upDownLoadFinished)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()


    # Callback for the GetInfo worker
    def updLabels(self, newFiles, checksumFiles):
        self.checksumLbl.setText(f"{checksumFiles}")
        self.newFLbl.setText(f"{newFiles}")


    # Callback for the GetInfo worker
    def updateUIFinished(self, newFiles, checksumFiles, newSize, checksumSize):
        self.checksumSize = checksumSize
        checksumSizeStr = self.bytesToStr(checksumSize)
        self.ChecksumSizeLbl.setText(checksumSizeStr)
        self.checksumFiles = checksumFiles

        self.newSize = newSize
        newSizeStr = self.bytesToStr(newSize)
        self.newFSizeLbl.setText(newSizeStr)
        self.newFiles = newFiles

        self.loading_movie.stop()
        self.loadingLbl.setHidden(True)
        self.statusLbl = ""
        self.confirmBtn.setEnabled(True)


    def bytesToStr(self, bytes):
        bytes = bytes / (1024**3)
        if bytes < 1000:
            bytesStr = f"{bytes} GB"
        else:
            bytes = bytes / 1000
            bytesStr = f"{bytes} TB"
        return bytesStr


    def upDownLoadFinished(self, status, statusmessage):
        QMessageBox(self, "status", statusmessage)
        self.confirmBtn.disconnect() # remove callback
        self.confirmBtn.setText("Close")
        self.confirmBtn.clicked.connect(self.close)


# Background worker to load the menu
class GetInfo(QObject):
    # Signals
    updLabels = pyqtSignal(int, int) # Num files
    finished = pyqtSignal(list, list, int, int) # Lists with size in bytes

    def __init__(self, ic, localFS, Coll, upload):
        super(GetInfo, self).__init__()
        self.ic = ic
        self.localFS =localFS
        self.Coll = Coll
        self.upload = upload

    def run(self):
        # Diff 
        (checksum, onlyFS, onlyIRods) = self.ic.diffIrodsLocalfs(self.Coll, self.localFS)
        if self.upload == True:
            self.updLabels.emit(len(onlyFS), len(checksum))
        else:
            self.updLabels.emit(len(onlyIRods), len(checksum))

        # Get size 
        if self.upload == True:
            checksumFSize = getSizeList(self.localFS, checksum)
            newFSize = getSizeList(self.localFS, onlyFS)
            self.finished.emit(onlyFS, checksum, newFSize, checksumFSize)
        else:
            self.finished.emit(onlyIRods, checksum, 0, 0)# TODO



# Background worker for the up/download
class UpDownload(QObject):
    finished = pyqtSignal(bool, str)
    def __init__(self, ic, upload, localFS, Coll, toProcess, totalSize):
        super(UpDownload, self).__init__()
        self.ic = ic
        self.upload = upload
        self.localFS = localFS
        self.Coll = Coll
        self.files = toProcess # files to up/download
        self.totalSize = totalSize

    def run(self):    
        try:
            if self.upload:
                for file in self.files:
                        source = self.localFS + file
                        #self.ic.uploadData(source, destColl, self.getResource(), self.totalSize, buff = 1024**3)# TODO keep 500GB free to avoid locking irods!
                        print(source)
                         # could be subfolder, create these first if they dont exist... 
                        print(self.Coll)
                raise ValueError
                self.finished.emit(True, "Upload finished")
        except Exception as error:
            logging.info(repr(error))
            self.finished.emit(False, "Something went wrong.")
