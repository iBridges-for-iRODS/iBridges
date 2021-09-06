from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import QDialog, QMessageBox
from PyQt5.uic import loadUi
import os
from irodsUtils import getDownloadDir

class irodsSearch(QDialog):
    def __init__(self, ic, collTable):
        super(irodsSearch, self).__init__()
        loadUi("ui-files/searchDialog.ui", self)
        self.ic = ic
        self.keys = [self.key1, self.key2, self.key3, self.key4, self.key5]
        self.vals = [self.val1, self.val2, self.val3, self.val4, self.val5]
        self.collTable = collTable

        self.setWindowTitle("iRODS search")
        self.startSearchButton.clicked.connect(self.search)
        self.selectSearchButton.clicked.connect(self.loadSearchResults)
        self.downloadButton.clicked.connect(self.downloadData)
        self.searchExitButton.released.connect(self.close)


    def search(self):
        self.setCursor(QtGui.QCursor(QtCore.Qt.WaitCursor))
        self.startSearchButton.setDisabled(True)
        self.searchResultTable.setRowCount(0)
        #gather all input from input fields in dictionary 'criteria'
        keyVals = dict(zip([key.text() for key in self.keys], [val.text() for val in self.vals]))
        
        criteria = {}
        if self.pathPattern.text():
            criteria['path'] =  self.pathPattern.text()
        if self.objPattern.text():
            criteria['object'] = self.objPattern.text()
        if self.checksumPattern.text():
            criteria['checksum'] = self.checksumPattern.text()
        for key in keyVals:
            if key:
                criteria[key] = ''
            if keyVals[key]:
                criteria[key] = keyVals[key]
        
        #get search results as [[collname, objname, checksum]...[]]
        results = self.ic.search(criteria)
        
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
        self.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))


    def loadSearchResults(self):
        rows = set([idx.row() for idx in self.searchResultTable.selectedIndexes() if idx.row() > 2])
        i = 0
        self.collTable.setRowCount(len(rows))
        for row in rows:
            if self.searchResultTable.item(row, 1).text() == '':
                self.collTable.setItem(i, 0,
                    QtWidgets.QTableWidgetItem(os.path.dirname( \
                    self.searchResultTable.item(row, 0).text())))
                self.collTable.setItem(i, 1,
                    QtWidgets.QTableWidgetItem(os.path.basename( \
                    self.searchResultTable.item(row, 0).text())+'/'))
            else:
                self.collTable.setItem(i, 0, 
                    QtWidgets.QTableWidgetItem(self.searchResultTable.item(row, 0).text()))
                self.collTable.setItem(i, 1,
                    QtWidgets.QTableWidgetItem(self.searchResultTable.item(row, 1).text()))
            self.collTable.setItem(i, 2, 
                QtWidgets.QTableWidgetItem(""))
            self.collTable.setItem(i, 3,
                QtWidgets.QTableWidgetItem(self.searchResultTable.item(row, 2).text()))
            i = i + 1
        
        self.collTable.resizeColumnsToContents()
        self.close()


    def downloadData(self):
        rows = set([idx.row() for idx in self.searchResultTable.selectedIndexes() if idx.row() > 2])
        irodsPaths = []
        for row in rows:
            if self.searchResultTable.item(row, 1).text() == '':
                irodsPaths.append(os.path.dirname(self.searchResultTable.item(row, 0).text()) \
                    + '/' + os.path.basename(self.searchResultTable.item(row, 0).text()))
            else:
                irodsPaths.append(self.searchResultTable.item(row, 0).text() \
                    + '/' + self.searchResultTable.item(row, 1).text())
        if len(irodsPaths) > 0:
            downloadDir = getDownloadDir()
            buttonReply = QMessageBox.question(self,
                                'Message Box',
                                'Download\n'+'\n'.join(irodsPaths)+'\nto\n'+downloadDir)

            if buttonReply == QMessageBox.Yes:
                for p in irodsPaths:
                    if self.ic.session.collections.exists(p):
                        item = self.ic.session.collections.get(p)
                        print("SEARCH widget: Downloading \t"+p+"\t to "+downloadDir)
                        self.ic.downloadData(item, downloadDir)
                    elif self.ic.session.data_objects.exists(p):
                        item = self.ic.session.data_objects.get(p)
                        print("SEARCH widget: Downloading \t"+p+"\t to "+downloadDir)
                        self.ic.downloadData(item, downloadDir)
                    else:
                        print("SEARCH widget ERROR: "+p+" not an irods item.")
                


