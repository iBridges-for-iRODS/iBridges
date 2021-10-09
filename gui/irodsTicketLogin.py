from PyQt5 import QtWidgets
from PyQt5.uic import loadUi
from utils.irodsConnectorAnonymous import irodsConnectorAnonymous
import os

class irodsTicketLogin():
    def __init__(self, widget):
        self.ic = None
        self.coll = None
        self.widget = widget
        self.widget.connectButton.clicked.connect(self.irodsSession)
        self.widget.homeButton.clicked.connect(self.loadTable)
        self.widget.collTable.doubleClicked.connect(self.browse)
        

    def irodsSession(self):
        self.widget.infoLabel.clear()
        host = self.widget.serverEdit.text()
        token = self.widget.ticketEdit.text()
        path = self.widget.pathEdit.text()

        try:
            self.ic = irodsConnectorAnonymous(host, token, path)
            self.coll = self.ic.getData()
            self.loadTable()
        except Exception as e:
            self.widget.infoLabel.setText("LOGIN ERROR: Check ticket and iRODS path.\n"+repr(e))

    
    def loadTable(self, update = None):
        self.widget.infoLabel.clear()
        if self.coll == None:
            self.widget.infoLabel.setText("No data avalaible. Check ticket and iRODS path.")
            return
        if update == None or update == False:
            update = self.coll

        self.widget.collTable.setRowCount(0)
        self.widget.collTable.setRowCount(len(update.subcollections)+len(update.data_objects))
        row = 0
        for subcoll in update.subcollections:
            self.widget.collTable.setItem(row, 0, 
                    QtWidgets.QTableWidgetItem(os.path.dirname(subcoll.path)))
            self.widget.collTable.setItem(row, 1, 
                    QtWidgets.QTableWidgetItem(subcoll.name+"/"))
            self.widget.collTable.setItem(1, 2, QtWidgets.QTableWidgetItem(""))
            self.widget.collTable.setItem(1, 3, QtWidgets.QTableWidgetItem(""))
            row = row + 1
        for obj in update.data_objects:
            self.widget.collTable.setItem(row, 0,
                    QtWidgets.QTableWidgetItem(os.path.dirname(obj.path)))
            self.widget.collTable.setItem(row, 1, QtWidgets.QTableWidgetItem(obj.name))
            self.widget.collTable.setItem(row, 2, QtWidgets.QTableWidgetItem(str(obj.size)))
            self.widget.collTable.setItem(row, 3, QtWidgets.QTableWidgetItem(str(obj.checksum)))
            self.widget.collTable.setItem(row, 4, 
                    QtWidgets.QTableWidgetItem(str(obj.modify_time)))
            row = row+1
        self.widget.collTable.resizeColumnsToContents()


    def browse(self, index):
        self.widget.infoLabel.clear()
        col = index.column()
        row = index.row()
        if self.widget.collTable.item(row, 0).text() != '':
            path = self.widget.collTable.item(row, 0).text()
            item = self.widget.collTable.item(row, 1).text()
            if item.endswith('/'):
                item = item[:-1]
            if self.ic.session.collections.exists(path+'/'+item):
                coll = self.ic.session.collections.get(path+'/'+item)
                self.loadTable(update = coll)
