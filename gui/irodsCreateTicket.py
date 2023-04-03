"""Create iRODS ticket tab.

"""
import sys

from PyQt6 import QtGui, QtCore
from PyQt6.QtWidgets import QWidget
from PyQt6.uic import loadUi

from gui.irodsTreeView import IrodsModel
from gui.ui_files.tabTicketCreate import Ui_tabticketCreate
import utils

context = utils.context.Context()


class irodsCreateTicket(QWidget, Ui_tabticketCreate):
    def __init__(self):
        self.conn = context.conn
        super().__init__()
        if getattr(sys, 'frozen', False):
            super().setupUi(self)
        else:
            loadUi("gui/ui_files/tabTicketCreate.ui", self)
        self.irodsmodel = IrodsModel(conn, self.irodsFsTreeView)
        self.irodsFsTreeView.setModel(self.irodsmodel)
        self.irodsRootColl = '/' + conn.zone
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

        self.createTicketButton.clicked.connect(self.create_ticket)

    def create_ticket(self):
        self.infoLabel.clear()
        self.ticketInfoBrowser.clear()
        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.WaitCursor))
        self.createTicketButton.setEnabled(False)
        # Gather info.
        indexes = self.irodsFsTreeView.selectedIndexes()
        obj_path = ''
        if len(indexes):
            obj_path = self.irodsmodel.irods_path_from_tree_index(indexes[0])
        if not self.conn.collection_exists(obj_path):
            self.infoLabel.setText('ERROR: Please select a collection.')
            self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
            self.createTicketButton.setEnabled(True)
            return
        acls = [(acl.user_name, acl.access_name) for acl in self.conn.get_permissions(obj_path)]
        if (self.conn.username, 'own') in acls:
            date = self.calendar.selectedDate()
            # format of time string for irods: 2012-05-07.23:00:00
            expiry_string = f'{date.toPyDate()}.23:59:59'
            ticket_name, expiration_set = self.conn.create_ticket(obj_path, expiry_string)
            self.ticketInfoBrowser.append(f'iRODS server:\t{self.conn.host}')
            self.ticketInfoBrowser.append(f'iRODS path:\t{obj_path}')
            self.ticketInfoBrowser.append(f'iRODS Ticket:\t{ticket_name}')
            if expiration_set:
                self.ticketInfoBrowser.append(f'Expiry date:\t{expiry_string}')
        else:
            self.infoLabel.setText('ERROR: Insufficient rights, you need to be owner.')
            self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
            self.createTicketButton.setEnabled(True)
            return
        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
        self.createTicketButton.setEnabled(True)
