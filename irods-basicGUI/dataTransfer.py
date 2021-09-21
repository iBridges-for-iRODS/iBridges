from typing import ClassVar
from PyQt5.uic import loadUi
from PyQt5.QtWidgets import QDialog, QMessageBox
from PyQt5.QtCore import QObject, QThread, pyqtSlot, pyqtSignal, QModelIndex
from PyQt5.QtGui import QMovie
#import logging

from irods.keywords import NO_PARA_OP_KW

from utils import getSize
import os


# Loading symbol generator
# http://www.ajaxload.info/#preview


class dataTransfer(QDialog):
    finished = pyqtSignal(bool, object)

    def __init__(self, ic, upload, localFsPath, irodsColl, irodsTreeIdx = None, resource = None):
        super(dataTransfer, self).__init__()
        loadUi("ui-files/dataTransferState.ui", self)

        self.ic = ic
        self.localFsPath = localFsPath
        self.coll = irodsColl
        self.TreeInd = irodsTreeIdx
        self.upload = upload
        self.addFiles = []
        self.updateFiles = []
        self.resource = resource
        self.statusLbl.setText("Loading")

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
        self.worker = getDataState(self.ic, localFsPath, irodsColl, upload)
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
        self.finished.emit(False, None)
        self.close()


    def closeAfterUpDownl(self):
        self.finished.emit(True, self.TreeInd)
        self.close() 


    def confirm(self):
        total_size = self.updateSize + self.addSize
        self.loading_movie.start()
        self.loadingLbl.setHidden(False)
        if self.upload:
            self.statusLbl.setText("Uploading... this might take a while")
        else:
            self.statusLbl.setText("Downloading... this might take a while")
        self.thread = QThread()
        if len(self.diff)+len(self.addFiles) == 0:
            self.statusLbl.setText("Nothing to update.")
            self.loading_movie.stop()
            self.loadingLbl.setHidden(True)
        else:
            self.worker = UpDownload(self.ic, self.upload, 
                                     self.localFsPath, self.coll, 
                                     total_size, self.resource, self.diff, self.addFiles)
            self.worker.moveToThread(self.thread)
            self.thread.started.connect(self.worker.run)
            self.worker.finished.connect(self.thread.quit)
            self.worker.finished.connect(self.upDownLoadFinished)
            self.worker.finished.connect(self.worker.deleteLater)
            self.thread.finished.connect(self.thread.deleteLater)
            self.thread.start()


    # Callback for the getDataSize worker
    def updLabels(self, numAdd, numDiff):
        self.numDiffLabel.setText(f"{numDiff}")
        self.numAddLabel.setText(f"{numAdd}")


    # Callback for the getDataSize worker
    def updateUiWithDataState(self, addFiles, diff, addSize, updateSize):
        self.updateSize = updateSize
        #checksumSizeStr = self.bytesToStr(updateSize)
        self.ChecksumSizeLbl.setText(self.bytesToStr(updateSize))
        self.diff = diff

        self.addSize = addSize
        #newSizeStr = self.bytesToStr(addSize)
        self.newFSizeLbl.setText(self.bytesToStr(addSize))
        self.addFiles = addFiles

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
        if status == True:
            self.confirmBtn.disconnect() # remove callback
            self.confirmBtn.setText("Close")
            self.confirmBtn.clicked.connect(self.closeAfterUpDownl)
            self.statusLbl.setText("Update complete.")
        else:
            self.statusLbl.setText(statusmessage)
            self.confirmBtn.setText("Retry")


# Background worker to load the menu
class getDataState(QObject):
    # Signals
    updLabels = pyqtSignal(int, int) # Num files
    finished = pyqtSignal(list, list, int, int) # Lists with size in bytes

    def __init__(self, ic, localFsPath, coll, upload):
        super(getDataState, self).__init__()
        self.ic = ic
        self.localFsPath = localFsPath
        self.coll = coll
        self.upload = upload

    def run(self):
        # Diff
        diff, onlyFS, onlyIrods, same = [], [], [], []
        try:
            if self.upload == True:
            #data is placed inside of coll, check if dir or file is inside
                subItemPath = self.coll.path+"/"+os.path.basename(self.localFsPath)
                if os.path.isdir(self.localFsPath):
                    subColl = self.ic.session.collections.create(subItemPath)
                    (diff, onlyFS, onlyIrods, same) = self.ic.diffIrodsLocalfs(
                                                  subColl, self.localFsPath, scope="checksum")
                elif os.path.isfile(self.localFsPath):
                    (diff, onlyFS, onlyIrods, same) = self.ic.diffObjFile(
                                                        subItemPath, 
                                                        self.localFsPath, scope="checksum")
                self.updLabels.emit(len(onlyFS), len(diff))
            else:
                #data is placed inside fsDir, check if obj or coll is inside
                subFsPath = os.path.join(self.localFsPath, self.coll.name)
                if not os.path.isdir(subFsPath):
                    os.mkdir(subFsPath)
                if self.ic.session.collections.exists(self.coll.path):
                    (diff, onlyFS, onlyIrods, same) = self.ic.diffIrodsLocalfs(
                                                  self.coll, subFsPath, scope="checksum")
                elif self.ic.session.data_objects.exists(self.coll.path):
                    (diff, onlyFS, onlyIrods, same) = self.ic.diffObjFile(
                                                   self.coll.path, subFsPath, scope="checksum")
                self.updLabels.emit(len(onlyIrods), len(diff))
        except Exception as error:
            print(error)

        # Get size 
        if self.upload == True:
            fsDiffFiles = [d[1] for d in diff]
            updateSize = getSize(fsDiffFiles)
            addSize = getSize(onlyFS)
            self.finished.emit(onlyFS, diff, addSize, updateSize)
        else:
            irodsDiffFiles = [d[0] for d in diff]
            updateSize =  self.ic.getSize(irodsDiffFiles)
            addSize = self.ic.getSize(onlyIrods)
            self.finished.emit(onlyIrods, diff, addSize, updateSize)


# Background worker for the up/download
class UpDownload(QObject):
    finished = pyqtSignal(bool, str)
    def __init__(self, ic, upload, localFS, Coll, totalSize, resource, diff, addFiles):
        super(UpDownload, self).__init__()
        self.ic = ic
        self.upload = upload
        self.localFS = localFS
        self.Coll = Coll
        self.totalSize = totalSize
        self.resource = resource
        self.diff = diff
        self.addFiles = addFiles

    def run(self):    
        try:
            if self.upload:
                diffs = (self.diff, self.addFiles, [], [])
                self.ic.uploadData(self.localFS, self.Coll, 
                                   self.resource, self.totalSize, buff = 1024**3, 
                                   force = False, diffs = diffs)
                self.finished.emit(True, "Upload finished")
            else:
                diffs = (self.diff, [], self.addFiles, [])
                print(diffs)
                self.ic.downloadData(self.Coll, self.localFS, 
                                    self.totalSize, buff = 1024**3, force = False, diffs = diffs)
                self.finished.emit(True, "Download finished")                
        except Exception as error:
            print(error)
            #logging.info(repr(error))
            self.finished.emit(False, str(error))