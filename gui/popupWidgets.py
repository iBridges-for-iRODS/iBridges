from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QDialog, QTableWidgetItem
from PyQt5.uic import loadUi
from PyQt5 import QtCore
from PyQt5 import QtGui

import sys
import os
import json
import datetime
import logging

class irodsCreateCollection(QDialog):
    def __init__(self, parent, ic):
        super(irodsCreateCollection, self).__init__()
        loadUi("gui/ui-files/createCollection.ui", self)
        self.setWindowTitle("Create iRODS collection")
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


class createDirectory(QDialog):
    def __init__(self, parent):
        super(createDirectory, self).__init__()
        loadUi("gui/ui-files/createCollection.ui", self)
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


class irodsIndexPopup(QDialog):
    def __init__(self, ic, irodsTarIndexFileList, tarFilePath, statusLabel):
        super(irodsIndexPopup, self).__init__()
        loadUi("gui/ui-files/irodsIndexPopup.ui", self)
        self.setWindowTitle("iRODS Tar/Zip index.")
        self.indexLabel.setText("Index of " + tarFilePath + ":")
        self.tabWidget.setCurrentIndex(0)
        self.closeButton.clicked.connect(self.closeWindow)
        self.textBrowser.clear()
        self.statusLabel = statusLabel
        self.formatJSON(irodsTarIndexFileList)
        for line in irodsTarIndexFileList:
            self.textBrowser.append(line)

        self.ic = ic
        self.tarFilePath = tarFilePath
        self.extractButton.clicked.connect(self.extractSelection)

    def closeWindow(self):
        self.statusLabel.clear()
        self.close()

    def formatJSON(self, irodsTarIndexFileList):
        index = json.loads('\n'.join(irodsTarIndexFileList))
        self.collLabel.setText("Data objects of: "+ index['collection'])
        objs = [obj for obj in index['items'] if obj['type'] == 'dataObj']
        table = [[obj['name'], obj['owner'], obj['size'], 
                    datetime.datetime.fromtimestamp(obj['created'])] for obj in objs]

        #self.dataObjectTable.clear()
        self.dataObjectTable.setRowCount(0)
        self.dataObjectTable.setRowCount(len(table))
        row = 0
        for item in table:
            self.dataObjectTable.setItem(row, 0,  QtWidgets.QTableWidgetItem(item[0]))
            self.dataObjectTable.setItem(row, 1,  QtWidgets.QTableWidgetItem(item[1]))
            self.dataObjectTable.setItem(row, 2,  QtWidgets.QTableWidgetItem(str(item[2])))
            self.dataObjectTable.setItem(row, 3,  QtWidgets.QTableWidgetItem(str(item[3])))
            row = row + 1

        self.dataObjectTable.resizeColumnsToContents()


    def enableButtons(self, enable):
        self.extractButton.setEnabled(enable)
        self.closeButton.setEnabled(enable)


    def extractSelection(self):
        self.setCursor(QtGui.QCursor(QtCore.Qt.WaitCursor))
        self.enableButtons(False)

        ruleFile = os.path.join(os.getcwd(),'rules/tarExtractOne.r')

        selection = self.dataObjectTable.selectedIndexes()
        selectedRows = set([index.row() for index in selection])
        
        logString = ""
        extractParent = os.path.dirname(self.tarFilePath)+'/'+ \
                        os.path.basename(self.tarFilePath).split('.irods')[0]
        logString = "Archive File: "+self.tarFilePath+"\n"
        for row in selectedRows:
            extractPath = self.dataObjectTable.item(row, 0).text()
            destination = extractParent+'/'+extractPath
            if self.ic.session.data_objects.exists(destination):
                 logString = logString+"\t Data alreay exists: "+destination+"; skipping\n"
            else:
                logString = logString+"Extracting: "+extractPath+"\n"
                params = {
                        '*obj': '"'+self.tarFilePath+'"',
                        '*resource': '"'+self.ic.defaultResc+'"',
                        '*extract': '"'+extractPath+'"',
                        }
                stdout, stderr = self.ic.executeRule(ruleFile, params)
                logging.info("TAR EXTRACT SCHEDULED: ")
                logging.info("iRODS user: "+self.ic.session.username)
                logging.info("Rule file: "+ruleFile)
                logging.info("params: "+str(params))
                logString = logString+"\tScheduled for Extraction: Check in browser tab: "+\
                                      extractParent+"\n"

        self.enableButtons(True)
        self.errorLabel.setText(logString)
        self.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))


