#!/usr/bin/env python3

import os
import sys
# import logging
from cryptography.fernet import Fernet
from json import load, dump
import subprocess
import logging

from PyQt6.QtWidgets import QDialog, QApplication, QLineEdit, QStackedWidget
from PyQt6.uic import loadUi
from PyQt6 import QtCore
from PyQt6 import QtGui

from utils.irodsConnector import irodsConnector
from utils.irodsConnectorIcommands import irodsConnectorIcommands
from utils.utils import ensure_dir
from irods.exception import CAT_INVALID_AUTHENTICATION, PAM_AUTH_PASSWORD_FAILED
from irods.exception import NetworkException
# from irods.exception import CollectionDoesNotExist

from gui.mainmenu import mainmenu
from utils.utils import networkCheck, setup_logger


class irodsLogin(QDialog):
    def __init__(self):
        import setproctitle
        setproctitle.setproctitle('iBridgesGUI')

        super(irodsLogin, self).__init__()
        loadUi("gui/ui-files/irodsLogin.ui", self)
        ensure_dir(os.path.expanduser('~') + os.sep + ".irods")
        
        self.irodsEnvPath = os.path.expanduser('~') + os.sep + ".irods"
        setup_logger(self.irodsEnvPath, "iBridgesGui")
        if not os.path.isdir(self.irodsEnvPath):
            os.makedirs(self.irodsEnvPath)
        self.configFilePath = self.irodsEnvPath + os.sep + "config.json"
        self.init_envbox()

        self.selectIcommandsButton.toggled.connect(self.setupIcommands)
        self.standardButton.toggled.connect(self.setupStandard)
        self.connectButton.clicked.connect(self.loginfunction)
        self.ticketButton.clicked.connect(self.ticketLogin)
        self.passwordField.setEchoMode(QLineEdit.EchoMode.Password)
        self.icommands = False

    def __encryption(self):
        salt = Fernet.generate_key()
        return Fernet(salt)
    
    def __irodsLogin(self, envFile, password, cipher):
        if self.icommands:
            ic = irodsConnectorIcommands(cipher.decrypt(password).decode())
        else:
            ic = irodsConnector(envFile, cipher.decrypt(password).decode())
        return ic

    def __resetErrorLabelsAndMouse(self):
        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
        self.passError.setText("")
        self.envError.setText("")

    def setupStandard(self):
        if self.standardButton.isChecked():
            self.init_envbox()
            self.icommands = False

    def setupIcommands(self):
        if self.selectIcommandsButton.isChecked():
            icommandsExist = False
            self.icommandsError.setText("")
            try:
                icommandsExist = subprocess.call(["which", "iinit"]) == 0
                if icommandsExist is False:
                    self.icommandsError.setText("ERROR: no icommands installed")
                    self.standardButton.setChecked(True)
                else:
                    self.icommands = True
                    self.envbox.clear()
                    # freeze envbox
                    self.envbox.addItems(["irods_environment.json"])
                    
            except Exception:
                self.icommandsError.setText("ERROR: no icommands installed")
                self.standardButton.setChecked(True)

    def init_envbox(self):
        envJsons = []
        for file in os.listdir(self.irodsEnvPath):
            if file != "config.json" and (file.endswith('.json') or file.startswith("irods_environment")):
                envJsons.append(file)
        if len(envJsons) == 0: 
            self.envError.setText(f"ERROR: no iRODS environment files found in {self.irodsEnvPath}")
        self.envbox.clear()
        self.envbox.addItems(envJsons)
        
        # Read config
        if os.path.isfile(self.configFilePath):
            with open(self.configFilePath) as f:
                conf = load(f)
            if ("last_ienv" in conf) and (conf["last_ienv"] != "") and (conf["last_ienv"] in envJsons):
                index = self.envbox.findText(conf["last_ienv"])
                self.envbox.setCurrentIndex(index)
                return
        if "irods_environment.json" in envJsons:
            index = self.envbox.findText("irods_environment.json")
            self.envbox.setCurrentIndex(index)                        

    def loginfunction(self):
        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.WaitCursor))
        cipher = self.__encryption()
        password = cipher.encrypt(bytes(self.passwordField.text(), 'utf-8'))
        envFile = self.irodsEnvPath + os.sep + self.envbox.currentText()
        connect = False
        try:
            if not os.path.isfile(envFile):
                raise FileNotFoundError
            with open(envFile) as f:
                ienv = load(f)
            connect = networkCheck(ienv['irods_host'])
            if not connect:
                logging.info("iRODS login: No network connection to server")
                self.envError.setText("No network connection to server")
                self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
                return
        except FileNotFoundError:
            self.passError.clear()
            self.envError.setText("ERROR: iRODS environment file or certificate not found.")
            self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
        except Exception as error:
            logging.info('ERROR IRODS LOGIN', exc_info=True)
            self.passError.clear()
            self.envError.setText("iRODS login: No network connection to server")
            self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
            return
             
        if connect:
            try:
                ic = self.__irodsLogin(envFile, password, cipher)

                # Add own filepath for easy saving
                ienv["ui_ienvFilePath"] = self.irodsEnvPath + os.sep + self.envbox.currentText()
                conf = {"last_ienv": self.envbox.currentText()}
                with open(self.configFilePath, 'w') as f:
                    dump(conf, f)

                browser = mainmenu(widget, ic, ienv)
                if len(widget) == 1:
                    widget.addWidget(browser)
                self.__resetErrorLabelsAndMouse()
                # self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
                widget.setCurrentIndex(widget.currentIndex()+1)

            except CAT_INVALID_AUTHENTICATION:
                self.envError.clear()
                self.passError.setText("ERROR: Wrong password.")
                self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
            except PAM_AUTH_PASSWORD_FAILED:
                self.envError.clear()
                self.passError.setText("ERROR: Wrong password.")
                self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
            except ConnectionRefusedError:
                self.envError.clear()
                self.passError.setText("ERROR: Wrong password.")
                self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
            except FileNotFoundError:
                self.passError.clear()
                self.envError.setText("ERROR: iRODS environment file or certificate not found.")
                self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
                raise
            except IsADirectoryError:
                self.passError.clear()
                self.envError.setText("ERROR: File expected.")
                self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
            except NetworkException:
                self.passError.clear()
                self.envError.setText("iRODS server ERROR: iRODS server down.")
                self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
            except:
                logging.exception("Something went wrong")
                # logging.info(repr(error))
                self.envError.setText("Something went wrong.")
                self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
                raise

    def ticketLogin(self):
        browser = mainmenu(widget, None, None)
        browser.menuOptions.clear()
        browser.menuOptions.deleteLater()

        if len(widget) == 1:
            widget.addWidget(browser)
        self.__resetErrorLabelsAndMouse()
        # self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
        widget.setCurrentIndex(widget.currentIndex()+1)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    loginWindow = irodsLogin()
    widget = QStackedWidget()
    widget.addWidget(loginWindow)
    widget.show()
    app.exec()
