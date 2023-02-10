"""Main menu window definition

"""
import logging
import sys

import PyQt6
import PyQt6.QtWidgets
import PyQt6.uic

import gui
import utils


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


class mainmenu(PyQt6.QtWidgets.QMainWindow, gui.ui_files.MainMenu.Ui_MainWindow):
    def __init__(self, widget, ic, ienv):
        super().__init__()
        if getattr(sys, 'frozen', False):
            super().setupUi(self)
        else:
            PyQt6.uic.loadUi('gui/ui_files/MainMenu.ui', self)
        self.ic = ic
        # stackedWddidget
        self.widget = widget
        self.ienv = ienv
        # Menu actions
        self.actionExit.triggered.connect(self.programExit)
        self.actionCloseSession.triggered.connect(self.newSession)
        if not ienv or not ic:
            self.actionSearch.setEnabled(False)
            self.actionSaveConfig.setEnabled(False)
            self.ticketAccessTab = gui.irodsTicketLogin.irodsTicketLogin()
            self.tabWidget.addTab(self.ticketAccessTab, 'Ticket Access')
        else:
            self.actionSearch.triggered.connect(self.search)
            self.actionSaveConfig.triggered.connect(self.saveConfig)
            # self.actionExportMetadata.triggered.connect(self.exportMeta)
            # needed for Search
            self.irodsBrowser = gui.IrodsBrowser.IrodsBrowser(ic)
            self.tabWidget.addTab(self.irodsBrowser, "Browser")
            ui_tabs_lookup = {
                "tabUpDownload": self.setupTabUpDownload,
                "tabELNData": self.setupTabELNData,
                "tabDataBundle": self.setupTabDataBundle,
                "tabCreateTicket": self.setupTabCreateTicket,
            }
            if ("ui_tabs" in ienv) and (ienv["ui_tabs"] != ""):
                # Setup up/download tab, index 1
                for tab in ienv["ui_tabs"]:
                    if tab in ui_tabs_lookup:
                        ui_tabs_lookup[tab](ic)
                    else:
                        logging.error("Unknown tab \"{uitab}\" defined in irods environment file".format(uitab=tab))

            # general info
            self.irodsInfo = gui.irodsInfo.irodsInfo(ic)
            self.tabWidget.addTab(self.irodsInfo, "Info")
            self.tabWidget.setCurrentIndex(0)

    def setupTabCreateTicket(self, ic):
        self.createTicket = gui.irodsCreateTicket.irodsCreateTicket(ic, self.ienv)
        self.tabWidget.addTab(self.createTicket, "Create access tokens")

    def setupTabDataBundle(self, ic):
        self.bundleTab = gui.IrodsDataBundle.IrodsDataBundle(ic, self.ienv)
        self.tabWidget.addTab(self.bundleTab, "Compress/bundle data")

    def setupTabELNData(self, ic):
        self.elnTab = gui.elabUpload.elabUpload(ic)
        self.tabWidget.addTab(self.elnTab, "ELN Data upload")

    def setupTabUpDownload(self, ic):
        self.updownload = gui.IrodsUpDownload.IrodsUpDownload(
                        ic, self.ienv)
        self.tabWidget.addTab(self.updownload, "Data Transfers")
        log_handler = QPlainTextEditLogger(self.updownload.logs)
        logging.getLogger().addHandler(log_handler)

    # Connect functions
    def programExit(self):
        quit_msg = "Are you sure you want to exit the program?"
        reply = PyQt6.QtWidgets.QMessageBox.question(
            self, 'Message', quit_msg,
            PyQt6.QtWidgets.QMessageBox.StandardButton.Yes,
            PyQt6.QtWidgets.QMessageBox.StandardButton.No)
        if reply == PyQt6.QtWidgets.QMessageBox.StandardButton.Yes:
            if self.ic:
                self.ic.session.cleanup()
            elif self.ticketAccessTab.ic:
                self.ticketAccessTab.ic.closeSession()
            sys.exit()
        else:
            pass

    def newSession(self):
        quit_msg = "Are you sure you want to disconnect?"
        reply = PyQt6.QtWidgets.QMessageBox.question(
            self, 'Message', quit_msg,
            PyQt6.QtWidgets.QMessageBox.StandardButton.Yes,
            PyQt6.QtWidgets.QMessageBox.StandardButton.No)
        if reply == PyQt6.QtWidgets.QMessageBox.StandardButton.Yes:
            if self.ic:
                self.ic.session.cleanup()
            elif self.ticketAccessTab.ic:
                self.ticketAccessTab.ic.closeSession()
            currentWidget = self.widget.currentWidget()
            self.widget.setCurrentIndex(self.widget.currentIndex()-1)
            self.widget.removeWidget(currentWidget)
            currentWidget = self.widget.currentWidget()
            #currentWidget._init_envbox()
        else:
            pass

    def search(self):
        search = gui.irodsSearch.irodsSearch(
            self.ic, self.irodsBrowser.collTable)
        search.exec()

    def saveConfig(self):
        path = utils.utils.save_irods_env(self.ienv)
        self.globalErrorLabel.setText("Environment saved to: "+path)

    def exportMeta(self):
        print("TODO: Metadata export")
