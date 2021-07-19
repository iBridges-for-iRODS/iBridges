from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QDialog, QApplication, QMainWindow, QMessageBox
from PyQt5.uic import loadUi
from PyQt5 import QtCore
from PyQt5 import QtGui

#class irodsBrowser(QDialog):
class irodsBrowser(QMainWindow):
    def __init__(self, ic):
        super(irodsBrowser, self).__init__()
        #loadUi("irodsBrowser.ui", self)
        loadUi("irodsBrowserMain.ui", self)
        self.ic = ic

        #Main widget --> browser
        self.irodsRoot = self.ic.session.collections.get("/"+ic.session.zone+"/home")
        self.collTable.setColumnWidth(1,399)
        self.collTable.setColumnWidth(2,199)
        self.collTable.setColumnWidth(3,399)
        self.collTable.setColumnWidth(0,20)
        self.collTable.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.collTable.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.collTable.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.collTable.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.resetPath() 

        #Home button
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("home.png"))
        self.homeButton.setIcon(icon)

        #Metadata table
        self.metadataTable.setColumnWidth(0,199)
        self.metadataTable.setColumnWidth(1,199)
        self.metadataTable.setColumnWidth(2,199)
        self.metadataTable.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.metadataTable.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.metadataTable.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
        self.metadataTable.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

        #ACL table
        self.aclTable.setColumnWidth(0,299)
        self.aclTable.setColumnWidth(1,299)
        self.aclTable.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.aclTable.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.aclTable.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.metadataTable.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

        #Resource table
        self.resourceTable.setColumnWidth(0,500)
        self.resourceTable.setColumnWidth(1,90)
        self.resourceTable.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.resourceTable.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.resourceTable.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)

        self.actionExit.triggered.connect(self.programExit)
        self.actionCloseSession.triggered.connect(self.newSession)
        self.browse()

    def programExit(self):
        quit_msg = "Are you sure you want to exit the program?"
        reply = QMessageBox.question(self, 'Message', quit_msg, QMessageBox.Yes, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.ic.session.cleanup()
            sys.exit()
        else:
            pass


    def newSession(self):
        quit_msg = "Are you sure you want to disconnect?"
        reply = QMessageBox.question(self, 'Message', quit_msg, QMessageBox.Yes, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.ic.session.cleanup()
            currentWidget = widget.currentWidget()
            widget.setCurrentIndex(widget.currentIndex()-1)
            widget.removeWidget(currentWidget)

        else:
            pass


    def browse(self):
        self.inputPath.returnPressed.connect(self.loadTable)
        self.homeButton.clicked.connect(self.resetPath)
        self.collTable.doubleClicked.connect(self.updatePath)
        self.collTable.clicked.connect(self.fillInfo)


    def resetPath(self):
        self.inputPath.setText(self.irodsRoot.path)
        self.loadTable()


    @QtCore.pyqtSlot(QtCore.QModelIndex)
    def fillInfo(self, index):
        self.previewBrowser.clear()
        self.metadataTable.setRowCount(0);
        self.aclTable.setRowCount(0);
        self.resourceTable.setRowCount(0);
        col = index.column()
        row = index.row()
        value = self.collTable.item(row, col).text()
        self.__fillPreview(value)
        self.__fillMetadata(value)
        self.__fillACLs(value)
        self.__fillResc(value)

    def __fillResc(self, value):
        newPath = "/"+self.inputPath.text().strip("/")+"/"+value.strip("/")
        if not value.endswith("/") and self.ic.session.data_objects.exists(newPath):
            resources = self.ic.listResources()
            self.resourceTable.setRowCount(len(resources)+1)
            obj = self.ic.session.data_objects.get(
                    "/"+self.inputPath.text().strip("/")+"/"+value.strip("/")
                    )
            replicas = [resc.resource_name for resc in obj.replicas]
            for i in range(len(resources)):
                self.resourceTable.setItem(i, 0, 
                        QtWidgets.QTableWidgetItem(resources[i]))
                if resources[i] in replicas:
                    item = QtWidgets.QTableWidgetItem()
                    item.setCheckState(QtCore.Qt.Checked)
                    item.setFlags(QtCore.Qt.ItemIsEnabled)
                    self.resourceTable.setItem(i, 1, item)
        self.resourceTable.resizeColumnsToContents()


    def __fillACLs(self, value):
        newPath = "/"+self.inputPath.text().strip("/")+"/"+value.strip("/")
        acls = []
        if value.endswith("/") and self.ic.session.collections.exists(newPath):
            item = self.ic.session.collections.get(
                        "/"+self.inputPath.text().strip("/")+"/"+value.strip("/")
                        )
            acls = self.ic.session.permissions.get(item)
        elif self.ic.session.data_objects.exists(newPath):
            item = self.ic.session.data_objects.get(
                    "/"+self.inputPath.text().strip("/")+"/"+value.strip("/")
                    )
            acls = self.ic.session.permissions.get(item)
        
        self.aclTable.setRowCount(len(acls)+1)
        row = 0
        for acl in acls:
            self.aclTable.setItem(row, 0,
                        QtWidgets.QTableWidgetItem(acl.user_name))
            self.aclTable.setItem(row, 1,
                        QtWidgets.QTableWidgetItem(acl.access_name))
            row = row+1

        self.aclTable.resizeColumnsToContents()

    def __fillMetadata(self, value):
        newPath = "/"+self.inputPath.text().strip("/")+"/"+value.strip("/")
        metadata = []
        if value.endswith("/") and self.ic.session.collections.exists(newPath):
            coll = self.ic.session.collections.get(
                        "/"+self.inputPath.text().strip("/")+"/"+value.strip("/")
                        )
            metadata = coll.metadata.items()
        elif self.ic.session.data_objects.exists(newPath):
            obj = self.ic.session.data_objects.get(
                    "/"+self.inputPath.text().strip("/")+"/"+value.strip("/")
                    )
            metadata = obj.metadata.items()
        self.metadataTable.setRowCount(len(metadata)+1)
        row = 0
        for item in metadata:
            self.metadataTable.setItem(row, 0,
                    QtWidgets.QTableWidgetItem(item.name))
            self.metadataTable.setItem(row, 1,
                    QtWidgets.QTableWidgetItem(item.value))
            self.metadataTable.setItem(row, 2,
                    QtWidgets.QTableWidgetItem(item.units))
            row = row+1
        self.metadataTable.resizeColumnsToContents()


    def __fillPreview(self, value):
        newPath = "/"+self.inputPath.text().strip("/")+"/"+value.strip("/")
        if value.endswith("/") and self.ic.session.collections.exists(newPath): # collection
            coll = self.ic.session.collections.get(
                        "/"+self.inputPath.text().strip("/")+"/"+value.strip("/")
                        )
            content = [c.name+'/' for c in coll.subcollections] + \
                      [o.name for o in coll.data_objects]

            previewString = '\n'.join(content)
            self.previewBrowser.append(previewString)
        elif self.ic.session.data_objects.exists(newPath): # object
            # get mimetype
            mimetype = value.split(".")[len(value.split("."))-1]
            if mimetype in ['txt', 'json', 'csv']:
                try:
                    obj = self.ic.session.data_objects.get(
                        "/"+self.inputPath.text().strip("/")+"/"+value.strip("/")
                        )
                    out = []
                    with obj.open('r') as readObj:
                        for i in range(20):
                            out.append(readObj.readline())
                    previewString = ''.join([line.decode('utf-8') for line in out])
                    self.previewBrowser.append(previewString)
                except:
                    self.previewBrowser.append(
			"No Preview for: " + "/"+self.inputPath.text().strip("/")+"/"+value.strip("/"))
    

    @QtCore.pyqtSlot(QtCore.QModelIndex)
    def updatePath(self, index):
        col = index.column()
        row = index.row()
        parent = self.inputPath.text()
        value = self.collTable.item(row, 1).text()
        if value.endswith("/"): #collection
            self.inputPath.setText("/"+parent.strip("/")+"/"+value.strip("/"))
            self.loadTable()

    def loadTable(self):
        newPath = "/"+self.inputPath.text().strip("/")
        if self.ic.session.collections.exists(newPath):
            coll = self.ic.session.collections.get(newPath)
            self.collTable.setRowCount(len(coll.data_objects)+len(coll.subcollections))
            row = 0
            for subcoll in coll.subcollections:
                self.collTable.setItem(row, 1, QtWidgets.QTableWidgetItem(subcoll.name+"/"))
                self.collTable.setItem(row, 2, QtWidgets.QTableWidgetItem(""))
                self.collTable.setItem(row, 3, QtWidgets.QTableWidgetItem(""))
                self.collTable.setItem(row, 0, QtWidgets.QTableWidgetItem(""))
                row = row+1
            for obj in coll.data_objects:
                self.collTable.setItem(row, 1, QtWidgets.QTableWidgetItem(obj.name))
                self.collTable.setItem(row, 2, QtWidgets.QTableWidgetItem(str(obj.size)))
                self.collTable.setItem(row, 3, QtWidgets.QTableWidgetItem(str(obj.checksum)))
                #item = QtWidgets.QTableWidgetItem()
                #item.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
                #item.setCheckState(QtCore.Qt.Unchecked)
                #self.collTable.itemClicked.connect(self.__gatherClicked)
                #self.collTable.setItem(row, 0, item)
                row = row+1
            self.collTable.resizeColumnsToContents()


    def __gatherClicked(self):
        print('Click')

