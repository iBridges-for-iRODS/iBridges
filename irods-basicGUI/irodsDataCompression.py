from irodsTreeView  import IrodsModel

class irodsDataCompression():
    def __init__(self, widget, ic, ienv):
        self.ic = ic
        self.widget = widget
        self.ienv = ienv

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
        source = self.collectionTreeModel.get_checked()
        print(source)
        #if source == None:
        #    self.widget.createStatusLabel.setText("No collection selected.")
        #    return
        if not self.ic.session.collections.exists(source):
            self.widget.createStatusLabel.setText("No collection selected.")
            return


        print("TODO")


    def unpackDataBundle(self):
        print("TODO")


    def getIndex(self):
        print("TODO")
