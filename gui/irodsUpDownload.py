import os
import sys
from PyQt6.QtWidgets import QHeaderView, QMessageBox, QWidget
from PyQt6 import QtCore
from PyQt6.QtGui import QFileSystemModel
from PyQt6.uic import loadUi

from gui.checkableFsTree import checkableFsTreeModel
from gui.irodsTreeView import IrodsModel
from gui.popupWidgets import irodsCreateCollection, createDirectory
from gui.dataTransfer import dataTransfer
from gui.ui_files.tabUpDownload import Ui_tabUpDownload
from utils.utils import saveIenv


class irodsUpDownload(QWidget, Ui_tabUpDownload):
    def __init__(self, ic, ienv):
        self.ic = ic
        self.ienv = ienv
        self.syncing = False  # syncing or not

        super(irodsUpDownload, self).__init__()
        if getattr(sys, 'frozen', False):
            super(irodsUpDownload, self).setupUi(self)
        else:
            loadUi("gui/ui_files/tabUpDownload.ui", self)

        # QTreeViews
        #self.dirmodel = checkableFsTreeModel(self.localFsTreeView)
        self.dirmodel = QFileSystemModel(self.localFsTreeView)
        self.localFsTreeView.setModel(self.dirmodel)
        # Hide all columns except the Name
        self.localFsTreeView.setColumnHidden(1, True)
        self.localFsTreeView.setColumnHidden(2, True)
        self.localFsTreeView.setColumnHidden(3, True)
        self.localFsTreeView.header().setSectionResizeMode(
                                             QHeaderView.ResizeMode.ResizeToContents)
        home_location = QtCore.QStandardPaths.standardLocations(
                               QtCore.QStandardPaths.StandardLocation.HomeLocation)[0]
        index = self.dirmodel.setRootPath(home_location)
        self.localFsTreeView.setCurrentIndex(index)
        #self.dirmodel.initial_expand()
        
        # iRODS zone info
        self.irodsZoneLabel.setText("/"+self.ic.session.zone+":")
        # iRODS tree
        self.irodsmodel = IrodsModel(ic, self.irodsFsTreeView)
        self.irodsFsTreeView.setModel(self.irodsmodel)
        self.irodsRootColl = '/'+ic.session.zone
        self.irodsmodel.setHorizontalHeaderLabels([self.irodsRootColl,
                                              'Level', 'iRODS ID',
                                              'parent ID', 'type'])

        self.irodsFsTreeView.expanded.connect(self.irodsmodel.refreshSubTree)
        self.irodsFsTreeView.clicked.connect(self.irodsmodel.refreshSubTree)
        self.irodsmodel.initTree()

        self.irodsFsTreeView.setHeaderHidden(True)
        self.irodsFsTreeView.header().setDefaultSectionSize(180)
        self.irodsFsTreeView.setColumnHidden(1, True)
        self.irodsFsTreeView.setColumnHidden(2, True)
        self.irodsFsTreeView.setColumnHidden(3, True)
        self.irodsFsTreeView.setColumnHidden(4, True)

        # Buttons
        self.UploadButton.clicked.connect(self.upload)
        self.DownloadButton.clicked.connect(self.download)
        self.createFolderButton.clicked.connect(self.createFolder)
        self.createCollButton.clicked.connect(self.createCollection)

        # Resource selector
        available_resources = set([i[0] for i in self.ic.listResources() if i[0] != "bundleResc"])
        self.resourceBox.clear()
        self.resourceBox.addItems(available_resources)
        if ("default_resource_name" in ienv) and \
                (ienv["default_resource_name"] != "") and \
                (ienv["default_resource_name"] in available_resources):
            index = self.resourceBox.findText(ienv["default_resource_name"])
            self.resourceBox.setCurrentIndex(index)

    def enableButtons(self, enable):
        self.UploadButton.setEnabled(enable)
        self.DownloadButton.setEnabled(enable)
        self.createFolderButton.setEnabled(enable)
        self.createCollButton.setEnabled(enable)
        self.localFsTreeView.setEnabled(enable)
        self.localFsTreeView.setEnabled(enable)

    def infoPopup(self, message):
        QMessageBox.information(self, 'Information', message)

    def getResource(self):
        return self.resourceBox.currentText()

    def getRemLocalCopy(self):
        return self.rLocalcopyCB.isChecked()

    def createFolder(self):
        index = self.localFsTreeView.selectedIndexes()[0]
        parent = self.dirmodel.filePath(index)
        if parent is None or os.path.isfile(parent):
            self.errorLabel.setText("No parent folder selected.")
        else:
            createDirWidget = createDirectory(parent)
            createDirWidget.exec()
            # self.dirmodel.initial_expand(previous_item = parent)

    def createCollection(self):
        index = self.irodsFsTreeView.selectedIndexes()[0]
        parent = self.irodsmodel.irodsPathFromTreeIdx(index)
        if parent is None or self.ic.session.data_objects.exists(parent):
            self.errorLabel.setText("No parent collection selected.")
        else:
            creteCollWidget = irodsCreateCollection(parent, self.ic)
            creteCollWidget.exec()
            self.irodsmodel.refreshSubTree(index)

    # Upload a file/folder to IRODS and refresh the TreeView
    def upload(self):
        self.enableButtons(False)
        self.errorLabel.clear()
        (fsSource, irodsDestIdx, irodsDestPath) = self.getPathsFromTrees()
        print(fsSource, irodsDestIdx, irodsDestPath)
        if fsSource is None or irodsDestPath is None:
            self.errorLabel.setText(
                    "ERROR Up/Download: Please select source and destination.")
            self.enableButtons(True)
            return
        if not self.ic.session.collections.exists(irodsDestPath):
            self.errorLabel.setText(
                    "ERROR UPLOAD: iRODS destination is file, must be collection.")
            self.enableButtons(True)
            return
        destColl = self.ic.session.collections.get(irodsDestPath)
        # if os.path.isdir(fsSource):
        self.uploadWindow = dataTransfer(self.ic, True, fsSource, destColl, 
                                         irodsDestIdx, self.getResource())
        self.uploadWindow.finished.connect(self.finishedUpDownload)

    def finishedUpDownload(self, success, irodsIdx):
        # Refreshes iRODS subtree ad irodsIdx (set "None" if to skip)
        # Saves upload parameters if check box is set
        if success is True:
            if irodsIdx is not None:
                self.irodsmodel.refreshSubTree(irodsIdx)
            self.errorLabel.setText("INFO UPLOAD/DOWNLOAD: completed.")
        self.uploadWindow = None  # Release
        self.enableButtons(True)

    def download(self):
        self.enableButtons(False)
        self.errorLabel.clear()
        (fsDest, irodsSourceIdx, irodsSourcePath) = self.getPathsFromTrees()
        if fsDest is None or irodsSourcePath is None:
            self.errorLabel.setText(
                    "ERROR Up/Download: Please select source and destination.")
            self.enableButtons(True)
            return
        if os.path.isfile(fsDest):
            self.errorLabel.setText(
                    "ERROR DOWNLOAD: Local Destination is file, must be folder.")
            self.enableButtons(True)
            return
        # File           
        if self.ic.session.data_objects.exists(irodsSourcePath):
            irodsItem = self.ic.session.data_objects.get(irodsSourcePath)
        else:
            irodsItem = self.ic.session.collections.get(irodsSourcePath)
        self.uploadWindow = dataTransfer(self.ic, False, fsDest, irodsItem)
        self.uploadWindow.finished.connect(self.finishedUpDownload)

    # Helpers to check file paths before upload
    def getPathsFromTrees(self):
        index = self.localFsTreeView.selectedIndexes()[0]
        local = self.dirmodel.filePath(index)
        if local is None:
            return (None, None, None)    
        irodsIdx = self.irodsFsTreeView.selectedIndexes()[0]
        irodsPath = self.irodsmodel.irodsPathFromTreeIdx(irodsIdx) 
        #irodsIdx, irodsPath = self.irodsmodel.get_checked()
        #if irodsIdx is None or os.path.isfile(irodsPath):
        if irodsIdx is None:
            return (None, None, None)   
        print(irodsPath) 
        return (local, irodsIdx, irodsPath)
