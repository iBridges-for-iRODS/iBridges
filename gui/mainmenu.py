import sys
from PyQt6.QtWidgets import QMainWindow, QMessageBox
from PyQt6.uic import loadUi

from gui.irodsBrowser import irodsBrowser
from gui.elabUpload import elabUpload
from gui.irodsSearch import irodsSearch
from gui.irodsUpDownload import irodsUpDownload
from gui.irodsDataCompression import irodsDataCompression
from gui.irodsInfo import irodsInfo
from gui.irodsCreateTicket import irodsCreateTicket
from gui.irodsTicketLogin import irodsTicketLogin
from gui.ui_files.MainMenu import Ui_MainWindow
from utils.utils import saveIenv

import sys
import logging

class QPlainTextEditLogger(logging.Handler):
    def __init__(self, widget):
        super(QPlainTextEditLogger, self).__init__()

        self.widget = widget
        self.widget.setReadOnly(True)

    def emit(self, record):
        msg = self.format(record)
        self.widget.appendPlainText(msg)

    def write(self, m):
        pass

class mainmenu(QMainWindow, Ui_MainWindow):
    def __init__(self, widget, ic, ienv):
        super(mainmenu, self).__init__()
        if getattr(sys, 'frozen', False):
            super(mainmenu, self).setupUi(self)
        else:
            loadUi("gui/ui_files/MainMenu.ui", self)
        self.ic = ic
        self.widget = widget  # stackedWidget
        self.ienv = ienv

        # Menu actions
        self.actionExit.triggered.connect(self.programExit)
        self.actionCloseSession.triggered.connect(self.newSession)

        if not ienv or not ic:
            self.actionSearch.setEnabled(False)
            self.actionSaveConfig.setEnabled(False)
            self.ticketAccessTab = irodsTicketLogin()
            self.tabWidget.addTab(self.ticketAccessTab, "Ticket Access")
        else:
            self.actionSearch.triggered.connect(self.search)
            self.actionSaveConfig.triggered.connect(self.saveConfig)
            # self.actionExportMetadata.triggered.connect(self.exportMeta)

            # needed for Search
            self.irodsBrowser = irodsBrowser(ic)
            self.tabWidget.addTab(self.irodsBrowser, "Browser")

            ui_tabs_lookup = {
                "tabUpDownload": self.setupTabUpDownload,
                "tabELNData": self.setupTabELNData,
                "tabDataCompression": self.setupTabDataCompression,
                "tabCreateTicket": self.setupTabCreateTicket
            }

            if ("ui_tabs" in ienv) and (ienv["ui_tabs"] != ""): 
                # Setup up/download tab, index 1
                for tab in ienv["ui_tabs"]:
                    if tab in ui_tabs_lookup:
                        ui_tabs_lookup[tab](ic)
                    else:
                        logging.error("Unknown tab \"{uitab}\" defined in irods environment file".format(uitab=tab))

            # general info
            self.irodsInfo = irodsInfo(ic)
            self.tabWidget.addTab(self.irodsInfo, "Info")
            self.tabWidget.setCurrentIndex(0)

    def setupTabCreateTicket(self, ic):
        self.createTicket = irodsCreateTicket(ic, self.ienv)
        self.tabWidget.addTab(self.createTicket, "Create access tokens")

    def setupTabDataCompression(self, ic):
        self.compressionTab = irodsDataCompression(ic, self.ienv)
        self.tabWidget.addTab(self.compressionTab, "Compress/bundle data")

    def setupTabELNData(self, ic):
        self.elnTab = elabUpload(ic)
        self.tabWidget.addTab(self.elnTab, "ELN Data upload")

    def setupTabUpDownload(self, ic):
        self.updownload = irodsUpDownload(ic, self.ienv)
        self.tabWidget.addTab(self.updownload, "Data Transfers")
        log_handler = QPlainTextEditLogger(self.updownload.logs)
        logging.getLogger().addHandler(log_handler)

    # connect functions
    def programExit(self):
        quit_msg = "Are you sure you want to exit the program?"
        reply = QMessageBox.question(self, 'Message', quit_msg, QMessageBox.StandardButton.Yes,
                                     QMessageBox.StandardButton.No)
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
        reply = QMessageBox.question(self, 'Message', quit_msg, QMessageBox.StandardButton.Yes,
                                     QMessageBox.StandardButton.No)
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
        search = irodsSearch(self.ic, self.irodsBrowser.collTable)
        search.exec()

    def saveConfig(self):
        path = saveIenv(self.ienv)
        self.globalErrorLabel.setText("Environment saved to: "+path)

    def exportMeta(self):
        print("TODO: Metadata export")
