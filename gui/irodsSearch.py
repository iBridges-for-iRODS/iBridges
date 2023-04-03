"""iRODS search dialog.

"""
import logging
import os
import sys

from PyQt6 import QtWidgets, QtGui, QtCore
from PyQt6.QtWidgets import QDialog, QMessageBox
from PyQt6.uic import loadUi

from gui.ui_files.searchDialog import Ui_searchDialog
import utils


class irodsSearch(QDialog, Ui_searchDialog):
    """

    """

    def __init__(self, conn, collTable):
        """

        Parameters
        ----------
        conn
        collTable

        """
        super().__init__()
        if getattr(sys, 'frozen', False):
            super().setupUi(self)
        else:
            loadUi("gui/ui_files/searchDialog.ui", self)
        self.conn = conn
        self.collTable = collTable
        self.keys = [self.key1, self.key2, self.key3, self.key4, self.key5]
        self.vals = [self.val1, self.val2, self.val3, self.val4, self.val5]

        self.setWindowTitle("iRODS search")
        self.startSearchButton.clicked.connect(self.search)
        self.selectSearchButton.clicked.connect(self.loadSearchResults)
        self.downloadButton.clicked.connect(self.download_data)
        self.searchExitButton.released.connect(self.close)

    def enableButtons(self, enabled=True):
        """

        Parameters
        ----------
        enabled

        """
        self.startSearchButton.setEnabled(enabled)
        self.selectSearchButton.setEnabled(enabled)
        self.downloadButton.setEnabled(enabled)
        self.searchExitButton.setEnabled(enabled)

    def search(self):
        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.WaitCursor))
        self.startSearchButton.setDisabled(True)
        self.searchResultTable.setRowCount(0)
        # gather all input from input fields in dictionary 'criteria'
        keyVals = dict(zip([key.text() for key in self.keys], [val.text() for val in self.vals]))
        
        criteria = {}
        if self.pathPattern.text():
            criteria['path'] = self.pathPattern.text()
        if self.objPattern.text():
            criteria['object'] = self.objPattern.text()
        if self.checksumPattern.text():
            criteria['checksum'] = self.checksumPattern.text()
        for key in keyVals:
            if key:
                criteria[key] = ''
            if keyVals[key]:
                criteria[key] = keyVals[key]
        
        # get search results as [[collname, objname, checksum]...[]]
        results = self.conn.search(criteria)
        
        row = 0 
        if len(results) == 0:
            self.searchResultTable.setRowCount(1)
            self.searchResultTable.setItem(row, 0, 
                    QtWidgets.QTableWidgetItem('No search results found'))
        else:
            self.searchResultTable.setRowCount(len(results))
            for collName, objName, checksum in results:
                self.searchResultTable.setItem(row, 0, QtWidgets.QTableWidgetItem(collName))
                self.searchResultTable.setItem(row, 1, QtWidgets.QTableWidgetItem(objName))
                self.searchResultTable.setItem(row, 2, QtWidgets.QTableWidgetItem(checksum))
                row = row + 1
        self.searchResultTable.resizeColumnsToContents()
        self.startSearchButton.setDisabled(False)
        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))

    def loadSearchResults(self):
        rows = set(
            [idx.row() for idx in self.searchResultTable.selectedIndexes()
             if idx.row() > 2])
        self.collTable.setRowCount(len(rows))
        for index, row in enumerate(rows):
            if self.searchResultTable.item(row, 1).text() == '':
                self.collTable.setItem(
                    index, 0, QtWidgets.QTableWidgetItem("Search"))
                self.collTable.setItem(
                    index, 1, QtWidgets.QTableWidgetItem(
                        self.searchResultTable.item(row, 0).text()+"/"))
            else:
                self.collTable.setItem(
                    index, 0, QtWidgets.QTableWidgetItem("Search"))
                self.collTable.setItem(
                    index, 1, QtWidgets.QTableWidgetItem(
                        self.searchResultTable.item(row, 0).text()+"/"+\
                        self.searchResultTable.item(row, 1).text()))
            self.collTable.setItem(
                index, 2, QtWidgets.QTableWidgetItem(""))
            self.collTable.setItem(
                index, 3, QtWidgets.QTableWidgetItem(
                    self.searchResultTable.item(row, 2).text()))
        self.collTable.resizeColumnsToContents()
        self.close()

    def download_data(self):
        self.enableButtons(enabled=False)
        rows = set(
            [idx.row() for idx in self.searchResultTable.selectedIndexes()
             if idx.row() > 2])
        # TODO check that this is correct
        irodsPaths = []
        for row in rows:
            path0 = utils.path.IrodsPath(
                self.searchResultTable.item(row, 0).text())
            path1 = utils.path.IrodsPath(
                self.searchResultTable.item(row, 1).text())
            if path1 == '':
                irodsPaths.append(path0)
            else:
                irodsPaths.append(path0.joinpath(path1))
        if len(irodsPaths) > 0:
            downloadDir = utils.utils.get_downloads_dir()
            buttonReply = QMessageBox.question(self,
                                'Message Box',
                                'Download\n'+'\n'.join(irodsPaths)+'\nto\n'+downloadDir)
            if buttonReply == QMessageBox.StandardButton.Yes:
                self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.WaitCursor))
                try:
                    for p in irodsPaths:
                        if self.conn.collection_exists(p):
                            item = self.conn.get_collection(p)
                            self.conn.download_data(item, downloadDir, 0, force=True)
                            self.errorLabel.setText("Download complete")
                        elif self.conn.dataobject_exists(p):
                            item = self.conn.get_dataobject(p)
                            self.conn.download_data(item, downloadDir, 0, force=True)
                            self.errorLabel.setText("Download complete")
                        else:
                            self.errorLabel.setText(
                                "SEARCH widget ERROR: "+p+" not an irods item.")
                except Exception as e:
                    logging.info("IRODS SEARCH ERROR: "+repr(e), exc_info=True)
        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
        self.enableButtons()


