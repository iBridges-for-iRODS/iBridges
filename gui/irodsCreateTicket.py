from PyQt6 import QtGui, QtCore
from gui.irodsTreeView import IrodsModel


class irodsCreateTicket:
    def __init__(self, widget, ic, ienv):

        self.ic = ic
        self.widget = widget

        self.irodsmodel = IrodsModel(ic, self.widget.irodsFsTreeView)
        self.widget.irodsFsTreeView.setModel(self.irodsmodel)
        self.irodsRootColl = '/'+ic.session.zone
        self.irodsmodel.setHorizontalHeaderLabels([self.irodsRootColl,
                                              'Level', 'iRODS ID',
                                              'parent ID', 'type'])
        self.widget.irodsFsTreeView.expanded.connect(self.irodsmodel.refreshSubTree)
        self.widget.irodsFsTreeView.clicked.connect(self.irodsmodel.refreshSubTree)
        self.irodsmodel.initTree()

        self.widget.irodsFsTreeView.setHeaderHidden(True)
        self.widget.irodsFsTreeView.header().setDefaultSectionSize(180)
        self.widget.irodsFsTreeView.setColumnHidden(1, True)
        self.widget.irodsFsTreeView.setColumnHidden(2, True)
        self.widget.irodsFsTreeView.setColumnHidden(3, True)
        self.widget.irodsFsTreeView.setColumnHidden(4, True)

        self.widget.createTicketButton.clicked.connect(self.createTicket)

    def createTicket(self):
        self.widget.infoLabel.clear()
        self.widget.ticketInfoBrowser.clear()
        self.widget.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.WaitCursor))
        self.widget.createTicketButton.setEnabled(False)

        # gather info
        idx, path = self.irodsmodel.get_checked()
        if path is None or self.ic.session.data_objects.exists(path):
            self.widget.infoLabel.setText("ERROR: Please select a collection.")
            self.widget.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
            self.widget.createTicketButton.setEnabled(True)
            return

        acls = [(acl.user_name, acl.access_name) for acl in self.ic.getPermissions(path)]
        if (self.ic.session.username, "own") in acls:
            date = self.widget.calendar.selectedDate()
            # format of time string for irods: 2012-05-07.23:00:00
            expiryString = str(date.toPyDate())+'.23:59:59'
            ticket, expiryDate = self.ic.createTicket(path, expiryString)
            self.widget.ticketInfoBrowser.append("iRODS server: \t"+self.ic.session.host)
            self.widget.ticketInfoBrowser.append("iRODS path:\t"+path)
            self.widget.ticketInfoBrowser.append("iRODS Ticket:\t"+ticket)
            if self.ic.__name__ == "irodsConnector":
                self.widget.ticketInfoBrowser.append("Expiry date:\tNot set (linux only)")
            else:
                self.widget.ticketInfoBrowser.append("Expiry date:\t"+expiryDate)

        else:
            self.widget.infoLabel.setText("ERROR: Insufficient rights, you need to be owner.")
            self.widget.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
            self.widget.createTicketButton.setEnabled(True)
            return
    
        self.widget.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
        self.widget.createTicketButton.setEnabled(True)
