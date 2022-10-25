"""Upload/download window residing in a tab.

"""
import os

import PyQt6.QtCore
import PyQt6.QtGui
import PyQt6.QtWidgets

import gui
import utils

REMOVE_LOCAL = 'ui_remLocalcopy'
UPLOAD_HOSTS = [
    "scomp1461.wur.nl",
    "npec-icat.irods.surfsara.nl",
]
UPLOAD_MODE = 'ui_uplMode'


class IrodsUpDownload():
    """Window for transfers between the local file system and the iRODS
    system.

    """

    def __init__(self, widget, ic, ienv):
        """Construct the transfer window.

        Parameters
        ----------
        widget : QtWidgets
            Common widget container.
        ic : IrodsConnector
            Connection to an iRODS session.
        ienv : dict
            iRODS environment settings.

        """
        self.ic = ic
        self.widget = widget
        self.ienv = ienv
        self.localmodel = None
        self.irodsmodel = None
        # syncing or not
        self.syncing = False
        self._initialize_local_model()
        self._initialize_irods_model()
        self._create_buttons()
        self._create_resource_selector()
        self.upload_window = None

    def _initialize_local_model(self):
        """Initialize local QTreeView.

        """
        self.localmodel = PyQt6.QtGui.QFileSystemModel(
            self.widget.localFsTreeView)
        self.widget.localFsTreeView.setModel(self.localmodel)
        # Hide all columns except the Name
        self.widget.localFsTreeView.setColumnHidden(1, True)
        self.widget.localFsTreeView.setColumnHidden(2, True)
        self.widget.localFsTreeView.setColumnHidden(3, True)
        self.widget.localFsTreeView.header().setSectionResizeMode(
            PyQt6.QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        home_location = PyQt6.QtCore.QStandardPaths.standardLocations(
            PyQt6.QtCore.QStandardPaths.StandardLocation.HomeLocation)[0]
        index = self.localmodel.setRootPath(home_location)
        self.widget.localFsTreeView.setCurrentIndex(index)

    def _initialize_irods_model(self):
        """Initialize iRODS QTreeView.

        """
        self.irodsmodel = gui.irodsTreeView.IrodsModel(
            self.ic, self.widget.irodsFsTreeView)
        self.widget.irodsFsTreeView.setModel(self.irodsmodel)
        self.widget.irodsZoneLabel.setText(f'{self.irodsmodel.zone_path}:')
        self.widget.irodsFsTreeView.expanded.connect(
            self.irodsmodel.refresh_subtree)
        self.widget.irodsFsTreeView.clicked.connect(
            self.irodsmodel.refresh_subtree)
        self.irodsmodel.init_tree()
        self.widget.irodsFsTreeView.setColumnHidden(1, True)
        self.widget.irodsFsTreeView.setColumnHidden(2, True)
        self.widget.irodsFsTreeView.setColumnHidden(3, True)
        self.widget.irodsFsTreeView.setColumnHidden(4, True)
        # XXX unsuccessful attempt to open home in tree view
        # index = self.irodsmodel.indexFromItem(
        #     PyQt6.QtGui.QStandardItem(self.irodsmodel.base_path))
        # self.widget.irodsFsTreeView.setCurrentIndex(index)
        # self.widget.irodsFsTreeView.scrollTo(index)
        # XXX

    def _create_buttons(self):
        """Create panel buttons.

        """
        self.widget.UploadButton.clicked.connect(self.upload)
        self.widget.DownloadButton.clicked.connect(self.download)
        self.widget.createFolderButton.clicked.connect(self.create_folder)
        self.widget.createCollButton.clicked.connect(
            self.create_collection)

    def _create_resource_selector(self):
        """Create resource drop-down menu.

        """
        default_resc = self.ic.default_resc
        names, spaces = self.ic.list_resources()
        resources = [
            f'{name} / {space}' for name, space in zip(names, spaces)]
        self.widget.resourceBox.clear()
        self.widget.resourceBox.addItems(resources)
        if default_resc in names:
            ridx = names.index(default_resc)
            index = self.widget.resourceBox.findText(resources[ridx])
            self.widget.resourceBox.setCurrentIndex(index)

    def enable_buttons(self, enable):
        """Set the state for all buttons.

        Parameters
        ----------
        enable : bool

        """
        self.widget.UploadButton.setEnabled(enable)
        self.widget.DownloadButton.setEnabled(enable)
        self.widget.createFolderButton.setEnabled(enable)
        self.widget.createCollButton.setEnabled(enable)
        self.widget.localFsTreeView.setEnabled(enable)
        self.widget.localFsTreeView.setEnabled(enable)

    def info_popup(self, message):
        """Display `message` in a pop-up subwindow.

        """
        PyQt6.QtWidgets.QMessageBox.information(
            self.widget, 'Information', message)

    def get_resource(self):
        """Get the resource name from the resource box.

        Returns
        -------
        str
            Current iRODS resource name.

        """
        return self.widget.resourceBox.currentText().split(' / ')[0]

    def get_remote_local_copy_state(self):
        """Get state of remote/local copy button.

        Returns
        -------
        bool
            Button checked state.

        """
        return self.widget.rLocalcopyCB.isChecked()

    def create_folder(self):
        """Create a directory/folder on the local filesystem.

        """
        indexes = self.widget.localFsTreeView.selectedIndexes()
        if len(indexes):
            parent = self.localmodel.filepath(indexes[0])
            if os.path.isfile(parent):
                self.widget.errorLabel.setText('No parent folder selected.')
            else:
                create_dir_widget = gui.popupWidgets.createDirectory(parent)
                create_dir_widget.exec()
        else:
            self.widget.errorLabel.setText('No parent folder selected.')

    def create_collection(self):
        """Create collection on the remote iRODS system.

        """
        indexes = self.widget.irodsFsTreeView.selectedIndexes()
        if len(indexes):
            index = indexes[0]
            parent = self.irodsmodel.irods_path_from_tree_index(index)
            if self.ic.dataobject_exists(parent):
                self.widget.errorLabel.setText(
                    "No parent collection selected.")
            else:
                create_coll_widget = gui.popupWidgets.irodsCreateCollection(
                    parent, self.ic)
                create_coll_widget.exec()
                self.irodsmodel.refresh_subtree(index)
        else:
            self.widget.errorLabel.setText("No parent collection selected.")

    def upload(self):
        """Upload a file or directory/folder to iRODS and refresh the
        tree views.

        """
        self.enable_buttons(False)
        self.widget.errorLabel.clear()
        local_path, irods_index, irods_path = self.get_paths_from_trees()
        if local_path is None or irods_path is None:
            self.widget.errorLabel.setText(
                    "ERROR Up/Download: Please select source and destination.")
            self.enable_buttons(True)
            return
        if not self.ic.collection_exists(irods_path):
            self.widget.errorLabel.setText(
                    "ERROR UPLOAD: iRODS destination is a file, must be a collection.")
            self.enable_buttons(True)
            return
        dest_coll = self.ic.get_collection(irods_path)
        self.upload_window = gui.dataTransfer.dataTransfer(
            self.ic, True, local_path, dest_coll, irods_index,
            self.get_resource())
        self.upload_window.finished.connect(self.transfer_complete)

    def transfer_complete(self, success, irods_index):
        """Refresh iRODS subtree and `irods_index` upon transfer
        completion.

        Parameters
        ----------
        success : bool
            Operation was successful.
        irods_index : int
            Location in the iRODS tree view.

        """
        if success:
            if irods_index is not None:
                self.irodsmodel.refresh_subtree(irods_index)
            self.widget.errorLabel.setText(
                "INFO UPLOAD/DOWLOAD: completed.")
        self.upload_window = None
        self.enable_buttons(True)

    def download(self):
        """Download an iRODS data object or collection to the local
        filesystem and refresh the tree views.

        """
        self.enable_buttons(False)
        self.widget.errorLabel.clear()
        (local_path, _, irods_path) = self.get_paths_from_trees()
        if local_path is None or irods_path is None:
            self.widget.errorLabel.setText(
                "ERROR Up/Download: Please select source and destination.")
            self.enable_buttons(True)
            return
        if os.path.isfile(local_path):
            self.widget.errorLabel.setText(
                "ERROR DOWNLOAD: Local Destination is file, must be folder.")
            self.enable_buttons(True)
            return
        if self.ic.dataobject_exists(irods_path):
            irods_obj = self.ic.session.data_objects.get(irods_path)
        else:
            irods_obj = self.ic.get_collection(irods_path)
        self.upload_window = gui.dataTransfer.dataTransfer(
            self.ic, False, local_path, irods_obj)
        self.upload_window.finished.connect(self.transfer_complete)

    def get_paths_from_trees(self):
        """Get both local and iRODS path from the tree views.

        """
        src_index = self.widget.localFsTreeView.selectedIndexes()[0]
        src_path = self.localmodel.filePath(src_index)
        if src_path is None:
            return None, None, None
        dst_index = self.widget.irodsFsTreeView.selectedIndexes()[0]
        dst_path = self.irodsmodel.irods_path_from_tree_index(dst_index)
        if dst_index is None:
            return None, None, None
        return src_path, dst_index, dst_path
