#!/usr/bin/env python3
"""iBridges GUI startup script.

"""
import datetime
import logging
import logging.handlers
import os
import setproctitle
import sys

import irods.exception
import PyQt6.QtCore
import PyQt6.QtGui
import PyQt6.QtWidgets
import PyQt6.uic

import gui
import irodsConnector
import utils

# Global constants
DEFAULT = '\x1b[0m'
RED = '\x1b[1;31m'
YELLOW = '\x1b[1;33m'
LOG_LEVEL = {
    'debug': logging.DEBUG,
    'info': logging.INFO,
    'warn': logging.WARNING,
    'error': logging.ERROR,
    'critical': logging.CRITICAL,
}
THIS_APPLICATION = 'iBridges'

# Application globals
app = PyQt6.QtWidgets.QApplication(sys.argv)
widget = PyQt6.QtWidgets.QStackedWidget()

# Work around a PRC XML issue handling special characters
os.environ['PYTHON_IRODSCLIENT_DEFAULT_XML'] = 'QUASI_XML'


class IrodsLoginWindow(PyQt6.QtWidgets.QDialog,
                       gui.ui_files.irodsLogin.Ui_irodsLogin):
    """Definition and initialization of the iRODS login window.

    """
    icommands = False
    this_application = ''
    context = utils.context.Context()

    def __init__(self):
        super().__init__()
        self.irods_path = utils.path.LocalPath(utils.context.IRODS_DIR).expanduser()
        self._load_gui()
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
        envname = ''
        if 'last_ienv' in self.context.ibridges_configuration.config and \
                self.context.ibridges_configuration.config['last_ienv'] in env_jsons:
            envname = self.context.ibridges_configuration.config['last_ienv']
        elif 'irods_environment.json' in env_jsons:
            envname = 'irods_environment.json'
        index = 0
        if envname:
            index = self.envbox.findText(envname)
        self.envbox.setCurrentIndex(index)

    def _init_password(self):
        """

        """
        if self.context.irods_connector.password:
            self.passwordField.setText(self.context.irods_connector.password)

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
            print(self.context.irods_connector.icommands)
            if self.context.irods_connector.has_icommands():
                self.icommands = True
                # TODO support arbitrary iRODS environment file for iCommands
            else:
                self.icommandsError.setText('ERROR: no iCommands found')
                self.standardButton.setChecked(True)

    def login_function(self):
        """Check connectivity and log in to iRODS handling common errors.

        """
        # Replacement connector (required for new sessions)
        if not self.context.irods_connector:
            logging.debug('Setting new instance of the IrodsConnector')
            self.context.irods_connector = irodsConnector.manager.IrodsConnector()
        irods_env_file = self.irods_path.joinpath(self.envbox.currentText())
        self.context.irods_env_file = irods_env_file
        logging.debug('IRODS ENVIRONMENT FILE SET: %s', irods_env_file.name)
        self.envError.setText('')
        if not (self.context.irods_environment.config and self.context.ienv_is_complete()):
            message = 'iRODS environment missing or incomplete.'
            logging.error(message)
            self.envError.setText(message)
            self.context.irods_environment.reset()
            self.passError.clear()
            self.setCursor(PyQt6.QtGui.QCursor(PyQt6.QtCore.Qt.CursorShape.ArrowCursor))
            return
        if not utils.utils.can_connect(self.context.irods_environment.config.get('irods_host', '')):
            message = 'No network connection to server'
            logging.warning(message)
            self.envError.setText(message)
            self.setCursor(PyQt6.QtGui.QCursor(PyQt6.QtCore.Qt.CursorShape.ArrowCursor))
            return
        self.setCursor(PyQt6.QtGui.QCursor(PyQt6.QtCore.Qt.CursorShape.WaitCursor))
        self.context.ibridges_configuration.config['last_ienv'] = irods_env_file.name
        self.context.save_ibridges_configuration()
        password = self.passwordField.text()

        self.context.irods_connector.password = password
        logging.debug(f'IRODS PASSWORD SET: {"*"*len(password)*2}')
        self.context.irods_connector.irods_env_file = self.context.irods_env_file
        self.context.irods_connector.irods_environment = self.context.irods_environment
        self.context.irods_connector.ibridges_configuration = self.context.ibridges_configuration

        try:
            self.context.irods_connector.connect()
        except (irods.exception.CAT_INVALID_AUTHENTICATION,
                irods.exception.PAM_AUTH_PASSWORD_FAILED,
                irods.exception.CAT_INVALID_USER,
                ConnectionRefusedError):
            message = 'Wrong password!  Try again'
            logging.error(message)
            self.passError.setText(message)
            self.envError.clear()
            self.setCursor(PyQt6.QtGui.QCursor(PyQt6.QtCore.Qt.CursorShape.ArrowCursor))
            return
        except irods.exception.CAT_PASSWORD_EXPIRED:
            message = 'Cached password expired!  Re-enter password'
            logging.error(message)
            self.passError.setText(message)
            self.envError.clear()
            self.setCursor(PyQt6.QtGui.QCursor(PyQt6.QtCore.Qt.CursorShape.ArrowCursor))
            return
        except irods.exception.NetworkException:
            message = 'iRODS server down!  Check and try again'
            logging.error(message)
            self.envError.setText(message)
            self.passError.clear()
            self.setCursor(PyQt6.QtGui.QCursor(PyQt6.QtCore.Qt.CursorShape.ArrowCursor))
            return
        except Exception as error:
            message = 'Something unexpected occurred: %r'
            # logging.error(utils.utils.err_msg(message), error)
            logging.error(message, error)
            self.envError.setText(message % error)
            self.setCursor(PyQt6.QtGui.QCursor(PyQt6.QtCore.Qt.CursorShape.ArrowCursor))
            return
        # widget is a global variable
        browser = gui.mainmenu.mainmenu(widget)
        if len(widget) == 1:
            widget.addWidget(browser)
        self._reset_mouse_and_error_labels()
        widget.setCurrentIndex(widget.currentIndex()+1)

    def ticket_login(self):
        """Log in to iRODS using a ticket.

        """
        # widget is a global variable
        browser = gui.mainmenu.mainmenu(widget)
        browser.menuOptions.clear()
        browser.menuOptions.deleteLater()
        if len(widget) == 1:
            widget.addWidget(browser)
        self._reset_mouse_and_error_labels()
        # self.setCursor(PyQt6.QtGui.QCursor(PyQt6.QtCore.Qt.CursorShape.ArrowCursor))
        widget.setCurrentIndex(widget.currentIndex()+1)


def closeClean():

    context = utils.context.Context()
    if context.irods_connector:
        context.irods_connector.cleanup()


def init_logger():
    """Initialize the application logging service.

    """
    old_factory = logging.getLogRecordFactory()

    def new_factory(*args, **kwargs) -> logging.LogRecord:
        """Custom record factory"""
        record = old_factory(*args, **kwargs)
        record.prefix = ''
        record.postfix = ''
        if record.levelname == 'WARNING':
            record.prefix = YELLOW
            record.postfix = DEFAULT
        if record.levelname == 'ERROR':
            record.prefix = RED
            record.postfix = DEFAULT
        return record

    logging.setLogRecordFactory(new_factory)
    logger = logging.getLogger()
    logdir = utils.path.LocalPath(utils.context.IBRIDGES_DIR).expanduser()
    logfile = logdir.joinpath(f'{THIS_APPLICATION}.log')
    log_formatter = logging.Formatter(
        '[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s')
    file_handler = logging.handlers.RotatingFileHandler(logfile, 'a', 100000, 1)
    file_handler.setFormatter(log_formatter)
    logger.addHandler(file_handler)
    log_formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s - %(prefix)s%(message)s%(postfix)s')
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(log_formatter)
    logger.addHandler(stream_handler)
    # Indicate start of a new session
    with open(logfile, 'a', encoding='utf-8') as logfd:
        logfd.write('\n\n')
        underscores = f'{"_" * 50}\n'
        logfd.write(underscores * 2)
        logfd.write(f'\t\t{datetime.datetime.now().isoformat()}\n')
        logfd.write(underscores * 2)


def main():
    """Main function

    """
    # Initialize logger first because Context may want to log as well.
    init_logger()
    # Singleton Context
    context = utils.context.Context()
    context.application_name = THIS_APPLICATION
    # Context is required to get the log_level from the configuration.
    verbose = context.ibridges_configuration.config.get('verbose', 'info')
    log_level = LOG_LEVEL.get(verbose, logging.INFO)
    utils.utils.set_log_level(log_level)
    context.irods_connector = irodsConnector.manager.IrodsConnector()
    setproctitle.setproctitle(context.application_name)
    login_window = IrodsLoginWindow()
    login_window.this_application = context.application_name
    widget.addWidget(login_window)
    widget.show()
    # app.setQuitOnLastWindowClosed(False)
    app.lastWindowClosed.connect(closeClean)
    app.exec()


if __name__ == "__main__":
    main()
