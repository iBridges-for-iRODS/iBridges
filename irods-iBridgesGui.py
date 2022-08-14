#!/usr/bin/env python3
"""iBridges GUI startup script.

"""
import json
import logging
import os
import subprocess
import sys

import irods.exception
import PyQt5
import PyQt5.QtWidgets
import PyQt5.uic

import gui
import utils

app = PyQt5.QtWidgets.QApplication(sys.argv)
widget = PyQt5.QtWidgets.QStackedWidget()


class IrodsLoginWindow(PyQt5.QtWidgets.QDialog):
    """Definition and initialization of the iRODS login window.

    """

    def __init__(self):
        super().__init__()
        PyQt5.uic.loadUi('gui/ui-files/irodsLogin.ui', self)
        self.selectIcommandsButton.toggled.connect(self.setup_icommands)
        self.standardButton.toggled.connect(self.setup_standard)
        self.connectButton.clicked.connect(self.login_function)
        self.ticketButton.clicked.connect(self.ticket_login)
        self.passwordField.setEchoMode(PyQt5.QtWidgets.QLineEdit.Password)
        self.icommands = False
        self._connector = None
        self.ibridges_env_path = os.path.expanduser(os.path.join('~', '.ibridges'))
        if not os.path.isdir(self.ibridges_env_path):
            os.makedirs(self.ibridges_env_path)
        self.irods_env_path = os.path.expanduser(os.path.join('~', '.irods'))
        if not os.path.isdir(self.irods_env_path):
            os.makedirs(self.irods_env_path)
        utils.utils.setup_logger(self.ibridges_env_path, 'iBridgesGui')
        self.config_file_path = os.path.join(self.ibridges_env_path, 'config.json')
        if not os.path.isfile(self.config_file_path):
            with open(self.config_file_path, 'w') as confd:
                json.dump({}, confd)
        self.init_envbox()

    def _get_connector(self):
        """iRODS connector getter.

        Returns
        -------
        IrodsConnector
            iRODS session container.

        """
        if not self.icommands:
            return utils.IrodsConnector.IrodsConnector
        return utils.IrodsConnectorIcommands.IrodsConnectorIcommands

    connector = property(_get_connector, None, None, 'IrodsConnector')

    def _reset_mouse_and_error_labels(self):
        """Reset cursor and clear error text

        """
        self.setCursor(PyQt5.QtGui.QCursor(PyQt5.QtCore.Qt.ArrowCursor))
        self.passError.setText('')
        self.envError.setText('')

    def setup_standard(self):
        """Check the state of the radio button for using the pure Python
        client.

        """
        if self.standardButton.isChecked():
            self.init_envbox()
            self.icommands = False

    def setup_icommands(self):
        """Check the state of the radio button for using iCommands.
        This includes a check for the existance of the iCommands on the
        current system.

        """
        if self.selectIcommandsButton.isChecked():
            icommands_exist = False
            self.icommandsError.setText('')
            with open(os.devnull, 'w') as devnull:
                icommands_exist = subprocess.call(['which', 'iinit'], stdout=devnull, stderr=devnull) == 0
            if icommands_exist:
                self.icommands = True
            else:
                self.icommandsError.setText('ERROR: no iCommands installed')
                self.standardButton.setChecked(True)

    def init_envbox(self):
        """Populate environment container.

        """
        env_jsons = []
        for file in os.listdir(self.irods_env_path):
            if file.startswith('irods_environment'):
                env_jsons.append(file)
        if len(env_jsons) == 0:
            self.envError.setText(f'ERROR: no iRODS environment files found in {self.irods_env_path}')
        self.envbox.clear()
        self.envbox.addItems(env_jsons)
        # Read config
        if os.path.isfile(self.config_file_path):
            with open(self.config_file_path) as confd:
                conf = json.load(confd)
            if ('last_ienv' in conf) and (conf['last_ienv'] != '') and (conf['last_ienv'] in env_jsons):
                index = self.envbox.findText(conf['last_ienv'])
                self.envbox.setCurrentIndex(index)
                return
        # Prefer default name
        if "irods_environment.json" in env_jsons:
            index = self.envbox.findText("irods_environment.json")
            self.envbox.setCurrentIndex(index)

    def login_function(self):
        """Check connectivity, log in to iRODS handling common errors.

        """
        self.setCursor(PyQt5.QtGui.QCursor(PyQt5.QtCore.Qt.WaitCursor))
        # TODO prefill IRODS_ENVIRONMENT_FILE and password in the GUI
        # TODO if they already are available
        password = self.passwordField.text()
        env_file = os.path.join(self.irods_env_path, self.envbox.currentText())
        # Overwrite IRODS_ENVIRONMENT_FILE variable, for now...
        os.environ['IRODS_ENVIRONMENT_FILE'] = env_file
        connect = False
        with open(self.config_file_path) as confd:
            conf = json.load(confd)
        try:
            with open(env_file) as envfd:
                ienv = json.load(envfd)
            connect = utils.utils.networkCheck(ienv['irods_host'])
            if not connect:
                logging.info('iRODS login: No network connection to server')
                self.envError.setText('No network connection to server')
                self.setCursor(PyQt5.QtGui.QCursor(PyQt5.QtCore.Qt.ArrowCursor))
                return
        except FileNotFoundError:
            self.passError.clear()
            # TODO test for missing certificate
            self.envError.setText('ERROR: iRODS environment file or certificate not found.')
            self.setCursor(PyQt5.QtGui.QCursor(PyQt5.QtCore.Qt.ArrowCursor))
        except Exception as error:
            message = f'ERROR IRODS LOGIN: {error}'
            logging.info(message, exc_info=True)
            self.passError.clear()
            # TODO discover what possible errors exist and avoid generic
            # TODO connection error
            self.envError.setText(f'iRODS login: {error}')
            self.setCursor(PyQt5.QtGui.QCursor(PyQt5.QtCore.Qt.ArrowCursor))
            return

        # TODO determine if this conditional is necessary
        if connect:
            try:
                conn = self.connector(password)
                # Add own filepath for easy saving
                ienv['ui_ienvFilePath'] = env_file
                conf['last_ienv'] = os.path.split(env_file)[-1]
                ienv.update(conf)
                with open(self.config_file_path, 'w') as confd:
                    json.dump(conf, confd, indent=4, sort_keys=True)
                # widget is a global variable
                browser = gui.mainmenu(widget, conn, ienv)
                if len(widget) == 1:
                    widget.addWidget(browser)
                self._reset_mouse_and_error_labels()
                # self.setCursor(PyQt5.QtGui.QCursor(PyQt5.QtCore.Qt.ArrowCursor))
                widget.setCurrentIndex(widget.currentIndex()+1)
            except (irods.exception.CAT_INVALID_AUTHENTICATION,
                    irods.exception.PAM_AUTH_PASSWORD_FAILED,
                    ConnectionRefusedError):
                self.envError.clear()
                self.passError.setText('ERROR: Wrong password.')
                self.setCursor(PyQt5.QtGui.QCursor(PyQt5.QtCore.Qt.ArrowCursor))
            except FileNotFoundError as fnfe:
                self.passError.clear()
                # TODO test for missing certificate
                self.envError.setText('ERROR: iRODS environment file or certificate not found.')
                self.setCursor(PyQt5.QtGui.QCursor(PyQt5.QtCore.Qt.ArrowCursor))
                raise fnfe
            except IsADirectoryError:
                self.passError.clear()
                self.envError.setText('ERROR: File expected.')
                self.setCursor(PyQt5.QtGui.QCursor(PyQt5.QtCore.Qt.ArrowCursor))
            except irods.exception.NetworkException:
                self.passError.clear()
                self.envError.setText('iRODS server ERROR: iRODS server down.')
                self.setCursor(PyQt5.QtGui.QCursor(PyQt5.QtCore.Qt.ArrowCursor))
            except Exception as unknown:
                message = f'Something went wrong: {unknown}'
                logging.exception(message)
                # logging.info(repr(error))
                self.envError.setText(message)
                self.setCursor(PyQt5.QtGui.QCursor(PyQt5.QtCore.Qt.ArrowCursor))
                raise unknown

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
        # self.setCursor(PyQt5.QtGui.QCursor(PyQt5.QtCore.Qt.ArrowCursor))
        widget.setCurrentIndex(widget.currentIndex()+1)


def main():
    """Main function

    """
    login_window = IrodsLoginWindow()
    widget.addWidget(login_window)
    widget.show()
    app.exec_()


if __name__ == "__main__":
    main()
