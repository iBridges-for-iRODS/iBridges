from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QMainWindow, QHeaderView, QMessageBox
from PyQt5 import QtCore
from PyQt5.uic import loadUi
from utils.irodsConnectorAnonymous import irodsConnectorAnonymous
from gui.checkableFsTree import checkableFsTreeModel
from gui.popupWidgets import createDirectory
from gui.dataTransfer import dataTransfer

import os

class irodsTicketLogin():
    def __init__(self, widget):
        self.ic = None
        self.coll = None
        self.widget = widget

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

        self.widget.connectButton.clicked.connect(self.irodsSession)
        self.widget.homeButton.clicked.connect(self.loadTable)
        self.widget.createDirectoryButton.clicked.connect(self.createFolder)
        self.widget.downloadButton.clicked.connect(self.download)
        self.widget.downloadAllButton.clicked.connect(self.downloadAll)
        self.widget.collTable.doubleClicked.connect(self.browse)
        self.widget.collTable.clicked.connect(self.fillInfo)


    def irodsSession(self):
        self.widget.infoLabel.clear()
        host = self.widget.serverEdit.text()
        token = self.widget.ticketEdit.text()
        path = self.widget.pathEdit.text()

        try:
            self.ic = irodsConnectorAnonymous(host, token, path)
            self.coll = self.ic.getData()
            self.loadTable()
        except Exception as e:
            self.widget.infoLabel.setText("LOGIN ERROR: Check ticket and iRODS path.\n"+repr(e))


    def enableButtons(self, enable):
        self.widget.connectButton.setEnabled(enable)
        self.widget.homeButton.setEnabled(enable)
        self.widget.createDirectoryButton.setEnabled(enable)
        self.widget.downloadButton.setEnabled(enable)
        self.widget.downloadAllButton.setEnabled(enable)

    
    def loadTable(self, update = None):
        self.widget.infoLabel.clear()
        if self.coll == None:
            self.widget.infoLabel.setText("No data avalaible. Check ticket and iRODS path.")
            return
        if update == None or update == False:
            update = self.coll

        self.widget.collTable.setRowCount(0)
        self.widget.collTable.setRowCount(len(update.subcollections)+len(update.data_objects))
        row = 0
        for subcoll in update.subcollections:
            self.widget.collTable.setItem(row, 0, 
                    QtWidgets.QTableWidgetItem(os.path.dirname(subcoll.path)))
            self.widget.collTable.setItem(row, 1, 
                    QtWidgets.QTableWidgetItem(subcoll.name+"/"))
            self.widget.collTable.setItem(1, 2, QtWidgets.QTableWidgetItem(""))
            self.widget.collTable.setItem(1, 3, QtWidgets.QTableWidgetItem(""))
            row = row + 1
        for obj in update.data_objects:
            self.widget.collTable.setItem(row, 0,
                    QtWidgets.QTableWidgetItem(os.path.dirname(obj.path)))
            self.widget.collTable.setItem(row, 1, QtWidgets.QTableWidgetItem(obj.name))
            self.widget.collTable.setItem(row, 2, QtWidgets.QTableWidgetItem(str(obj.size)))
            self.widget.collTable.setItem(row, 3, QtWidgets.QTableWidgetItem(str(obj.checksum)))
            self.widget.collTable.setItem(row, 4, 
                    QtWidgets.QTableWidgetItem(str(obj.modify_time)))
            row = row+1
        self.widget.collTable.resizeColumnsToContents()


    def browse(self, index):
        self.widget.infoLabel.clear()
        col = index.column()
        row = index.row()
        if self.widget.collTable.item(row, 0).text() != '':
            path = self.widget.collTable.item(row, 0).text()
            item = self.widget.collTable.item(row, 1).text()
            if item.endswith('/'):
                item = item[:-1]
            if self.ic.session.collections.exists(path+'/'+item):
                coll = self.ic.session.collections.get(path+'/'+item)
                self.loadTable(update = coll)


    def fillInfo(self, index):
        self.widget.previewBrowser.clear()
        self.widget.metadataTable.setRowCount(0)
        row = index.row()
        value = self.widget.collTable.item(row, 1).text()
        path = self.widget.collTable.item(row, 0).text()
        try:
            self.__fillPreview(value, path)
            self.__fillMetadata(value, path)
        except Exception as e:
            self.widget.infoLabel.setText(repr(e))
            raise


    def __fillPreview(self, value, path):
        newPath = "/"+path.strip("/")+"/"+value.strip("/")
        if self.ic.session.collections.exists(newPath): # collection
            coll = self.ic.session.collections.get(newPath)
            content = ['Collections:', '-----------------'] +\
                      [c.name+'/' for c in coll.subcollections] + \
                      ['\n', 'Data:', '-----------------']+\
                      [o.name for o in coll.data_objects]
            previewString = '\n'.join(content)
            self.widget.previewBrowser.append(previewString)
        else: # object
            subcoll = self.ic.session.collections.get(path)
            obj = [o for o in subcoll.data_objects if o.name == value][0]
            # get mimetype
            mimetype = value.split(".")[len(value.split("."))-1]
            if mimetype in ['txt', 'json', 'csv']:
                try:
                    out = []
                    with obj.open('r') as readObj:
                        for i in range(20):
                            out.append(readObj.read(50))
                    previewString = ''.join([line.decode('utf-8') for line in out])
                    self.widget.previewBrowser.append(previewString)
                except Exception as e:
                    self.widget.previewBrowser.append(obj.path)
                    self.widget.previewBrowser.append(repr(e))
                    self.widget.previewBrowser.append("Storage resource might be down.")
            else:
                self.widget.previewBrowser.append("No preview for "+obj.path)


    def __fillMetadata(self, value, path):
        newPath = "/"+path.strip("/")+"/"+value.strip("/")
        metadata = []
        if value.endswith("/") and self.ic.session.collections.exists(newPath):
            coll = self.ic.session.collections.get(
                        "/"+path.strip("/")+"/"+value.strip("/")
                        )
            metadata = coll.metadata.items()
        else:
            subcoll = self.ic.session.collections.get(path)
            obj = [o for o in subcoll.data_objects if o.name == value][0]
            metadata = obj.metadata.items()
        self.widget.metadataTable.setRowCount(len(metadata))
        row = 0
        for item in metadata:
            self.widget.metadataTable.setItem(row, 0,
                    QtWidgets.QTableWidgetItem(item.name))
            self.widget.metadataTable.setItem(row, 1,
                    QtWidgets.QTableWidgetItem(item.value))
            self.widget.metadataTable.setItem(row, 2,
                    QtWidgets.QTableWidgetItem(item.units))
            row = row+1
        self.widget.metadataTable.resizeColumnsToContents()


    def createFolder(self):
        self.widget.infoLabel.clear()
        parent = self.dirmodel.get_checked()
        if parent == None:
            self.widget.infoLabel.setText("No parent folder selected.")
        else:
            createDirWidget = createDirectory(parent)
            createDirWidget.exec_()
            #self.dirmodel.initial_expand(previous_item = parent)


    def downloadAll(self):
        self.download(allData = True)


    def download(self, allData = False):
        #irods data
        self.enableButtons(False)
        self.widget.infoLabel.clear()
        if allData:
            collPath = os.path.dirname(self.coll.path)
            dataName = self.coll.name.strip('/')
        else:
            row = self.widget.collTable.selectedIndexes()[0].row()
            if row == -1:
                self.widget.infoLabel.setText("No iRODS data selected.")
                return
            else:
                collPath = self.widget.collTable.item(row, 0).text()
                dataName = self.widget.collTable.item(row, 1).text().strip('/')

        #fielsystem data
        destination = self.dirmodel.get_checked()
        if destination == None or os.path.isfile(destination):
            self.widget.infoLabel.setText("No download folder selected.")
            return
        
        if self.ic.session.collections.exists(collPath+'/'+dataName):
            item = self.ic.session.collections.get(collPath+'/'+dataName)
        else: #data object with workaround for bug
            parent = self.ic.session.collections.get(collPath)
            item = [obj for obj in parent.data_objects if obj.name == dataName][0]
        self.downloadWindow = dataTransfer(self.ic, False, destination, item)
        self.downloadWindow.finished.connect(self.finishedTransfer)


    def finishedTransfer(self, succes, irodsIdx):
        #Refreshes iRODS sub tree ad irodsIdx (set "None" if to skip)
        #Saves upload parameters if check box is set
        if succes == True:
            self.widget.infoLabel.setText("INFO UPLOAD/DOWLOAD: completed.")
        self.uploadWindow = None # Release
        self.enableButtons(True)


