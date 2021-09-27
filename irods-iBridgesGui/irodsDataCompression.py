from irodsTreeView  import IrodsModel
from popupWidgets import irodsIndexPopup

from PyQt5.QtWidgets import QMessageBox
from PyQt5.uic import loadUi
from PyQt5.QtCore import QObject, QThread, pyqtSlot, pyqtSignal
from PyQt5 import QtGui, QtCore

from os import path, getcwd
import json

class irodsDataCompression():
    def __init__(self, widget, ic, ienv):
        self.ic = ic
        self.widget = widget
        self.ienv = ienv
        rescs = self.ic.listResources()
        if ic.defaultResc not in rescs:
            self.infoPopup('ERROR resource config: "default_resource_name" invalid:\n'\
                           +ic.defaultResc \
                           +'\nDataCompression view not setup.')
            return

        ruleFiles = [path.join(getcwd(),'rules/tarCollection.r'), 
                     path.join(getcwd(),'rules/tarReadIndex.r'), 
                     path.join(getcwd(),'rules/tarExtract.r')]
        for rule in ruleFiles:
            if not path.isfile(rule):
                self.infoPopup('ERROR rules not configured:\n'+rule\
                           +'\nDataCompression view not setup.')
                return

        self.widget.irodsZoneLabel1.setText("/"+self.ic.session.zone+":")
        self.widget.irodsZoneLabel2.setText("/"+self.ic.session.zone+":")
        self.irodsRootColl = '/'+ic.session.zone

        #irodsCollectionTree
        self.collectionTreeModel = self.setupFsTree(self.widget.irodsCollectionTree)
        self.widget.irodsCollectionTree.expanded.connect(self.collectionTreeModel.refreshSubTree)
        #self.widget.irodsCollectionTree.clicked.connect(self.collectionTreeModel.refreshSubTree)
        #irodsCompressionTree
        self.compressionTreeModel = self.setupFsTree(self.widget.irodsCompressionTree)
        self.widget.irodsCompressionTree.expanded.connect(self.compressionTreeModel.refreshSubTree)
        #self.widget.irodsCompressionTree.clicked.connect(self.compressionTreeModel.refreshSubTree)
        #resource buttons
        self.setupResourceButton(self.widget.compressRescButton)
        self.setupResourceButton(self.widget.decompressRescButton)

        #Create/Unpack/Index buttons
        self.widget.createButton.clicked.connect(self.createDataBundle)
        self.widget.unpackButton.clicked.connect(self.unpackDataBundle)
        self.widget.indexButton.clicked.connect(self.getIndex)
        

    def infoPopup(self, message):
        QMessageBox.information(self.widget, 'Information', message)


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
        if "irods_default_resource" in self.ienv and \
                self.ienv["irods_default_resource"] in resources:
            index = self.widget.resourceBox.findText(self.ienv["default_resource_name"])
            button.setCurrentIndex(index)

    def enableButtons(self, enable):
        self.widget.compressRescButton.setEnabled(enable)
        self.widget.decompressRescButton.setEnabled(enable)
        #Create/Unpack/Index buttons
        self.widget.createButton.setEnabled(enable)
        self.widget.unpackButton.setEnabled(enable)
        self.widget.indexButton.setEnabled(enable)


    def createDataBundle(self):
        self.widget.setCursor(QtGui.QCursor(QtCore.Qt.WaitCursor))
        self.enableButtons(False)

        self.widget.createStatusLabel.clear()
        ruleFile = path.join(getcwd(),'rules/tarCollection.r')
        idx, source = self.collectionTreeModel.get_checked()

        if not self.ic.session.collections.exists(source):
            self.widget.createStatusLabel.setText("ERROR: No collection selected.")
            self.widget.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
            return

        #data bundling only allowed for collections in home/user
        if len(source.split('/')) < 5:
            self.widget.createStatusLabel.setText(
                    "ERROR: Selected collection is not a user collection.")
            self.widget.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
            return

        compress = self.widget.compressCheckBox.isChecked()
        remove = self.widget.removeCheckBox.isChecked()
        migrateResc = self.widget.compressRescButton.currentText()
        params = {
                '*coll': '"'+source+'"',
                '*resource': '"'+self.ic.defaultResc+'"',
                '*compress': '"'+str(compress).lower()+'"',
                '*delete': '"'+str(remove).lower()+'"'
                }

        self.threadCreate = QThread()
        self.widget.createStatusLabel.setText("STATUS: compressing "+source)
        self.worker = dataBundleCreateExtract(self.ic, ruleFile, params, "create")
        self.worker.moveToThread(self.threadCreate)
        self.threadCreate.started.connect(self.worker.run)
        self.worker.finished.connect(self.threadCreate.quit)
        self.worker.finished.connect(self.dataCreateExtractFinished)
        self.worker.finished.connect(self.worker.deleteLater)
        self.threadCreate.finished.connect(self.threadCreate.deleteLater)
        self.threadCreate.start()


    def dataCreateExtractFinished(self, success, message, operation):
        self.widget.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.enableButtons(True)
        if success and operation == "create":
            idx, source = self.collectionTreeModel.get_checked()
            stdout, stderr = message
            self.widget.createStatusLabel.setText("STATUS: Created " + str(stdout))
            parentIdx = self.collectionTreeModel.getParentIdx(idx)
            self.collectionTreeModel.refreshSubTree(parentIdx)
        elif not success and operation == "create":
            self.widget.createStatusLabel.setText("ERROR: Create failed: " + str(stderr))
        elif success and operation == "extract":
            idx, source = self.compressionTreeModel.get_checked()
            stdout, stderr = message
            self.widget.unpackStatusLabel.setText("STATUS: Extracted " + str(stdout))
            parentIdx = self.compressionTreeModel.getParentIdx(idx)
            self.compressionTreeModel.refreshSubTree(parentIdx)
        elif not success and operation == "extract":
            self.widget.unpackStatusLabel.setText("ERROR: Create failed: " + str(stderr))


    def unpackDataBundle(self):
        self.widget.setCursor(QtGui.QCursor(QtCore.Qt.WaitCursor))
        idx, source = self.compressionTreeModel.get_checked()
        if not source.endswith(".irods.tar") and not source.endswith(".irods.zip"):
            self.widget.unpackStatusLabel.setText("ERROR: No *.irods.tar or *.irods.zip selected")
            self.widget.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
            return
        extractPath = path.dirname(source)+'/'+path.basename(source).split('.irods')[0]
        if self.ic.session.collections.exists(extractPath):
            extractColl = self.ic.session.collections.get(extractPath)
            if extractColl.subcollections != [] or extractColl.data_objects != []:
                self.widget.unpackStatusLabel.setText("ERROR: Destination not empty: "+extractPath)
                self.widget.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
                return

        self.enableButtons(False)

        self.widget.unpackStatusLabel.clear()
        ruleFile = path.join(getcwd(),'rules/tarExtract.r')

        migrateResc = self.widget.decompressRescButton.currentText()
        params = {
                '*obj': '"'+source+'"',
                '*resource': '"'+self.ic.defaultResc+'"',
                }

        self.threadExtract = QThread()
        self.widget.unpackStatusLabel.setText("STATUS: extracting "+source)
        self.worker = dataBundleCreateExtract(self.ic, ruleFile, params, "extract")
        self.worker.moveToThread(self.threadExtract)
        self.threadExtract.started.connect(self.worker.run)
        self.worker.finished.connect(self.threadExtract.quit)
        self.worker.finished.connect(self.dataCreateExtractFinished)
        self.worker.finished.connect(self.worker.deleteLater)
        self.threadExtract.finished.connect(self.threadExtract.deleteLater)
        self.threadExtract.start()


    def getIndex(self):
        self.widget.unpackStatusLabel.clear()
        ruleFile = path.join(getcwd(),'rules/tarReadIndex.r')

        idx, source = self.compressionTreeModel.get_checked()
        if source == None:
            self.widget.unpackStatusLabel.setText("ERROR: No *.irods.tar or *.irods.zip selected")
            return
        if not source.endswith(".irods.tar") and not source.endswith(".irods.zip"):
            self.widget.unpackStatusLabel.setText("ERROR: No *.irods.tar or *.irods.zip selected")
            return

        params = {
                '*path': '"'+source+'"'
                }
        stdout, stderr = self.ic.executeRule(ruleFile, params)
        self.widget.unpackStatusLabel.setText("INFO: Loaded Index of "+source)
        indexPopup = irodsIndexPopup(stdout[1:], source, self.widget.unpackStatusLabel)
        indexPopup.exec_()


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

