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
            # Browser tab needed for Search
            self.irodsBrowser = gui.IrodsBrowser.IrodsBrowser(ic)
            self.tabWidget.addTab(self.irodsBrowser, 'Browser')
            # Optional tabs
            if ('ui_tabs' in ienv) and (ienv['ui_tabs'] != []):
                # Setup up/download tab, index 1
                if 'tabUpDownload' in ienv['ui_tabs']:
                    self.updownload = gui.IrodsUpDownload.IrodsUpDownload(
                        ic, self.ienv)
                    self.tabWidget.addTab(self.updownload, "Data Transfers")
                    log_handler = QPlainTextEditLogger(self.updownload.logs)
                    logging.getLogger().addHandler(log_handler)
                # Elabjournal tab, index 2
                if 'tabELNData' in ienv['ui_tabs']:
                    self.elnTab = gui.elabUpload.elabUpload(ic)
                    self.tabWidget.addTab(self.elnTab, "ELN Data upload")
                # Data (un)bundle tab, index 3
                if 'tabDataBundle' in ienv['ui_tabs']:
                    self.bundleTab = gui.IrodsDataBundle.IrodsDataBundle(ic, self.ienv)
                    self.tabWidget.addTab(self.bundleTab, "(Un)Bundle data")
                # Grant access by tickets, index 4
                if 'tabCreateTicket' in ienv['ui_tabs']:
                    self.createTicket = gui.irodsCreateTicket.irodsCreateTicket(ic, self.ienv)
                    self.tabWidget.addTab(self.createTicket, "Create access tokens")
            # General info
            self.irodsInfo = gui.irodsInfo.irodsInfo(ic)
            self.tabWidget.addTab(self.irodsInfo, 'Info')
            self.tabWidget.setCurrentIndex(0)

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
            currentWidget.init_envbox()
        else:
            pass

    def search(self):
        search = gui.irodsSearch.irodsSearch(
            self.ic, self.irodsBrowser.collTable)
        search.exec()

    def saveConfig(self):
        path = utils.utils.saveIenv(self.ienv)
        self.globalErrorLabel.setText("Environment saved to: "+path)

    def exportMeta(self):
        print("TODO: Metadata export")
