"""Pop-up widget definitions.

"""
import datetime
import io
import json
import logging
import os
import sys

from PyQt6 import QtWidgets
from PyQt6.QtWidgets import QDialog
from PyQt6.uic import loadUi
from PyQt6 import QtCore
from PyQt6 import QtGui

from gui.ui_files.createCollection import Ui_createCollection
from gui.ui_files.irodsIndexPopup import Ui_irodsIndexPopup

import utils

class irodsCreateCollection(QDialog, Ui_createCollection):
    context = utils.context.Context()
    def __init__(self, parent):
        super().__init__()
        if getattr(sys, 'frozen', False):
            super().setupUi(self)
        else:
            loadUi("gui/ui_files/createCollection.ui", self)

        self.conn = self.context.irods_connector
        self.setWindowTitle("Create iRODS collection")
        self.setWindowFlags(QtCore.Qt.WindowType.WindowStaysOnTopHint)
        self.parent = parent
        self.label.setText(self.parent + "/")
        self.buttonBox.accepted.connect(self.accept)

    def accept(self):
        if self.collPathLine.text() != "":
            newCollPath = self.parent + "/" + self.collPathLine.text()
            try:
                self.conn.ensure_coll(newCollPath)
                self.done(1)
            except Exception as error:
                if hasattr(error, 'message'):
                    self.errorLabel.setText(error.message)
                else:
                    self.errorLabel.setText("ERROR: insufficient rights.")


class createDirectory(QDialog, Ui_createCollection):
    def __init__(self, parent):
        super().__init__()
        if getattr(sys, 'frozen', False):
            super().setupUi(self)
        else:
            loadUi("gui/ui_files/createCollection.ui", self)
        self.setWindowTitle("Create directory")
        self.setWindowFlags(QtCore.Qt.WindowType.WindowStaysOnTopHint)
        self.parent = parent
        self.label.setText(self.parent + os.sep)
        self.buttonBox.accepted.connect(self.accept)

    def accept(self):
        if self.collPathLine.text() != "":
            newDirPath = self.parent + os.sep + self.collPathLine.text()
            try:
                os.makedirs(newDirPath)
                self.done(1)
            except Exception as error:
                if hasattr(error, 'message'):
                    self.errorLabel.setText(error.message)
                else:
                    self.errorLabel.setText("ERROR: insufficient rights.")


class irodsIndexPopup(QDialog, Ui_irodsIndexPopup):
    def __init__(self, irodsTarIndexFileList, tarFilePath, statusLabel):
        super().__init__()
        if getattr(sys, 'frozen', False):
            super().setupUi(self)
        else:
            loadUi("gui/ui_files/irodsIndexPopup.ui", self)
        self.setWindowTitle("iRODS Tar/Zip index.")
        self.setWindowFlags(QtCore.Qt.WindowType.WindowStaysOnTopHint)
        self.indexLabel.setText("Index of " + tarFilePath + ":")
        self.tabWidget.setCurrentIndex(0)
        self.closeButton.clicked.connect(self.closeWindow)
        self.textBrowser.clear()
        self.statusLabel = statusLabel
        self.formatJSON(irodsTarIndexFileList)
        for line in irodsTarIndexFileList:
            self.textBrowser.append(line)
        self.tarFilePath = tarFilePath
        self.extractButton.clicked.connect(self.extractSelection)

    def closeWindow(self):
        self.statusLabel.clear()
        self.close()

    def formatJSON(self, irodsTarIndexFileList):
        index = json.loads('\n'.join(irodsTarIndexFileList))
        self.collLabel.setText("Data objects of: " + index['collection'])
        objs = [obj for obj in index['items'] if obj['type'] == 'dataObj']
        table = [[obj['name'], obj['owner'], obj['size'], 
                    datetime.datetime.fromtimestamp(obj['created'])] for obj in objs]
        # self.dataObjectTable.clear()
        self.dataObjectTable.setRowCount(0)
        self.dataObjectTable.setRowCount(len(table))
        for row, item in enumerate(table):
            self.dataObjectTable.setItem(row, 0,  QtWidgets.QTableWidgetItem(item[0]))
            self.dataObjectTable.setItem(row, 1,  QtWidgets.QTableWidgetItem(item[1]))
            self.dataObjectTable.setItem(row, 2,  QtWidgets.QTableWidgetItem(str(item[2])))
            self.dataObjectTable.setItem(row, 3,  QtWidgets.QTableWidgetItem(str(item[3])))
        self.dataObjectTable.resizeColumnsToContents()

    def enableButtons(self, enable):
        self.extractButton.setEnabled(enable)
        self.closeButton.setEnabled(enable)

    def extractSelection(self):
        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.WaitCursor))
        self.enableButtons(False)

        selection = self.dataObjectTable.selectedIndexes()
        selectedRows = set([index.row() for index in selection])

        extractParent = os.path.dirname(self.tarFilePath)+'/' + \
                        os.path.basename(self.tarFilePath).split('.irods')[0]
        logString = "Archive File: " + self.tarFilePath+"\n"
        for row in selectedRows:
            extractPath = self.dataObjectTable.item(row, 0).text()
            destination = extractParent+'/'+extractPath
            if self.conn.dataobject_exists(destination):
                logString = logString+"\t Data already exists: "+destination+"; skipping\n"
            else:
                logString = logString+"Extracting: "+extractPath+"\n"
                params = {
                        '*obj': '"'+self.tarFilePath+'"',
                        '*resource': '"' + self.conn.default_resc + '"',
                        '*extract': '"'+extractPath+'"',
                        }
                self.conn.execute_rule(io.stringIO(EXTRACT_ONE_RULE), params)
                logging.info('TAR EXTRACT SCHEDULED: ')
                logging.info('iRODS user: %s', self.conn.get_username)
                logging.info('Rule file: extractOne')
                logging.info('params: %s', params)
                logString = logString+"\tScheduled for Extraction: Check in browser tab: " + \
                                      extractParent+"\n"
        self.enableButtons(True)
        self.errorLabel.setText(logString)
        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))


EXTRACT_ONE_RULE = '''extractOne {
    msiGetObjType(*obj, *objType);
    writeLine("stdout", "*obj, *objType");
    msiSplitPath(*obj, *parentColl, *objName);
    *suffix = substr(*obj, strlen(*obj)-9, strlen(*obj));
    *objName = substr(*objName, 0, strlen(*objName)-10);
    writeLine("stdout", "DEBUG tarExtract *parentColl");
    writeLine("stdout", "DEBUG tarExtract *objName, *suffix");
    *run = true;
    if(*objType != '-d'){
        *run = false;
        writeLine("stderr", "ERROR tarExtract: not a data object, *path")
    }
    if(*suffix != "irods.tar" && *suffix != "irods.zip"){
        *run = false;
        writeLine("stderr", "ERROR tarExtract: not an irods.tar file, *path")
    }
    if(*run==true && *extract!="null"){
        writeLine("stdout", "STATUS tarExtract: Create collection *parentColl/*objName");
        msiCollCreate("*parentColl/*objName", 1, *collCreateOut);
        if(*collCreateOut == 0) {
            writeLine("stdout", "STATUS tarExtract: Extract *extract to *parentColl/*objName");
            msiArchiveExtract(*obj, "*parentColl/*objName", *extract,  *resource, *outTarExtract);
            if(*outTarExtract != 0) {
                writeLine("stderr", "ERROR tarExtract: Failed to extract data");
            }
        }
        else {
            writeLine("stderr", "ERROR tarExtract: Failed to create *parentColl/*objName")
        }
    }
    else {
        writeLine("stdout", "DEBUG tarExtract: no action.")
    }
}
OUTPUT ruleExecOut
'''
