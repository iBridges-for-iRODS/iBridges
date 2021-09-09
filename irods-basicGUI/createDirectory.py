from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QDialog
from PyQt5.uic import loadUi
from PyQt5 import QtCore
from PyQt5 import QtGui

import sys
import os

class createDirectory(QDialog):
    def __init__(self, parent):
        super(createDirectory, self).__init__()
        loadUi("ui-files/createCollection.ui", self)
        self.setWindowTitle("Create directory")
        self.parent = parent
        self.label.setText(self.parent+os.sep)
        self.buttonBox.accepted.connect(self.accept)

    def accept(self):
        if self.collPathLine.text() != "":
            newDirPath = self.parent+os.sep+self.collPathLine.text()
            try:
                os.makedirs(newDirPath)
                self.done(1)
            except Exception as error:
                if hasattr(error, 'message'):
                    self.errorLabel.setText(error.message)
                else:
                    self.errorLabel.setText("ERROR: insufficient rights.")




