import logging
import sys

import irods.exception
import PyQt6.QtCore
import PyQt6.QtGui
import PyQt6.QtWidgets
import PyQt6.uic

import gui
import meta
import utils
from gui.irodsTreeView import IrodsModel

class IrodsExampleTab(PyQt6.QtWidgets.QWidget,
                   gui.ui_files.ExampleTab.Ui_ExampleTab):
    context = utils.context.Context()
    def __init__(self):
        super().__init__()
        if getattr(sys, 'frozen', False):
            super().setupUi(self)
        else:
            PyQt6.uic.loadUi("gui/ui_files/ExampleTab.ui", self)
        self.error_label.setText("Whooohoo")

        self._initialize_irods_model(self.irodsTreeView)
        self.irodsTreeView.clicked.connect(self.treeFunction)

    def _initialize_irods_model(self, treeView):
        self.irodsmodel = IrodsModel(treeView)
        treeView.setModel(self.irodsmodel)
        irodsRootColl = self.context.irods_environment.config.get(
                'irods_home', '/'+self.context.irods_connector.zone)
        self.irodsmodel.setHorizontalHeaderLabels([irodsRootColl,
                                              'Level', 'iRODS ID',
                                              'parent ID', 'type'])
        treeView.expanded.connect(self.irodsmodel.refresh_subtree)
        treeView.clicked.connect(self.irodsmodel.refresh_subtree)
        self.irodsmodel.init_tree()

        treeView.setHeaderHidden(True)
        treeView.header().setDefaultSectionSize(180)
        treeView.setColumnHidden(1, True)
        treeView.setColumnHidden(2, True)
        treeView.setColumnHidden(3, True)
        treeView.setColumnHidden(4, True)

    def _get_paths_from_trees(self, treeView, local=False):
        index = treeView.selectedIndexes()[0]
        if local:
            path = self.localmodel.filePath(index)
        else:
            path = self.irodsmodel.irods_path_from_tree_index(index)
        return(index, path)

    def treeFunction(self):
        index, path = self._get_paths_from_trees(self.irodsTreeView)
        self.textField.setText(path)
 
        return(index, path)



