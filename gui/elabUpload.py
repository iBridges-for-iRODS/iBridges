"""eLabJournal electronic laboratory notebook upload tab.

"""
import logging
import os
import sys
import logging

from utils.elabConnector import elabConnector
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtWidgets import QMessageBox, QTableWidgetItem, QWidget
from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6.QtGui import QFileSystemModel
from PyQt6.uic import loadUi
from gui.checkableFsTree import checkableFsTreeModel
from gui.ui_files.tabELNData import Ui_tabELNData

from utils.utils import get_local_size, get_coll_dict
from irods.exception import CATALOG_ALREADY_HAS_ITEM_BY_THAT_NAME


class elabUpload(QWidget, Ui_tabELNData):
    """ELabJournal upload tab.

    """
    thread = None
    worker = None

    def __init__(self, ic):
        """

        Parameters
        ----------
        ic
        """
        self.elab = None
        self.coll = None
        self.ic = ic
        super().__init__()
        if getattr(sys, 'frozen', False):
            super().setupUi(self)
        else:
            loadUi("gui/ui_files/tabELNData.ui", self)
        # Selecting and uploading local files and folders
        self.dirmodel = QFileSystemModel(self.localFsTable)
        self.localFsTable.setModel(self.dirmodel)
        self.localFsTable.setColumnHidden(1, True)
        self.localFsTable.setColumnHidden(2, True)
        self.localFsTable.setColumnHidden(3, True)
        # TODO remove commented commands that are not required?
        # self.localFsTable.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        # TODO standardize tree initialization
        home_location = QtCore.QStandardPaths.standardLocations(
            QtCore.QStandardPaths.StandardLocation.HomeLocation)[0]
        self.dirmodel.setRootPath(home_location)
        #self.localFsTable.setCurrentIndex(index)
        self.elnIrodsPath.setText(
                '/'+self.ic.session.zone+'/home/'+self.ic.session.username)
        # defining events and listeners
        self.elnTokenInput.returnPressed.connect(self.connectElab)
        self.elnGroupTable.clicked.connect(self.loadExperiments)
        self.elnExperimentTable.clicked.connect(self.selectExperiment)
        self.elnUploadButton.clicked.connect(self.upload_data)

    def connectElab(self):
        self.errorLabel.clear()
        token = self.elnTokenInput.text()
        print("ELAB INFO token: "+token)
        # ELN can potentially be offline
        try:
            self.elab = elabConnector(token)
            groups = self.elab.showGroups(get=True)
            self.elnGroupTable.setRowCount(len(groups))
            for row, group in enumerate(groups):
                self.elnGroupTable.setItem(row, 0, QTableWidgetItem(group[0]))
                self.elnGroupTable.setItem(row, 1, QTableWidgetItem(group[1]))
            self.elnGroupTable.resizeColumnsToContents()
            # self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
        except Exception as error:
            logging.info("elabUpload: "+repr(error))
            self.errorLabel.setText(
                "ELN ERROR: "+repr(error)+"\n Your permissions for your current active group might be blocked.")
            # self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))

    def selectExperiment(self):
        # TODO put exp id in self experimentIdLabel
        self.errorLabel.clear()
        row = self.elnExperimentTable.currentRow()
        if row > -1:
            expId = self.elnExperimentTable.item(row, 0).text()
            self.experimentIdLabel.setText(expId)

    def loadExperiments(self):
        self.errorLabel.clear()
        self.elnExperimentTable.setRowCount(0)
        # self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.WaitCursor))
        row = self.elnGroupTable.currentRow()
        if row > -1:
            groupId = self.elnGroupTable.item(row, 0).text()
            self.groupIdLabel.setText(groupId)
            try:
                userExp, otherExp = self.elab.showExperiments(int(groupId), get=True)
                self.elnExperimentTable.setRowCount(len(userExp+otherExp)+1)
                for row, exp in enumerate(userExp):
                    self.elnExperimentTable.setItem(row, 0, QTableWidgetItem(exp[0]))
                    self.elnExperimentTable.setItem(row, 1, QTableWidgetItem(exp[1]))
                    self.elnExperimentTable.setItem(row, 2, QTableWidgetItem(exp[2]))
                row += 1
                self.elnExperimentTable.setItem(row, 0, QTableWidgetItem(""))
                self.elnExperimentTable.setItem(row, 1, QTableWidgetItem(""))
                self.elnExperimentTable.setItem(row, 2, QTableWidgetItem(""))
                for row, exp in enumerate(otherExp, start=row+1):
                    self.elnExperimentTable.setItem(row, 0, QTableWidgetItem(exp[0]))
                    self.elnExperimentTable.setItem(row, 1, QTableWidgetItem(exp[1]))
                    self.elnExperimentTable.setItem(row, 2, QTableWidgetItem(exp[2]))
            except Exception as error:
                logging.info("ElabUpload groupId "+str(groupId)+": "+repr(error))
                self.errorLabel.setText(
                    "ELN ERROR: "+repr(error)+"\n You might not have permissions for that group.")
                # self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
                return
        self.elnExperimentTable.resizeColumnsToContents()
        # self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
    
    def reportProgress(self):
        self.errorLabel.setText("ELN UPLOAD STATUS: Uploading ...")

    def reportFinished(self):
        # self.elnUploadButton.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
        self.elnUploadButton.setEnabled(True)
        self.showPreview()
        self.elnIrodsPath.setText(self.coll.path.split('/ELN')[0])
        self.errorLabel.setText("ELN UPLOAD STATUS: Uploaded to "+self.coll.path)
        self.thread.quit()

    def showPreview(self):
        irodsDict = get_coll_dict(self.coll)
        for key in list(irodsDict.keys())[:50]:
            self.elnPreviewBrowser.append(key)
            if len(irodsDict[key]) > 0:
                for item in irodsDict[key]:
                    self.elnPreviewBrowser.append('\t'+item)
        self.elnPreviewBrowser.append('\n\n<First 50 items printed>')
        self.errorLabel.setText("ELN upload success: "+self.coll.path)

    def upload_data(self):
        # TODO check why cursor changes are commented out
        # self.elnUploadButton.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.WaitCursor))
        self.elnPreviewBrowser.clear()
        self.errorLabel.clear()
        groupId = self.groupIdLabel.text()
        expId = self.experimentIdLabel.text()
        index = self.localFsTable.selectedIndexes()[0]
        path = self.dirmodel.filePath(index)
        if groupId == "":
            self.errorLabel.setText("ERROR: No group selected.")
            # self.elnUploadButton.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
            return
        if expId == "":
            self.errorLabel.setText("ERROR: No experiment selected.")
            # self.elnUploadButton.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
            return
        if path == "":
            self.errorLabel.setText("ERROR: No data selected.")
            # self.elnUploadButton.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
            return
        try:
            print("Group and Experiment: ", groupId, expId)
            # preconfigure upload path prefix
            subcoll = 'ELN/'+groupId+'/'+expId
            # stop if no exp and group is given
            if groupId == '' or expId == '':
                self.errorLabel.setText('ERROR ELN Upload: No Experiment selected')
                pass
            # get the url that will be uploaded as metadata to irods
            expUrl = self.elab.updateMetadataUrl(**{'group': int(groupId), 'experiment': int(expId)})
            print("ELN DATA UPLOAD experiment: \n"+expUrl)
            # get upload total size to inform user
            size = get_local_size([path])
            # if user specifies a different path than standard home
            collPath = '/'+self.elnIrodsPath.text().strip('/')+'/'+subcoll
            self.coll = self.ic.ensure_coll(collPath)
            self.elnIrodsPath.setText(collPath)
            buttonReply = QMessageBox.question(
                self.elnUploadButton,
                'Message Box', "Upload\n" + path + '\n'+str(size)+'MB',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            upload = buttonReply == QMessageBox.StandardButton.Yes
            if upload:
                # self.elnUploadButton.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.WaitCursor))
                self.elnUploadButton.setEnabled(False)
                # start own thread for the upload
                self.thread = QThread()
                self.worker = Worker(
                    self.ic, self.elab, self.coll, size, path, expUrl,
                    self.elnPreviewBrowser, self.errorLabel)
                self.worker.moveToThread(self.thread)
                self.thread.started.connect(self.worker.run)
                self.worker.finished.connect(self.thread.quit)
                self.worker.finished.connect(self.worker.deleteLater)
                self.thread.finished.connect(self.thread.exit)
                self.worker.progress.connect(self.reportProgress)
                self.thread.start()
                self.thread.finished.connect(self.reportFinished)
            # else:
            #     self.elnUploadButton.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
        except Exception as error:
            logging.info("ElabUpload UploadData: "+repr(error))
            self.errorLabel.setText(repr(error))
            self.elnUploadButton.setEnabled(True)
            # self.elnUploadButton.setCursor(
            #    QtGui.QCursor(QtCore.Qt.ArrowCursor))
            return

class Worker(QObject):
    """

    """
    finished = pyqtSignal()
    progress = pyqtSignal(int)

    def __init__(self, ic, elab, coll, size, filePath, expUrl,
                 elnPreviewBrowser, errorLabel):
        """

        Parameters
        ----------
        ic
        elab
        coll
        size
        filePath
        expUrl
        elnPreviewBrowser
        errorLabel
        """
        super().__init__()
        self.ic = ic
        self.coll = coll
        self.filePath = filePath
        self.elnPreviewBrowser = elnPreviewBrowser
        self.size = size
        self.expUrl = expUrl
        self.elab = elab
        self.errorLabel = errorLabel
        print("Start worker: ")

    def run(self):
        try:
            if os.path.isfile(self.filePath):
                # TODO should all the "force"es here be configurable?
                self.ic.upload_data(self.filePath, self.coll, None, self.size, force=True)
                item = self.ic.session.data_objects.get(
                        self.coll.path+'/'+os.path.basename(self.filePath))
                self.ic.addMetadata([item], 'ELN', self.expUrl)
            elif os.path.isdir(self.filePath):
                self.ic.upload_data(self.filePath, self.coll, None, self.size, force=True)
                upColl = self.ic.session.collections.get(
                            self.coll.path+'/'+os.path.basename(self.filePath))
                items = [upColl]
                for c, _, objs in upColl.walk():
                    items.append(c)
                    items.extend(objs)
                self.ic.addMetadata(items, 'ELN', self.expUrl)
            self.progress.emit(3)
            self.finished.emit()
        except Exception as error:
            logging.info("ElabUpload data upload and annotation worker: "+repr(error))
            print(repr(error))
        annotation = {
            "Data size": f'{self.size} Bytes',
            "iRODS path": self.coll.path,
            "iRODS server": self.ic.session.host,
            "iRODS user": self.ic.session.username,
        }
        self.annotateElab(annotation)

    def annotateElab(self, annotation):
        """

        Parameters
        ----------
        metadata

        """
        self.errorLabel.setText("Linking data to Elabjournal experiment.")
        # YODA: webdav URL does not contain "home", but iRODS path does!
        if self.ic.davrods and ("yoda" in self.ic.session.host or "uu.nl" in self.ic.session.host):
            self.elab.addMetadata(
                self.ic.davrods+'/'+self.coll.path.split('home/')[1].strip(),
                meta=annotation,
                title='Data in iRODS')
        elif self.ic.davrods and "surfsara.nl" in self.ic.session.host:
                self.elab.addMetadata(
                    self.ic.davrods+'/'+self.coll.path.split(
                        self.ic.session.zone)[1].strip('/'), 
                    meta=annotation,
                    title='Data in iRODS')
        elif self.ic.davrods:
            self.elab.addMetadata(
                    self.ic.davrods+'/'+self.coll.path.strip('/'), 
                    meta=annotation,
                    title='Data in iRODS')
        else:
            host = self.ic.session.host
            zone = self.ic.session.zone
            name = self.ic.session.username
            port = self.ic.session.port
            path = self.coll.path
            conn = f'{{{host}\n{zone}\n{name}\n{port}\n{path}}}'
            self.elab.addMetadata(conn, meta=annotation, title='Data in iRODS')
