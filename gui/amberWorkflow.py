"""eLabJournal electronic laboratory notebook upload tab.
"""
import logging
import sys
import os
import io

from PyQt6 import QtCore
from PyQt6.QtWidgets import QWidget, QLineEdit
from PyQt6.QtGui import QFileSystemModel
from PyQt6.uic import loadUi
from gui.ui_files.tabAmberData import Ui_tabAmberData
from gui.irodsTreeView import IrodsModel

import utils


class amberWorkflow(QWidget, Ui_tabAmberData):
    context = utils.context.Context()
    def __init__(self):
        """

        """
        self.amber = None
        self.coll = None
        super(amberWorkflow, self).__init__()
        if getattr(sys, 'frozen', False):
            super(amberWorkflow, self).setupUi(self)
        else:
            loadUi("gui/ui_files/tabAmberData.ui", self)

        # Selecting and uploading local files and folders
        self._initialize_irods_model(self.irodsUploadTree)
        self._initialize_irods_model(self.irodsDownloadTree)

        self.amberToken.setText(self.context.ibridges_configuration.config.get("amber_token", 'Enter token'))
        self.amberToken.setEchoMode(QLineEdit.EchoMode.Password)
        self.amberToken.returnPressed.connect(self.connectAmber)
        self.amber_connect_button.clicked.connect(self.connectAmber)

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
        self.irodsmodel = IrodsModel(treeView)
        treeView.setModel(self.irodsmodel)
        irodsRootColl = self.context.irods_environment.config.get(
                'irods_home', '/'+self.context.irods_connector.zone)
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
            self.ac = utils.AmberConnector.AmberConnector(token)
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
            logging.error('amberWorkflow: %r', error)
            self.jobSubmitLabel.setText(
                "AMBER ERROR: "+repr(error))

    def refreshJobs(self):
        self.jobBox.clear()
        jobs = [j['filename']+' / '+j['status']+' / '+j['jobId'] for j in self.ac.jobs]
        self.jobBox.addItems(jobs)


    def submitData(self):
        self.jobSubmitLabel.clear()
        self.jobSubmitLabel.setText('   ')
        (index, path) = self.getPathsFromTrees(self.irodsUploadTree, False)
        obj_path = utils.path.IrodsPath(path) 
        if  self.context.irods_connector.dataobject_exists(path) and obj_path.suffix in ['.wav', '.mp3']:
            obj = self.context.irods_connector.get_dataobject(obj_path)
            tempFile = utils.path.LocalPath(self.context.ibridges_conf_file.parent,
                                            obj.name)
            glossary = None
            if self.glossaryBox.currentText() != "None":
                glossary = self.glossaryBox.currentText().split(" / ")[1]

            try:
                obj = self.context.irods_connector.get_dataobject(path)
                g = io.BytesIO(obj.open('r').read())
                print(tempFile, glossary)
                with open(tempFile, 'wb') as out:
                    out.write(g.read())
                info = self.ac.submit_job(tempFile, glossary_id=glossary)
                self.jobSubmitLabel.setText(
                        info["jobStatus"]["jobId"]+" / "+info["jobStatus"]["filename"]+ \
                                " / "+info["jobStatus"]["status"])
            except Exception as error:
                self.jobSubmitLabel.setText(f'AMBER ERROR: {error!r}')
            finally:
                if tempFile.exists():
                    os.remove(tempFile)
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
        try:
            (index, path) = self.getPathsFromTrees(self.irodsDownloadTree, False)
            if self.context.irods_connector.collection_exists(path):
                info = self.jobBox.currentText().split(' / ')
                if info[1] == "DONE":
                    obj = self.context.irods_connector.ensure_data_object(path + '/' + info[0] + '_' + info[2] + '.txt')
                    self.importLabel.setText("IRODS INFO: writing to "+obj.path)
                    with obj.open('w') as obj_desc:
                        results = self.ac.get_results_txt(info[2])
                        obj_desc.write(results.encode())
                    self.context.irods_connector.add_metadata([obj], 'prov:softwareAgent', "Amberscript")
                    self.context.irods_connector.add_metadata([obj], 'AmberscriptJob', info[2])
                    self.importLabel.setText("IRODS INFO: "+obj.path)
                else:
                    self.importLabel.setText("AMBER ERROR: Job not finished yet.")
            else:
                self.importLabel.setText("IRODS ERROR: Not a collection.")
        except Exception:
            self.importLabel.setText(f"ERROR: Choose destination.")

    def getPathsFromTrees(self, treeView, local):
        index = treeView.selectedIndexes()[0]
        if local:
            path = self.localmodel.filePath(index)
        else:
            path = self.irodsmodel.irods_path_from_tree_index(index)
        
        return(index, path)
