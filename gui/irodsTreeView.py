from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import QFileIconProvider, QMessageBox
from PyQt5.QtCore import Qt
from irods.exception import NetworkException

import os
from collections import deque
import logging

"""
Tree model for IRODS collections. 
The IRODS database is huge and retreiving a complete tree of all files can take ages. 
Too improve the loading time the tree is only grown as far as its shows. 
""" 

class IrodsModel(QStandardItemModel):
    def __init__(self, irods_session, TreeView, parent=None):
        """
        Initializes the Treeview with the root node and first level. 
        """
        super(IrodsModel, self).__init__(parent)
        self._checked_indeces = set()
        self.ic = irods_session
        #Groups which the user id member of to check access rights on tree
        try:
            self.user_groups = self.ic.get_user_info()[1]
        except Exception as e:
            logging.info('iRODS FILE TREE ERROR: user info', exc_info=True)

        try:
            coll = self.ic.session.collections.get('/'+self.ic.session.zone+'/home')
            self.irodsRootColl = "/"+self.ic.session.zone+"/home"
        except NetworkException:
            logging.info('iRODS FILE TREE ERROR: retrieving collection', exc_info=True)
        except:
            self.irodsRootColl = "/"+self.ic.session.zone+"/home/"+self.ic.session.username

        self.TreeView = TreeView
        self.clear() # Empty tree
        rootnode = self.invisibleRootItem()


    def data(self, index, role= Qt.DisplayRole):
        if role == Qt.CheckStateRole:
            if index in self._checked_indeces:
                return Qt.Checked
            else:
                return Qt.Unchecked
        return super(IrodsModel, self).data(index, role)


    def flags(self, index):
        return super(IrodsModel, self).flags(index) | Qt.ItemIsUserCheckable | Qt.ItemIsAutoTristate


    def setData(self, index, value, role=Qt.EditRole):

        if role == Qt.CheckStateRole:
            if value == Qt.Checked:
                #check irods ACLs for access rights
                path = self.irodsPathFromTreeIdx(index)
                try:
                    reqAcls = [('own', path, group, self.ic.session.zone) for group in self.user_groups]
                    reqAcls.extend([('write', path, group, self.ic.session.zone) \
                                    for group in self.user_groups])
                    reqAcls.extend([('read object', path, group, self.ic.session.zone) \
                                    for group in self.user_groups])

                    acls = set([(acl.access_name, acl.path, acl.user_name, acl.user_zone) 
                            for acl in self.ic.get_permissions(path)])
                    # Block checking of home item (found no easy way to remove the checkbox)
                    if acls.intersection(reqAcls) == set():
                        message = "ERROR, insufficient rights:\nCannot select "+path
                        QMessageBox.information(self.TreeView, 'Error', message)
                        #logging.info("Filedownload:" + message)
                        return False
                except:
                    logging.info('IRODS TREE ERROR', exc_info=True)
                    return False
                # Enforce single select
                while self._checked_indeces:
                    selected_index = self._checked_indeces.pop()
                    super(IrodsModel, self).setData(selected_index, Qt.Unchecked, role)
                # Add newly selected item
                self._checked_indeces.add(index)
            else:
                self._checked_indeces.discard(index)
            self.TreeView.repaint() # force refresh
            return True
        return super(self).setData(self, index, value, role)


    def get_checked(self):
        if len(self._checked_indeces) < 1:
            return (None, None)
        checked_item = list(self._checked_indeces)[0]
        return (checked_item, self.irodsPathFromTreeIdx(checked_item))


    def initIrodsFsData(self):
        """
        Retrieves the first levels of an iRODS tree: /zone/home/*.
        Returns the information as list of dictionaries:
        [{'irodsID': 12345, 'level': 10, 'parentID': 54321, 'shortName': 'myColl', 'type': 'C'}, {}]
        The level of 'home' is 0 and its parentID is -1.
        'type' can take values 'C' (collection) or 'd' (dtaa object)
        """
        #initial tree information
        parentId = -1
        try:
            coll = self.ic.session.collections.get(self.irodsRootColl)
        except:
            logging.info('IRODS TREE INIT ERROR',
                        exc_info=True)
            return
        level = 0
        data = [{'level': level, 'irodsID': coll.id, 'parentID': -1,
                 'shortName': coll.name, 'type': 'C'}]
        #get content of home
        for subColl in coll.subcollections:
            level = 1
            data.append({'level': level, 'irodsID': subColl.id,
                         'parentID': coll.id, 'shortName': subColl.name, 'type': 'C'})
            if subColl.data_objects != [] or subColl.subcollections != []:
                data.append({'level': level+1, 'irodsID': 'test',
                             'parentID': subColl.id, 'shortName': 'test', 'type': 'd'})
        for obj in coll.data_objects:
            #level = len(obj.path.split(self.irodsRootColl+'/')[1].split('/')) - 1
            level = 1
            data.append({'level': level, 'irodsID': obj.id,
                         'parentID': coll.id, 'shortName': obj.name, 'type': 'd'})
        return data


    def initTree(self):
        """
        Draws the first levels of an iRODS filesystem as a tree.
        """
        icon_provider = QFileIconProvider()
        self.setRowCount(0)
        root = self.invisibleRootItem()

        # First levels of iRODS data
        irodsFsData = self.initIrodsFsData()

        # Build Tree
        seen = {} # nodes in the tree
        values = deque(irodsFsData)
        while values:
            value = values.popleft()
            if value['level'] == 0:
                parent = root
            else:
                pid = value['parentID']
                if pid not in seen:
                    values.append(value)
                    continue
                parent = seen[pid]
            irodsID = value['irodsID']
            display = QStandardItem(value['shortName'])
            if value['type'] == 'd':
                 display.setIcon(icon_provider.icon(QFileIconProvider.IconType.File))
            if value['type'] == 'C':
                 display.setIcon(icon_provider.icon(QFileIconProvider.IconType.Folder))
            parent.appendRow([
                              display,
                              QStandardItem(str(value['level'])),
                              QStandardItem(str(value['irodsID'])),
                              QStandardItem(str(value['parentID'])),
                              QStandardItem(value['type'])
                            ])
            seen[irodsID] = parent.child(parent.rowCount() - 1)


    def deletesubTree(self, treeItem):
        """
        treeItem: QStandardItem in the QTreeView
        """
        #Adjust treeview --> remove subtree
        treeItem.removeRows(0, treeItem.rowCount())


    def getCollData(self, coll):
        """
        Retrieves the subcollections and data objects of a collection.
        Returns the information as list of dictionaries
        [{'irodsID': 12345, 'level': 10, 'parentID': 54321, 'shortName': 'myColl', 'type': 'C'}, {}]
        coll: irods collection
        data: list of dictionaries
        """
        data = []
        for subColl in coll.subcollections:
            level = len(subColl.path.split('/')) - len(self.irodsRootColl.split('/'))
            data.append({'level': level, 'irodsID': subColl.id,
                         'parentID': coll.id, 'shortName': subColl.name, 'type': 'C'})
            if subColl.data_objects != [] or subColl.subcollections != []:
                data.append({'level': level+1, 'irodsID': 'test',
                             'parentID': subColl.id, 'shortName': 'test', 'type': 'd'})
        for obj in coll.data_objects:
            level = len(obj.path.split('/')) - len(self.irodsRootColl.split('/'))
            data.append({'level': level, 'irodsID': obj.id,
                         'parentID': coll.id, 'shortName': obj.name, 'type': 'd'})
        return data


    def addSubtree(self, treeItem, treeLevel, irodsFsSubtreeData):
        #grow treeView from treeItem
        icon_provider = QFileIconProvider()
        values = deque(irodsFsSubtreeData)
        seen = {}

        while values:
            value = values.popleft()
            if value['level'] == treeLevel:
                parent = treeItem
            else:
                pid = value['parentID']
                if pid not in seen:
                    values.append(value)
                    continue
                parent = seen[pid]
            irodsID = value['irodsID']
            display = QStandardItem(value['shortName'])
            if value['type'] == 'd':
                display.setIcon(icon_provider.icon(QFileIconProvider.IconType.File))
            if value['type'] == 'C':
                 display.setIcon(icon_provider.icon(QFileIconProvider.IconType.Folder))
            parent.appendRow([
                              display,
                              QStandardItem(str(value['level'])),
                              QStandardItem(str(value['irodsID'])),
                              QStandardItem(str(value['parentID'])),
                              QStandardItem(value['type'])
                            ])
            seen[irodsID] = parent.child(parent.rowCount() - 1)


    def getParentIdx(self, position):
        try: #index when right mouse click
            modelIndex = self.tree.indexAt(position)
            if not modelIndex.isValid():
                return
        except: #index when expand is clicked
            modelIndex = position

        treeItem = self.itemFromIndex(modelIndex)

        parent = treeItem.parent()
        
        return parent.index()

    def refreshSubTree(self, position):
        
        try: #index when right mouse click
            modelIndex = self.tree.indexAt(position)
            if not modelIndex.isValid():
                return
        except: #index when expand is clicked
            modelIndex = position

        treeItem = self.itemFromIndex(modelIndex)
        parent = treeItem.parent()
        if parent == None:
            parent = self.invisibleRootItem()

        row = treeItem.row()

        treeItemData = []
        for col in range(parent.columnCount()):
            child = parent.child(row, col)
            treeItemData.append(child.data(0))

        irodsItemPath = self.irodsPathFromTreeIdx(modelIndex)

        if treeItemData[4] == 'C': # collection
            coll = self.ic.session.collections.get(irodsItemPath)
        else:
            return
        #delete subtree in irodsFsdata and the TreeView
        self.deletesubTree(treeItem)

        #Retrieve updated data from the collection
        recentCollData = self.getCollData(coll)

        #update irodsFsData and the treeView
        #Level of subcollections
        level = len(coll.path.split('/')) - len(self.irodsRootColl.split('/')) + 1
        self.addSubtree(treeItem, level, recentCollData)


    def irodsPathFromTreeIdx(self, modelindex):
        fullpath = modelindex.data()
        parentmodel = modelindex.parent()
        while parentmodel.isValid():
            fullpath = parentmodel.data() + "/" + fullpath
            parentmodel = parentmodel.parent()
        return os.path.dirname(self.irodsRootColl) + "/" + fullpath

