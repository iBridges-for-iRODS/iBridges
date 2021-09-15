from PyQt5.QtWidgets import QMainWindow, QHeaderView, QMessageBox
from PyQt5 import QtCore
#import logging
import os

from checkableFsTree import checkableFsTreeModel
from irodsTreeView  import IrodsModel
from utils import getSize, saveIenv
from continousUpload import contUpload

from popupWidgets import irodsCreateCollection, createDirectory
from UpDownloadCheck import UpDownloadCheck

class irodsUpDownload():
    def __init__(self, widget, ic, ienv):
        self.ic = ic
        self.widget = widget
        self.ienv = ienv
        self.syncing = False # syncing or not

        # QTreeViews
        self.dirmodel = checkableFsTreeModel(self.widget.localFsTreeView)
        self.widget.localFsTreeView.setModel(self.dirmodel)
        # Hide all columns except the Name
        self.widget.localFsTreeView.setColumnHidden(1, True)
        self.widget.localFsTreeView.setColumnHidden(2, True)
        self.widget.localFsTreeView.setColumnHidden(3, True)
        self.widget.localFsTreeView.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        home_location = QtCore.QStandardPaths.standardLocations(
                               QtCore.QStandardPaths.HomeLocation)[0]
        index = self.dirmodel.setRootPath(home_location)
        self.widget.localFsTreeView.setCurrentIndex(index)
        self.dirmodel.initial_expand()
        
        # iRODS  zone info
        self.widget.irodsZoneLabel.setText("/"+self.ic.session.zone+":")
        # iRODS tree
        self.irodsmodel = IrodsModel(ic, self.widget.irodsFsTreeView)
        self.widget.irodsFsTreeView.setModel(self.irodsmodel)
        self.irodsRootColl = '/'+ic.session.zone
        self.irodsmodel.setHorizontalHeaderLabels([self.irodsRootColl,
                                              'Level', 'iRODS ID',
                                              'parent ID', 'type'])

        self.widget.irodsFsTreeView.expanded.connect(self.irodsmodel.refreshSubTree)
        self.widget.irodsFsTreeView.clicked.connect(self.irodsmodel.refreshSubTree)
        self.irodsmodel.initTree()

        self.widget.irodsFsTreeView.setHeaderHidden(True)
        self.widget.irodsFsTreeView.header().setDefaultSectionSize(180)
        self.widget.irodsFsTreeView.setColumnHidden(1, True)
        self.widget.irodsFsTreeView.setColumnHidden(2, True)
        self.widget.irodsFsTreeView.setColumnHidden(3, True)
        self.widget.irodsFsTreeView.setColumnHidden(4, True)


        # Buttons
        self.widget.UploadButton.clicked.connect(self.upload)
        self.widget.DownloadButton.clicked.connect(self.download)
        #self.widget.ContUplBut.clicked.connect(self.cont_upload)
        #self.widget.ChecksumCheckBut.clicked.connect(self.check_checksum)
        self.widget.createFolderButton.clicked.connect(self.createFolder)
        self.widget.createCollButton.clicked.connect(self.createCollection)

        # Resource selector
        available_resources = self.ic.listResources()
        self.widget.resourceBox.clear()
        self.widget.resourceBox.addItems(available_resources)
        if ("ui_resource" in ienv) and \
                (ienv["ui_resource"] != "") and (ienv["ui_resource"] in available_resources):
            index = self.widget.resourceBox.findText(ienv["ui_resource"])
            self.widget.resourceBox.setCurrentIndex(index)
        elif ("default_resource_name" in ienv) and \
                (ienv["default_resource_name"] != "") and \
                (ienv["default_resource_name"] in available_resources):
            index = self.widget.resourceBox.findText(ienv["default_resource_name"])
            self.widget.resourceBox.setCurrentIndex(index)
        #self.widget.resourceBox.currentIndexChanged.connect(self.saveUIset)

        # Continious upload settings
        if ienv["irods_host"] in ["scomp1461.wur.nl", "npec-icat.irods.surfsara.nl"]:
            #self.widget.uplSetGB_2.setVisible(True)
            if ("ui_remLocalcopy" in ienv):
                self.widget.rLocalcopyCB.setChecked(ienv["ui_remLocalcopy"])
            if ("ui_uplMode" in ienv):
                uplMode =  ienv["ui_uplMode"]
                if uplMode == "f500":
                    self.widget.uplF500RB.setChecked(True)
                elif uplMode == "meta":
                    self.widget.uplMetaRB.setChecked(True)
                else:
                    self.widget.uplAllRB.setChecked(True)
            #self.widget.rLocalcopyCB.stateChanged.connect(self.saveUIset)
            #self.widget.uplF500RB.toggled.connect(self.saveUIset)
            #self.widget.uplMetaRB.toggled.connect(self.saveUIset)
            #self.widget.uplAllRB.toggled.connect(self.saveUIset)
        else:
            self.widget.uplSetGB_2.hide()
            self.widget.ContUplBut.hide()
            self.widget.ChecksumCheckBut.hide()

    def saveUIset(self):
        self.ienv["ui_resource"] = self.getResource()
        self.ienv["ui_remLocalcopy"] = self.getRemLocalCopy()
        self.ienv["ui_uplMode"] = self.getUplMode()
        saveIenv(self.ienv)


    def getResource(self):
        return self.widget.resourceBox.currentText()

    def getRemLocalCopy(self):
        return self.widget.rLocalcopyCB.isChecked()

    def getUplMode(self):
        if self.widget.uplF500RB.isChecked():
            uplMode = "f500"
        elif self.widget.uplMetaRB.isChecked():
            uplMode = "meta"
        else: # Default
            uplMode = "all"
        return uplMode


    def createFolder(self):
        parent = self.dirmodel.get_checked()
        if parent == None:
            self.widget.errorLabel.setText("No parent folder selected.")
        else:
            createDirWidget = createDirectory(parent)
            createDirWidget.exec_()
            #self.dirmodel.initial_expand(previous_item = parent)


    def createCollection(self):
        idx, parent = self.irodsmodel.get_checked()
        if parent == None:
            self.widget.errorLabel.setText("No parent collection selected.")
        else:
            creteCollWidget = irodsCreateCollection(parent, self.ic)
            creteCollWidget.exec_()
            self.irodsmodel.refreshSubTree(idx)


    # Upload a file/folder to IRODS and refresh the TreeView
    def upload(self):
        self.widget.errorLabel.clear()
        (fsSource, irodsDestIdx, irodsDestPath) = self.getPathsFromTrees()
        if fsSource == None or irodsDestPath == None: 
            self.widget.errorLabel.setText(
                    "ERROR Up/Download: Please select source and destination.")
            return           
        destColl = self.ic.session.collections.get(irodsDestPath)
        if os.path.isdir(fsSource):
            self.uploadWindow = UpDownloadCheck(self.ic, True, fsSource, destColl, 
                                                irodsDestIdx, self.getResource())
            self.uploadWindow.finished.connect(self.finishedUpDownload)
        else: # File
            try:
                self.ic.uploadData(fsSource, destColl, self.getResource(), 
                                   getSize(fsSource), buff = 1024**3)
                self.finishedUpDownload(True, irodsDestIdx)
            except ValueError:
                self.widget.errorLabel.setText(
                        "ERROR upload data: not enough space left on resource.")
            except Exception as error:
                #raise error
                #logging.info(repr(error))
                print(error)
                self.widget.errorLabel.setText("ERROR: Something went wrong.")

    def finishedUpDownload(self, succes, destInd):# slot for uploadcheck
        if succes == True:
            self.irodsmodel.refreshSubTree(destInd)
            if self.widget.saveSettings.isChecked():
                print("FINISH UPLOAD: saving ui parameters.")
                self.saveUIset()
            self.widget.errorLabel.setText("INFO UPLOAD: Upload completed.")
        self.uploadWindow = None # Release


    # Download a file/folder from IRODS to local disk
    def download(self):
        source_ind, source_path = self.irodsmodel.get_checked()
        if source_ind == None:
            self.widget.errorLabel.setText("ERROR download data: No iRODS data selected.")
            return
        destination = self.dirmodel.get_checked()
        if destination == None or os.path.isfile(destination):
            message = "No Folder selected to download to"
            self.widget.errorLabel.setText("ERROR download data: no destination folder selected.")
            return
        # File           
        if self.ic.session.data_objects.exists(source_path):
            try:
                sourceObj = self.ic.session.data_objects.get(source_path)
                self.ic.downloadData(sourceObj, destination)
                QMessageBox.information(self.widget, "status", "File downloaded.")
            except Exception as error:
                #logging.info(repr(error))
                print(error)
                QMessageBox.information(self.widget, "status", "Something went wrong.")
        else:
            sourceColl = self.ic.session.collections.get(source_path)
            self.uploadWindow = UpDownloadCheck(self.ic, False, destination, sourceColl)
            self.uploadWindow.finished.connect(self.finishedUpDownload)


    def en_disable_controls(self, enable):
        # Loop over all tabs enabling/disabling them
        for i in range(0, self.widget.tabWidget.count()):
            t = self.widget.tabWidget.tabText(i)
            if self.widget.tabWidget.tabText(i) == "Up and Download":
                continue
            self.widget.tabWidget.setTabVisible(i, enable)
        self.widget.UploadButton.setEnabled(enable)
        self.widget.DownloadButton.setEnabled(enable)
        self.widget.uplSetGB.setEnabled(enable)


    # Helpers to check file paths before upload
    def getPathsFromTrees(self):
        source = self.dirmodel.get_checked()
        if source == None:
            return (None, None, None)     
        destIdx, destPath = self.irodsmodel.get_checked()
        if destIdx == None or os.path.isfile(destPath):
            return (None, None, None)     
        return (source, destIdx, destPath)

