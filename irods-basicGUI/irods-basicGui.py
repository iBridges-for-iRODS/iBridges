import os
from pathlib import Path
import sys
from cryptography.fernet import Fernet
import subprocess

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QDialog, QApplication, QMainWindow, QMessageBox
from PyQt5.uic import loadUi
from PyQt5 import QtCore
from PyQt5 import QtGui

from irodsConnector import irodsConnector
from irodsConnectorIcommands import irodsConnectorIcommands
from irods.exception import CAT_INVALID_AUTHENTICATION
from irods.exception import NetworkException
from irods.exception import CollectionDoesNotExist

from irodsBrowser import irodsBrowser
from irodsUtils import networkCheck
import json
import os

RED = '\x1b[1;31m'
DEFAULT = '\x1b[0m'
YEL = '\x1b[1;33m'
BLUE = '\x1b[1;34m'

class irodsLogin(QDialog):
    def __init__(self):
        super(irodsLogin, self).__init__()
        loadUi("ui-files/irodsLogin.ui", self)
        self.envFileField.setText(os.path.expanduser('~')+os.sep+".irods/irods_environment.json")
        self.selectIcommandsButton.toggled.connect(self.setupIcommands)
        self.standardButton.toggled.connect(self.setupStandard)
        self.connectButton.clicked.connect(self.loginfunction)
        self.passwordField.setEchoMode(QtWidgets.QLineEdit.Password)
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
        self.connectButton.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.passError.clear()
        self.envError.clear()


    def setupStandard(self):
        if self.standardButton.isChecked():
            self.envFileField.setEnabled(True)
            self.icommands = False


    def setupIcommands(self):
        if self.selectIcommandsButton.isChecked():
            icommandsExist = False
            self.icommandsError.setText("")
            try:
                icommandsExist = subprocess.call(["which", "iinit"]) == 0
                if icommandsExist == False:
                    self.icommandsError.setText("ERROR: no icommands installed")
                    self.standardButton.setChecked(True)
                else:
                    self.envFileField.setText(os.environ['HOME']+"/.irods/irods_environment.json")
                    self.envFileField.setEnabled(False)
                    self.icommands = True
            except Exception:
                self.icommandsError.setText("ERROR: no icommands installed")
                self.standardButton.setChecked(True)

    def loginfunction(self):
        self.__resetErrorLabelsAndMouse()
        self.connectButton.setCursor(QtGui.QCursor(QtCore.Qt.WaitCursor))
        cipher = self.__encryption()
        password = cipher.encrypt(bytes(self.passwordField.text(), 'utf-8'))
        envFile = self.envFileField.text()
        connect = False
       
        try:
            with open(envFile) as f:
                ienv = json.load(f)
            connect = networkCheck(ienv['irods_host'])
            if not connect:
                print("Network down")
                self.envError.setText("No network connection to server")
                self.connectButton.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        except FileNotFoundError:
            self.envError.setText("ERROR: iRODS environment file or certificate not found.")
            self.connectButton.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        except Exception as error:
            print(repr(error))
            self.envError.setText("No network connection to server")
            self.connectButton.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
            raise
             
        if connect:
            try:
                ic = self.__irodsLogin(envFile, password, cipher)
                browser = irodsBrowser(widget, ic)
                if len(widget) == 1:
                    widget.addWidget(browser)
                widget.setCurrentIndex(widget.currentIndex()+1)
                self.__resetErrorLabelsAndMouse()
            except CAT_INVALID_AUTHENTICATION:
                self.passError.setText("ERROR: Wrong password.")
                self.connectButton.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
            except ConnectionRefusedError:
                self.passError.setText("ERROR: Wrong password.")
                self.connectButton.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
            except FileNotFoundError:
                self.envError.setText("ERROR: iRODS environment file or certificate not found.")
                self.connectButton.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
            except IsADirectoryError:
                self.envError.setText("ERROR: File expected.")
                self.connectButton.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
            except NetworkException:
                self.envError.setText("iRODS server ERROR: iRODS server down.")
                self.connectButton.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
            except Exception:
                self.envError.setText("Something went wrong.")
                self.connectButton.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
                raise


if __name__ == "__main__":
    app = QApplication(sys.argv)
    loginWindow = irodsLogin()
    widget = QtWidgets.QStackedWidget()
    widget.addWidget(loginWindow)
    widget.show()
    app.exec_()
