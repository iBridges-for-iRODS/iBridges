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


class mainmenu(PyQt6.QtWidgets.QMainWindow,
               gui.ui_files.MainMenu.Ui_MainWindow,
               utils.context.ContextContainer):
    def __init__(self, widget):
        super().__init__()
        if getattr(sys, 'frozen', False):
            super().setupUi(self)
        else:
            PyQt6.uic.loadUi('gui/ui_files/MainMenu.ui', self)
        # stackedWidget
        self.widget = widget
        # Menu actions
        self.actionExit.triggered.connect(self.programExit)
        self.actionCloseSession.triggered.connect(self.newSession)
        if not self.ienv or not self.conn:
            self.actionSearch.setEnabled(False)
            # self.actionSaveConfig.setEnabled(False)
            self.ticketAccessTab = gui.irodsTicketLogin.irodsTicketLogin()
            self.tabWidget.addTab(self.ticketAccessTab, 'Ticket Access')
        else:
            self.actionSearch.triggered.connect(self.search)
            self.actionSaveConfig.setEnabled(False)
            # self.actionSaveConfig.triggered.connect(self.saveConfig)
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
            found = set(self.conf.get('ui_tabs', []))
            if not found:
                found = {'tabBrowser', 'tabInfo'}
            else:
                # Ensure browser and info always are shown.
                found = found.union({'tabBrowser', 'tabInfo'})
            expected = ui_tabs_lookup.keys()
            # TODO the browser tabs can take a while.  Use async to
            #      load other tabs at the same time?
            for uitab in expected:
                if uitab in found:
                    ui_tabs_lookup[uitab]()
                    logging.debug(f'Setup the {uitab} tab')
            for uitab in found:
                if uitab not in expected:
                    logging.error(
                        f'Unknown tab "{uitab}" defined in iBridges config file')
                    logging.info(
                        f'Only {", ".join(expected)} tabs supported')
        self.tabWidget.setCurrentIndex(0)

    def setupTabAmberWorkflow(self):
        self.amberTab = gui.amberWorkflow.amberWorkflow()
        self.tabWidget.addTab(self.amberTab, "AmberScript Connection")

    def setupTabBrowser(self):
        # needed for Search
        self.irodsBrowser = gui.IrodsBrowser.IrodsBrowser()
        self.tabWidget.addTab(self.irodsBrowser, 'Browser')

    def setupTabUpDownload(self):
        self.updownload = gui.IrodsUpDownload.IrodsUpDownload()
        self.tabWidget.addTab(self.updownload, "Data Transfers")
        log_handler = QPlainTextEditLogger(self.updownload.logs)
        logging.getLogger().addHandler(log_handler)

    def setupTabELNData(self):
        self.elnTab = gui.elabUpload.elabUpload()
        self.tabWidget.addTab(self.elnTab, "ELN Data upload")

    def setupTabDataBundle(self):
        self.bundleTab = gui.IrodsDataBundle.IrodsDataBundle()
        self.tabWidget.addTab(self.bundleTab, "Compress/bundle data")

    def setupTabCreateTicket(self):
        self.createTicket = gui.irodsCreateTicket.irodsCreateTicket()
        self.tabWidget.addTab(self.createTicket, "Create access tokens")

    def setupTabInfo(self):
        self.irodsInfo = gui.irodsInfo.irodsInfo()
        self.tabWidget.addTab(self.irodsInfo, "Info")

    # Connect functions
    def programExit(self):
        quit_msg = "Are you sure you want to exit the program?"
        reply = PyQt6.QtWidgets.QMessageBox.question(
            self, 'Message', quit_msg,
            PyQt6.QtWidgets.QMessageBox.StandardButton.Yes,
            PyQt6.QtWidgets.QMessageBox.StandardButton.No)
        if reply == PyQt6.QtWidgets.QMessageBox.StandardButton.Yes:
            # connector must be destroyed directly, not a reference to it.
            if self.context.irods_connector:
                del self.context.irods_connector
            elif self.ticketAccessTab.conn:
                self.ticketAccessTab.conn.closeSession()
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
            if self.conn:
                self.context.reset()
            elif self.ticketAccessTab.conn:
                self.ticketAccessTab.conn.close_session()
            currentWidget = self.widget.currentWidget()
            self.widget.setCurrentIndex(self.widget.currentIndex()-1)
            self.widget.removeWidget(currentWidget)
            currentWidget = self.widget.currentWidget()
            #currentWidget._init_envbox()
        else:
            pass

    def search(self):
        search = gui.irodsSearch.irodsSearch(self.irodsBrowser.collTable)
        search.exec()

    def saveConfig(self):
        print("TODO")
        # TODO is there any reason for this?
        # self.context.save_ibridges_configuration()
        # self.context.save_irods_environment()
        # self.globalErrorLabel.setText(f'Environment saved to: {self.context.irods_env_file}')

    def exportMeta(self):
        print("TODO: Metadata export")
