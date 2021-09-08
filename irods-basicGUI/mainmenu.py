from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QDialog, QFileDialog, QApplication, QMainWindow, QMessageBox, QPushButton
from PyQt5.uic import loadUi
from PyQt5 import QtCore
from PyQt5 import QtGui

from irodsCreateCollection import irodsCreateCollection
from utils import walkToDict, getDownloadDir 

from irodsBrowser import irodsBrowser
from elabUpload import elabUpload
from irodsSearch import irodsSearch
from UpDownload import irodsUpDownload

import sys

class mainmenu(QMainWindow):
    def __init__(self, widget, ic, ienv):
        super(mainmenu, self).__init__()
        loadUi("ui-files/MainMenu.ui", self)
        self.ic = ic
        self.widget = widget #stackedWidget

        # Menu actions
        self.actionExit.triggered.connect(self.programExit)
        self.actionCloseSession.triggered.connect(self.newSession)
        self.actionSearch.triggered.connect(self.search)
        self.actionExportMetadata.triggered.connect(self.exportMeta)

        
        if ("ui_tabs" in ienv) and (ienv["ui_tabs"] != ""): 
            # iRODS collection browser tab, index 0
            if("tabBrowser" in ienv["ui_tabs"]):
                browserWidget = loadUi("ui-files/tabBrowser.ui")
                self.tabWidget.addTab(browserWidget, "Browser")
                self.irodsBrowser = irodsBrowser(browserWidget, ic)

            # Setup up/download tab, index 1
            if ("tabUpDownload" in ienv["ui_tabs"]):
                updownloadWidget = loadUi("ui-files/tabUpDownload.ui")
                self.tabWidget.addTab(updownloadWidget, "Up and Download")
                self.updownload = irodsUpDownload(updownloadWidget, ic, ienv)

            # Elabjournal tab, index 2
            if ("tabELNData" in ienv["ui_tabs"]):
                elabUploadWidget = loadUi("ui-files/tabELNData.ui")
                self.tabWidget.addTab(elabUploadWidget, "ELN Data upload")
                self.elnTab = elabUpload(elabUploadWidget, ic)

            # iRODS federation tab, index 3
            ## TODO
            #if ("tabFederations" in ienv["ui_tabs"]):
            #FederationsWidget = loadUi("ui-files/tabFederations.ui")
            #self.tabWidget.addTab(FederationsWidget, "Federations")
            #self.elnTab = Federations(FederationsWidget, ic)

            ## TODO page, index 4
            #if ("tabPage" in ienv["ui_tabs"]):
            #PageWidget = loadUi("ui-files/tabPage.ui")
            #self.tabWidget.addTab(FederationsWidget, "Federations")
            #self.elnTab = Federations(FederationsWidget, ic)        
        
        self.tabWidget.setCurrentIndex(0)

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


