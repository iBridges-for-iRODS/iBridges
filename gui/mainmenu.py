from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QDialog, QFileDialog, QApplication, QMainWindow, QMessageBox, QPushButton
from PyQt5.uic import loadUi
from PyQt5 import QtCore
from PyQt5 import QtGui

from gui.popupWidgets import irodsCreateCollection
from gui.irodsBrowser import irodsBrowser
from gui.elabUpload import elabUpload
from gui.irodsSearch import irodsSearch
from gui.irodsUpDownload import irodsUpDownload
from gui.irodsDataCompression import irodsDataCompression
from gui.irodsInfo import irodsInfo
from gui.irodsTicketLogin import irodsTicketLogin
from gui.irodsCreateTicket import irodsCreateTicket
from utils.utils import saveIenv

import sys

class mainmenu(QMainWindow):
    def __init__(self, widget, ic, ienv):
        super(mainmenu, self).__init__()
        loadUi("gui/ui-files/MainMenu.ui", self)

        self.actionExit.triggered.connect(self.programExit)
        self.actionCloseSession.triggered.connect(self.newSession)
        self.widget = widget #stackedWidget

        if ic == None and ienv == None:
            ticketAccessWidget = loadUi("gui/ui-files/tabTicketAccess.ui")
            self.tabWidget.addTab(ticketAccessWidget, "Ticket Access")
            self.ticketAccessTab = irodsTicketLogin()
        else:
            self.ic = ic
            self.ienv = ienv

            # Menu actions
            self.actionSearch.triggered.connect(self.search)
            self.actionSaveConfig.triggered.connect(self.saveConfig)

            #needed for Search
            self.browserWidget = loadUi("gui/ui-files/tabBrowser.ui")
            self.tabWidget.addTab(self.browserWidget, "Browser")
            self.irodsBrowser = irodsBrowser(self.browserWidget, ic)

        
            if ("ui_tabs" in ienv) and (ienv["ui_tabs"] != ""): 

                # Setup up/download tab, index 1
                if ("tabUpDownload" in ienv["ui_tabs"]):
                    updownloadWidget = loadUi("gui/ui-files/tabUpDownload.ui")
                    self.tabWidget.addTab(updownloadWidget, "Up and Download")
                    self.updownload = irodsUpDownload(updownloadWidget, ic, self.ienv)

                # Elabjournal tab, index 2
                if ("tabELNData" in ienv["ui_tabs"]):
                    elabUploadWidget = loadUi("gui/ui-files/tabELNData.ui")
                    self.tabWidget.addTab(elabUploadWidget, "ELN Data upload")
                    self.elnTab = elabUpload(elabUploadWidget, ic)

                # Data compression tab, index 3
                if ("tabDataCompression" in ienv["ui_tabs"]):
                    dataCompressWidget = loadUi("gui/ui-files/tabDataCompression.ui")
                    self.tabWidget.addTab(dataCompressWidget, "Compress/bundle data")
                    self.compressionTab = irodsDataCompression(dataCompressWidget, ic, self.ienv)

                # Grant access by tickets
                if ("tabCreateTicket" in ienv["ui_tabs"]):
                    createTicketWidget = loadUi("gui/ui-files/tabTicketCreate.ui")
                    self.tabWidget.addTab(createTicketWidget, "Create access tokens")
                    self.compressionTab = irodsCreateTicket(createTicketWidget, ic, self.ienv)


            #general info
            self.infoWidget = loadUi("gui/ui-files/tabInfo.ui")
            self.tabWidget.addTab(self.infoWidget, "Info")
            self.irodsInfo = irodsInfo(self.infoWidget, ic)

            self.tabWidget.setCurrentIndex(0)

    #connect functions
    def programExit(self):
        quit_msg = "Are you sure you want to exit the program?"
        reply = QMessageBox.question(self, 'Message', quit_msg, QMessageBox.Yes, QMessageBox.No)
        if reply == QMessageBox.Yes:
            if ic:
                self.ic.session.cleanup()
            sys.exit()
        else:
            pass


    def newSession(self):
        quit_msg = "Are you sure you want to disconnect?"
        reply = QMessageBox.question(self, 'Message', quit_msg, QMessageBox.Yes, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                self.ic.session.cleanup()
            except:
                pass
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


