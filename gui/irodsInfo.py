"""Provide the GUI with iRODS information
"""
import PyQt5
import PyQt5.QtWidgets


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
        self.widget.setCursor(PyQt5.QtGui.QCursor(PyQt5.QtCore.Qt.WaitCursor))
        # irods Zone
        self.widget.zoneLabel.setText(self.ic.session.zone)
        # irods user
        self.widget.userLabel.setText(self.ic.session.username)
        # irods user type and groups
        user_type, user_groups = self.ic.get_user_info()
        self.widget.typeLabel.setText(user_type)
        self.widget.groupsLabel.setText('\n'.join(user_groups))
        # default resource
        self.widget.rescLabel.setText(self.ic.default_resc)
        # irods server and version
        self.widget.serverLabel.setText(self.ic.session.host)
        self.widget.versionLabel.setText(
            '.'.join(str(num) for num in self.ic.session.server_version))
        # irods resources
        names_spaces = list(zip(*self.ic.list_resources()))
        if not self.ic.ienv.get('force_unknown_free_space'):
            names, spaces = zip(*(
                (name, space) for name, space in names_spaces
                if space != 0))
        else:
            names, spaces = zip(*names_spaces)
        resources = [
            (name, f'{round(space / 2**30)}') for name, space in
            zip(names, spaces)]
        self.widget.rescTable.setRowCount(len(resources))
        row = 0
        for name, space in resources:
            resc = self.ic.get_resource(name)
            self.widget.rescTable.setItem(row, 0, PyQt5.QtWidgets.QTableWidgetItem(name))
            self.widget.rescTable.setItem(row, 1, PyQt5.QtWidgets.QTableWidgetItem(space))
            self.widget.rescTable.setItem(row, 2, PyQt5.QtWidgets.QTableWidgetItem(resc.status))
            row = row + 1
        self.widget.rescTable.resizeColumnsToContents()
        self.widget.setCursor(PyQt5.QtGui.QCursor(PyQt5.QtCore.Qt.ArrowCursor))
