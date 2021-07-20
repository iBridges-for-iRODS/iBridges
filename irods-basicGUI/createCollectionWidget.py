from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QDialog, QFileDialog, QApplication, QMainWindow, QMessageBox, QPushButton
from PyQt5.uic import loadUi
from PyQt5 import QtCore
from PyQt5 import QtGui

import sys

class createCollectionWidget(QDialog):
    def __init__(self, parent, ic):
        super(createCollectionWidget, self).__init__()
        loadUi("createCollection.ui", self)
        self.ic = ic
        self.parent = parent
        self.label.setText(self.parent+"/")
        self.buttonBox.accepted.connect(self.accept)

    def accept(self):
        if self.collPathLine.text() != "":
            newCollPath = self.parent+"/"+self.collPathLine.text()
            try:
                self.ic.ensureColl(newCollPath)
                self.done(1)
            except Exception as error:
                if hasattr(error, 'message'):
                    self.errorLabel.setText(error.message)
                else:
                    self.errorLabel.setText("ERROR: insufficient rights.")




