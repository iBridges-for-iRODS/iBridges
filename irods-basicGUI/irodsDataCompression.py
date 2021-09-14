from irodsTreeView  import IrodsModel
from irodsCreateCollection import irodsIndexPopup

from PyQt5.QtWidgets import QMessageBox
from PyQt5.uic import loadUi

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
                     path.join(getcwd(),'rules/tarReadIndex.r')]
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
        #irodsCompressionTree
        self.compressionTreeModel = self.setupFsTree(self.widget.irodsCompressionTree)

        #resource buttons
        self.setupResourceButton(self.widget.compressRescButton)
        self.setupResourceButton(self.widget.decompressRescButton)

        #Create/Unpack/Index buttons
        self.widget.createButton.clicked.connect(self.createDataBundle)
        self.widget.unpackButton.clicked.connect(self.unpackDataBundle)
        self.widget.indexButton.clicked.connect(self.getIndex)


    def infoPopup(self, message):
        QMessageBox.information(self.widget, 'Error', message)


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


    def createDataBundle(self):
        self.widget.createStatusLabel.clear()
        ruleFile = path.join(getcwd(),'rules/tarCollection.r')

        idx, source = self.collectionTreeModel.get_checked()

        if not self.ic.session.collections.exists(source):
            self.widget.createStatusLabel.setText("ERROR: No collection selected.")
            return

        #data bundling only allowed for collections in home/user
        if len(source.split('/')) < 5:
            self.widget.createStatusLabel.setText(
                    "ERROR: Selected collection is not a user collection.")
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
        self.widget.createStatusLabel.setText("STATUS: compressing "+source)
        self.collectionTreeModel.uncheckTree()
        stdout, stderr = self.ic.executeRule(ruleFile, params)
        if stderr == []:
            self.widget.createStatusLabel.setText("STATUS: Created " + str(stdout))
            parentIdx = self.collectionTreeModel.getParentIdx(idx)
            self.collectionTreeModel.refreshSubTree(parentIdx)
            if migrateResc != self.ic.defaultResc:
                obj = self.ic.session.data_objects.get(stdout[0])
                self.widget.createStatusLabel.setText("STATUS: Created " + str(stdout) +\
                                                      "\n Migrate data bundle.")
                self.ic.updateMetadata([obj], 'RESOURCE', 'archive')
        else:
            self.widget.createStatusLabel.setText("ERROR: Create failed: " + str(stderr))


    def unpackDataBundle(self):
        idx, source = self.collectionTreeModel.get_checked()
        if not source.endswith(".irods.tar") or source.endswith(".irods.tar"):
            self.widget.unpack.setText("ERROR: No *.irods.tar or *.irods.zip selected")

        print("TODO")


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

