"""Browser tab.

"""
import logging
import sys

import irods.exception
import PyQt6.QtCore
import PyQt6.QtGui
import PyQt6.QtWidgets
import PyQt6.uic

import gui
import meta
import utils

# See: https://github.com/irods/irods_docs/blob/main/docs/system_overview/data_objects.md
OBJ_STATUS_SYMBOL = {
    '0': 'X',
    '1': '&',
    '2': '?',
    '3': '?',
    '4': '?',
}
OBJ_STATUS_HUMAN = {
    '0': 'stale',
    '1': 'good',
    '2': 'intermediate',
    '3': 'read-locked',
    '4': 'write-locked',
}


class IrodsBrowser(PyQt6.QtWidgets.QWidget,
                   gui.ui_files.tabBrowser.Ui_tabBrowser,
                   utils.context.ContextContainer):
    """Browser view for iRODS session.

    """
    current_browser_row = -1

    def __init__(self):
        """Initialize an iRODS browser view.

        """
        super().__init__()
        if getattr(sys, 'frozen', False):
            super().setupUi(self)
        else:
            PyQt6.uic.loadUi("gui/ui_files/tabBrowser.ui", self)
        self.force = self.conf.get('force_transfers', False)
        self.viewTabs.setCurrentIndex(0)
        # Browser table
        self.collTable.setColumnWidth(0, 20)
        self.collTable.setColumnWidth(1, 399)
        self.collTable.setColumnWidth(2, 199)
        self.collTable.setColumnWidth(3, 399)
        # Metadata table
        self.metadataTable.setColumnWidth(0, 199)
        self.metadataTable.setColumnWidth(1, 199)
        self.metadataTable.setColumnWidth(2, 199)
        # ACL table
        self.aclTable.setColumnWidth(0, 299)
        self.aclTable.setColumnWidth(1, 299)
        # If user is not a rodsadmin, hide Admin controls.
        user_type = ''
        try:
            user_type, _ = self.conn.get_user_info()
        except irods.exception.NetworkException:
            self.errorLabel.setText(
                    "iRODS NETWORK ERROR: No Connection, please check network")
        if user_type != 'rodsadmin':
            self.aclAdminBox.hide()
        # Replica table
        self.replicaTable.setColumnWidth(0, 500)
        self.replicaTable.setColumnWidth(1, 90)
        # iRODS defaults
        if 'irods_cwd' in self.ienv:
            root_path = self.ienv['irods_cwd']
        elif 'irods_home' in self.ienv:
            root_path = self.ienv['irods_home']
        else:
            root_path = f'/{self.conn.zone}/home/{self.conn.username}'
        try:
            self.root_coll = self.conn.get_collection(root_path)
        except irods.exception.CollectionDoesNotExist:
            self.root_coll = self.conn.get_collection(f'/{self.conn.zone}/home')
        except irods.exception.NetworkException:
            self.errorLabel.setText(
                'iRODS NETWORK ERROR: No Connection, please check network')
        self.resetPath()
        self.browse()

    def browse(self):
        """Initialize browser view GUI elements.  Defines the signals
        and slots.

        """
        # update main table when iRODS path is changed upon 'Enter'
        self.inputPath.returnPressed.connect(self.loadTable)
        self.refreshButton.clicked.connect(self.loadTable)
        self.homeButton.clicked.connect(self.resetPath)
        self.parentButton.clicked.connect(self.set_parent_path)
        # quick data upload and download (files only)
        self.UploadButton.clicked.connect(self.fileUpload)
        self.DownloadButton.clicked.connect(self.fileDownload)
        # new collection
        self.createCollButton.clicked.connect(self.createCollection)
        self.dataDeleteButton.clicked.connect(self.deleteData)
        self.loadDeleteSelectionButton.clicked.connect(self.loadSelection)
        # functionality to lower tabs for metadata, acls and replicas
        self.collTable.doubleClicked.connect(self.updatePath)
        self.collTable.clicked.connect(self.fillInfo)
        self.metadataTable.clicked.connect(self.edit_metadata)
        self.aclTable.clicked.connect(self.edit_acl)
        # actions to update iCat entries of metadata and acls
        self.metaAddButton.clicked.connect(self.addIcatMeta)
        self.metaUpdateButton.clicked.connect(self.updateIcatMeta)
        self.metaDeleteButton.clicked.connect(self.deleteIcatMeta)
        self.metaLoadFile.clicked.connect(self.loadMetadataFile)
        self.aclAddButton.clicked.connect(self.update_icat_acl)

    def _clear_error_label(self):
        """Clear any error text.

        """
        self.errorLabel.clear()

    def _clear_view_tabs(self):
        """Clear the tabs view.

        """
        self.aclTable.setRowCount(0)
        self.metadataTable.setRowCount(0)
        self.replicaTable.setRowCount(0)
        self.previewBrowser.clear()

    def _fill_replicas_tab(self, obj_path):
        """Populate the table in the Replicas tab with the details of
        the replicas of the selected data object.

        Parameters
        ----------
        obj_path : str
            Path of iRODS collection or data object selected.

        """
        self.replicaTable.setRowCount(0)
        if self.conn.dataobject_exists(obj_path):
            obj = self.conn.get_dataobject(obj_path)
            # hierarchies = [(repl.number, repl.resc_hier) for repl in obj.replicas]
            self.replicaTable.setRowCount(len(obj.replicas))
            for row, repl in enumerate(obj.replicas):
                self.replicaTable.setItem(
                    row, 0, PyQt6.QtWidgets.QTableWidgetItem(obj.owner_name))
                self.replicaTable.setItem(
                    row, 1, PyQt6.QtWidgets.QTableWidgetItem(str(repl.number)))
                self.replicaTable.setItem(
                    row, 2, PyQt6.QtWidgets.QTableWidgetItem(repl.resc_hier))
                self.replicaTable.setItem(
                    row, 3, PyQt6.QtWidgets.QTableWidgetItem(str(repl.size)))
                self.replicaTable.setItem(
                    row, 4, PyQt6.QtWidgets.QTableWidgetItem(str(obj.modify_time)))
                self.replicaTable.setItem(
                    row, 5, PyQt6.QtWidgets.QTableWidgetItem(
                        f'{OBJ_STATUS_SYMBOL[repl.status]} ({OBJ_STATUS_HUMAN[repl.status]})'))
        self.replicaTable.resizeColumnsToContents()

    def _fill_acls_tab(self, obj_path):
        """Populate the table in the ACLs tab.

        Parameters
        ----------
        obj_path : str
            Path of iRODS collection or data object selected.

        """
        self.aclTable.setRowCount(0)
        self.aclUserField.clear()
        self.aclZoneField.clear()
        self.aclBox.setCurrentText('')
        obj = None
        if self.conn.collection_exists(obj_path):
            obj = self.conn.get_collection(obj_path)
        elif self.conn.dataobject_exists(obj_path):
            obj = self.conn.get_dataobject(obj_path)
        if obj is not None:
            inheritance = ''
            if self.conn.is_collection(obj):
                inheritance = obj.inheritance
            acls = self.conn.get_permissions(obj=obj)
            self.aclTable.setRowCount(len(acls))
            for row, acl in enumerate(acls):
                acl_access_name = self.conn.permissions[acl.access_name]
                self.aclTable.setItem(
                    row, 0, PyQt6.QtWidgets.QTableWidgetItem(acl.user_name))
                self.aclTable.setItem(
                    row, 1, PyQt6.QtWidgets.QTableWidgetItem(acl.user_zone))
                self.aclTable.setItem(
                    row, 2, PyQt6.QtWidgets.QTableWidgetItem(acl_access_name))
                self.aclTable.setItem(
                    row, 3, PyQt6.QtWidgets.QTableWidgetItem(str(inheritance)))
        self.aclTable.resizeColumnsToContents()
        self.owner_label.setText(f'Owner: {obj.owner_name}')

    def _fill_metadata_tab(self, obj_path):
        """Populate the table in the metadata tab.

        Parameters
        ----------
        obj_path : str
            Full name of iRODS collection or data object selected.

        """
        self.metaKeyField.clear()
        self.metaValueField.clear()
        self.metaUnitsField.clear()
        obj = None
        if self.conn.collection_exists(obj_path):
            obj = self.conn.get_collection(obj_path)
        elif self.conn.dataobject_exists(obj_path):
            obj = self.conn.get_dataobject(obj_path)
        if obj is not None:
            metadata = obj.metadata.items()
            self.metadataTable.setRowCount(len(metadata))
            for row, avu in enumerate(metadata):
                self.metadataTable.setItem(
                    row, 0, PyQt6.QtWidgets.QTableWidgetItem(avu.name))
                self.metadataTable.setItem(
                    row, 1, PyQt6.QtWidgets.QTableWidgetItem(avu.value))
                self.metadataTable.setItem(
                    row, 2, PyQt6.QtWidgets.QTableWidgetItem(avu.units))
        self.metadataTable.resizeColumnsToContents()

    def _fill_preview_tab(self, obj_path):
        """Populate the table in the metadata tab.

        Parameters
        ----------
        obj_path : str
            Full name of iRODS collection or data object selected.

        """
        obj = None
        if self.conn.collection_exists(obj_path):
            obj = self.conn.get_collection(obj_path)
            content = ['Collections:', '-----------------']
            content.extend([sc.name for sc in obj.subcollections])
            content.extend(['\n', 'DataObjects:', '-----------------'])
            content.extend([do.name for do in obj.data_objects])
            preview_string = '\n'.join(content)
            self.previewBrowser.append(preview_string)
        elif self.conn.dataobject_exists(obj_path):
            obj = self.conn.get_dataobject(obj_path)
            file_type = utils.path.IrodsPath(obj_path).suffix[1:]
            if file_type in ['txt', 'json', 'csv']:
                try:
                    with obj.open('r') as objfd:
                        preview_string = objfd.read(1024).decode('utf-8')
                    self.previewBrowser.append(preview_string)
                except Exception as error:
                    self.previewBrowser.append(
                        f'No Preview for: {obj_path}')
                    self.previewBrowser.append(repr(error))
                    self.previewBrowser.append(
                        "Storage resource might be down.")
            else:
                self.previewBrowser.append(
                    f'No Preview for: {obj_path}')

    def _get_object_path_name(self, row):
        """"""
        if self.collTable.item(row, 1).text().startswith("/"+self.conn.zone):
            logging.debug(self.collTable.item(row, 1).text())
            sub_paths = self.collTable.item(row, 1).text().strip("/").split("/")
            obj_path = "/"+"/".join(sub_paths[:len(sub_paths)-1])
            obj_name = sub_paths[-1]
        else:
            obj_path = self.inputPath.text()
            obj_name = self.collTable.item(row, 1).text()
        return obj_path, obj_name

    # @TODO: Add a proper data model for the table model
    def _get_irods_item_of_table_row(self, row):
        obj_path, obj_name = self._get_object_path_name(row)
        full_path = utils.path.IrodsPath(obj_path, obj_name)
        try:
            item = self.conn.get_collection(full_path)
        except irods.exception.CollectionDoesNotExist:
            item = self.conn.get_dataobject(full_path)
        return item

    def _get_selected_objects(self):
        rows = {row.row() for row in self.collTable.selectedIndexes()}
        objects = []
        for row in rows:
            item = self._get_irods_item_of_table_row(row)
            objects.append(item)
        return objects

    def loadTable(self):
        # loads main browser table
        try:
            self._clear_error_label()
            self._clear_view_tabs()
            obj_path = utils.path.IrodsPath(self.inputPath.text())
            if self.conn.collection_exists(obj_path):
                coll = self.conn.get_collection(obj_path)
                self.collTable.setRowCount(len(coll.data_objects)+len(coll.subcollections))
                row = 0
                for subcoll in coll.subcollections:
                    self.collTable.setItem(
                        row, 0, PyQt6.QtWidgets.QTableWidgetItem('C-'))
                    self.collTable.setItem(
                        row, 1, PyQt6.QtWidgets.QTableWidgetItem(subcoll.name))
                    # TODO see if a collection size calculation can be backgrounded
                    # coll_size = sum((sum(obj.size for obj in objs) for _, _, objs in subcoll.walk()))
                    self.collTable.setItem(
                        row, 2, PyQt6.QtWidgets.QTableWidgetItem(''))
                    self.collTable.setItem(
                        row, 3, PyQt6.QtWidgets.QTableWidgetItem(''))
                    self.collTable.setItem(
                        row, 4, PyQt6.QtWidgets.QTableWidgetItem(str(subcoll.create_time)))
                    self.collTable.setItem(
                        row, 5, PyQt6.QtWidgets.QTableWidgetItem(str(subcoll.modify_time)))
                    row += 1
                for obj in coll.data_objects:
                    statuses = {repl.status: None for repl in obj.replicas}
                    if len(set(statuses.keys())) == 1:
                        status = OBJ_STATUS_SYMBOL[list(statuses.keys())[0]]
                    else:
                        statuses.pop('1', None)
                        if len(set(statuses.keys())) == 1:
                            status = OBJ_STATUS_SYMBOL[list(statuses.keys())[0]]
                        else:
                            status = OBJ_STATUS_SYMBOL[sorted(statuses.keys())[-1]]
                    self.collTable.setItem(
                        row, 0, PyQt6.QtWidgets.QTableWidgetItem(status))
                    self.collTable.setItem(
                        row, 1, PyQt6.QtWidgets.QTableWidgetItem(obj.name))
                    self.collTable.setItem(
                        row, 2, PyQt6.QtWidgets.QTableWidgetItem(str(obj.size)))
                    self.collTable.setItem(
                        row, 3, PyQt6.QtWidgets.QTableWidgetItem(obj.checksum))
                    self.collTable.setItem(
                        row, 4, PyQt6.QtWidgets.QTableWidgetItem(str(obj.create_time)))
                    self.collTable.setItem(
                        row, 5, PyQt6.QtWidgets.QTableWidgetItem(str(obj.modify_time)))
                    row += 1
                self.collTable.resizeColumnsToContents()
            else:
                self.collTable.setRowCount(0)
                self.errorLabel.setText("Collection does not exist.")
        except irods.exception.NetworkException:
            logging.exception('Something went wrong')
            self.errorLabel.setText(
                    "iRODS NETWORK ERROR: No Connection, please check network")

    def set_parent_path(self):
        current_path = utils.path.IrodsPath(self.inputPath.text())
        self.inputPath.setText(current_path.parent)
        self.loadTable()

    def resetPath(self):
        self.inputPath.setText(self.root_coll.path)
        self.loadTable()

    # @PyQt6.QtCore.pyqtSlot(PyQt6.QtCore.QModelIndex)
    def updatePath(self, index):
        self._clear_error_label()
        row = index.row()
        obj_path, obj_name = self._get_object_path_name(row)
        full_path = utils.path.IrodsPath(obj_path, obj_name)
        if self.conn.collection_exists(full_path):
            self.inputPath.setText(full_path)
            self.loadTable()

    # @PyQt6.QtCore.pyqtSlot(PyQt6.QtCore.QModelIndex)
    def fillInfo(self, index):
        self._clear_error_label()
        self._clear_view_tabs()
        self.metadataTable.setRowCount(0)
        self.aclTable.setRowCount(0)
        self.replicaTable.setRowCount(0)
        row = index.row()
        self.current_browser_row = row
        obj_path, obj_name = self._get_object_path_name(row)
        obj_path = utils.path.IrodsPath(obj_path, obj_name)
        self._clear_view_tabs()
        try:
            self._fill_preview_tab(obj_path)
            self._fill_metadata_tab(obj_path)
            self._fill_acls_tab(obj_path)
            self._fill_replicas_tab(obj_path)
        except Exception as e:
            logging.error('Browser', exc_info=True)
            self.errorLabel.setText(repr(e))

    def loadSelection(self):
        # loads selection from main table into delete tab
        self.setCursor(PyQt6.QtGui.QCursor(PyQt6.QtCore.Qt.CursorShape.WaitCursor))
        self.deleteSelectionBrowser.clear()
        path_name = self.inputPath.text()
        row = self.collTable.currentRow()
        if row > -1:
            obj_name = self.collTable.item(row, 1).text()
            obj_path = "/"+path_name.strip("/")+"/"+obj_name.strip("/")
            try:
                if self.conn.collection_exists(obj_path):
                    irodsDict = utils.utils.get_coll_dict(self.conn.get_collection(obj_path))
                elif self.conn.dataobject_exists(obj_path):
                    irodsDict = {self.conn.get_dataobject(obj_path).path: []}
                else:
                    self.errorLabel.setText("Load: nothing selected.")
                    pass
                for key in list(irodsDict.keys())[:20]:
                    self.deleteSelectionBrowser.append(key)
                    if len(irodsDict[key]) > 0:
                        for item in irodsDict[key]:
                            self.deleteSelectionBrowser.append('\t'+item)
                self.deleteSelectionBrowser.append('...')
            except irods.exception.NetworkException:
                self.errorLabel.setText(
                    "iRODS NETWORK ERROR: No Connection, please check network")
                self.setCursor(PyQt6.QtGui.QCursor(PyQt6.QtCore.Qt.CursorShape.ArrowCursor))
        self.setCursor(PyQt6.QtGui.QCursor(PyQt6.QtCore.Qt.CursorShape.ArrowCursor))

    def deleteData(self):
        # Deletes all data in the deleteSelectionBrowser
        self.errorLabel.clear()
        data = self.deleteSelectionBrowser.toPlainText().split('\n')
        if data[0] != '':
            deleteItem = data[0].strip()
            quit_msg = "Delete all data in \n\n"+deleteItem+'\n'
            reply = PyQt6.QtWidgets.QMessageBox.question(
                self, 'Message', quit_msg,
                PyQt6.QtWidgets.QMessageBox.StandardButton.Yes,
                PyQt6.QtWidgets.QMessageBox.StandardButton.No)
            if reply == PyQt6.QtWidgets.QMessageBox.StandardButton.Yes:
                try:
                    if self.conn.collection_exists(deleteItem):
                        item = self.conn.get_collection(deleteItem)
                    else:
                        item = self.conn.get_dataobject(deleteItem)
                    self.conn.delete_data(item)
                    self.deleteSelectionBrowser.clear()
                    self.loadTable()
                    self.errorLabel.clear()
                except Exception as error:
                    self.errorLabel.setText("ERROR DELETE DATA: "+repr(error))

    def createCollection(self):
        parent = "/"+self.inputPath.text().strip("/")
        creteCollWidget = gui.popupWidgets.irodsCreateCollection(parent)
        creteCollWidget.exec()
        self.loadTable()

    def fileUpload(self):
        # TODO determine if this unused variable is required
        # dialog = PyQt6.QtWidgets.QFileDialog(self)
        fileSelect = PyQt6.QtWidgets.QFileDialog.getOpenFileName(self,
                        "Open File", "","All Files (*);;Python Files (*.py)")
        size = utils.utils.get_local_size([fileSelect[0]])
        buttonReply = PyQt6.QtWidgets.QMessageBox.question(
            self, 'Message Box', "Upload " + fileSelect[0],
            PyQt6.QtWidgets.QMessageBox.StandardButton.Yes | PyQt6.QtWidgets.QMessageBox.StandardButton.No,
            PyQt6.QtWidgets.QMessageBox.StandardButton.No)
        if buttonReply == PyQt6.QtWidgets.QMessageBox.StandardButton.Yes:
            try:
                parentColl = self.conn.get_collection(
                    "/" + self.inputPath.text().strip("/"))
                self.conn.upload_data(
                    fileSelect[0], parentColl, None, size, force=self.force)
                self.loadTable()
            except irods.exception.NetworkException:
                self.errorLabel.setText(
                    "iRODS NETWORK ERROR: No Connection, please check network")
            except Exception as error:
                logging.error('Upload failed %s: %r', fileSelect[0], error)
                self.errorLabel.setText(repr(error))

    def fileDownload(self):
        if self.current_browser_row == -1:
            self.errorLabel.setText('Please select an object first!')
            return
        # If table is filled
        if self.collTable.item(self.current_browser_row, 1) is not None:
            objName = self.collTable.item(self.current_browser_row, 1).text()
            if self.collTable.item(self.current_browser_row, 1).text().startswith("/" + self.conn.zone):
                parent = '/'.join(objName.split("/")[:len(objName.split("/"))-1])
                objName = objName.split("/")[len(objName.split("/"))-1]
            else:
                parent = self.inputPath.text()
            try:
                if self.conn.dataobject_exists(parent + '/' + objName):
                    downloadDir = utils.utils.get_downloads_dir()
                    buttonReply = PyQt6.QtWidgets.QMessageBox.question(
                        self, 'Message Box',
                        'Download\n'+parent+'/'+objName+'\tto\n'+downloadDir)
                    if buttonReply == PyQt6.QtWidgets.QMessageBox.StandardButton.Yes:
                        obj = self.conn.get_dataobject(parent + '/' + objName)
                        self.conn.download_data(obj, downloadDir, obj.size)
                        self.errorLabel.setText("File downloaded to: "+downloadDir)
            except irods.exception.NetworkException:
                self.errorLabel.setText(
                    "iRODS NETWORK ERROR: No Connection, please check network")
            except Exception as error:
                logging.error('Download failed %s/%s: %r', parent, objName, error)
                self.errorLabel.setText(repr(error))

    # @PyQt6.QtCore.pyqtSlot(PyQt6.QtCore.QModelIndex)
    def edit_metadata(self, index):
        self._clear_error_label()
        self.metaValueField.clear()
        self.metaUnitsField.clear()
        row = index.row()
        key = self.metadataTable.item(row, 0).text()
        value = self.metadataTable.item(row, 1).text()
        units = self.metadataTable.item(row, 2).text()
        self.metaKeyField.setText(key)
        self.metaValueField.setText(value)
        self.metaUnitsField.setText(units)

    # @PyQt6.QtCore.pyqtSlot(PyQt6.QtCore.QModelIndex)
    def edit_acl(self, index):
        self._clear_error_label()
        self.aclUserField.clear()
        self.aclZoneField.clear()
        self.aclBox.setCurrentText('')
        row = index.row()
        user_name = self.aclTable.item(row, 0).text()
        user_zone = self.aclTable.item(row, 1).text()
        acc_name = self.aclTable.item(row, 2).text()
        self.aclUserField.setText(user_name)
        self.aclZoneField.setText(user_zone)
        self.aclBox.setCurrentText(acc_name)

    def update_icat_acl(self):
        if self.current_browser_row == -1:
            self.errorLabel.setText('Please select an object first!')
            return
        self.errorLabel.clear()
        errors = {}
        obj_path, obj_name = self._get_object_path_name(self.current_browser_row)
        obj_path = utils.path.IrodsPath(obj_path, obj_name)
        user_name = self.aclUserField.text()
        if not user_name:
            errors['User name'] = None
        user_zone = self.aclZoneField.text()
        acc_name = self.aclBox.currentText()
        if not acc_name:
            errors['Access name'] = None
        if acc_name.endswith('inherit'):
            if self.conn.dataobject_exists(obj_path):
                self.errorLabel.setText(
                    'WARNING: (no)inherit is not applicable to data objects')
                return
            errors.pop('User name', None)
        if len(errors):
            self.errorLabel.setText(
                f'Missing input: {", ".join(errors.keys())}')
            return
        recursive = self.recurseBox.currentText() == 'True'
        admin = self.aclAdminBox.isChecked()
        try:
            self.conn.set_permissions(
                acc_name, obj_path, user_name, user_zone, recursive, admin)
            self._fill_acls_tab(obj_path)
        except irods.exception.NetworkException:
            self.errorLabel.setText(
                    "iRODS NETWORK ERROR: No Connection, please check network")
        except Exception as error:
            self.errorLabel.setText(repr(error))

    def updateIcatMeta(self):
        if self.current_browser_row == -1:
            self.errorLabel.setText('Please select an object first!')
            return
        self.errorLabel.clear()
        newKey = self.metaKeyField.text()
        newVal = self.metaValueField.text()
        newUnits = self.metaUnitsField.text()
        try:
            if newKey != "" and newVal != "":
                item = self._get_irods_item_of_table_row(self.current_browser_row)
                self.conn.update_metadata([item], newKey, newVal, newUnits)
                self._fill_metadata_tab(item.path)
                self._fill_replicas_tab(item.path)
        except irods.exception.NetworkException:
            self.errorLabel.setText(
                "iRODS NETWORK ERROR: No Connection, please check network")
        except Exception as error:
            self.errorLabel.setText(repr(error))

    def addIcatMeta(self):
        if self.current_browser_row == -1:
            self.errorLabel.setText('Please select an object first!')
            return
        self.errorLabel.clear()
        newKey = self.metaKeyField.text()
        newVal = self.metaValueField.text()
        newUnits = self.metaUnitsField.text()
        if newKey != "" and newVal != "":
            try:
                item = self._get_irods_item_of_table_row(self.current_browser_row)
                self.conn.add_metadata([item], newKey, newVal, newUnits)
                self._fill_metadata_tab(item.path)
                self._fill_replicas_tab(item.path)
            except irods.exception.NetworkException:
                self.errorLabel.setText(
                    "iRODS NETWORK ERROR: No Connection, please check network")
            except Exception as error:
                self.errorLabel.setText(repr(error))

    def deleteIcatMeta(self):
        if self.current_browser_row == -1:
            self.errorLabel.setText('Please select an object first!')
            return
        self.errorLabel.clear()
        key = self.metaKeyField.text()
        val = self.metaValueField.text()
        units = self.metaUnitsField.text()
        try:
            if key != "" and val != "":
                item = self._get_irods_item_of_table_row(self.current_browser_row)
                self.conn.delete_metadata([item], key, val, units)
                self._fill_metadata_tab(item.path)
        except irods.exception.NetworkException:
            self.errorLabel.setText(
                "iRODS NETWORK ERROR: No Connection, please check network")
        except Exception as error:
            self.errorLabel.setText(repr(error))

    def loadMetadataFile(self):
        path, filter = PyQt6.QtWidgets.QFileDialog.getOpenFileName(
            None, 'Select file', '',
            'Metadata files (*.csv *.json *.xml);;All files (*)')
        if path:
            self.errorLabel.clear()
            items = self._get_selected_objects()
            avus = meta.metadataFileParser.parse(path)
            if len(items) and len(avus):
                self.conn.add_multiple_metadata(items, avus)
                self._fill_metadata_tab(items[0].path)
