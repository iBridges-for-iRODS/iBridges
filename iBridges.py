#!/usr/bin/env python3
"""iBridges GUI startup script.

"""
import logging
import os
import setproctitle
import subprocess
import sys

import irods.exception
import PyQt6.QtCore
import PyQt6.QtGui
import PyQt6.QtWidgets
import PyQt6.uic

import gui
from irodsConnector.manager import IrodsConnector
import utils

app = PyQt6.QtWidgets.QApplication(sys.argv)
widget = PyQt6.QtWidgets.QStackedWidget()

# Work around a PRC XML issue handling special characters
os.environ['PYTHON_IRODSCLIENT_DEFAULT_XML'] = 'QUASI_XML'

class IrodsLoginWindow(PyQt6.QtWidgets.QDialog, gui.ui_files.irodsLogin.Ui_irodsLogin):
    """Definition and initialization of the iRODS login window.

    """

    this_application = 'iBridges'

    def __init__(self):
        super().__init__()
        self.icommands = False
        self._load_gui()
        self._init_configs_and_logging()
        self._init_envbox()
        self._init_password()

    def _load_gui(self):
        """

        """
        if getattr(sys, 'frozen', False):
            super().setupUi(self)
        else:
            PyQt6.uic.loadUi("gui/ui_files/irodsLogin.ui", self)
        self.selectIcommandsButton.toggled.connect(self.setup_icommands)
        self.standardButton.toggled.connect(self.setup_standard)
        self.connectButton.clicked.connect(self.login_function)
        self.ticketButton.clicked.connect(self.ticket_login)
        self.passwordField.setEchoMode(PyQt6.QtWidgets.QLineEdit.EchoMode.Password)

    def _init_configs_and_logging(self):
        """

        """
        # iBridges configuration
        ibridges_path = utils.utils.LocalPath(
            os.path.join('~', '.ibridges')).expanduser()
        if not ibridges_path.is_dir():
            ibridges_path.mkdir(parents=True)
        self.ibridges_config = ibridges_path.joinpath('ibridges_config.json')
        self.ibridges = utils.utils.JsonConfig(self.ibridges_config)
        if self.ibridges.config is None:
            self.ibridges.config = {}
        # iRODS configuration (environment)
        self.irods = None
        self.irods_path = utils.utils.LocalPath(
            os.path.join('~', '.irods')).expanduser()
        if not self.irods_path.is_dir():
            self.irods_path.mkdir(parents=True)
        # iBridges logging
        utils.utils.setup_logger(ibridges_path, 'iBridges')

    def _init_envbox(self):
        """Populate environment drop-down.

        """
        env_jsons = [
            path.name for path in
            self.irods_path.glob('irods_environment*json')]
        if len(env_jsons) == 0:
            self.envError.setText(f'ERROR: no "irods_environment*json" files found in {self.irods_path}')
        self.envbox.clear()
        self.envbox.addItems(env_jsons)
        conf = self.ibridges.config
        envname = ''
        if 'last_ienv' in conf and conf['last_ienv'] in env_jsons:
            envname = conf['last_ienv']
        elif 'irods_environment.json' in env_jsons:
            envname = 'irods_environment.json'
        index = 0
        if envname:
            index = self.envbox.findText(envname)
        self.envbox.setCurrentIndex(index)

    def _init_password(self):
        """

        """
        conn = IrodsConnector()
        if conn.password:
            self.passwordField.setText(conn.password)

    def _reset_mouse_and_error_labels(self):
        """Reset cursor and clear error text

        """
        self.setCursor(PyQt6.QtGui.QCursor(PyQt6.QtCore.Qt.CursorShape.ArrowCursor))
        self.passError.setText('')
        self.envError.setText('')

    def setup_standard(self):
        """Check the state of the radio button for using the pure Python
        client.

        """
        if self.standardButton.isChecked():
            self._init_envbox()
            self.icommands = False

    def setup_icommands(self):
        """Check the state of the radio button for using iCommands.
        This includes a check for the existance of the iCommands on the
        current system.

        """
        if self.selectIcommandsButton.isChecked():
            self.icommandsError.setText('')
            with open(os.devnull, 'w', encoding='utf-8') as devnull:
                icommands_exist = subprocess.call(
                    ['which', 'iinit'], stdout=devnull, stderr=devnull) == 0
            if icommands_exist:
                self.icommands = True
                # TODO support arbitrary iRODS environment file for iCommands
            else:
                self.icommandsError.setText('ERROR: no iCommands found')
                self.standardButton.setChecked(True)

    def login_function(self):
        """Check connectivity and log in to iRODS handling common errors.

        """
        irods_env_file = self.irods_path.joinpath(self.envbox.currentText())
        # TODO expand JsonConfig usage to all relevant modules
        ienv = utils.utils.JsonConfig(irods_env_file).config
        if ienv is None:
            self.passError.clear()
            self.envError.setText('ERROR: iRODS environment file not found.')
            self.setCursor(PyQt6.QtGui.QCursor(PyQt6.QtCore.Qt.CursorShape.ArrowCursor))
            return
        if 'irods_host' in ienv and not utils.utils.can_connect(ienv['irods_host']):
            logging.info('iRODS login: No network connection to server')
            self.envError.setText('No network connection to server')
            self.setCursor(PyQt6.QtGui.QCursor(PyQt6.QtCore.Qt.CursorShape.ArrowCursor))
            return
        self.setCursor(PyQt6.QtGui.QCursor(PyQt6.QtCore.Qt.CursorShape.WaitCursor))
        password = self.passwordField.text()
        conn = IrodsConnector(irods_env_file=irods_env_file, password=password)
        # Add own filepath for easy saving.
        config = self.ibridges.config
        config['ui_ienvFilePath'] = irods_env_file
        config['last_ienv'] = irods_env_file.name
        # Save iBridges config to disk and combine with iRODS config.
        self.ibridges.config = config
        # TODO consider passing separate configurations or rename
        #  `ienv` to reflect common nature
        ienv.update(config)
        try:
            # widget is a global variable
            browser = gui.mainmenu(widget, conn, ienv)
            if len(widget) == 1:
                widget.addWidget(browser)
            self._reset_mouse_and_error_labels()
            # self.setCursor(PyQt6.QtGui.QCursor(PyQt6.QtCore.Qt.CursorShape.ArrowCursor))
            widget.setCurrentIndex(widget.currentIndex()+1)
        except (irods.exception.CAT_INVALID_AUTHENTICATION,
                irods.exception.PAM_AUTH_PASSWORD_FAILED,
                ConnectionRefusedError):
            self.envError.clear()
            self.passError.setText('ERROR: Wrong password.')
            self.setCursor(PyQt6.QtGui.QCursor(PyQt6.QtCore.Qt.CursorShape.ArrowCursor))
        except irods.exception.CAT_PASSWORD_EXPIRED:
            self.envError.clear()
            self.passError.setText('ERROR: Cached password expired. Re-enter password.')
            self.setCursor(PyQt6.QtGui.QCursor(PyQt6.QtCore.Qt.CursorShape.ArrowCursor))
        except irods.exception.NetworkException:
            self.passError.clear()
            self.envError.setText('iRODS server ERROR: iRODS server down.')
            self.setCursor(PyQt6.QtGui.QCursor(PyQt6.QtCore.Qt.CursorShape.ArrowCursor))
        except Exception as unknown:
            message = f'Something went wrong: {unknown}'
            logging.exception(message)
            # logging.info(repr(error))
            self.envError.setText(message)
            self.setCursor(PyQt6.QtGui.QCursor(PyQt6.QtCore.Qt.CursorShape.ArrowCursor))

    def ticket_login(self):
        """Log in to iRODS using a ticket.

        """
        # widget is a global variable
        browser = gui.mainmenu(widget, None, None)
        browser.menuOptions.clear()
        browser.menuOptions.deleteLater()
        if len(widget) == 1:
            widget.addWidget(browser)
        self._reset_mouse_and_error_labels()
        # self.setCursor(PyQt6.QtGui.QCursor(PyQt6.QtCore.Qt.CursorShape.ArrowCursor))
        widget.setCurrentIndex(widget.currentIndex()+1)

def closeClean():
    activeWidget = widget.currentWidget()
    try:
        activeWidget.ic.cleanup()
    except:
        pass

def main():
    """Main function

    """
    setproctitle.setproctitle('iBridges')
    login_window = IrodsLoginWindow()
    widget.addWidget(login_window)
    widget.show()
    #app.setQuitOnLastWindowClosed(False)
    app.lastWindowClosed.connect(closeClean)
    app.exec()


if __name__ == "__main__":
    main()
