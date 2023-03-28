"""eLabJournal electronic laboratory notebook upload tab.
"""
import logging
import os
import sys
import logging
import datetime

from utils.AmberConnector import AmberConnector
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtWidgets import QMessageBox, QTableWidgetItem, QWidget
from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6.QtGui import QFileSystemModel
from PyQt6.uic import loadUi
from gui.ui_files.tabAmberData import Ui_tabAmberData
from gui.irodsTreeView import IrodsModel
from utils.utils import file_exists
from irods.exception import CATALOG_ALREADY_HAS_ITEM_BY_THAT_NAME


class amberWorkflow(QWidget, Ui_tabAmberData):
    def __init__(self, ic, ienv):
        """
        Parameters
        ----------
        ic
        """
        self.amber = None
        self.coll = None
        self.ic = ic
        self.ienv = ienv
        super(amberWorkflow, self).__init__()
        if getattr(sys, 'frozen', False):
            super(amberWorkflow, self).setupUi(self)
        else:
            loadUi("gui/ui_files/tabAmberData.ui", self)
        
        # Selecting and uploading local files and folders
        self._initialize_local_model(self.irodsUploadTree)
        self._initialize_irods_model(self.irodsDownloadTree)
        
        self.amberToken.setText(self.ienv.get("amber_token"))
        self.amberToken.returnPressed.connect(self.connectAmber)
        
        self.refreshJobsButton.setEnabled(False)
        self.refreshJobsButton.clicked.connect(self.refreshJobs)
        self.submitButton.setEnabled(False)
        self.submitButton.clicked.connect(self.submitData)
        self.importDataButton.setEnabled(False)
        self.importDataButton.clicked.connect(self.importData)
        self.previewButton.setEnabled(False)
        self.previewButton.clicked.connect(self.previewData)

    def _initialize_local_model(self, treeView):
        self.localmodel = QFileSystemModel(treeView)
        treeView.setModel(self.localmodel)
        treeView.setColumnHidden(1, True)
        treeView.setColumnHidden(2, True)
        treeView.setColumnHidden(3, True)
        home_location = QtCore.QStandardPaths.standardLocations(
            QtCore.QStandardPaths.StandardLocation.HomeLocation)[0]
        index = self.localmodel.setRootPath(home_location)
        treeView.setCurrentIndex(index)

    def _initialize_irods_model(self, treeView):
        self.irodsmodel = IrodsModel(self.ic, treeView)
        treeView.setModel(self.irodsmodel)
        irodsRootColl = '/'+self.ic.zone
        self.irodsmodel.setHorizontalHeaderLabels([irodsRootColl,
                                              'Level', 'iRODS ID',
                                              'parent ID', 'type'])
        treeView.expanded.connect(self.irodsmodel.refresh_subtree)
        treeView.clicked.connect(self.irodsmodel.refresh_subtree)
        self.irodsmodel.init_tree()

        treeView.setHeaderHidden(True)
        treeView.header().setDefaultSectionSize(180)
        treeView.setColumnHidden(1, True)
        treeView.setColumnHidden(2, True)
        treeView.setColumnHidden(3, True)
        treeView.setColumnHidden(4, True)


    def connectAmber(self):
        token = self.amberToken.text()
        try:
            self.ac = AmberConnector(token)
            glossary_names = ["None"]+[g['name']+" / "+g['id'] for g in self.ac.glossaries]
            self.glossaryBox.clear()
            self.glossaryBox.addItems(glossary_names)
            index = self.glossaryBox.findText("None")
            self.glossaryBox.setCurrentIndex(index)
            self.refreshJobs()
            self.refreshJobsButton.setEnabled(True)
            self.submitButton.setEnabled(True)
            self.importDataButton.setEnabled(True)
            self.previewButton.setEnabled(True)

        except Exception as error:
            logging.info("amberWorkflow: "+repr(error))
            self.jobSubmitLabel.setText(
                "AMBER ERROR: "+repr(error))

    def refreshJobs(self):
        self.jobBox.clear()
        jobs = [j['filename']+' / '+j['status']+' / '+j['jobId'] for j in self.ac.jobs]
        self.jobBox.addItems(jobs)


    def submitData(self):
        self.jobSubmitLabel.clear()
        (index, path) = self.getPathsFromTrees(self.irodsUploadTree, True)
        if file_exists(path) and path.endswith("wav"):
            try:
                if self.glossaryBox.currentText() == "None":
                    info = self.ac.submit_job(path)
                else:
                    info = self.ac.submit_job(path, 
                                              self.glossaryBox.currentText().split(" / ")[1])
                self.jobSubmitLabel.setText(
                        info["jobStatus"]["jobId"]+" / "+info["jobStatus"]["filename"]+" / "+info["jobStatus"]["status"])
            except Exception as e:
                self.jobSubmitLabel.setText("AMBER ERROR: "+repr(e))
        else:
            self.jobSubmitLabel.setText("AMBER ERROR: Not a valid file.")

    def previewData(self):
        self.importLabel.clear()
        info = self.jobBox.currentText().split(' / ')
        if 'OPEN' in info:
            self.importLabel.setText("AMBER ERROR: Job not finished yet.")
        else:
            results = self.ac.get_results_txt(info[2])
            self.previewBrowser.clear()
            if info[1] == "DONE":
                self.previewBrowser.append(results)
            else:
                self.importLabel.setText("AMBER ERROR: Job not finished yet.")

    def importData(self):
        self.importLabel.clear()
        (index, path) = self.getPathsFromTrees(self.irodsDownloadTree, False)
        if self.ic.collection_exists(path):
            info = self.jobBox.currentText().split(' / ')
            if info[1] == "DONE":
                obj = self.ic.ensure_data_object(path+'/'+info[0]+'_'+info[2]+'.txt')
                self.importLabel.setText("IRODS INFO: writing to "+obj.path)
                with obj.open('w') as obj_desc:
                    results = self.ac.get_results_txt(info[2])
                    obj_desc.write(results.encode())
                self.ic.add_metadata([obj], 'prov:softwareAgent', "Amberscript")
                self.ic.add_metadata([obj], 'AmberscriptJob', info[2])
                self.importLabel.setText("IRODS INFO: "+obj.path)
            else:
                self.importLabel.setText("AMBER ERROR: Job not finished yet.")
        else:
            self.importLabel.setText("IRODS ERROR: Not a collection.")

    def getPathsFromTrees(self, treeView, local):
        index = treeView.selectedIndexes()[0]
        if local:
            path = self.localmodel.filePath(index)
        else:
            path = self.irodsmodel.irods_path_from_tree_index(index)
        
        return(index, path)
