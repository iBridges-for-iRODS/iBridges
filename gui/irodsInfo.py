"""Provide the GUI with iRODS information
"""
from PyQt5 import QtWidgets
from PyQt5 import QtCore
from PyQt5 import QtGui

from utils.irodsConnector import FreeSpaceNotSet, ResourceDoesNotExist


class irodsInfo():
    """Set iRODS information in the GUI
    """

    def __init__(self, widget, ic):
        self.ic = ic
        self.widget = widget
        self.widget.refreshButton.clicked.connect(self.refresh_info)
        self.refresh_info()

    def refresh_info(self):
        """Find and set the information of the connected iRODS system
        including the availble top-level resources.
        """
        self.widget.rescTable.setRowCount(0)
        self.widget.setCursor(QtGui.QCursor(QtCore.Qt.WaitCursor))
        # irods Zone
        self.widget.zoneLabel.setText(self.ic.session.zone)
        # irods user
        self.widget.userLabel.setText(self.ic.session.username)
        # irods user type and groups
        user_type, user_groups = self.ic.getUserInfo()
        group_names = [x for x in user_groups if not isinstance(x, int)]
        self.widget.typeLabel.setText(user_type[0])
        self.widget.groupsLabel.setText('\n'.join(group_names))
        # defaul resource
        self.widget.rescLabel.setText(self.ic.defaultResc)
        # irods server and version
        self.widget.serverLabel.setText(self.ic.session.host)
        self.widget.versionLabel.setText(
            '.'.join(str(num) for num in self.ic.session.server_version))
        # irods resources
        resc_names = self.ic.listResources()
        resources = []
        for resc_name in resc_names:
            try:
                free_space = self.ic.resourceSpace(resc_name)
                # Round to nearest GiB
                resources.append((resc_name, str(round(free_space / 2**30))))
            except FreeSpaceNotSet:
                resources.append((resc_name, "no information"))
            except ResourceDoesNotExist:
                resources.append((resc_name, "invalid resource"))
        self.widget.rescTable.setRowCount(len(resources))
        row = 0
        for resc_name, free_space in resources:
            resc = self.ic.getResource(resc_name)
            self.widget.rescTable.setItem(row, 0, QtWidgets.QTableWidgetItem(resc_name))
            self.widget.rescTable.setItem(row, 1, QtWidgets.QTableWidgetItem(free_space))
            self.widget.rescTable.setItem(row, 2, QtWidgets.QTableWidgetItem(resc.status))
            row = row + 1
        self.widget.rescTable.resizeColumnsToContents()
        self.widget.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
