"""Upload/download window residing in a tab.

"""
import os
import sys

import PyQt6.QtCore
import PyQt6.QtGui
import PyQt6.QtWidgets
import PyQt6.uic

import gui
import utils

REMOVE_LOCAL = 'ui_remLocalcopy'
UPLOAD_HOSTS = [
    "scomp1461.wur.nl",
    "npec-icat.irods.surfsara.nl",
]
UPLOAD_MODE = 'ui_uplMode'


class IrodsUpDownload(PyQt6.QtWidgets.QWidget,
                      gui.ui_files.tabUpDownload.Ui_tabUpDownload,
                      utils.context.ContextContainer):
    """Window for transfers between the local file system and the iRODS
    system.

    """

    def __init__(self):
        """Construct the transfer window.

        """
        super().__init__()
        if getattr(sys, 'frozen', False):
            super().setupUi(self)
        else:
            PyQt6.uic.loadUi("gui/ui_files/tabUpDownload.ui", self)
        self.localmodel = None
        self.irodsmodel = None
        self.syncing = False
        self._initialize_local_model()
        self._initialize_irods_model()
        self._create_buttons()
        self._create_resource_selector()
        self.upload_window = None

    def _initialize_local_model(self):
        """Initialize local QTreeView.

        """
        self.localmodel = PyQt6.QtGui.QFileSystemModel(self.localFsTreeView)
        self.localFsTreeView.setModel(self.localmodel)
        # Hide all columns except the Name
        self.localFsTreeView.setColumnHidden(1, True)
        self.localFsTreeView.setColumnHidden(2, True)
        self.localFsTreeView.setColumnHidden(3, True)
        self.localFsTreeView.header().setSectionResizeMode(
            PyQt6.QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        # TODO standardize tree initialization
        home_location = PyQt6.QtCore.QStandardPaths.standardLocations(
            PyQt6.QtCore.QStandardPaths.StandardLocation.HomeLocation)[0]
        index = self.localmodel.setRootPath(home_location)
        self.localFsTreeView.setCurrentIndex(index)

    def _initialize_irods_model(self):
        """Initialize iRODS QTreeView.

        """
        self.irodsmodel = gui.irodsTreeView.IrodsModel(self.irodsFsTreeView)
        self.irodsFsTreeView.setModel(self.irodsmodel)
        self.irodsZoneLabel.setText(f'{self.irodsmodel.zone_path}:')
        self.irodsFsTreeView.expanded.connect(
            self.irodsmodel.refresh_subtree)
        self.irodsFsTreeView.clicked.connect(
            self.irodsmodel.refresh_subtree)
        self.irodsmodel.init_tree()
        self.irodsFsTreeView.setHeaderHidden(True)
        self.irodsFsTreeView.header().setDefaultSectionSize(180)
        self.irodsFsTreeView.setColumnHidden(1, True)
        self.irodsFsTreeView.setColumnHidden(2, True)
        self.irodsFsTreeView.setColumnHidden(3, True)
        self.irodsFsTreeView.setColumnHidden(4, True)
        # TODO standardize tree initialization
        # index = self.irodsmodel.indexFromItem(
        #     PyQt6.QtGui.QStandardItem(self.irodsmodel.base_path))
        # self.irodsFsTreeView.setCurrentIndex(index)
        # self.irodsFsTreeView.scrollTo(index)


    def _create_buttons(self):
        """Create panel buttons.

        """
        self.UploadButton.clicked.connect(self.upload)
        self.DownloadButton.clicked.connect(self.download)
        self.createFolderButton.clicked.connect(self.create_folder)
        self.createCollButton.clicked.connect(
            self.create_collection)

    def _create_resource_selector(self):
        """Create resource drop-down menu.

        """
        default_resc = self.conn.default_resc
        names, spaces = self.conn.list_resources()
        resources = [
            f'{name} / {space}' for name, space in zip(names, spaces)]
        self.resourceBox.clear()
        self.resourceBox.addItems(resources)
        if default_resc in names:
            ridx = names.index(default_resc)
            index = self.resourceBox.findText(resources[ridx])
            self.resourceBox.setCurrentIndex(index)

    def enable_buttons(self, enable):
        """Set the state for all buttons.

        Parameters
        ----------
        enable : bool

        """
        self.UploadButton.setEnabled(enable)
        self.DownloadButton.setEnabled(enable)
        self.createFolderButton.setEnabled(enable)
        self.createCollButton.setEnabled(enable)
        self.localFsTreeView.setEnabled(enable)
        self.localFsTreeView.setEnabled(enable)

    def info_popup(self, message):
        """Display `message` in a pop-up subwindow.

        """
        PyQt6.QtWidgets.QMessageBox.information(
            self, 'Information', message)

    def get_resource(self):
        """Get the resource name from the resource box.

        Returns
        -------
        str
            Current iRODS resource name.

        """
        return self.resourceBox.currentText().split(' / ')[0]

    def get_remote_local_copy_state(self):
        """Get state of remote/local copy button.

        Returns
        -------
        bool
            Button checked state.

        """
        return self.rLocalcopyCB.isChecked()

    def create_folder(self):
        """Create a directory/folder on the local filesystem.

        """
        indexes = self.localFsTreeView.selectedIndexes()
        if len(indexes):
            parent = self.localmodel.filePath(indexes[0])
            if os.path.isfile(parent):
                self.errorLabel.setText('No parent folder selected.')
            else:
                create_dir_widget = gui.popupWidgets.createDirectory(parent)
                create_dir_widget.exec()
        else:
            self.errorLabel.setText('No parent folder selected.')

    def create_collection(self):
        """Create collection on the remote iRODS system.

        """
        indexes = self.irodsFsTreeView.selectedIndexes()
        if len(indexes):
            index = indexes[0]
            parent = self.irodsmodel.irods_path_from_tree_index(index)
            if self.conn.dataobject_exists(parent):
                self.errorLabel.setText(
                    "No parent collection selected.")
            else:
                create_coll_widget = gui.popupWidgets.irodsCreateCollection(
                    parent)
                create_coll_widget.exec()
                self.irodsmodel.refresh_subtree(index)
        else:
            self.errorLabel.setText("No parent collection selected.")

    def upload(self):
        """Upload a file or directory/folder to iRODS and refresh the
        tree views.

        """
        self.enable_buttons(False)
        self.errorLabel.clear()
        local_path, irods_index, irods_path = self.get_paths_from_trees()
        if local_path is None or irods_path is None:
            self.errorLabel.setText(
                    "ERROR Up/Download: Please select source and destination.")
            self.enable_buttons(True)
            return
        if not self.conn.collection_exists(irods_path):
            self.errorLabel.setText(
                    "ERROR UPLOAD: iRODS destination is a file, must be a collection.")
            self.enable_buttons(True)
            return
        dest_coll = self.conn.get_collection(irods_path)
        self.upload_window = gui.dataTransfer.dataTransfer(
            True, local_path, dest_coll, irods_index,
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
            self.errorLabel.setText("INFO UPLOAD/DOWLOAD: completed.")
        self.upload_window = None
        self.enable_buttons(True)

    def download(self):
        """Download an iRODS data object or collection to the local
        filesystem and refresh the tree views.

        """
        self.enable_buttons(False)
        self.errorLabel.clear()
        (local_path, _, irods_path) = self.get_paths_from_trees()
        if local_path is None or irods_path is None:
            self.errorLabel.setText(
                "ERROR Up/Download: Please select source and destination.")
            self.enable_buttons(True)
            return
        if os.path.isfile(local_path):
            self.errorLabel.setText(
                "ERROR DOWNLOAD: Local Destination is file, must be folder.")
            self.enable_buttons(True)
            return
        # TODO check if querying for collection is faster
        if self.conn.dataobject_exists(irods_path):
            irods_obj = self.conn.get_dataobject(irods_path)
        else:
            irods_obj = self.conn.get_collection(irods_path)
        self.upload_window = gui.dataTransfer.dataTransfer(
            False, local_path, irods_obj)
        self.upload_window.finished.connect(self.transfer_complete)

    def get_paths_from_trees(self):
        """Get both local and iRODS path from the tree views.

        """
        selected_src_index = self.localFsTreeView.selectedIndexes()
        if len(selected_src_index) == 0:
            return None, None, None
        src_index = selected_src_index[0]
        src_path = self.localmodel.filePath(src_index)
        if src_path is None:
            return None, None, None
        selected_dst_index = self.irodsFsTreeView.selectedIndexes()
        if len(selected_dst_index) == 0:
            return None, None, None
        dst_index = selected_dst_index[0]
        dst_path = self.irodsmodel.irods_path_from_tree_index(dst_index)
        if dst_index is None:
            return None, None, None
        return src_path, dst_index, dst_path
