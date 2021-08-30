
from PyQt5.QtWidgets import QMainWindow, QHeaderView
from customTreeViews import CheckableDirModel, IrodsModel

# Vaiables
# localFsTreeWidget, irodsFsTreeWidget
# tab2UploadButton, tab2DownloadButton
# ic (irodsConnector)

# Treeviews
#localFsTreeView
#irodsFsTreeView

# Buttons
#tab2UploadButton
#tab2ContUplBut
#tab2DownloadButton

class irodsUpDownload(QMainWindow):
    def __init__(self, form, ic):
        self.ic = ic
        self.form = form

        # QTreeViews
        self.dirmodel = CheckableDirModel(self.form.localFsTreeView)
        self.form.localFsTreeView.setModel(self.dirmodel)
        # Hide all columns except the Name
        self.form.localFsTreeView.setColumnHidden(1, True)
        self.form.localFsTreeView.setColumnHidden(2, True)
        self.form.localFsTreeView.setColumnHidden(3, True)
        self.form.localFsTreeView.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.dirmodel.inital_expand()

        self.irodsmodel = IrodsModel(ic, self.form.irodsFsTreeView)
        self.form.irodsFsTreeView.setModel(self.irodsmodel)
        self.form.irodsFsTreeView.expanded.connect(self.irodsmodel.expanded)
        self.form.irodsFsTreeView.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.irodsmodel.inital_expand()

        print("init")