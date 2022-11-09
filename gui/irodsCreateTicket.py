"""Create iRODS ticket tab.

"""
import sys

from PyQt6 import QtGui, QtCore
from PyQt6.QtWidgets import QWidget
from PyQt6.uic import loadUi

from gui.irodsTreeView import IrodsModel
from gui.ui_files.tabTicketCreate import Ui_tabticketCreate


class irodsCreateTicket(QWidget, Ui_tabticketCreate):
    def __init__(self, ic):
        self.ic = ic
        super().__init__()
        if getattr(sys, 'frozen', False):
            super().setupUi(self)
        else:
            loadUi("gui/ui_files/tabTicketCreate.ui", self)
        self.irodsmodel = IrodsModel(ic, self.irodsFsTreeView)
        self.irodsFsTreeView.setModel(self.irodsmodel)
        self.irodsRootColl = '/'+ic.session.zone
        self.irodsmodel.setHorizontalHeaderLabels(
            [self.irodsRootColl, 'Level', 'iRODS ID', 'parent ID', 'type'])
        self.irodsFsTreeView.expanded.connect(self.irodsmodel.refresh_subtree)
        self.irodsFsTreeView.clicked.connect(self.irodsmodel.refresh_subtree)
        self.irodsmodel.init_tree()
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
        indexes = self.irodsFsTreeView.selectedIndexes()
        path = ''
        if len(indexes):
            path = self.irodsmodel.irods_path_from_tree_index(indexes[0])
        if not self.ic.session.collections.exists(path):
            self.infoLabel.setText("ERROR: Please select a collection.")
            self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
            self.createTicketButton.setEnabled(True)
            return
        acls = [(acl.user_name, acl.access_name) for acl in self.ic.get_permissions(path)]
        if (self.ic.session.username, "own") in acls:
            date = self.calendar.selectedDate()
            # format of time string for irods: 2012-05-07.23:00:00
            expiryString = str(date.toPyDate())+'.23:59:59'
            ticket, expiryDate = self.ic.createTicket(path, expiryString)
            self.ticketInfoBrowser.append("iRODS server: \t"+self.ic.session.host)
            self.ticketInfoBrowser.append("iRODS path:\t"+path)
            self.ticketInfoBrowser.append("iRODS Ticket:\t"+ticket)
            if self.ic.__name__ == "IrodsConnector":
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
