from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QDialog, QFileDialog, QApplication, QMainWindow, QMessageBox, QPushButton
from PyQt5.uic import loadUi
from PyQt5 import QtCore
from PyQt5 import QtGui

from createCollectionWidget import createCollectionWidget
from irodsUtils import walkToDict 
from elabUpload import elabUpload
from irodsSearch import irodsSearch
from irodsUpDownload import irodsUpDownload

import sys

class irodsBrowser(QMainWindow):
    def __init__(self, widget, ic):
        super(irodsBrowser, self).__init__()
        loadUi("ui-files/irodsBrowserMain.ui", self)
        self.ic = ic
        self.widget = widget
        self.tabWidget.setCurrentIndex(0)
        self.viewTabs.setCurrentIndex(0)

        #some placeholder variables to catch information
        self.currentBrowserRow = 0

        #Main widget --> browser
        self.irodsRoot = self.ic.session.collections.get("/"+ic.session.zone+"/home")
        self.collTable.setColumnWidth(1,399)
        self.collTable.setColumnWidth(2,199)
        self.collTable.setColumnWidth(3,399)
        self.collTable.setColumnWidth(0,20)
        self.collTable.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.collTable.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.collTable.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.collTable.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.resetPath() 

        #Home button
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("icons/home.png"))
        self.homeButton.setIcon(icon)

        #Metadata table
        self.metadataTable.setColumnWidth(0,199)
        self.metadataTable.setColumnWidth(1,199)
        self.metadataTable.setColumnWidth(2,199)
        self.metadataTable.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.metadataTable.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.metadataTable.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.metadataTable.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

        #ACL table
        self.aclTable.setColumnWidth(0,299)
        self.aclTable.setColumnWidth(1,299)
        self.aclTable.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.aclTable.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.aclTable.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.metadataTable.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

        #Resource table
        self.resourceTable.setColumnWidth(0,500)
        self.resourceTable.setColumnWidth(1,90)
        self.resourceTable.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.resourceTable.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.resourceTable.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)

        self.actionExit.triggered.connect(self.programExit)
        self.actionCloseSession.triggered.connect(self.newSession)
        self.actionSearch.triggered.connect(self.search)
        self.actionExportMetadata.triggered.connect(self.exportMeta)


        # setup Elabjournal tab
        self.elnTab = elabUpload(
                    self.ic, self.globalErrorLabel, self.elnTokenInput,
                    self.elnGroupTable, self.elnExperimentsTable, self.groupIdLabel,
                    self.experimentIdLabel, self.localFsTable,
                    self.elnUploadButton, self.elnPreviewBrowser, self.elnIrodsPath
                    )

        # Setup up/download tab
        self.updownload = irodsUpDownload(self, ic)

        self.browse()

    #Frame start

    def browse(self):
        #update main table when iRODS paht is changed upon 'Enter'
        self.inputPath.returnPressed.connect(self.loadTable)
        self.homeButton.clicked.connect(self.resetPath)
        #quick data upload
        self.UploadButton.clicked.connect(self.fileUpload)
        #new collection
        self.createCollButton.clicked.connect(self.createCollection)
        self.dataDeleteButton.clicked.connect(self.deleteData)
        self.loadDeleteSelectionButton.clicked.connect(self.loadSelection)
        #functionality to lower tabs for metadata, acls and resources
        self.collTable.doubleClicked.connect(self.updatePath)
        self.collTable.clicked.connect(self.fillInfo)
        self.metadataTable.clicked.connect(self.editMetadata)
        self.aclTable.clicked.connect(self.editACL)
        #actions to update iCat entries of metadata and acls
        self.metaAddButton.clicked.connect(self.addIcatMeta)
        self.metaUpdateButton.clicked.connect(self.updateIcatMeta)
        self.metaDeleteButton.clicked.connect(self.deleteIcatMeta)
        self.aclAddButton.clicked.connect(self.updateIcatAcl)


    #connect functions
    def programExit(self):
        quit_msg = "Are you sure you want to exit the program?"
        reply = QMessageBox.question(self, 'Message', quit_msg, QMessageBox.Yes, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.ic.session.cleanup()
            sys.exit()
        else:
            pass


    def newSession(self):
        quit_msg = "Are you sure you want to disconnect?"
        reply = QMessageBox.question(self, 'Message', quit_msg, QMessageBox.Yes, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.ic.session.cleanup()
            currentWidget = self.widget.currentWidget()
            self.widget.setCurrentIndex(self.widget.currentIndex()-1)
            self.widget.removeWidget(currentWidget)
            self.loadTable()

        else:
            pass

    def search(self):
        search = irodsSearch(self.ic, self.collTable)
        search.exec_()
        #search.search()


    def exportMeta(Self):
        print("TODO: search")


    def resetPath(self):
        self.inputPath.setText(self.irodsRoot.path)
        self.loadTable()


    def loadSelection(self):
        self.loadDeleteSelectionButton.setCursor(QtGui.QCursor(QtCore.Qt.WaitCursor))
        self.deleteSelectionBrowser.clear()
        parent = self.inputPath.text()
        row = self.collTable.currentRow()
        if row > -1:
            cell = self.collTable.item(row, 1).text()
            path = "/"+parent.strip("/")+"/"+cell.strip("/")
            if self.ic.session.collections.exists(path):
                irodsDict = walkToDict(self.ic.session.collections.get(path))
            elif self.ic.session.data_objects.exists(path):
                irodsDict = {self.ic.session.data_objects.get(path).path: []}
            else:
                errorLabel.setText("Load: nothing selected.")
                pass

            for key in list(irodsDict.keys())[:20]:
                self.deleteSelectionBrowser.append(key)
                if len(irodsDict[key]) > 0:
                    for item in irodsDict[key]:
                        self.deleteSelectionBrowser.append('\t'+item)
            self.deleteSelectionBrowser.append('...')
        self.loadDeleteSelectionButton.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))


    def deleteData(self):
        #Deletes all data in the deleteSelectionBrowser
        data = self.deleteSelectionBrowser.toPlainText().split('\n')
        self.dataDeleteButton.setCursor(QtGui.QCursor(QtCore.Qt.WaitCursor))
        if data[0] != '':
            deleteItem = data[0].strip()
            quit_msg = "Delete all data in \n\n"+deleteItem+'\n'
            reply = QMessageBox.question(self, 'Message', quit_msg, QMessageBox.Yes, QMessageBox.No)
            if reply == QMessageBox.Yes:
                if self.ic.session.collections.exists(deleteItem):
                    item = self.ic.session.collections.get(deleteItem)
                else:
                    item = self.ic.session.data_objects.get(deleteItem)
                self.ic.deleteData(item)
            self.deleteSelectionBrowser.clear()
            self.loadTable()
            self.dataDeleteButton.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))


    def createCollection(self):
        parent = "/"+self.inputPath.text().strip("/")
        creteCollWidget = createCollectionWidget(parent, self.ic)
        creteCollWidget.exec_()
        self.loadTable()

    def fileUpload(self):
        from irodsUtils import getSize
        dialog = QFileDialog(self)
        fileSelect = QFileDialog.getOpenFileName(self,"Open File", "","All Files (*);;Python Files (*.py)")
        size = getSize(fileSelect[0])
        buttonReply = QMessageBox.question(self, 'Message Box', "Upload " + fileSelect[0], 
                                           QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if buttonReply == QMessageBox.Yes:
            try:
                parentColl = self.ic.session.collections.get("/"+self.inputPath.text().strip("/"))
                print("Upload "+fileSelect[0]+" to "+parentColl.path+" on resource "+self.ic.defaultResc)
                self.ic.uploadData(fileSelect[0], parentColl, 
                        None, size, force=True)
                self.loadTable()
            except Exception as error:
                self.errorLabel.setText(repr(error))
        else:
            pass


    def updateIcatAcl(self):
        self.errorLabel.clear()
        user = self.aclUserField.text()
        rights = self.aclBox.currentText()
        recursive = self.recurseBox.currentText() == 'True'
        if self.collTable.item(self.currentBrowserRow, 0).text() == '':
            parent = self.inputPath.text()
        else:
            parent = self.collTable.item(self.currentBrowserRow, 0).text()
        cell = self.collTable.item(self.currentBrowserRow, 1).text()
        zone = self.aclZoneField.text()
        try:
            self.ic.setPermissions(rights, user, "/"+parent.strip("/")+"/"+cell.strip("/"), zone, recursive)
            self.__fillACLs(cell, parent)
        except Exception as error:
            self.errorLabel.setText(repr(error))


    def updateIcatMeta(self):
        self.errorLabel.clear()
        newKey = self.metaKeyField.text()
        newVal = self.metaValueField.text()
        newUnits = self.metaUnitsField.text()
        try:
            if not (newKey == "" or newVal == ""):
                if self.collTable.item(self.currentBrowserRow, 0).text() == '':
                    parent = self.inputPath.text()
                else:
                    parent = self.collTable.item(self.currentBrowserRow, 0).text()

                cell = self.collTable.item(self.currentBrowserRow, 1).text()
                if cell.endswith("/"):
                    item = self.ic.session.collections.get("/"+parent.strip("/")+"/"+cell.strip("/"))
                else:
                    item = self.ic.session.data_objects.get("/"+parent.strip("/")+"/"+cell.strip("/"))
                self.ic.updateMetadata([item], newKey, newVal, newUnits)
                self.__fillMetadata(cell, parent)
                self.__fillResc(cell, parent)
        except Exception as error:
            self.errorLabel.setText(repr(error))


    def addIcatMeta(self):
        self.errorLabel.clear()
        newKey = self.metaKeyField.text()
        newVal = self.metaValueField.text()
        newUnits = self.metaUnitsField.text()
        if not (newKey == "" or newVal == ""):
            try:
                if self.collTable.item(self.currentBrowserRow, 0).text() == '':
                    parent = self.inputPath.text()
                else:
                    parent = self.collTable.item(self.currentBrowserRow, 0).text()

                cell = self.collTable.item(self.currentBrowserRow, 1).text()
                if cell.endswith("/"):
                    item = self.ic.session.collections.get("/"+parent.strip("/")+"/"+cell.strip("/"))
                else:
                    item = self.ic.session.data_objects.get("/"+parent.strip("/")+"/"+cell.strip("/"))
                self.ic.addMetadata([item], newKey, newVal, newUnits)
                self.__fillMetadata(cell, parent)
                self.__fillResc(cell, parent)
            except Exception as error:
                self.errorLabel.setText(repr(error))



    def deleteIcatMeta(self):
        self.errorLabel.clear()
        key = self.metaKeyField.text()
        val = self.metaValueField.text()
        units = self.metaUnitsField.text()
        try:
            if not (key == "" or val == ""):
                if self.collTable.item(self.currentBrowserRow, 0).text() == '':
                    parent = self.inputPath.text()
                else:
                    parent = self.collTable.item(self.currentBrowserRow, 0).text()

                cell = self.collTable.item(self.currentBrowserRow, 1).text()
                if cell.endswith("/"):
                    item = self.ic.session.collections.get("/"+parent.strip("/")+"/"+cell.strip("/"))
                else:
                    item = self.ic.session.data_objects.get("/"+parent.strip("/")+"/"+cell.strip("/"))
                self.ic.deleteMetadata([item], key, val, units)
                self.__fillMetadata(cell, parent)
        except Exception as error:
            self.errorLabel.setText(repr(error))


    @QtCore.pyqtSlot(QtCore.QModelIndex)
    def updatePath(self, index):
        self.__clearErrorLabel()
        col = index.column()
        row = index.row()
        if self.collTable.item(row, 0).text() != '':
            parent = self.collTable.item(row, 0).text()
        else:
            parent = self.inputPath.text()
        value = self.collTable.item(row, 1).text()
        if value.endswith("/"): #collection
            self.inputPath.setText("/"+parent.strip("/")+"/"+value.strip("/"))
            self.loadTable()


    @QtCore.pyqtSlot(QtCore.QModelIndex)
    def fillInfo(self, index):
        self.__clearErrorLabel()
        self.__clearViewTabs()

        self.metadataTable.setRowCount(0);
        self.aclTable.setRowCount(0);

        self.resourceTable.setRowCount(0);
        col = index.column()
        row = index.row()
        self.currentBrowserRow = row
        value = self.collTable.item(row, col).text()
        if self.collTable.item(row, 0).text() != '':
            path = self.collTable.item(row, 0).text()
        else:
            path = self.inputPath.text()
        self.__clearViewTabs()
        self.__fillPreview(value, path)
        self.__fillMetadata(value, path)
        self.__fillACLs(value, path)
        self.__fillResc(value, path)


    @QtCore.pyqtSlot(QtCore.QModelIndex)
    def editMetadata(self, index):
        self.__clearErrorLabel()
        self.metaValueField.clear()
        self.metaUnitsField.clear()
        row = index.row()
        key = self.metadataTable.item(row, 0).text()
        value = self.metadataTable.item(row, 1).text() 
        units = self.metadataTable.item(row, 2).text()
        self.metaKeyField.setText(key)
        self.metaValueField.setText(value)
        self.metaUnitsField.setText(units)
        self.currentMetadata = (key, value, units)


    @QtCore.pyqtSlot(QtCore.QModelIndex)
    def editACL(self, index):
        self.__clearErrorLabel()
        self.aclUserField.clear()
        self.aclZoneField.clear()
        self.aclBox.setCurrentText("----")
        row = index.row()
        user = self.aclTable.item(row, 0).text()
        zone = self.aclTable.item(row, 1).text()
        acl = self.aclTable.item(row, 2).text()
        self.aclUserField.setText(user)
        self.aclZoneField.setText(zone)
        self.aclBox.setCurrentText(acl)
        self.currentAcl = (user, acl)


    # Util functions
    def __clearErrorLabel(self):
        self.errorLabel.clear()


    def __clearViewTabs(self):
        self.aclTable.setRowCount(0)
        self.metadataTable.setRowCount(0)
        self.resourceTable.setRowCount(0)
        self.previewBrowser.clear()
        #self.deleteTreeWidget


    def loadTable(self):
        self.__clearErrorLabel()
        self.__clearViewTabs()
        newPath = "/"+self.inputPath.text().strip("/")
        if self.ic.session.collections.exists(newPath):
            coll = self.ic.session.collections.get(newPath)
            self.collTable.setRowCount(len(coll.data_objects)+len(coll.subcollections))
            row = 0
            for subcoll in coll.subcollections:
                self.collTable.setItem(row, 1, QtWidgets.QTableWidgetItem(subcoll.name+"/"))
                self.collTable.setItem(row, 2, QtWidgets.QTableWidgetItem(""))
                self.collTable.setItem(row, 3, QtWidgets.QTableWidgetItem(""))
                self.collTable.setItem(row, 0, QtWidgets.QTableWidgetItem(""))
                row = row+1
            for obj in coll.data_objects:
                self.collTable.setItem(row, 1, QtWidgets.QTableWidgetItem(obj.name))
                self.collTable.setItem(row, 2, QtWidgets.QTableWidgetItem(str(obj.size)))
                self.collTable.setItem(row, 3, QtWidgets.QTableWidgetItem(str(obj.checksum)))
                self.collTable.setItem(row, 0, QtWidgets.QTableWidgetItem(""))
                row = row+1
            self.collTable.resizeColumnsToContents()
        else:
            self.collTable.setRowCount(0)
            self.errorLabel.setText("Collection does not exist.")


    def __fillResc(self, value, path):
        self.resourceTable.setRowCount(0)
        newPath = "/"+path.strip("/")+"/"+value.strip("/")
        if not value.endswith("/") and self.ic.session.data_objects.exists(newPath):
            resources = self.ic.listResources()
            self.resourceTable.setRowCount(len(resources))
            obj = self.ic.session.data_objects.get(
                    "/"+path.strip("/")+"/"+value.strip("/")
                    )
            replicas = [resc.resource_name for resc in obj.replicas]
            for i in range(len(resources)):
                self.resourceTable.setItem(i, 0, 
                        QtWidgets.QTableWidgetItem(resources[i]))
                if resources[i] in replicas:
                    item = QtWidgets.QTableWidgetItem()
                    item.setCheckState(QtCore.Qt.Checked)
                    item.setFlags(QtCore.Qt.ItemIsEnabled)
                    self.resourceTable.setItem(i, 1, item)
        self.resourceTable.resizeColumnsToContents()


    def __fillACLs(self, value, path):
        self.aclTable.setRowCount(0)
        self.aclUserField.clear()
        self.aclZoneField.clear()
        self.aclBox.setCurrentText("----")

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
        
        self.aclTable.setRowCount(len(acls))
        row = 0
        for acl in acls:
            self.aclTable.setItem(row, 0, QtWidgets.QTableWidgetItem(acl.user_name))
            self.aclTable.setItem(row, 1,QtWidgets.QTableWidgetItem(acl.user_zone))
            self.aclTable.setItem(row, 2,
                        QtWidgets.QTableWidgetItem(acl.access_name.split(' ')[0].replace('modify', 'write')))
            row = row+1

        self.aclTable.resizeColumnsToContents()


    def __fillMetadata(self, value, path):
        self.metaKeyField.clear()
        self.metaValueField.clear()
        self.metaUnitsField.clear()

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
        self.metadataTable.setRowCount(len(metadata))
        row = 0
        for item in metadata:
            self.metadataTable.setItem(row, 0,
                    QtWidgets.QTableWidgetItem(item.name))
            self.metadataTable.setItem(row, 1,
                    QtWidgets.QTableWidgetItem(item.value))
            self.metadataTable.setItem(row, 2,
                    QtWidgets.QTableWidgetItem(item.units))
            row = row+1
        self.metadataTable.resizeColumnsToContents()


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
            self.previewBrowser.append(previewString)
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
                    self.previewBrowser.append(previewString)
                except Exception as e:
                    self.previewBrowser.append(
			"No Preview for: " + "/"+self.inputPath.text().strip("/")+"/"+value.strip("/"))
                    self.previewBrowser.append(repr(e))
                    self.previewBrowser.append("Storage resource might be down.")
            else:
                self.previewBrowser.append(
                        "No Preview for: " + "/"+self.inputPath.text().strip("/")+"/"+value.strip("/"))



