import sys
from os import path, getcwd
from PyQt6.QtWidgets import QMessageBox, QWidget
from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6 import QtGui, QtCore
from PyQt6.uic import loadUi

from gui.irodsTreeView import IrodsModel
from gui.popupWidgets import irodsIndexPopup
from gui.ui_files.tabDataCompression import Ui_tabDataCompression

class irodsDataCompression(QWidget, Ui_tabDataCompression):
    def __init__(self, ic, ienv):
        self.ic = ic
        self.ienv = ienv

        super(irodsDataCompression, self).__init__()
        if getattr(sys, 'frozen', False):
            super(irodsDataCompression, self).setupUi(self)
        else:
            loadUi("gui/ui_files/tabDataCompression.ui", self)

        rescs = self.ic.listResources()
        if ic.defaultResc not in rescs:
            self.infoPopup('ERROR resource config: "default_resource_name" invalid:\n'
                           + ic.defaultResc
                           + '\nDataCompression view not setup.')
            return

        ruleFiles = [path.join(getcwd(), 'rules/tarCollection.r'),
                     path.join(getcwd(), 'rules/tarReadIndex.r'),
                     path.join(getcwd(), 'rules/tarExtract.r')]
        for rule in ruleFiles:
            if not path.isfile(rule):
                self.infoPopup('ERROR rules not configured:\n' + rule
                           + '\nDataCompression view not setup.')
                return

        self.irodsZoneLabel1.setText("/"+self.ic.session.zone+":")
        self.irodsZoneLabel2.setText("/"+self.ic.session.zone+":")
        self.irodsRootColl = '/'+ic.session.zone
        index = self.decompressRescButton.findText(ic.defaultResc)
        self.decompressRescButton.setCurrentIndex(index)

        # irodsCollectionTree
        self.collectionTreeModel = self.setupFsTree(self.irodsCollectionTree)
        self.irodsCollectionTree.expanded.connect(self.collectionTreeModel.refreshSubTree)
        # self.irodsCollectionTree.clicked.connect(self.collectionTreeModel.refreshSubTree)
        # irodsCompressionTree
        self.compressionTreeModel = self.setupFsTree(self.irodsCompressionTree)
        self.irodsCompressionTree.expanded.connect(self.compressionTreeModel.refreshSubTree)
        # self.irodsCompressionTree.clicked.connect(self.compressionTreeModel.refreshSubTree)
        # resource buttons
        self.setupResourceButton(self.compressRescButton)
        self.setupResourceButton(self.decompressRescButton)

        # Create/Unpack/Index buttons
        self.createButton.clicked.connect(self.createDataBundle)
        self.unpackButton.clicked.connect(self.unpackDataBundle)
        self.indexButton.clicked.connect(self.getIndex)

    def infoPopup(self, message):
        QMessageBox.information(self, 'Information', message)

    def setupFsTree(self, treeView):
        model = IrodsModel(self.ic, treeView)
        treeView.setModel(model)
        model.setHorizontalHeaderLabels([self.irodsRootColl,
                                              'Level', 'iRODS ID',
                                              'parent ID', 'type'])

        treeView.expanded.connect(model.refreshSubTree)
        treeView.clicked.connect(model.refreshSubTree)
        model.initTree()

        treeView.setHeaderHidden(True)
        treeView.header().setDefaultSectionSize(180)
        treeView.setColumnHidden(1, True)
        treeView.setColumnHidden(2, True)
        treeView.setColumnHidden(3, True)
        treeView.setColumnHidden(4, True)

        return model

    def setupResourceButton(self, button):
        button.clear()
        resources = self.ic.listResources()
        button.addItems(resources)
        if self.ic.defaultResc in resources:
            index = button.findText(self.ic.defaultResc)
            button.setCurrentIndex(index)

    def enableButtons(self, enable):
        self.compressRescButton.setEnabled(enable)
        self.decompressRescButton.setEnabled(enable)
        # Create/Unpack/Index buttons
        self.createButton.setEnabled(enable)
        self.unpackButton.setEnabled(enable)
        self.indexButton.setEnabled(enable)

    def createDataBundle(self):
        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.WaitCursor))
        self.enableButtons(False)

        self.createStatusLabel.clear()
        ruleFile = path.join(getcwd(), 'rules/tarCollection.r')
        idx, source = self.collectionTreeModel.get_checked()

        if not self.ic.session.collections.exists(source):
            self.createStatusLabel.setText("ERROR: No collection selected.")
            self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
            self.enableButtons(True)
            return

        # data bundling only allowed for collections in home/user
        if len(source.split('/')) < 5:
            self.createStatusLabel.setText(
                    "ERROR: Selected collection is not a user collection.")
            self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
            self.enableButtons(True)
            return

        compress = self.compressCheckBox.isChecked()
        remove = self.removeCheckBox.isChecked()
        migrateResc = self.compressRescButton.currentText()
        params = {
                '*coll': '"'+source+'"',
                '*resource': '"'+migrateResc+'"',
                '*compress': '"'+str(compress).lower()+'"',
                '*delete': '"'+str(remove).lower()+'"'
                }

        self.threadCreate = QThread()
        self.createStatusLabel.setText("STATUS: compressing "+source)
        self.worker = dataBundleCreateExtract(self.ic, ruleFile, params, "create")
        self.worker.moveToThread(self.threadCreate)
        self.threadCreate.started.connect(self.worker.run)
        self.worker.finished.connect(self.threadCreate.quit)
        self.worker.finished.connect(self.dataCreateExtractFinished)
        self.worker.finished.connect(self.worker.deleteLater)
        self.threadCreate.finished.connect(self.threadCreate.deleteLater)
        self.threadCreate.start()

    def dataCreateExtractFinished(self, success, message, operation):
        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
        self.enableButtons(True)
        stdout, stderr = message
        if success and operation == "create":
            idx, source = self.collectionTreeModel.get_checked()
            self.createStatusLabel.setText("STATUS: Created " + str(stdout))
            parentIdx = self.collectionTreeModel.getParentIdx(idx)
            self.collectionTreeModel.refreshSubTree(parentIdx)
        elif not success and operation == "create":
            self.createStatusLabel.setText("ERROR: Create failed: " + str(stderr))
        elif success and operation == "extract":
            idx, source = self.compressionTreeModel.get_checked()
            stdout, stderr = message
            self.unpackStatusLabel.setText("STATUS: Extracted " + str(stdout))
            parentIdx = self.compressionTreeModel.getParentIdx(idx)
            self.compressionTreeModel.refreshSubTree(parentIdx)
        elif not success and operation == "extract":
            self.unpackStatusLabel.setText("ERROR: Create failed: " + str(stderr))

    def unpackDataBundle(self):
        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.WaitCursor))
        idx, source = self.compressionTreeModel.get_checked()

        if not idx or (not source.endswith(".irods.tar") and not source.endswith(".irods.zip")):
            self.unpackStatusLabel.setText("ERROR: No *.irods.tar or *.irods.zip selected")
            self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
            return
        extractPath = path.dirname(source)+'/'+path.basename(source).split('.irods')[0]
        if self.ic.session.collections.exists(extractPath):
            extractColl = self.ic.session.collections.get(extractPath)
            if extractColl.subcollections != [] or extractColl.data_objects != []:
                self.unpackStatusLabel.setText("ERROR: Destination not empty: "+extractPath)
                self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
                return

        self.enableButtons(False)

        self.unpackStatusLabel.clear()
        ruleFile = path.join(getcwd(), 'rules/tarExtract.r')

        migrateResc = self.decompressRescButton.currentText()
        params = {
                '*obj': '"'+source+'"',
                '*resource': '"'+migrateResc+'"',
                }

        self.threadExtract = QThread()
        self.unpackStatusLabel.setText("STATUS: extracting "+source)
        self.worker = dataBundleCreateExtract(self.ic, ruleFile, params, "extract")
        self.worker.moveToThread(self.threadExtract)
        self.threadExtract.started.connect(self.worker.run)
        self.worker.finished.connect(self.threadExtract.quit)
        self.worker.finished.connect(self.dataCreateExtractFinished)
        self.worker.finished.connect(self.worker.deleteLater)
        self.threadExtract.finished.connect(self.threadExtract.deleteLater)
        self.threadExtract.start()

    def getIndex(self):
        self.unpackStatusLabel.clear()
        ruleFile = path.join(getcwd(), 'rules/tarReadIndex.r')

        idx, source = self.compressionTreeModel.get_checked()
        if source is None:
            self.unpackStatusLabel.setText("ERROR: No *.irods.tar or *.irods.zip selected")
            return
        if not source.endswith(".irods.tar") and not source.endswith(".irods.zip"):
            self.unpackStatusLabel.setText("ERROR: No *.irods.tar or *.irods.zip selected")
            return

        params = {
                '*path': '"'+source+'"'
                }
        stdout, stderr = self.ic.executeRule(ruleFile, params)
        self.unpackStatusLabel.setText("INFO: Loaded Index of "+source)
        indexPopup = irodsIndexPopup(self.ic, stdout[1:], source, self.unpackStatusLabel)
        indexPopup.exec()


class dataBundleCreateExtract(QObject):
    finished = pyqtSignal(bool, list, str)

    def __init__(self, ic, ruleFile, params, operation):
        super(dataBundleCreateExtract, self).__init__()
        self.ruleFile = ruleFile
        self.params = params
        self.ic = ic
        self.operation = operation

    def run(self):
        stdout, stderr = self.ic.executeRule(self.ruleFile, self.params)
        if stderr != []:
            self.finished.emit(False, [stdout, stderr], self.operation)
        else:
            self.finished.emit(True, [stdout, stderr], self.operation)
