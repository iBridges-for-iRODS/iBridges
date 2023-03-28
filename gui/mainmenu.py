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
            ui_tabs_lookup = {
                'tabBrowser': self.setupTabBrowser,
                'tabUpDownload': self.setupTabUpDownload,
                'tabELNData': self.setupTabELNData,
                'tabDataBundle': self.setupTabDataBundle,
                'tabCreateTicket': self.setupTabCreateTicket,
                'tabAmberWorkflow': self.setupTabAmberWorkflow,
                'tabInfo': self.setupTabInfo,
            }
            found = ienv.get('ui_tabs', False)
            if not found:
                found = set(['tabBrowser', 'tabInfo'])
            else:
                # Ensure browser and info always are shown.
                found = set(found + ['tabBrowser', 'tabInfo'])
            expected = ui_tabs_lookup.keys()
            # TODO the browser tabs can take a while.  Use async to
            #      load other tabs at the same time?
            for uitab in expected:
                if uitab in found:
                    ui_tabs_lookup[uitab](ic, ienv)
                    logging.debug(f'Setup the {uitab} tab')
            for uitab in found:
                if uitab not in expected:
                    logging.error(
                        f'Unknown tab "{uitab}" defined in iBridges config file')
                    logging.info(
                        f'Only {", ".join(expected)} tabs supported')
        self.tabWidget.setCurrentIndex(0)


    def setupTabAmberWorkflow(self, ic, ienv):
        self.amberTab = gui.amberWorkflow.amberWorkflow(ic, ienv)
        self.tabWidget.addTab(self.amberTab, "AmberScript Connection")


    def setupTabBrowser(self, ic, ienv):
        # needed for Search
        self.irodsBrowser = gui.IrodsBrowser.IrodsBrowser(ic)
        self.tabWidget.addTab(self.irodsBrowser, 'Browser')

    def setupTabUpDownload(self, ic, ienv):
        self.updownload = gui.IrodsUpDownload.IrodsUpDownload(ic, self.ienv)
        self.tabWidget.addTab(self.updownload, "Data Transfers")
        log_handler = QPlainTextEditLogger(self.updownload.logs)
        logging.getLogger().addHandler(log_handler)

    def setupTabELNData(self, ic, ienv):
        self.elnTab = gui.elabUpload.elabUpload(ic, ienv)
        self.tabWidget.addTab(self.elnTab, "ELN Data upload")

    def setupTabDataBundle(self, ic, ienv):
        self.bundleTab = gui.IrodsDataBundle.IrodsDataBundle(ic, self.ienv)
        self.tabWidget.addTab(self.bundleTab, "Compress/bundle data")

    def setupTabCreateTicket(self, ic, ienv):
        self.createTicket = gui.irodsCreateTicket.irodsCreateTicket(ic)
        self.tabWidget.addTab(self.createTicket, "Create access tokens")

    def setupTabInfo(self, ic, ienv):
        self.irodsInfo = gui.irodsInfo.irodsInfo(ic)
        self.tabWidget.addTab(self.irodsInfo, "Info")

    # Connect functions
    def programExit(self):
        quit_msg = "Are you sure you want to exit the program?"
        reply = PyQt6.QtWidgets.QMessageBox.question(
            self, 'Message', quit_msg,
            PyQt6.QtWidgets.QMessageBox.StandardButton.Yes,
            PyQt6.QtWidgets.QMessageBox.StandardButton.No)
        if reply == PyQt6.QtWidgets.QMessageBox.StandardButton.Yes:
            if self.ic:
                self.ic.cleanup()
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
                self.ic.cleanup()
            elif self.ticketAccessTab.ic:
                self.ticketAccessTab.ic.close_session()
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
        print("TODO")
        #path = utils.utils.save_irods_env(self.ienv)
        #self.globalErrorLabel.setText("Environment saved to: "+path)

    def exportMeta(self):
        print("TODO: Metadata export")
