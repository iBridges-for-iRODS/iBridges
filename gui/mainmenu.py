"""Main menu window definition

"""
import PyQt6
import PyQt6.QtWidgets
import PyQt6.uic



from PyQt6 import QtWidgets
from PyQt6.QtWidgets import QDialog, QFileDialog, QApplication, QMainWindow, QMessageBox, QPushButton
from PyQt6.uic import loadUi
from PyQt6 import QtCore
from PyQt6 import QtGui

from gui.IrodsBrowser import IrodsBrowser
from gui.elabUpload import elabUpload
from gui.irodsSearch import irodsSearch
from gui.IrodsUpDownload import IrodsUpDownload
from gui.IrodsDataBundle import IrodsDataBundle
from gui.irodsInfo import irodsInfo
from gui.irodsCreateTicket import irodsCreateTicket
from gui.irodsTicketLogin import irodsTicketLogin
from utils.utils import saveIenv

import sys


class mainmenu(QMainWindow):
    def __init__(self, widget, ic, ienv):
        super(mainmenu, self).__init__()
        loadUi('gui/ui-files/MainMenu.ui', self)
        self.ic = ic
        # stackedWidget
        self.widget = widget
        self.ienv = ienv

        # Menu actions
        self.actionExit.triggered.connect(self.programExit)
        self.actionCloseSession.triggered.connect(self.newSession)

        if not ienv or not ic:
            self.actionSearch.setEnabled(False)
            self.actionSaveConfig.setEnabled(False)
            ticketAccessWidget = loadUi('gui/ui-files/tabTicketAccess.ui')
            self.tabWidget.addTab(ticketAccessWidget, 'Ticket Access')
            self.ticketAccessTab = irodsTicketLogin(ticketAccessWidget)

        else:
            self.actionSearch.triggered.connect(self.search)
            self.actionSaveConfig.triggered.connect(self.saveConfig)
            # self.actionExportMetadata.triggered.connect(self.exportMeta)

            # tabBrowser needed for Search
            self.browserWidget = loadUi('gui/ui-files/tabBrowser.ui')
            self.tabWidget.addTab(self.browserWidget, 'Browser')
            self.irodsBrowser = IrodsBrowser(self.browserWidget, ic)
            # Optional tabs
            if ('ui_tabs' in ienv) and (ienv['ui_tabs'] != []):
                # Setup up/download tab, index 1
                if 'tabUpDownload' in ienv['ui_tabs']:
                    updownloadWidget = loadUi('gui/ui-files/tabUpDownload.ui')
                    self.tabWidget.addTab(updownloadWidget, 'Up and Download')
                    self.updownload = IrodsUpDownload(updownloadWidget, ic, self.ienv)
                # Elabjournal tab, index 2
                if 'tabELNData' in ienv['ui_tabs']:
                    elabUploadWidget = loadUi('gui/ui-files/tabELNData.ui')
                    self.tabWidget.addTab(elabUploadWidget, 'ELN Data upload')
                    self.elnTab = elabUpload(elabUploadWidget, ic)
                # Data (un)bundle tab, index 3
                if 'tabDataBundle' in ienv['ui_tabs']:
                    dataBundleWidget = loadUi('gui/ui-files/tabDataBundle.ui')
                    self.tabWidget.addTab(dataBundleWidget, '(Un)Bundle data')
                    self.bundleTab = IrodsDataBundle(dataBundleWidget, ic, self.ienv)
                # Grant access by tickets, index 4
                if 'tabCreateTicket' in ienv['ui_tabs']:
                    createTicketWidget = loadUi('gui/ui-files/tabTicketCreate.ui')
                    self.tabWidget.addTab(createTicketWidget, 'Create access tokens')
                    self.createTicket = irodsCreateTicket(createTicketWidget, ic, self.ienv)
            # General info
            self.infoWidget = loadUi('gui/ui-files/tabInfo.ui')
            self.tabWidget.addTab(self.infoWidget, 'Info')
            self.irodsInfo = irodsInfo(self.infoWidget, ic)

            self.tabWidget.setCurrentIndex(0)

    # Connect functions
    def programExit(self):
        quit_msg = "Are you sure you want to exit the program?"
        reply = QMessageBox.question(self, 'Message', quit_msg, QMessageBox.StandardButton.Yes, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            if self.ic:
                self.ic.session.cleanup()
            elif self.ticketAccessTab.ic:
                self.ticketAccessTab.ic.closeSession()
            sys.exit()
        else:
            pass


    def newSession(self):
        quit_msg = "Are you sure you want to disconnect?"
        reply = QMessageBox.question(self, 'Message', quit_msg, QMessageBox.StandardButton.Yes, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            if self.ic:
                self.ic.session.cleanup()
            elif self.ticketAccessTab.ic:
                self.ticketAccessTab.ic.closeSession()
            currentWidget = self.widget.currentWidget()
            self.widget.setCurrentIndex(self.widget.currentIndex()-1)
            self.widget.removeWidget(currentWidget)
            currentWidget = self.widget.currentWidget()
            currentWidget.init_envbox()
        else:
            pass

    def search(self):
        search = irodsSearch(self.ic, self.browserWidget.collTable)
        search.exec()


    def saveConfig(self):
        path = saveIenv(self.ienv)
        self.globalErrorLabel.setText("Environment saved to: "+path)

    def exportMeta(self):
        print("TODO: Metadata export")

