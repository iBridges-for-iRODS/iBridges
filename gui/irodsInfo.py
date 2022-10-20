import sys
from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.uic import loadUi
from PyQt6.QtWidgets import QWidget

from gui.ui_files.tabInfo import Ui_tabInfo

class irodsInfo(QWidget, Ui_tabInfo):
    def __init__(self, ic):
        self.ic = ic
        super(irodsInfo, self).__init__()
        if getattr(sys, 'frozen', False):
            super(irodsInfo, self).setupUi(self)
        else:
            loadUi("gui/ui_files/tabInfo.ui", self)

        self.refreshButton.clicked.connect(self.refreshInfo)
        self.refreshInfo()

    def refreshInfo(self):

        self.rescTable.setRowCount(0)
        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.WaitCursor))

        # irods Zone
        self.zoneLabel.setText(self.ic.session.zone)
        # irods user
        self.userLabel.setText(self.ic.session.username)
        # irods user type and groups
        userType, userGroups = self.ic.getUserInfo()
        groupNames = [x for x in userGroups if not isinstance(x, int)]
        self.typeLabel.setText(userType[0])
        self.groupsLabel.setText('\n'.join(groupNames))
        # default resource
        self.rescLabel.setText(self.ic.defaultResc)
        
        # irods server and version
        self.serverLabel.setText(self.ic.session.host)
        self.versionLabel.setText(
            '.'.join(str(num) for num in self.ic.session.server_version))
        # irods resources
        resourceNames = set([i[0] for i in self.ic.listResources()])
        resources = []
        for name in resourceNames:
            size = self.ic.resourceSize(name)
            if size:
                resources.append((name, str(round(int(self.ic.resourceSize(name))/1024**3))))
            else:
                resources.append((name, "no information"))

        self.rescTable.setRowCount(len(resources))
        row = 0
        for rescName, rescSize in resources:
            resc = self.ic.getResource(rescName)
            self.rescTable.setItem(row, 0, QtWidgets.QTableWidgetItem(rescName))
            self.rescTable.setItem(row, 1, QtWidgets.QTableWidgetItem(rescSize))
            self.rescTable.setItem(row, 2, QtWidgets.QTableWidgetItem(resc.status))
            row = row + 1
        self.rescTable.resizeColumnsToContents()
        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
