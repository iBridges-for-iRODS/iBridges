
from PyQt5.QtWidgets import QMainWindow, QHeaderView, QMessageBox
import logging

from checkableFsTree import checkableFsTreeModel
from irodsTreeView  import IrodsModel
from irodsUtils import getSize, saveIenv
from continousUpload import contUpload

from irodsCreateCollection import irodsCreateCollection
from createDirectory import createDirectory

# Vaiables
# localFsTreeWidget, irodsFsTreeWidget
# tab2UploadButton, tab2DownloadButton
# ic (irodsConnector)

# Treeviews
#localFsTreeView
#irodsFsTreeView

# Buttons
#tab2UploadButton
#tab2ContUplBut
#tab2DownloadButton

# Rest
#uplAllRB
#uplMetaRB
#uplF500RB
#rLocalcopyCB

class irodsUpDownload():
    def __init__(self, widget, ic, ienv):
        self.ic = ic
        self.widget = widget
        self.ienv = ienv
        self.syncing = False # syncing or not

        # QTreeViews
        self.dirmodel = checkableFsTreeModel(self.widget.localFsTreeView)
        self.widget.localFsTreeView.setModel(self.dirmodel)
        # Hide all columns except the Name
        self.widget.localFsTreeView.setColumnHidden(1, True)
        self.widget.localFsTreeView.setColumnHidden(2, True)
        self.widget.localFsTreeView.setColumnHidden(3, True)
        self.widget.localFsTreeView.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.dirmodel.initial_expand()
        
         # iRODS  zone info
        self.widget.irodsZoneLabel.setText("/"+self.ic.session.zone+":")
        # iRODS tree
        self.irodsmodel = IrodsModel(ic, self.widget.irodsFsTreeView)
        self.widget.irodsFsTreeView.setModel(self.irodsmodel)
        self.irodsRootColl = '/'+ic.session.zone
       
        #self.widget.irodsFsTreeView.expanded.connect(self.irodsmodel.expanded)
        #self.widget.irodsFsTreeView.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        #self.irodsmodel.initial_expand()
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


        # Buttons
        self.widget.tab2UploadButton.clicked.connect(self.upload)
        self.widget.tab2DownloadButton.clicked.connect(self.download)
        self.widget.tab2ContUplBut.clicked.connect(self.cont_upload)
        self.widget.tab2ChecksumCheckBut.clicked.connect(self.check_checksum)
        self.widget.createFolderButton.clicked.connect(self.createFolder)
        self.widget.createCollButtonTab2.clicked.connect(self.createCollection)

        # Resource selector
        available_resources = self.ic.listResources()
        self.widget.resourceBox_2.clear()
        self.widget.resourceBox_2.addItems(available_resources)
        if ("ui_resource" in ienv) and (ienv["ui_resource"] != "") and (ienv["ui_resource"] in available_resources):
            index = self.widget.resourceBox_2.findText(ienv["ui_resource"])
            self.widget.resourceBox_2.setCurrentIndex(index)
        elif ("default_resource_name" in ienv) and (ienv["default_resource_name"] != "") and (ienv["default_resource_name"] in available_resources):
            index = self.widget.resourceBox_2.findText(ienv["default_resource_name"])
            self.widget.resourceBox_2.setCurrentIndex(index)
        self.widget.resourceBox_2.currentIndexChanged.connect(self.saveUIset)

        # Continious upload settings
        if ("ui_remLocalcopy" in ienv):
            self.widget.rLocalcopyCB.setChecked(ienv["ui_remLocalcopy"])
        if ("ui_uplMode" in ienv):
            uplMode =  ienv["ui_uplMode"]
            if uplMode == "f500":
                self.widget.uplF500RB.setChecked(True)
            elif uplMode == "meta":
                self.widget.uplMetaRB.setChecked(True)
            else:
                self.widget.uplAllRB.setChecked(True)
        self.widget.rLocalcopyCB.stateChanged.connect(self.saveUIset)
        self.widget.uplF500RB.toggled.connect(self.saveUIset)
        self.widget.uplMetaRB.toggled.connect(self.saveUIset)
        self.widget.uplAllRB.toggled.connect(self.saveUIset)

    def saveUIset(self):
        self.ienv["ui_resource"] = self.getResource()
        self.ienv["ui_remLocalcopy"] = self.getRemLocalCopy()
        self.ienv["ui_uplMode"] = self.getUplMode()
        saveIenv(self.ienv)


    def getResource(self):
        return self.widget.resourceBox_2.currentText()

    def getRemLocalCopy(self):
        return self.widget.rLocalcopyCB.isChecked()

    def getUplMode(self):
        if self.widget.uplF500RB.isChecked():
            uplMode = "f500"
        elif self.widget.uplMetaRB.isChecked():
            uplMode = "meta"
        else: # Default
            uplMode = "all"
        return uplMode


    # Check checksums to confirm the upload
    def check_checksum(self):
        print("TODO")


    def createFolder(self):
        parent = self.dirmodel.get_checked()
        if parent != None:
            createDirWidget = createDirectory(parent)
            createDirWidget.exec_()
            #self.dirmodel.initial_expand(previous_item = parent)


    def createCollection(self):
        idx, parent = self.irodsmodel.get_checked()
        creteCollWidget = irodsCreateCollection(parent, self.ic)
        creteCollWidget.exec_()
        self.irodsmodel.refreshSubTree(idx)


    # Upload a file/folder to IRODS and refresh the TreeView
    def upload(self):
        (source, dest_ind, dest_path) = self.upload_get_paths()
        if source == None: 
            return           
        try:
            destColl = self.ic.session.collections.get(dest_path)
            self.ic.uploadData(source, destColl, self.getResource(), getSize(source), buff = 1024**3)# TODO keep 500GB free to avoid locking irods!
            self.irodsmodel.refreshSubTree(dest_ind)
        except Exception as error:
                self.widget.globalErrorLabel.setText(repr(error))


    # Download a file/folder from IRODS to local disk
    def download(self):
        source_ind, source_path = self.irodsmodel.get_checked()
        if source_ind == None:
            message = "No file/folder selected for download"
            QMessageBox.information(self.widget, 'Error', message)
            #logging.info("Filedownload:" + message)
            return
        destination = self.dirmodel.get_checked()
        if destination == None:
            message = "No Folder selected to download to"
            QMessageBox.information(self.widget, 'Error', message)
            #logging.info("Fileupload:" + message)
            return
        elif destination.find(".") != -1:
            message = "Can only download to folders, not files."
            QMessageBox.information(self.widget, 'Error', message)
            #logging.info("Fileupload:" + message)
            return      
        try:
            if self.ic.session.data_objects.exists(source_path):
                sourceColl = self.ic.session.data_objects.get(source_path)
            else:
                sourceColl = self.ic.session.collections.get(source_path)
            self.ic.downloadData(sourceColl, destination)
        except Exception as error:
                self.form.globalErrorLabel.setText(repr(error))


    # Continous file upload
    def cont_upload(self):
        (source, dest_ind, dest_path) = self.upload_get_paths()
        if source == None: 
            return
        if self.syncing == False:
            self.syncing = True
            self.widget.tab2ContUplBut.setStyleSheet("image : url(icons/syncing.png) stretch stretch;")
            self.en_disable_controls(False)
            upl_mode = self.get_upl_mode()
            r_local_copy = self.widget.rLocalcopyCB.isChecked()
            destColl = self.ic.session.collections.get(dest_path)
            self.uploader = contUpload(self.ic, source, destColl, upl_mode, r_local_copy)
            #self.uploader.start()
        else:
            #self.uploader.stop()
            self.syncing = False
            self.widget.tab2ContUplBut.setStyleSheet("image : url(icons/nosync.png) stretch stretch;")
            self.en_disable_controls(True)


    def en_disable_controls(self, enable):
        # Loop over all tabs enabling/disabling them
        for i in range(0, self.widget.tabWidget.count()):
            t = self.widget.tabWidget.tabText(i)
            if self.widget.tabWidget.tabText(i) == "Up and Download":
                continue
            self.widget.tabWidget.setTabVisible(i, enable)
        self.widget.tab2UploadButton.setEnabled(enable)
        self.widget.tab2DownloadButton.setEnabled(enable)
        self.widget.uplSetGB.setEnabled(enable)


    # Helpers to check file paths before upload
    def upload_get_paths(self):
        source = self.dirmodel.get_checked()
        if self.upload_check_source(source) == False:
            return (None, None, None)     
        dest_ind, dest_path = self.irodsmodel.get_checked()
        if self.upload_check_dest(dest_ind, dest_path) == False:
            return (None, None, None)     
        return (source, dest_ind, dest_path)

    def upload_check_source(self, source):
        if source == None:
            message = "No file selected to upload"
            QMessageBox.information(self.widget, 'Error', message)
            #logging.info("Fileupload:" + message)
            return False

    def upload_check_dest(self, dest_ind, dest_collection):
        if dest_ind == None:
            message = "No Folder selected to upload to"
            QMessageBox.information(self.widget, 'Error', message)
            #logging.info("Fileupload:" + message)
            return False
        elif dest_collection.find(".") != -1:
            message = "Can only upload to folders, not files."
            QMessageBox.information(self.widget, 'Error', message)
            #logging.info("Fileupload:" + message)
            return False
