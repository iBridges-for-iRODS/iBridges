import sys
from PyQt6 import QtGui, QtCore
from PyQt6.QtWidgets import QWidget
from PyQt6.uic import loadUi

from gui.irodsTreeView import IrodsModel
from gui.ui_files.tabTicketCreate import Ui_tabticketCreate

class irodsCreateTicket(QWidget, Ui_tabticketCreate):
    def __init__(self, ic, ienv):
        self.ic = ic
        super(irodsCreateTicket, self).__init__()
        if getattr(sys, 'frozen', False):
            super(irodsCreateTicket, self).setupUi(self)
        else:
            loadUi("gui/ui_files/tabTicketCreate.ui", self)


        self.irodsmodel = IrodsModel(ic, self.irodsFsTreeView)
        self.irodsFsTreeView.setModel(self.irodsmodel)
        self.irodsRootColl = '/'+ic.session.zone
        self.irodsmodel.setHorizontalHeaderLabels([self.irodsRootColl,
                                              'Level', 'iRODS ID',
                                              'parent ID', 'type'])
        self.irodsFsTreeView.expanded.connect(self.irodsmodel.refreshSubTree)
        self.irodsFsTreeView.clicked.connect(self.irodsmodel.refreshSubTree)
        self.irodsmodel.initTree()

        self.irodsFsTreeView.setHeaderHidden(True)
        self.irodsFsTreeView.header().setDefaultSectionSize(180)
        self.irodsFsTreeView.setColumnHidden(1, True)
        self.irodsFsTreeView.setColumnHidden(2, True)
        self.irodsFsTreeView.setColumnHidden(3, True)
        self.irodsFsTreeView.setColumnHidden(4, True)

        self.createTicketButton.clicked.connect(self.createTicket)

    def createTicket(self):
        self.infoLabel.clear()
        self.ticketInfoBrowser.clear()
        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.WaitCursor))
        self.createTicketButton.setEnabled(False)

        # gather info
        selected_folders = self.irodsFsTreeView.selectedIndexes()
        if len(selected_folders) != 1:
            self.infoLabel.setText("ERROR: Please select one collection.")
            self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
            self.createTicketButton.setEnabled(True)
            return
        idx = selected_folders[0]
        path = self.irodsmodel.irodsPathFromTreeIdx(idx)
        if path is None or self.ic.session.data_objects.exists(path):
            self.infoLabel.setText("ERROR: Please select a collection.")
            self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
            self.createTicketButton.setEnabled(True)
            return

        acls = [(acl.user_name, acl.access_name) for acl in self.ic.getPermissions(path)]
        if (self.ic.session.username, "own") in acls:
            date = self.calendar.selectedDate()
            # format of time string for irods: 2012-05-07.23:00:00
            expiryString = str(date.toPyDate())+'.23:59:59'
            ticket, expiryDate = self.ic.createTicket(path, expiryString)
            self.ticketInfoBrowser.append("iRODS server: \t"+self.ic.session.host)
            self.ticketInfoBrowser.append("iRODS path:\t"+path)
            self.ticketInfoBrowser.append("iRODS Ticket:\t"+ticket)
            if self.ic.__name__ == "irodsConnector":
                self.ticketInfoBrowser.append("Expiry date:\tNot set (linux only)")
            else:
                self.ticketInfoBrowser.append("Expiry date:\t"+expiryDate)

        else:
            self.infoLabel.setText("ERROR: Insufficient rights, you need to be owner.")
            self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
            self.createTicketButton.setEnabled(True)
            return
    
        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
        self.createTicketButton.setEnabled(True)
