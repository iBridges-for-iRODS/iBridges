from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QDialog, QFileDialog, QApplication, QMainWindow, QMessageBox, QPushButton
from PyQt5.uic import loadUi
from PyQt5 import QtCore
from PyQt5 import QtGui

from popupWidgets import irodsCreateCollection
from utils import walkToDict, getDownloadDir

import sys


class irodsBrowser():
    def __init__ (self, widget, ic):
        
        self.ic = ic
        self.widget = widget
        self.widget.viewTabs.setCurrentIndex(0)

        #Browser table
        self.widget.collTable.setColumnWidth(1,399)
        self.widget.collTable.setColumnWidth(2,199)
        self.widget.collTable.setColumnWidth(3,399)
        self.widget.collTable.setColumnWidth(0,20)

        #Metadata table
        self.widget.metadataTable.setColumnWidth(0,199)
        self.widget.metadataTable.setColumnWidth(1,199)
        self.widget.metadataTable.setColumnWidth(2,199)

        #ACL table
        self.widget.aclTable.setColumnWidth(0,299)
        self.widget.aclTable.setColumnWidth(1,299)

        #if user is not admin nor datasteward, hide ACL buttons
        userType, userGroups = self.ic.getUserInfo()

        if "rodsadmin" not in userType and \
           "datastewards" not in userGroups and \
           "training" not in userGroups:

            self.widget.aclAddButton.hide()
            self.widget.aclBox.setEnabled(False)
            self.widget.recurseBox.setEnabled(False)

        #Resource table
        self.widget.resourceTable.setColumnWidth(0,500)
        self.widget.resourceTable.setColumnWidth(1,90)

        #iRODS defaults
        try:
            self.irodsRoot = self.ic.session.collections.get("/"+ic.session.zone+"/home")
        except:
            self.irodsRoot = self.ic.session.collections.get(
                    "/"+ic.session.zone+"/home/"+ic.session.username)
        self.resetPath()

        self.currentBrowserRow = 0

        self.browse()


    def browse(self):
        #update main table when iRODS paht is changed upon 'Enter'
        self.widget.inputPath.returnPressed.connect(self.loadTable)
        self.widget.homeButton.clicked.connect(self.resetPath)
        #quick data upload and download (files only)
        self.widget.UploadButton.clicked.connect(self.fileUpload)
        self.widget.DownloadButton.clicked.connect(self.fileDownload)
        #new collection
        self.widget.createCollButton.clicked.connect(self.createCollection)
        self.widget.dataDeleteButton.clicked.connect(self.deleteData)
        self.widget.loadDeleteSelectionButton.clicked.connect(self.loadSelection)
        #functionality to lower tabs for metadata, acls and resources
        self.widget.collTable.doubleClicked.connect(self.updatePath)
        self.widget.collTable.clicked.connect(self.fillInfo)
        self.widget.metadataTable.clicked.connect(self.editMetadata)
        self.widget.aclTable.clicked.connect(self.editACL)
        #actions to update iCat entries of metadata and acls
        self.widget.metaAddButton.clicked.connect(self.addIcatMeta)
        self.widget.metaUpdateButton.clicked.connect(self.updateIcatMeta)
        self.widget.metaDeleteButton.clicked.connect(self.deleteIcatMeta)
        self.widget.aclAddButton.clicked.connect(self.updateIcatAcl)


    # Util functions
    def __clearErrorLabel(self):
        self.widget.errorLabel.clear()


    def __clearViewTabs(self):
        self.widget.aclTable.setRowCount(0)
        self.widget.metadataTable.setRowCount(0)
        self.widget.resourceTable.setRowCount(0)
        self.widget.previewBrowser.clear()


    def __fillResc(self, value, path):
        self.widget.resourceTable.setRowCount(0)
        newPath = "/"+path.strip("/")+"/"+value.strip("/")
        if not value.endswith("/") and self.ic.session.data_objects.exists(newPath):
            resources = self.ic.listResources()
            self.widget.resourceTable.setRowCount(len(resources))
            obj = self.ic.session.data_objects.get(
                    "/"+path.strip("/")+"/"+value.strip("/")
                    )
            replicas = [resc.resource_name for resc in obj.replicas]
            for i in range(len(resources)):
                self.widget.resourceTable.setItem(i, 0, 
                        QtWidgets.QTableWidgetItem(resources[i]))
                if resources[i] in replicas:
                    item = QtWidgets.QTableWidgetItem()
                    item.setCheckState(QtCore.Qt.Checked)
                    item.setFlags(QtCore.Qt.ItemIsEnabled)
                    self.widget.resourceTable.setItem(i, 1, item)
        self.widget.resourceTable.resizeColumnsToContents()


    def __fillACLs(self, value, path):
        self.widget.aclTable.setRowCount(0)
        self.widget.aclUserField.clear()
        self.widget.aclZoneField.clear()
        self.widget.aclBox.setCurrentText("----")

        newPath = "/"+path.strip("/")+"/"+value.strip("/")
        acls = []
        if value.endswith("/") and self.ic.session.collections.exists(newPath):
            item = self.ic.session.collections.get(
                        "/"+path.strip("/")+"/"+value.strip("/")
                        )
            acls = self.ic.session.permissions.get(item)
        elif self.ic.session.data_objects.exists(newPath):
            item = self.ic.session.data_objects.get(
                        "/"+path.strip("/")+"/"+value.strip("/")
                        )
            acls = self.ic.session.permissions.get(item)

        self.widget.aclTable.setRowCount(len(acls))
        row = 0
        for acl in acls:
            self.widget.aclTable.setItem(row, 0, QtWidgets.QTableWidgetItem(acl.user_name))
            self.widget.aclTable.setItem(row, 1,QtWidgets.QTableWidgetItem(acl.user_zone))
            self.widget.aclTable.setItem(row, 2,
                QtWidgets.QTableWidgetItem(acl.access_name.split(' ')[0].replace('modify', 'write')))
            row = row+1

        self.widget.aclTable.resizeColumnsToContents()


    def __fillMetadata(self, value, path):
        self.widget.metaKeyField.clear()
        self.widget.metaValueField.clear()
        self.widget.metaUnitsField.clear()

        newPath = "/"+path.strip("/")+"/"+value.strip("/")
        metadata = []
        if value.endswith("/") and self.ic.session.collections.exists(newPath):
            coll = self.ic.session.collections.get(
                        "/"+path.strip("/")+"/"+value.strip("/")
                        )
            metadata = coll.metadata.items()
        elif self.ic.session.data_objects.exists(newPath):
            obj = self.ic.session.data_objects.get(
                    "/"+path.strip("/")+"/"+value.strip("/")
                    )
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


    def __fillPreview(self, value, path):
        newPath = "/"+path.strip("/")+"/"+value.strip("/")
        if value.endswith("/") and self.ic.session.collections.exists(newPath): # collection
            coll = self.ic.session.collections.get(
                        "/"+path.strip("/")+"/"+value.strip("/")
                        )
            content = ['Collections:', '-----------------'] +\
                      [c.name+'/' for c in coll.subcollections] + \
                      ['\n', 'Data:', '-----------------']+\
                      [o.name for o in coll.data_objects]

            previewString = '\n'.join(content)
            self.widget.previewBrowser.append(previewString)
        elif self.ic.session.data_objects.exists(newPath): # object
            # get mimetype
            mimetype = value.split(".")[len(value.split("."))-1]
            obj = self.ic.session.data_objects.get(
                    "/"+path.strip("/")+"/"+value.strip("/")
                    )
            if mimetype in ['txt', 'json', 'csv']:
                try:
                    out = []
                    with obj.open('r') as readObj:
                        for i in range(20):
                            out.append(readObj.read(50))
                    previewString = ''.join([line.decode('utf-8') for line in out])
                    self.widget.previewBrowser.append(previewString)
                except Exception as e:
                    self.widget.previewBrowser.append(
                        "No Preview for: " + "/"+self.widget.inputPath.text().strip("/")+"/"+value.strip("/"))
                    self.widget.previewBrowser.append(repr(e))
                    self.widget.previewBrowser.append("Storage resource might be down.")
            else:
                self.widget.previewBrowser.append(
                    "No Preview for: " + "/"+self.widget.inputPath.text().strip("/")+"/"+value.strip("/"))


    def loadTable(self):
        #loads main browser table
        self.__clearErrorLabel()
        self.__clearViewTabs()
        newPath = "/"+self.widget.inputPath.text().strip("/")
        if self.ic.session.collections.exists(newPath):
            coll = self.ic.session.collections.get(newPath)
            self.widget.collTable.setRowCount(len(coll.data_objects)+len(coll.subcollections))
            row = 0
            for subcoll in coll.subcollections:
                self.widget.collTable.setItem(row, 1, QtWidgets.QTableWidgetItem(subcoll.name+"/"))
                self.widget.collTable.setItem(row, 2, QtWidgets.QTableWidgetItem(""))
                self.widget.collTable.setItem(row, 3, QtWidgets.QTableWidgetItem(""))
                self.widget.collTable.setItem(row, 0, QtWidgets.QTableWidgetItem(""))
                row = row+1
            for obj in coll.data_objects:
                self.widget.collTable.setItem(row, 1, QtWidgets.QTableWidgetItem(obj.name))
                self.widget.collTable.setItem(row, 2, QtWidgets.QTableWidgetItem(str(obj.size)))
                self.widget.collTable.setItem(row, 3, QtWidgets.QTableWidgetItem(str(obj.checksum)))
                self.widget.collTable.setItem(row, 0, QtWidgets.QTableWidgetItem(""))
                row = row+1
            self.widget.collTable.resizeColumnsToContents()
        else:
            self.widget.collTable.setRowCount(0)
            self.widget.errorLabel.setText("Collection does not exist.")


    def resetPath(self):
        self.widget.inputPath.setText(self.irodsRoot.path)
        self.loadTable()


    #@QtCore.pyqtSlot(QtCore.QModelIndex)
    def updatePath(self, index):
        self.__clearErrorLabel()
        col = index.column()
        row = index.row()
        if self.widget.collTable.item(row, 0).text() != '':
            parent = self.widget.collTable.item(row, 0).text()
        else:
            parent = self.widget.inputPath.text()
        value = self.widget.collTable.item(row, 1).text()
        if value.endswith("/"): #collection
            self.widget.inputPath.setText("/"+parent.strip("/")+"/"+value.strip("/"))
            self.loadTable()


    #@QtCore.pyqtSlot(QtCore.QModelIndex)
    def fillInfo(self, index):
        self.__clearErrorLabel()
        self.__clearViewTabs()

        self.widget.metadataTable.setRowCount(0);
        self.widget.aclTable.setRowCount(0);

        self.widget.resourceTable.setRowCount(0);
        col = index.column()
        row = index.row()
        self.currentBrowserRow = row
        value = self.widget.collTable.item(row, col).text()
        if self.widget.collTable.item(row, 0).text() != '':
            path = self.widget.collTable.item(row, 0).text()
        else:
            path = self.widget.inputPath.text()
        self.__clearViewTabs()
        self.__fillPreview(value, path)
        self.__fillMetadata(value, path)
        self.__fillACLs(value, path)
        self.__fillResc(value, path)


    def loadSelection(self):
        #loads selection from main table into delete tab
        self.widget.loadDeleteSelectionButton.setCursor(QtGui.QCursor(QtCore.Qt.WaitCursor))
        self.widget.deleteSelectionBrowser.clear()
        parent = self.widget.inputPath.text()
        row = self.widget.collTable.currentRow()
        if row > -1:
            cell = self.widget.collTable.item(row, 1).text()
            path = "/"+parent.strip("/")+"/"+cell.strip("/")
            if self.ic.session.collections.exists(path):
                irodsDict = walkToDict(self.ic.session.collections.get(path))
            elif self.ic.session.data_objects.exists(path):
                irodsDict = {self.ic.session.data_objects.get(path).path: []}
            else:
                self.widget.errorLabel.setText("Load: nothing selected.")
                pass

            for key in list(irodsDict.keys())[:20]:
                self.widget.deleteSelectionBrowser.append(key)
                if len(irodsDict[key]) > 0:
                    for item in irodsDict[key]:
                        self.widget.deleteSelectionBrowser.append('\t'+item)
            self.widget.deleteSelectionBrowser.append('...')
        self.widget.loadDeleteSelectionButton.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))


    def deleteData(self):
        #Deletes all data in the deleteSelectionBrowser
        data = self.widget.deleteSelectionBrowser.toPlainText().split('\n')
        self.widget.dataDeleteButton.setCursor(QtGui.QCursor(QtCore.Qt.WaitCursor))
        if data[0] != '':
            deleteItem = data[0].strip()
            quit_msg = "Delete all data in \n\n"+deleteItem+'\n'
            reply = QMessageBox.question(self.widget, 'Message', quit_msg, QMessageBox.Yes, QMessageBox.No)
            if reply == QMessageBox.Yes:
                if self.ic.session.collections.exists(deleteItem):
                    item = self.ic.session.collections.get(deleteItem)
                else:
                    item = self.ic.session.data_objects.get(deleteItem)
                self.ic.deleteData(item)
            self.widget.deleteSelectionBrowser.clear()
            self.loadTable()
            self.widget.dataDeleteButton.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))

    def createCollection(self):
        parent = "/"+self.widget.inputPath.text().strip("/")
        creteCollWidget = irodsCreateCollection(parent, self.ic)
        creteCollWidget.exec_()
        self.loadTable()


    def fileUpload(self):
        from utils import getSize
        dialog = QFileDialog(self.widget)
        fileSelect = QFileDialog.getOpenFileName(self.widget,
                        "Open File", "","All Files (*);;Python Files (*.py)")
        size = getSize([fileSelect[0]])
        buttonReply = QMessageBox.question(self.widget, 'Message Box', "Upload " + fileSelect[0],
                                           QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if buttonReply == QMessageBox.Yes:
            try:
                parentColl = self.ic.session.collections.get("/"+self.widget.inputPath.text().strip("/"))
                print("Upload "+fileSelect[0]+" to "+parentColl.path+" on resource "+self.ic.defaultResc)
                self.ic.uploadData(fileSelect[0], parentColl,
                        None, size, force=True)
                self.loadTable()
            except Exception as error:
                print("ERROR upload :", fileSelect[0], "failed; \n\t", repr(error))
                self.widget.errorLabel.setText(repr(error))
        else:
            pass

    def fileDownload(self):
        #If table is filled
        if self.widget.collTable.item(self.currentBrowserRow, 1) != None:
            objName = self.widget.collTable.item(self.currentBrowserRow, 1).text()
            if self.widget.collTable.item(self.currentBrowserRow, 0).text() == '':
                parent = self.widget.inputPath.text()
            else:
                parent = self.widget.collTable.item(self.currentBrowserRow, 0).text()
            if self.ic.session.data_objects.exists(parent+'/'+objName):
                downloadDir = getDownloadDir()
                buttonReply = QMessageBox.question(self.widget,
                                'Message Box',
                                'Download\n'+parent+'/'+objName+'\tto\n'+downloadDir)
                if buttonReply == QMessageBox.Yes:
                    obj = self.ic.session.data_objects.get(parent+'/'+objName)
                    self.ic.downloadData(obj, downloadDir, obj.size)
                    self.widget.errorLabel.setText("File downloaded to: "+downloadDir)


    #@QtCore.pyqtSlot(QtCore.QModelIndex)
    def editMetadata(self, index):
        self.__clearErrorLabel()
        self.widget.metaValueField.clear()
        self.widget.metaUnitsField.clear()
        row = index.row()
        key = self.widget.metadataTable.item(row, 0).text()
        value = self.widget.metadataTable.item(row, 1).text()
        units = self.widget.metadataTable.item(row, 2).text()
        self.widget.metaKeyField.setText(key)
        self.widget.metaValueField.setText(value)
        self.widget.metaUnitsField.setText(units)
        self.currentMetadata = (key, value, units)


    #@QtCore.pyqtSlot(QtCore.QModelIndex)
    def editACL(self, index):
        self.__clearErrorLabel()
        self.widget.aclUserField.clear()
        self.widget.aclZoneField.clear()
        self.widget.aclBox.setCurrentText("----")
        row = index.row()
        user = self.widget.aclTable.item(row, 0).text()
        zone = self.widget.aclTable.item(row, 1).text()
        acl = self.widget.aclTable.item(row, 2).text()
        self.widget.aclUserField.setText(user)
        self.widget.aclZoneField.setText(zone)
        self.widget.aclBox.setCurrentText(acl)
        self.currentAcl = (user, acl)


    def updateIcatAcl(self):
        self.widget.errorLabel.clear()
        user = self.widget.aclUserField.text()
        rights = self.widget.aclBox.currentText()
        recursive = self.widget.recurseBox.currentText() == 'True'
        if self.widget.collTable.item(self.currentBrowserRow, 0).text() == '':
            parent = self.widget.inputPath.text()
        else:
            parent = self.widget.collTable.item(self.currentBrowserRow, 0).text()
        cell = self.widget.collTable.item(self.currentBrowserRow, 1).text()
        zone = self.widget.aclZoneField.text()
        try:
            self.ic.setPermissions(rights, user, "/"+parent.strip("/")+"/"+cell.strip("/"), zone, recursive)
            self.__fillACLs(cell, parent)
        except Exception as error:
            self.widget.errorLabel.setText(repr(error))


    def updateIcatMeta(self):
        self.widget.errorLabel.clear()
        newKey = self.widget.metaKeyField.text()
        newVal = self.widget.metaValueField.text()
        newUnits = self.widget.metaUnitsField.text()
        try:
            if not (newKey == "" or newVal == ""):
                if self.widget.collTable.item(self.currentBrowserRow, 0).text() == '':
                    parent = self.widget.inputPath.text()
                else:
                    parent = self.widget.collTable.item(self.currentBrowserRow, 0).text()

                cell = self.widget.collTable.item(self.currentBrowserRow, 1).text()
                if cell.endswith("/"):
                    item = self.ic.session.collections.get("/"+parent.strip("/")+"/"+cell.strip("/"))
                else:
                    item = self.ic.session.data_objects.get("/"+parent.strip("/")+"/"+cell.strip("/"))
                self.ic.updateMetadata([item], newKey, newVal, newUnits)
                self.__fillMetadata(cell, parent)
                self.__fillResc(cell, parent)
        except Exception as error:
            self.widget.errorLabel.setText(repr(error))


    def addIcatMeta(self):
        self.widget.errorLabel.clear()
        newKey = self.widget.metaKeyField.text()
        newVal = self.widget.metaValueField.text()
        newUnits = self.widget.metaUnitsField.text()
        if not (newKey == "" or newVal == ""):
            try:
                if self.widget.collTable.item(self.currentBrowserRow, 0).text() == '':
                    parent = self.widget.inputPath.text()
                else:
                    parent = self.widget.collTable.item(self.currentBrowserRow, 0).text()

                cell = self.widget.collTable.item(self.currentBrowserRow, 1).text()
                if cell.endswith("/"):
                    item = self.ic.session.collections.get("/"+parent.strip("/")+"/"+cell.strip("/"))
                else:
                    item = self.ic.session.data_objects.get("/"+parent.strip("/")+"/"+cell.strip("/"))
                self.ic.addMetadata([item], newKey, newVal, newUnits)
                self.__fillMetadata(cell, parent)
                self.__fillResc(cell, parent)
            except Exception as error:
                self.widget.errorLabel.setText(repr(error))


    def deleteIcatMeta(self):
        self.widget.errorLabel.clear()
        key = self.widget.metaKeyField.text()
        val = self.widget.metaValueField.text()
        units = self.widget.metaUnitsField.text()
        try:
            if not (key == "" or val == ""):
                if self.widget.collTable.item(self.currentBrowserRow, 0).text() == '':
                    parent = self.widget.inputPath.text()
                else:
                    parent = self.widget.collTable.item(self.currentBrowserRow, 0).text()

                cell = self.widget.collTable.item(self.currentBrowserRow, 1).text()
                if cell.endswith("/"):
                    item = self.ic.session.collections.get("/"+parent.strip("/")+"/"+cell.strip("/"))
                else:
                    item = self.ic.session.data_objects.get("/"+parent.strip("/")+"/"+cell.strip("/"))
                self.ic.deleteMetadata([item], key, val, units)
                self.__fillMetadata(cell, parent)
        except Exception as error:
            self.widget.errorLabel.setText(repr(error))

