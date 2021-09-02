from PyQt5.QtWidgets import QMainWindow, QHeaderView, QMessageBox
import logging

from customTreeViews import CheckableDirModel, IrodsModel
from continousUpload import contUpload

from irodsCreateCollection import irodsCreateCollection


class testIrodsFS:
    def __init__(self, widget, ic):
        self.ic = ic
        self.widget = widget

        self.testirodsmodel = IrodsModel(ic, self.widget.testIrodsTree)
        self.widget.testIrodsTree.setModel(self.testirodsmodel)
        self.widget.testIrodsTree.expanded.connect(self.testirodsmodel.expanded)
        self.widget.testIrodsTree.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.testirodsmodel.initial_expand()

        self.widget.refreshButton.clicked.connect(self.refresh)


    def refresh(self):
        idx, irodsColl = self.testirodsmodel.get_checked()
        self.testirodsmodel.initial_expand(irodsColl)
