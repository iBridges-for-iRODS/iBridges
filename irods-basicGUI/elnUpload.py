from elabConnector import elabConnector
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QMessageBox, QTableWidgetItem, QFileSystemModel

import os
from irodsUtils import getSize, walkToDict

class elnUpload():
    def __init__(self, ic, globalErrorLabel, elnTokenInput,
                 elnGroupTable, elnExperimentTable, groupIdLabel,
                 experimentIdLabel, localFsTable, 
                 elnUploadButton, elnPreviewBrowser, elnIrodsPath):

        self.elab = None
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

        except Exception as e:
            self.globalErrorLabel.setText("ELN ERROR: "+repr(e))

    
    def setElabConfig(self):
        #Ensure that elab object has correct experiment ID
        print("Todo setElabConfig")
        self.loadLocalFileView()
        #get group id and expid from tables
        #params = {'group': id, 'experiment': id}
        #self.elab.updateMetadataUrl(**params)
    
    
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
    
    def uploadData(self):
        #upload data to iRODS
        # Upload to /ELN/projectID/ExperimentID
        # Show new iRODS paths in self.elnPreviewBrouwser
        self.elnUploadButton.setCursor(QtGui.QCursor(QtCore.Qt.WaitCursor))
        self.elnPreviewBrowser.clear()
        self.globalErrorLabel.clear()
        groupId = self.groupIdLabel.text()
        expId = self.experimentIdLabel.text()
        print("Group and Experiment: ", groupId, expId)
        subcoll = 'ELN/'+groupId+'/'+expId
        if groupId == '' or expId == '':
            self.globalErrorLabel.setText('ERROR ELN Upload: No Experiment selected')
            pass

        expUrl = self.elab.updateMetadataUrl(**{'group': int(groupId), 'experiment': int(expId)})
        print(expUrl)

        indices = self.localFsTable.selectedIndexes()
        filePaths = set([idx.model().filePath(idx) for idx in indices])
        #If folder is uploaded get all filenames to annotate
        filenames = [os.path.basename(path) for path in filePaths]
        [filenames.extend(os.listdir(path)) for path in filePaths if os.path.isdir(path)]
        filenames = set(filenames)
        size = round(sum([getSize(path) for path in filePaths])/1024**2)
        
        buttonReply = QMessageBox.question(self.elnUploadButton, 
                                  'Message Box', "Upload\n" + '\n'.join(filePaths) + \
                                          '\n'+str(size)+'MB',
                                  QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        upload = buttonReply == QMessageBox.Yes
        if upload:
            try:
                collPath = '/'+self.ic.session.zone+'/home/'+self.ic.session.username+\
                                   '/'+subcoll
                coll = self.ic.ensureColl(collPath)
                self.elnIrodsPath.setText(collPath)
                for path in filePaths:
                    self.ic.uploadData(path, coll, None, size, force=True)
                print("Upload complete.")
                items = [item for sub in [[c]+objs for c, _, objs in coll.walk()] 
                            for item in sub if item.name in filenames]

                self.ic.addMetadata(items, 'ELN', expUrl)
                if self.ic.davrods:
                    self.elab.addMetadata(self.ic.davrods, title='Data in iRODS')
                else:
                    self.elab.addMetadata('{'+self.ic.session.host+', \n'\
                                             +self.ic.session.zone+', \n'\
                                             +self.ic.session.username+', \n'\
                                             +str(self.ic.session.port)+'}', title='Data in iRODS')
                irodsDict = walkToDict(coll)
                for key in list(irodsDict.keys())[:20]:
                    self.elnPreviewBrowser.append(key)
                    if len(irodsDict[key]) > 0:
                        for item in irodsDict[key]:
                            self.elnPreviewBrowser.append('\t'+item)
                self.elnPreviewBrowser.append('...')
                self.globalErrorLabel.setText("ELN upload success: "+coll.path)
            except Exception as error:
                self.globalErrorLabel.setText(repr(error))
                raise
            self.elnUploadButton.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        else:
            self.elnUploadButton.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
            pass

    
    
    #elab.updateMetadataUrl(**{'group': 2518, 'experiment': 479738}) #string:int
    
    
    
