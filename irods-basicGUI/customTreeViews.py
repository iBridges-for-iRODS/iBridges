from PyQt5.QtWidgets import QFileSystemModel, QFileIconProvider
from PyQt5.QtCore import QFile, Qt, QDir
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from sys import platform
from time import sleep
import logging
import os

# a class to put checkbox on the folders and record which ones are checked.
class CheckableDirModel(QFileSystemModel):

    def __init__(self, TreeView, parent=None):
        """
        Initializes the Treeview with the root node. 
        """
        QFileSystemModel.__init__(self, None)
        self._checked_indeces = set() # keep track of the check files and folders...
        self.TreeView = TreeView
        self.setRootPath(QDir.currentPath())


    def inital_expand(self, previous_item = None):
        """
        Expands the Tree untill 'previous_item' and selects it.
        Input: filepath till previously selected file or folder
        """
        if previous_item != None: 
            index = self.index(previous_item, 0)
            self.TreeView.scrollTo(index)
            self._checked_indeces.add(index)
            self.setData(index, Qt.Checked, Qt.CheckStateRole)


    # Used to update the UI
    def data(self, index, role= Qt.DisplayRole):
        if role == Qt.CheckStateRole:
            if index in self._checked_indeces:
                return Qt.Checked
            else:
                return Qt.Unchecked
        return QFileSystemModel.data(self, index, role)

    def flags(self, index):
        return QFileSystemModel.flags(self, index) | Qt.ItemIsUserCheckable | Qt.ItemIsAutoTristate


    # Callback of the checkbox
    def setData(self, index, value, role=Qt.EditRole):
        if role == Qt.CheckStateRole:
            #filename = self.data(index, QFileSystemModel.FileNameRole)
            if value == Qt.Checked:
                # Enforce single select
                while self._checked_indeces:
                    selected_index = self._checked_indeces.pop()
                    self.setData(selected_index, Qt.Unchecked, role)
                self._checked_indeces.add(index)
            else:
                self._checked_indeces.discard(index)
            self.TreeView.repaint()
            return True
        return QFileSystemModel.setData(self, index, value, role)


    # Returns the last selected item
    def get_checked(self):
        if len(self._checked_indeces) < 1:
            return None
        checked_item = list(self._checked_indeces)[0]
        filepath = self.filePath(checked_item)
        return filepath

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
        self.basepath = "/" + self.ic.session.zone + "/"
        self.TreeView = TreeView
        self.clear() # Empty tree
        rootnode = self.invisibleRootItem()
        self.grow_tree(rootnode, self.basepath, "home") 


    # Grow Tree till 'previous_item' and select it.
    def inital_expand(self, previous_item = None):
        """
        Grows the Tree untill 'previous_item' and selects it.
        Input: filepath till previously selected file or folder
        """
        if previous_item != None:
            folders = previous_item.split("/")
            cur_path = ""
            modelindex = None
            for folder in folders[2:]:
                cur_path = cur_path + "/" + folder
                if modelindex == None: # Root
                    modelindex = self.index(0, 0) 
                else:  # Find right child and expand
                    for row in range(self.rowCount(modelindex)):
                        childindex = self.index(row, 0, modelindex)
                        if childindex.data() == folder: # foldername
                            modelindex = self.index(row, 0, modelindex)
                self.expanded(modelindex)
            self.TreeView.scrollTo(modelindex)
            self._checked_indeces.add(modelindex)
            self.setData(modelindex, Qt.Checked, Qt.CheckStateRole)


    # Used to update the UI
    def data(self, index, role= Qt.DisplayRole):
        if role == Qt.CheckStateRole:
            if index in self._checked_indeces:
                return Qt.Checked
            else:
                return Qt.Unchecked
        return super(IrodsModel, self).data(index, role)


    def flags(self, index):
        return super(IrodsModel, self).flags(index) | Qt.ItemIsUserCheckable | Qt.ItemIsAutoTristate


    # Callback of the checkbox
    def setData(self, index, value, role=Qt.EditRole):
        if role == Qt.CheckStateRole:
            #filename = self.data(index)
            if value == Qt.Checked:
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


    # Use to create the tree one layer at a time (avoid retreiving all files at the start of the program)
    def grow_tree(self, root, path, child):
        icon_provider = QFileIconProvider()
        fullpath = path + child
        if "." in fullpath:
            #logging.info(f"can't grow files: {fullpath}")
            return
        coll = self.ic.session.collections.get(fullpath)
        if path[-1] != "/":
            path = path + "/"
        parent = root
        for obj in coll.data_objects:
            # Add file to Tree
            file = QStandardItem(obj.name)
            file.setIcon(icon_provider.icon(QFileIconProvider.IconType.File))
            parent.setChild(parent.rowCount(), file)

        # folders 
        for srcColl in coll.subcollections:
            parent = root
            folders = srcColl.path.replace(path,'').split("/")
            for folder in folders:
                for i in range(parent.rowCount()):
                    item = parent.child(i) 
                    if item.text() == folder:
                        it = item
                        break
                else:
                    it = QStandardItem(folder)     
                    it.setIcon(icon_provider.icon(QFileIconProvider.IconType.Folder))
                    parent.setChild(parent.rowCount(), it)
                parent = it


    # Grow tree when a folder is opend.
    def expanded(self, modelindex):#Qt.QtCore.Qmoddelindex
        fullpath = self.create_fullpath(modelindex)
        for row in range(self.rowCount(modelindex)):
            childindex = self.index(row, 0, modelindex)
            childname = childindex.data()
            item = self.itemFromIndex(childindex)
            temp = item.text()
            if item.hasChildren() == False:
                self.grow_tree(item, fullpath + "/" + childname, "")


    # Refresh a folder after uploading files
    def upload_refresh(self, modelindex, new_path):
        item = self.itemFromIndex(modelindex)
        icon_provider = QFileIconProvider()
        if os.path.isfile(new_path):
            folder, filename = os.path.split(new_path)
            file = QStandardItem(filename)
            file.setIcon(icon_provider.icon(QFileIconProvider.IconType.File))
            item.setChild(item.rowCount(), file)
        else:
            foldername = new_path.split('/')[-1]
            it = QStandardItem(foldername)     
            it.setIcon(icon_provider.icon(QFileIconProvider.IconType.Folder))
            item.setChild(item.rowCount(), it)
            self.grow_tree(it, self.create_fullpath(modelindex) + "/" + foldername, "")



    # Returns index & path pairs which can be used to update the tree after an upload
    def get_checked(self):
        if len(self._checked_indeces) < 1:
            return (None, None)
        checked_item = list(self._checked_indeces)[0]
        return (checked_item, self.create_fullpath(checked_item))


    # Helper function to traverse the tree from the current index back to the root, storing the item names along the way
    def create_fullpath(self, modelindex):
        fullpath = modelindex.data()
        parentmodel = modelindex.parent()
        while parentmodel.isValid():
            fullpath = parentmodel.data() + "/" + fullpath
            parentmodel = parentmodel.parent()
        return self.basepath + fullpath