from PyQt5 import QtWidgets
from PyQt5 import QtCore
from PyQt5 import QtGui

class irodsInfo():
    def __init__(self, widget, ic):

        self.ic = ic
        self.widget = widget

        self.widget.refreshButton.clicked.connect(self.refreshInfo)
        self.refreshInfo()


    def refreshInfo(self):

        self.widget.rescTable.setRowCount(0)
        self.widget.setCursor(QtGui.QCursor(QtCore.Qt.WaitCursor))

        #irods Zone
        self.widget.zoneLabel.setText(self.ic.session.zone)
        #irods user
        self.widget.userLabel.setText(self.ic.session.username)
        #irods user type and groups
        userType, userGroups = self.ic.getUserInfo()
        groupNames = [x for x in userGroups if not isinstance(x, int)]
        self.widget.typeLabel.setText(userType[0])
        self.widget.groupsLabel.setText('\n'.join(groupNames))
        #irods server and version
        self.widget.serverLabel.setText(self.ic.session.host)
        self.widget.versionLabel.setText(
            '.'.join(str(num) for num in self.ic.session.server_version))
        #irods resources
        resourceNames = self.ic.listResources()
        try:
            resources = [(name, str(round(int(self.ic.resourceSize(name))/1024**3)))
                     for name in resourceNames]
        except:
            resources = [(name, "no information") for name in resourceNames]

        self.widget.rescTable.setRowCount(len(resources))
        row = 0
        for rescName, rescSize in resources:
            self.widget.rescTable.setItem(row, 0, QtWidgets.QTableWidgetItem(rescName))
            self.widget.rescTable.setItem(row, 1, QtWidgets.QTableWidgetItem(rescSize))
            row = row + 1
        self.widget.rescTable.resizeColumnsToContents()
        self.widget.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
