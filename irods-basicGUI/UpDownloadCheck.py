from typing import ClassVar
from PyQt5.uic import loadUi
from PyQt5.QtWidgets import QDialog, QMessageBox
from PyQt5.QtCore import QObject, QThread, pyqtSlot, pyqtSignal, QModelIndex
from PyQt5.QtGui import QMovie
import logging

from irods.keywords import NO_PARA_OP_KW

from utils import getSizeList


# Loading symbol generator
# http://www.ajaxload.info/#preview


class UpDownloadCheck(QDialog):
    finished = pyqtSignal(bool, object)

    def __init__(self, ic, upload, localFS, Coll, TreeInd = None, resource = None):
        super(UpDownloadCheck, self).__init__()
        loadUi("ui-files/upDownloadCheck.ui", self)

        self.ic = ic
        self.localFS = localFS
        self.Coll = Coll
        self.TreeInd = TreeInd
        self.upload = upload
        self.newFiles = []
        self.checksumFiles = []
        self.resource = resource

        self.cancelBtn.clicked.connect(self.cancel)
        self.confirmBtn.clicked.connect(self.confirm)

        # Upload
        if self.upload == True:
            self.confirmBtn.setText("Upload")
        else:
            self.confirmBtn.setText("Download")        
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
        self.finished.emit(False, None)
        self.close()

    def closeAfterUpDownl(self):
        if self.upload:
            self.finished.emit(True, self.TreeInd)
        else:
            self.finished.emit(False, None)
        self.close() 


    def confirm(self):
        total_size = self.checksumSize + self.newSize
        self.loading_movie.start()
        self.loadingLbl.setHidden(False)
        if self.upload:
            self.statusLbl.setText("Uploading... this might take a while")
        else:
            self.statusLbl.setText("Downloading... this might take a while")
        self.thread = QThread()
        self.worker = UpDownload(self.ic, self.upload, self.localFS, self.Coll, total_size, self.resource)
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
        self.statusLbl.setText("")
        self.confirmBtn.setEnabled(True)


    def bytesToStr(self, bytes):
        bytes = bytes / (1024**3)
        if bytes < 1000:
            bytesStr = f"{round(bytes, 3)} GB"
        else:
            bytes = bytes / 1000
            bytesStr = f"{round(bytes, 3)} TB"
        return bytesStr


    def upDownLoadFinished(self, status, statusmessage):
        self.loading_movie.stop()
        self.loadingLbl.setHidden(True)
        self.statusLbl.setText("")
        QMessageBox.information(self, "status", statusmessage)
        if status == True:
            self.confirmBtn.disconnect() # remove callback
            self.confirmBtn.setText("Close")
            self.confirmBtn.clicked.connect(self.closeAfterUpDownl)
        else:
            self.confirmBtn.setText("Retry")


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
    def __init__(self, ic, upload, localFS, Coll, totalSize, resource = None):
        super(UpDownload, self).__init__()
        self.ic = ic
        self.upload = upload
        self.localFS = localFS
        self.Coll = Coll
        self.totalSize = totalSize
        self.resource = resource

    def run(self):    
        try:
            if self.upload:
                self.ic.uploadData(self.localFS, self.Coll, self.resource, self.totalSize, buff = 1024**3)# TODO keep 500GB free to avoid locking irods!
                self.finished.emit(True, "Upload finished")
            else:
                self.ic.downloadData(self.Coll, self.localFS)
                self.finished.emit(True, "Download finished")                
        except Exception as error:
            logging.info(repr(error))
            self.finished.emit(False, "Something went wrong.")
