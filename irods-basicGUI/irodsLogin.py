import os
import json
from cryptography.fernet import Fernet
import subprocess

from PyQt5.QtWidgets import QDialog, QLineEdit#, QApplication, QMainWindow, QMessageBox
from PyQt5.uic import loadUi
from PyQt5 import QtCore
from PyQt5 import QtGui

from irodsConnector import irodsConnector
from irodsConnectorIcommands import irodsConnectorIcommands
from irods.exception import CAT_INVALID_AUTHENTICATION
from irods.exception import NetworkException
from irods.exception import CollectionDoesNotExist

from irodsBrowser import irodsBrowser
from utils import networkCheck


class irodsLogin(QDialog):
    def __init__(self, stackedWidget):
        super(irodsLogin, self).__init__()
        loadUi("ui-files/irodsLogin.ui", self)
        self.envFileField.setText(os.path.expanduser('~')+os.sep+".irods/irods_environment.json")
        self.selectIcommandsButton.toggled.connect(self.setupIcommands)
        self.standardButton.toggled.connect(self.setupStandard)
        self.connectButton.clicked.connect(self.loginfunction)
        self.passwordField.setEchoMode(QLineEdit.Password)
        self.icommands = False
        self.stackedWidget = stackedWidget


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
                return
        except FileNotFoundError:
            self.envError.setText("ERROR: iRODS environment file or certificate not found.")
            self.connectButton.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        except Exception as error:
            print(repr(error))
            self.envError.setText("No network connection to server")
            self.connectButton.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
            return
             
        if connect:
            try:
                #Connect to irods and add irods browser on stackedWidget
                ic = self.__irodsLogin(envFile, password, cipher)
                browser = irodsBrowser(self.stackedWidget, ic)
                if len(self.stackedWidget) == 1:
                    self.stackedWidget.addWidget(browser)
                self.stackedWidget.setCurrentIndex(self.stackedWidget.currentIndex()+1)
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
