
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

class irodsUpDownload():
    def __init__(self, form, ic):
        self.ic = ic
        self.form = form

        # QTreeViews
        self.dirmodel = CheckableDirModel(self.form.localFsTreeView)
        self.form.localFsTreeView.setModel(self.dirmodel)
        # Hide all columns except the Name
        self.form.localFsTreeView.setColumnHidden(1, True)
        self.form.localFsTreeView.setColumnHidden(2, True)
        self.form.localFsTreeView.setColumnHidden(3, True)
        self.form.localFsTreeView.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.dirmodel.inital_expand()

        self.irodsmodel = IrodsModel(ic, self.form.irodsFsTreeView)
        self.form.irodsFsTreeView.setModel(self.irodsmodel)
        self.form.irodsFsTreeView.expanded.connect(self.irodsmodel.expanded)
        self.form.irodsFsTreeView.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.irodsmodel.inital_expand()

        # Buttons
        self.form.tab2UploadButton.clicked.connect(self.upload)
        self.form.tab2DownloadButton.clicked.connect(self.download)



    # Upload a file/folder to IRODS and refresh the TreeView
    def upload(self):
        source = self.dirmodel.get_checked()
        if self.upload_check_source(source) == False:
            return       
        dest_ind, dest_collection = self.irodsmodel.get_checked()
        if self.upload_check_dest(dest_ind, dest_collection) == False:
            return                    

        self.ic.uploadData(source, dest_collection, None, None, force = True) #getSize(source))
        self.irodsmodel.upload_refresh(dest_ind)


    # Download a file/folder from IRODS to local disk
    def download(self):
        source_ind, source_collection = self.irodsmodel.get_checked()
        if source_ind == None:
            message = "No file/folder selected for download"
            QMessageBox.information(self, 'Error', message)
            #logging.info("Filedownload:" + message)
            return
        destination = self.dirmodel.get_checked()
        if destination == None:
            message = "No Folder selected to upload to"
            QMessageBox.information(self, 'Error', message)
            #logging.info("Fileupload:" + message)
            return
        elif destination.find(".") != -1:
            message = "Can only upload to folders, not files."
            QMessageBox.information(self, 'Error', message)
            #logging.info("Fileupload:" + message)
            return      
        self.ic.downloadData(source_collection, destination)


    # Helpers to check file paths before upload
    def upload_check_source(self, source):
        if source == None:
            message = "No file selected to upload"
            QMessageBox.information(self, 'Error', message)
            logging.info("Fileupload:" + message)
            return False

    def upload_check_dest(self, dest_ind, dest_collection):
        if dest_ind == None:
            message = "No Folder selected to upload to"
            QMessageBox.information(self, 'Error', message)
            logging.info("Fileupload:" + message)
            return False
        elif dest_collection.find(".") != -1:
            message = "Can only upload to folders, not files."
            QMessageBox.information(self, 'Error', message)
            logging.info("Fileupload:" + message)
            return False