from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QDialog, QFileDialog, QApplication, QMainWindow, QMessageBox, QPushButton
from PyQt5.uic import loadUi
from PyQt5 import QtCore
from PyQt5 import QtGui

from popupWidgets import irodsCreateCollection

from irodsBrowser import irodsBrowser
from elabUpload import elabUpload
from irodsSearch import irodsSearch
from irodsUpDownload import irodsUpDownload
from irodsDataCompression import irodsDataCompression
from utils import saveIenv

import sys

class mainmenu(QMainWindow):
    def __init__(self, widget, ic, ienv):
        super(mainmenu, self).__init__()
        loadUi("ui-files/MainMenu.ui", self)
        self.ic = ic
        self.widget = widget #stackedWidget
        self.ienv = ienv

        # Menu actions
        self.actionExit.triggered.connect(self.programExit)
        self.actionCloseSession.triggered.connect(self.newSession)
        self.actionSearch.triggered.connect(self.search)
        self.actionSaveConfig.triggered.connect(self.saveConfig)
        #self.actionExportMetadata.triggered.connect(self.exportMeta)

        #needed for Search
        self.browserWidget = loadUi("ui-files/tabBrowser.ui")
        self.tabWidget.addTab(self.browserWidget, "Browser")
        self.irodsBrowser = irodsBrowser(self.browserWidget, ic)

        
        if ("ui_tabs" in ienv) and (ienv["ui_tabs"] != ""): 

            # Setup up/download tab, index 1
            if ("tabUpDownload" in ienv["ui_tabs"]):
                updownloadWidget = loadUi("ui-files/tabUpDownload.ui")
                self.tabWidget.addTab(updownloadWidget, "Up and Download")
                self.updownload = irodsUpDownload(updownloadWidget, ic, self.ienv)

            # Elabjournal tab, index 2
            if ("tabELNData" in ienv["ui_tabs"]):
                elabUploadWidget = loadUi("ui-files/tabELNData.ui")
                self.tabWidget.addTab(elabUploadWidget, "ELN Data upload")
                self.elnTab = elabUpload(elabUploadWidget, ic)

            # Data compression tab, index 3
            if ("tabDataCompression" in ienv["ui_tabs"]):
                dataCompressWidget = loadUi("ui-files/tabDataCompression.ui")
                self.tabWidget.addTab(dataCompressWidget, "Compress/bundle data")
                self.compressionTab = irodsDataCompression(dataCompressWidget, ic, self.ienv)

            # iRODS federation tab, index 4
            ## TODO
            #if ("tabFederations" in ienv["ui_tabs"]):
            #FederationsWidget = loadUi("ui-files/tabFederations.ui")
            #self.tabWidget.addTab(FederationsWidget, "Federations")
            #self.elnTab = Federations(FederationsWidget, ic)

            ## TODO page, index 5
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
            currentWidget = self.widget.currentWidget()
            currentWidget.init_envbox()
        else:
            pass

    def search(self):
        search = irodsSearch(self.ic, self.browserWidget.collTable)
        search.exec_()


    def saveConfig(self):
        path = saveIenv(self.ienv)
        self.globalErrorLabel.setText("Environment saved to: "+path)

    def exportMeta(self):
        print("TODO: Metadata export")


