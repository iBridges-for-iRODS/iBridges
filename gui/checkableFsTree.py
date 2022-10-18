from PyQt6.QtWidgets import QFileIconProvider, QMessageBox
from PyQt6.QtCore import QFile, Qt, QDir
from PyQt6.QtGui import QFileSystemModel, QStandardItemModel, QStandardItem
from sys import platform
from time import sleep
import logging
import os

# a class to put checkbox on the folders and record which ones are checked.
class checkableFsTreeModel(QFileSystemModel):

    def __init__(self, TreeView):
        """
        Initializes the Treeview with the root node. 
        """
        super().__init__()
        self._checked_indexes = set() # keep track of the check files and folders...
        self.TreeView = TreeView
        self.setRootPath(QDir.currentPath())


    def initial_expand(self, previous_item = None):
        """
        Expands the Tree untill 'previous_item' and selects it.
        Input: filepath till previously selected file or folder
        """
        if previous_item != None: 
            index = self.index(previous_item, 0)
            self.TreeView.scrollTo(index)
            self._checked_indexes.add(index)
            self.setData(index, Qt.CheckState.Checked, Qt.ItemDataRole.CheckStateRole)


    # Used to update the UI
    def data(self, index, role= Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.CheckStateRole:
            if index in self._checked_indexes:
                return Qt.CheckState.Checked
            else:
                return Qt.CheckState.Unchecked
        return QFileSystemModel.data(self, index, role)

    def flags(self, index):
        return QFileSystemModel.flags(self, index) | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsAutoTristate


    # Callback of the checkbox
    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if role == Qt.ItemDataRole.CheckStateRole:
            if value == Qt.CheckState.Checked:
                path = self.data(index, QFileSystemModel.FilePathRole)
                if not os.access(path, os.W_OK):
                    message = "ERROR, insufficient rights:\nCannot select "+path
                    QMessageBox.information(self.TreeView, 'Error', message)
                    return False

                # Enforce single select
                while self._checked_indexes:
                    selected_index = self._checked_indexes.pop()
                    self.setData(selected_index, Qt.CheckState.Unchecked, role)
                self._checked_indexes.add(index)
            else:
                self._checked_indexes.discard(index)
            self.TreeView.repaint()
            return True
        return QFileSystemModel.setData(self, index, value, role)


    # Returns the last selected item
    def get_checked(self):
        if len(self._checked_indexes) < 1:
            return None
        checked_item = list(self._checked_indexes)[0]
        filepath = self.filePath(checked_item)
        return filepath
