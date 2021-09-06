from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QDialog, QFileDialog, QApplication, QMainWindow, QMessageBox, QPushButton
from PyQt5.uic import loadUi
from PyQt5 import QtCore
from PyQt5 import QtGui

from irodsCreateCollection import irodsCreateCollection
from irodsUtils import walkToDict, getDownloadDir 

from irodsBrowser import irodsBrowser
from elabUpload import elabUpload
from irodsSearch import irodsSearch
from irodsUpDownload import irodsUpDownload

import sys

class irodsTabview(QMainWindow):
    def __init__(self, widget, ic, hideTabs = []):
        super(irodsTabview, self).__init__()
        loadUi("ui-files/irodsBrowserMain.ui", self)
        self.ic = ic
        self.widget = widget #stackedWidget

        self.tabWidget.setCurrentIndex(0)
        #hide tabs
        for tab in hideTabs:
            self.tabWidget.setTabVisible(tab, False)

        # Menu actions
        self.actionExit.triggered.connect(self.programExit)
        self.actionCloseSession.triggered.connect(self.newSession)
        self.actionSearch.triggered.connect(self.search)
        self.actionExportMetadata.triggered.connect(self.exportMeta)


        # iRODS collection browser tab, index 0
        if 0 not in hideTabs:
            self.irodsBrowser = irodsBrowser(self, ic)
            self.tabWidget.setCurrentIndex(0)

        # Setup up/download tab, index 1
        if 1 not in hideTabs:
            self.updownload = irodsUpDownload(self, ic)


        # Elabjournal tab, index 2
        if 2 not in hideTabs:
            self.elnTab = elabUpload(
                    self.ic, self.globalErrorLabel, self.elnTokenInput,
                    self.elnGroupTable, self.elnExperimentsTable, self.groupIdLabel,
                    self.experimentIdLabel, self.localFsTable,
                    self.elnUploadButton, self.elnPreviewBrowser, self.elnIrodsPath
                    )

        # iRODS federation tab, index 3
        #TODO

        # Setup test tab 4
        if 4 not in hideTabs:
            self.test = testIrodsFS(self, ic)


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
            #self.loadTable()

        else:
            pass

    def search(self):
        search = irodsSearch(self.ic, self.collTable)
        search.exec_()
        #search.search()


    def exportMeta(Self):
        print("TODO: search")


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


