from elabConnector import elabConnector
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QMessageBox, QTableWidgetItem, QFileSystemModel
from PyQt5.QtCore import QObject, QThread, pyqtSignal

import os
from irodsUtils import getSize, walkToDict
from irods.exception import CATALOG_ALREADY_HAS_ITEM_BY_THAT_NAME

class elabUpload():
    def __init__(self, ic, globalErrorLabel, elnTokenInput,
                 elnGroupTable, elnExperimentTable, groupIdLabel,
                 experimentIdLabel, localFsTable, 
                 elnUploadButton, elnPreviewBrowser, elnIrodsPath):

        self.elab = None
        self.coll = None
        self.ic = ic
        # Return errors to:
        self.globalErrorLabel = globalErrorLabel
        #Gathering Eln configuration
        self.elnTokenInput = elnTokenInput
        self.elnGroupTable = elnGroupTable
        self.elnGroupTable.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.elnExperimentTable = elnExperimentTable
        self.elnExperimentTable.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        #Config ok check
        self.groupIdLabel = groupIdLabel
        self.experimentIdLabel = experimentIdLabel
        #Selecting and uploading local files and folders
        self.localFsTable = localFsTable
        self.localFsTable.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.elnUploadButton = elnUploadButton
        #Showing result
        self.elnPreviewBrowser = elnPreviewBrowser
        self.elnIrodsPath = elnIrodsPath

        #defining events and listeners
        self.elnTokenInput.returnPressed.connect(self.connectElab)
        self.elnGroupTable.clicked.connect(self.loadExperiments)
        self.elnExperimentTable.clicked.connect(self.selectExperiment)
        self.elnUploadButton.clicked.connect(self.uploadData)
    
    
    def connectElab(self):
        self.globalErrorLabel.clear()
        token = self.elnTokenInput.text()
        print(token)
        #ELN can potentially be offline
        try:
            self.elab = elabConnector(token)
            groups = self.elab.showGroups(get=True)
            self.elnGroupTable.setRowCount(len(groups))
            row = 0
            for group in groups:
                self.elnGroupTable.setItem(row, 0, QTableWidgetItem(group[0]))
                self.elnGroupTable.setItem(row, 1, QTableWidgetItem(group[1]))
                row = row + 1
            self.elnGroupTable.resizeColumnsToContents()
            self.loadLocalFileView()
            self.elnGroupTable.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        except Exception as e:
            self.globalErrorLabel.setText("ELN ERROR: "+repr(e))

    
    def selectExperiment(self, expId):
        #put exp id in self experimentIdLabel
        self.globalErrorLabel.clear()
        row = self.elnExperimentTable.currentRow()
        if row > -1:
            expId = self.elnExperimentTable.item(row, 0).text()
            self.experimentIdLabel.setText(expId)


    def loadExperiments(self):
        self.globalErrorLabel.clear()
        self.elnGroupTable.setCursor(QtGui.QCursor(QtCore.Qt.WaitCursor))
        row = self.elnGroupTable.currentRow()
        if row > -1:
            groupId = self.elnGroupTable.item(row, 0).text()
            self.groupIdLabel.setText(groupId)
            try:
                userExp, otherExp = self.elab.showExperiments(int(groupId), get = True)
                self.elnExperimentTable.setRowCount(len(userExp+otherExp)+1)
                row = 0
                for exp in userExp:
                    self.elnExperimentTable.setItem(row, 0, QTableWidgetItem(exp[0]))
                    self.elnExperimentTable.setItem(row, 1, QTableWidgetItem(exp[1]))
                    self.elnExperimentTable.setItem(row, 2, QTableWidgetItem(exp[2]))
                    row = row+1
                self.elnExperimentTable.setItem(row, 0, QTableWidgetItem(""))
                self.elnExperimentTable.setItem(row, 1, QTableWidgetItem(""))
                self.elnExperimentTable.setItem(row, 2, QTableWidgetItem(""))
                row = row+1
                for exp in otherExp:
                    self.elnExperimentTable.setItem(row, 0, QTableWidgetItem(exp[0]))
                    self.elnExperimentTable.setItem(row, 1, QTableWidgetItem(exp[1]))
                    self.elnExperimentTable.setItem(row, 2, QTableWidgetItem(exp[2]))
                    row = row+1
            except Exception as e:
                self.globalErrorLabel.setText("ELN ERROR: "+repr(e))
                raise

        self.elnExperimentTable.resizeColumnsToContents()
        self.elnGroupTable.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
    

    def loadLocalFileView(self):
        #Load current directory in self.localFsTable
        model = QFileSystemModel()
        home_location = QtCore.QStandardPaths.standardLocations(
                               QtCore.QStandardPaths.HomeLocation)[0]
        index = model.setRootPath(home_location)
        self.localFsTable.setModel(model)
        self.localFsTable.setCurrentIndex(index)
        self.localFsTable.setIndentation(20)
        self.localFsTable.setColumnWidth(0, 400)


    def reportProgress(self, n):
        self.globalErrorLabel.setText("ELN UPLOAD STATUS: Uploading ...")

    def reportFinished(self):
        self.elnUploadButton.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.elnUploadButton.setEnabled(True)
        self.showPreview()
        self.globalErrorLabel.setText("ELN UPLOAD STATUS: Uploaded to "+self.coll.path)
        self.elnIrodsPath.setText('/zone/home/user')
        self.thread.quit()

    def showPreview(self):
        irodsDict = walkToDict(self.coll)
        for key in list(irodsDict.keys())[:50]:
            self.elnPreviewBrowser.append(key)
            if len(irodsDict[key]) > 0:
                for item in irodsDict[key]:
                    self.elnPreviewBrowser.append('\t'+item)
        self.elnPreviewBrowser.append('\n\n<First 50 items printed>')
        self.globalErrorLabel.setText("ELN upload success: "+self.coll.path)


    def uploadData(self):
        self.elnUploadButton.setCursor(QtGui.QCursor(QtCore.Qt.WaitCursor))
        self.elnPreviewBrowser.clear()
        self.globalErrorLabel.clear()
	
        try:
            groupId = self.groupIdLabel.text()
            expId = self.experimentIdLabel.text()
            print("Group and Experiment: ", groupId, expId)
            
            #preconfigure upload path prefix
            subcoll = 'ELN/'+groupId+'/'+expId
            #stop if no exp and group is given
            if groupId == '' or expId == '':
                self.globalErrorLabel.setText('ERROR ELN Upload: No Experiment selected')
                pass
            #get the url that will be uploaded as metadata to irods
            expUrl = self.elab.updateMetadataUrl(**{'group': int(groupId), 'experiment': int(expId)})
            print("ELN DATA UPLOAD experiment: \n"+expUrl)
    
            #get all file and folder names from local fs
            indices = self.localFsTable.selectedIndexes()
            filePaths = set([idx.model().filePath(idx) for idx in indices])
            #Get all filenames to annotate later with url
            filenames = [os.path.basename(path) for path in filePaths]
            [filenames.extend(os.listdir(path)) for path in filePaths if os.path.isdir(path)]
            filenames = set(filenames)
    
            #get upload total size to inform user
            size = round(sum([getSize(path) for path in filePaths])/1024**2)
            #if user specifies a different path than standard home
            if self.elnIrodsPath.text() == '/zone/home/user':
                collPath = '/'+self.ic.session.zone+'/home/'+self.ic.session.username+'/'+subcoll
            else:
                collPath = '/'+self.elnIrodsPath.text().strip('/')+'/'+subcoll
            self.coll = self.ic.ensureColl(collPath)
            self.elnIrodsPath.setText(collPath)
    
            buttonReply = QMessageBox.question(
                            self.elnUploadButton,
                            'Message Box', "Upload\n" + '\n'.join(filePaths) + '\n'+str(size)+'MB',
                            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            upload = buttonReply == QMessageBox.Yes
            if upload:
                self.elnUploadButton.setCursor(QtGui.QCursor(QtCore.Qt.WaitCursor))
                self.elnUploadButton.setEnabled(False)
                #start own thread for the upload 
                self.thread = QThread()
                self.worker = Worker(self.ic, self.elab, self.coll, 
                                    size, filePaths, filenames, 
                                    expUrl, self.elnPreviewBrowser, self.globalErrorLabel)
                self.worker.moveToThread(self.thread)
                self.thread.started.connect(self.worker.run)
                self.worker.finished.connect(self.thread.quit)
                self.worker.finished.connect(self.worker.deleteLater)
                self.thread.finished.connect(self.thread.exit)
                self.worker.progress.connect(self.reportProgress)
                self.thread.start()
                self.thread.finished.connect(self.reportFinished)
            else:
                self.elnUploadButton.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
    
        except Exception as e:
            self.globalErrorLabel.setText(repr(e))
            self.elnUploadButton.setEnabled(True)
            self.elnUploadButton.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))

class Worker(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(int)

    def __init__(self, ic, elab, coll, size, 
                 filePaths, filenames, expUrl, elnPreviewBrowser, globalErrorLabel):
        super(Worker, self).__init__()
        self.ic = ic
        self.coll = coll
        self.filePaths = filePaths
        self.filenames = filenames
        self.elnPreviewBrowser = elnPreviewBrowser
        self.size = size
        self.expUrl = expUrl
        self.elab = elab
        self.globalErrorLabel = globalErrorLabel

        print("Start worker: ")


    def run(self):
        i = 1
        try:
            for path in self.filePaths:
                self.progress.emit(i)
                self.ic.uploadData(path, self.coll, None, self.size, force=True)
                i = i+1
            print("Upload complete.")
            items = [item for sub in [[c]+objs for c, _, objs in self.coll.walk()] 
                    for item in sub if item.name in self.filenames]
            try:
                self.ic.addMetadata(items, 'ELN', self.expUrl)
            except CATALOG_ALREADY_HAS_ITEM_BY_THAT_NAME as e:
                print(repr(e))
            self.progress.emit(3)
            self.finished.emit()
        except Exception as e:
            print(repr(e))

        self.annotateElab()
	
    def annotateElab(self):
        self.globalErrorLabel.setText("Linking data to Elabjournal experiment.")
        if self.ic.davrods and "yoda" in self.ic.session.host:
            self.elab.addMetadata(self.ic.davrods+'/'+self.coll.path.split('home/')[1],
                    title='Data in iRODS')
        elif self.ic.davrods:
            self.elab.addMetadata(self.ic.davrods+'/'+self.coll.path, title='Data in iRODS')
        else:
            self.elab.addMetadata('{'+self.ic.session.host+', \n'\
                                    +self.ic.session.zone+', \n'\
                                    +self.ic.session.username+', \n'\
                                    +str(self.ic.session.port)+'}\n'+
                                    self.coll.path, title='Data in iRODS')
    
