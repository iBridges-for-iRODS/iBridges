#!/usr/bin/env python3
"""iBridges GUI startup script.

"""
import json
import logging
import os
import pathlib
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


class JsonConfig():
    """A configuration stored in a JSON file.

    """

    def __init__(self, filepath):
        """Create the configuration.

        Parameter
        ---------
        filepath : str

        """
        self.filepath = pathlib.Path(filepath)
        self._config = None

    def _get_config(self):
        """Configuration getter.

        Attempt to load a configuration from the JSON file.

        Returns
        -------
        dict or None
            The configuration if it exists.

        """
        if self._config is None:
            if self.filepath.exists():
                with open(self.filepath, 'r', encoding='utf-8') as confd:
                    self._config = json.load(confd)
        return self._config

    def _set_config(self, conf_dict):
        """Configuration setter.

        Set the configuration to `conf_dict` and write it to the JSON
        file.

        """
        self._config = conf_dict
        with open(self.filepath, 'w', encoding='utf-8') as confd:
            json.dump(conf_dict, confd, indent=4, sort_keys=True)

    def _del_config(self):
        """Configuration deleter.

        Delete both the configuration and its JSON file.

        """
        self._config = None
        self.filepath.unlink(missing_ok=True)

    config = property(
        _get_config, _set_config, _del_config,
        'A configuration dictionary linked to a JSON file.')


class IrodsLoginWindow(PyQt5.QtWidgets.QDialog):
    """Definition and initialization of the iRODS login window.

    """

    def __init__(self):
        super().__init__()
        self.icommands = False
        self._connector = None
        self._load_gui()
        self._init_configs_and_logging()
        self._init_envbox()
        self._init_password()

    def _load_gui(self):
        """

        """
        PyQt5.uic.loadUi('gui/ui-files/irodsLogin.ui', self)
        self.selectIcommandsButton.toggled.connect(self.setup_icommands)
        self.standardButton.toggled.connect(self.setup_standard)
        self.connectButton.clicked.connect(self.login_function)
        self.ticketButton.clicked.connect(self.ticket_login)
        self.passwordField.setEchoMode(PyQt5.QtWidgets.QLineEdit.Password)

    def _init_configs_and_logging(self):
        """

        """
        # iBridges configuration
        ibridges_path = pathlib.Path(
            os.path.join('~', '.ibridges')).expanduser()
        if not ibridges_path.is_dir():
            ibridges_path.mkdir(parents=True)
        self.ibridges_config = ibridges_path.joinpath('config.json')
        self.ibridges = JsonConfig(self.ibridges_config)
        if self.ibridges.config is None:
            self.ibridges.config = {}
        # iRODS configuration (environment)
        self.irods = None
        self.irods_path = pathlib.Path(
            os.path.join('~', '.irods')).expanduser()
        if not self.irods_path.is_dir():
            self.irods_path.mkdir(parents=True)
            self.irods_env = 'irods_environment.json'
        # iBridges logging
        utils.utils.setup_logger(ibridges_path, 'iBridgesGui')

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
        env_path = self.irods_path.joinpath(self.envbox.currentText())
        # Overwrite IRODS_ENVIRONMENT_FILE variable, for now...
        os.environ['IRODS_ENVIRONMENT_FILE'] = str(env_path)
        # Fish for a cached password
        conn = self.connector(password='')
        if conn.password is not None:
            self.passwordField.setText(conn.password)

    def _get_connector(self):
        """iRODS connector getter (factory).

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
            self._init_envbox()
            self.icommands = False

    def setup_icommands(self):
        """Check the state of the radio button for using iCommands.
        This includes a check for the existance of the iCommands on the
        current system.

        """
        if self.selectIcommandsButton.isChecked():
            icommands_exist = False
            self.icommandsError.setText('')
            with open(os.devnull, 'w', encoding='utf-8') as devnull:
                icommands_exist = subprocess.call(['which', 'iinit'], stdout=devnull, stderr=devnull) == 0
            if icommands_exist:
                self.icommands = True
            else:
                self.icommandsError.setText('ERROR: no iCommands installed')
                self.standardButton.setChecked(True)

    def login_function(self):
        """Check connectivity and log in to iRODS handling common errors.

        """
        conf = self.ibridges.config
        conf['last_ienv'] = self.envbox.currentText()
        env_path = self.irods_path.joinpath(conf['last_ienv'])
        conf['ui_ienvFilePath'] = str(env_path)
        ienv = JsonConfig(env_path).config
        if ienv is None:
            self.passError.clear()
            self.envError.setText('ERROR: iRODS environment file not found.')
            self.setCursor(PyQt5.QtGui.QCursor(PyQt5.QtCore.Qt.ArrowCursor))
            return
        if 'irods_host' in ienv:
            connect = utils.utils.can_connect(ienv['irods_host'])
            if not connect:
                logging.info('iRODS login: No network connection to server')
                self.envError.setText('No network connection to server')
                self.setCursor(PyQt5.QtGui.QCursor(PyQt5.QtCore.Qt.ArrowCursor))
                return
        self.setCursor(PyQt5.QtGui.QCursor(PyQt5.QtCore.Qt.WaitCursor))
        password = self.passwordField.text()
        env_path = self.irods_path.joinpath(self.envbox.currentText())
        # Overwrite IRODS_ENVIRONMENT_FILE variable, again...
        os.environ['IRODS_ENVIRONMENT_FILE'] = str(env_path)
        conn = self.connector(password=password)
        # Add own filepath for easy saving.
        conf['ui_ienvFilePath'] = str(env_path)
        conf['last_ienv'] = env_path.name
        # Save iBridges config to disk and combine with iRODS' config.
        self.ibridges.config = conf
        ienv.update(conf)
        try:
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
