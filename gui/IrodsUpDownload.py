"""Upload/download window residing in a tab.

"""
import os

import PyQt5.QtCore
import PyQt5.QtWidgets

import gui
import utils

DEFAULT_RESC = 'irods_default_resource'
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
        # syncing or not
        self.syncing = False
        self._initialize_local_model()
        self._initialize_irods_model()
        self._create_buttons()
        self._create_resource_selector()
        self._configure_continuous_upload()
        self.upload_window = None

    def _initialize_local_model(self):
        """Initialize local QTreeView.

        """
        self.localmodel = gui.checkableFsTree.checkableFsTreeModel(
            self.widget.localFsTreeView)
        self.widget.localFsTreeView.setModel(self.localmodel)
        # Hide all columns except the Name
        self.widget.localFsTreeView.setColumnHidden(1, True)
        self.widget.localFsTreeView.setColumnHidden(2, True)
        self.widget.localFsTreeView.setColumnHidden(3, True)
        self.widget.localFsTreeView.header().setSectionResizeMode(
            PyQt5.QtWidgets.QHeaderView.ResizeToContents)
        # TODO discover proper way to determine local home directory
        home_location = PyQt5.QtCore.QStandardPaths.standardLocations(
            PyQt5.QtCore.QStandardPaths.HomeLocation)[0]
        index = self.localmodel.setRootPath(home_location)
        self.widget.localFsTreeView.setCurrentIndex(index)
        self.localmodel.initial_expand()

    def _initialize_irods_model(self):
        """Initialize iRODS QTreeView.

        """
        irods_root_path = f'/{self.ic.session.zone}/home'
        self.widget.irodsZoneLabel.setText(f'{irods_root_path}:')
        self.irodsmodel = gui.irodsTreeView.IrodsModel(
            self.ic, self.widget.irodsFsTreeView)
        self.widget.irodsFsTreeView.setModel(self.irodsmodel)
        header_labels = [
            irods_root_path,
            'Level',
            'iRODS ID',
            'parent ID',
            'type',
        ]
        self.irodsmodel.setHorizontalHeaderLabels(header_labels)
        self.widget.irodsFsTreeView.expanded.connect(
            self.irodsmodel.refreshSubTree)
        self.widget.irodsFsTreeView.clicked.connect(
            self.irodsmodel.refreshSubTree)
        self.irodsmodel.initTree()
        self.widget.irodsFsTreeView.setHeaderHidden(True)
        self.widget.irodsFsTreeView.header().setDefaultSectionSize(180)
        self.widget.irodsFsTreeView.setColumnHidden(1, True)
        self.widget.irodsFsTreeView.setColumnHidden(2, True)
        self.widget.irodsFsTreeView.setColumnHidden(3, True)
        self.widget.irodsFsTreeView.setColumnHidden(4, True)

    def _create_buttons(self):
        """Create panel buttons.

        """
        self.widget.UploadButton.clicked.connect(self.upload)
        self.widget.DownloadButton.clicked.connect(self.download)
        # self.widget.ContUplBut.clicked.connect(self.cont_upload)
        # For first release hide special buttons
        self.widget.ContUplBut.setHidden(True)
        self.widget.uplSetGB_2.setHidden(True)
        self.widget.createFolderButton.clicked.connect(self.create_folder)
        self.widget.createCollButton.clicked.connect(
            self.create_collection)

    def _create_resource_selector(self):
        """Create resource drop-down menu.

        """
        ienv = self.ienv
        available_resources = self.ic.list_resources()
        self.widget.resourceBox.clear()
        self.widget.resourceBox.addItems(available_resources)
        if (DEFAULT_RESC in ienv and ienv[DEFAULT_RESC] != '' and
                ienv[DEFAULT_RESC] in available_resources):
            index = self.widget.resourceBox.findText(ienv[DEFAULT_RESC])
            self.widget.resourceBox.setCurrentIndex(index)

    def _configure_continuous_upload(self):
        """Configure upload settings.

        """
        if self.ienv['irods_host'] in UPLOAD_HOSTS:
            # self.widget.uplSetGB_2.setVisible(True)
            if REMOVE_LOCAL in self.ienv:
                self.widget.rLocalcopyCB.setChecked(
                    self.ienv[REMOVE_LOCAL])
            if UPLOAD_MODE in self.ienv:
                upload_mode = self.ienv[UPLOAD_MODE]
                if upload_mode == "f500":
                    self.widget.uplF500RB.setChecked(True)
                elif upload_mode == "meta":
                    self.widget.uplMetaRB.setChecked(True)
                else:
                    self.widget.uplAllRB.setChecked(True)
            # self.widget.rLocalcopyCB.stateChanged.connect(
            #     self.save_ui_settings)
            # self.widget.uplF500RB.toggled.connect(self.save_ui_settings)
            # self.widget.uplMetaRB.toggled.connect(self.save_ui_settings)
            # self.widget.uplAllRB.toggled.connect(self.save_ui_settings)
        else:
            self.widget.uplSetGB_2.hide()
            self.widget.ContUplBut.hide()

    def enable_buttons(self, enable):
        """Set the state for all buttons.

        Parameters
        ----------
        enable : bool

        """
        self.widget.UploadButton.setEnabled(enable)
        self.widget.DownloadButton.setEnabled(enable)
        self.widget.ContUplBut.setEnabled(enable)
        self.widget.uplSetGB_2.setEnabled(enable)
        self.widget.createFolderButton.setEnabled(enable)
        self.widget.createCollButton.setEnabled(enable)
        self.widget.localFsTreeView.setEnabled(enable)
        self.widget.localFsTreeView.setEnabled(enable)

    def info_popup(self, message):
        """Display `message` in a pop-up subwindow.

        """
        PyQt5.QtWidgets.QMessageBox.information(
            self.widget, 'Information', message)

    # FIXME Move these parameters to the iBridges settings.
    def save_ui_settings(self):
        """Save the UI settings in the iRODS environment.

        """
        self.ienv[REMOVE_LOCAL] = self.get_remote_local_copy_state()
        self.ienv[UPLOAD_MODE] = self.get_upload_mode()
        utils.utils.saveIenv(self.ienv)

    def get_resource(self):
        """Get the resource name from the resource box.

        Returns
        -------
        str
            Current iRODS resource name.

        """
        return self.widget.resourceBox.currentText()

    def get_remote_local_copy_state(self):
        """Get state of remote/local copy button.

        Returns
        -------
        bool
            Button checked state.

        """
        return self.widget.rLocalcopyCB.isChecked()

    def get_upload_mode(self):
        """Get upload mode.

        Returns
        -------
        str
            Upload mode.

        """
        if self.widget.uplF500RB.isChecked():
            upload_mode = 'f500'
        elif self.widget.uplMetaRB.isChecked():
            upload_mode = 'meta'
        else:
            upload_mode = 'all'
        return upload_mode

    def create_folder(self):
        """Create a directory/folder on the local filesystem.

        """
        parent = self.localmodel.get_checked()
        if parent is None:
            self.widget.errorLabel.setText('No parent folder selected.')
        else:
            create_dir_widget = gui.popupWidgets.createDirectory(parent)
            create_dir_widget.exec_()
            # self.localmodel.initial_expand(previous_item = parent)

    def create_collection(self):
        """Create collection on the remote iRODS system.

        """
        index, parent = self.irodsmodel.get_checked()
        if parent is None:
            self.widget.errorLabel.setText(
                "No parent collection selected.")
        else:
            create_coll_widget = gui.popupWidgets.irodsCreateCollection(
                parent, self.ic)
            create_coll_widget.exec_()
            self.irodsmodel.refreshSubTree(index)

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
                self.irodsmodel.refreshSubTree(irods_index)
            if self.widget.saveSettings.isChecked():
                print("FINISH UPLOAD/DOWNLOAD: saving ui parameters.")
                self.save_ui_settings()
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
        source = self.localmodel.get_checked()
        if source is None:
            return (None, None, None)
        dest_index, dest_path = self.irodsmodel.get_checked()
        if dest_index is None or os.path.isfile(dest_path):
            return (None, None, None)
        return (source, dest_index, dest_path)
