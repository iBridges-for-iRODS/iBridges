
from PyQt5.QtWidgets import QMainWindow, QHeaderView, QMessageBox
from customTreeViews import CheckableDirModel, IrodsModel
import logging
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
    def __init__(self, widget, ic):
        self.ic = ic
        self.widget = widget
        self.syncing = False # syncing or not

        # QTreeViews
        self.dirmodel = CheckableDirModel(self.widget.localFsTreeView)
        self.widget.localFsTreeView.setModel(self.dirmodel)
        # Hide all columns except the Name
        self.widget.localFsTreeView.setColumnHidden(1, True)
        self.widget.localFsTreeView.setColumnHidden(2, True)
        self.widget.localFsTreeView.setColumnHidden(3, True)
        self.widget.localFsTreeView.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.dirmodel.inital_expand()

        self.irodsmodel = IrodsModel(ic, self.widget.irodsFsTreeView)
        self.widget.irodsFsTreeView.setModel(self.irodsmodel)
        self.widget.irodsFsTreeView.expanded.connect(self.irodsmodel.expanded)
        self.widget.irodsFsTreeView.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.irodsmodel.inital_expand()

        # Buttons
        self.widget.tab2UploadButton.clicked.connect(self.upload)
        self.widget.tab2DownloadButton.clicked.connect(self.download)
        self.widget.tab2ContUplBut.clicked.connect(self.cont_upload)


    # Upload a file/folder to IRODS and refresh the TreeView
    def upload(self):
        source = self.dirmodel.get_checked()
        if self.upload_check_source(source) == False:
            return       
        dest_ind, dest_path = self.irodsmodel.get_checked()
        if self.upload_check_dest(dest_ind, dest_path) == False:
            return                    
        try:
            destColl = self.ic.session.collections.get(dest_path)
            self.ic.uploadData(source, destColl, None, None, force = True) #getSize(source))
            self.irodsmodel.upload_refresh(dest_ind)
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


    # Helpers to check file paths before upload
    def upload_check_source(self, source):
        if source == None:
            message = "No file selected to upload"
            QMessageBox.information(self.widget, 'Error', message)
            logging.info("Fileupload:" + message)
            return False

    def upload_check_dest(self, dest_ind, dest_collection):
        if dest_ind == None:
            message = "No Folder selected to upload to"
            QMessageBox.information(self.widget, 'Error', message)
            logging.info("Fileupload:" + message)
            return False
        elif dest_collection.find(".") != -1:
            message = "Can only upload to folders, not files."
            QMessageBox.information(self.widget, 'Error', message)
            logging.info("Fileupload:" + message)
            return False

    def cont_upload(self):
        if self.syncing == False:
            self.syncing = True
            self.widget.tab2ContUplBut.setStyleSheet("image : url(icons/syncing.png) stretch stretch;")
        else:
            self.syncing = False
            self.widget.tab2ContUplBut.setStyleSheet("image : url(icons/nosync.png) stretch stretch;")