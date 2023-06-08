"""Data (Un)Bundle window residing in a tab.

"""
import io
import os
import sys

import PyQt6.QtCore
import PyQt6.QtGui
import PyQt6.QtWidgets
import PyQt6.uic

import gui
import utils
import irodsConnector.keywords as kw

CWD = os.getcwd()
EXTENSIONS = [
    'tar',
    'tar.gz',
    'tgz',
    'tar.bz2',
    'tbz2',
    'zip',
]


class IrodsDataBundle(PyQt6.QtWidgets.QWidget,
                      gui.ui_files.tabDataBundle.Ui_tabDataBundle):
    """Window for (un)bundling data withing the iRODS system.

    """

    context = utils.context.Context()

    def __init__(self):
        """Construct the data bundle window.

        """
        super().__init__()
        if getattr(sys, 'frozen', False):
            super().setupUi(self)
        else:
            PyQt6.uic.loadUi("gui/ui_files/tabDataBundle.ui", self)
        
        self.conf = self.context.ibridges_configuration.config
        self.conn = self.context.irods_connector
        self.thread_create = None
        self.thread_extract = None
        self.worker_create = None
        self.worker_extract = None
        self.root_path = f'/{self.conn.zone}'
        self.irodsZoneLabel.setText(f'{self.root_path}:')
        self.irods_tree_model = self.setup_fs_tree(self.irodsFsTreeView)
        self.irodsFsTreeView.expanded.connect(self.irods_tree_model.refresh_subtree)
        self.setup_resource_selector(self.resourceBox)
        self.createButton.clicked.connect(self.create_data_bundle)
        self.extractButton.clicked.connect(self.extract_data_bundle)

    def info_popup(self, message):
        """Display an informational pop-up with the `message`.

        Parameters
        ----------
        message : str
            Text to display in pop-up.

        """
        PyQt6.QtWidgets.QMessageBox.information(self, 'Information', message)

    def setup_fs_tree(self, tree_view):
        """Initialize the iRODS tree view.

        tree_view : QtWidget
            The widget for this tree view.

        Returns
        -------
        IrodsModel
            Constructed tree view.

        """
        model = gui.irodsTreeView.IrodsModel(tree_view)
        tree_view.setModel(model)
        model.setHorizontalHeaderLabels(
            [self.root_path, 'Level', 'iRODS ID', 'parent ID', 'type'])
        tree_view.expanded.connect(model.refresh_subtree)
        tree_view.clicked.connect(model.refresh_subtree)
        model.init_tree()
        tree_view.setHeaderHidden(True)
        tree_view.header().setDefaultSectionSize(180)
        tree_view.setColumnHidden(1, True)
        tree_view.setColumnHidden(2, True)
        tree_view.setColumnHidden(3, True)
        tree_view.setColumnHidden(4, True)
        return model

    def setup_resource_selector(self, selector):
        """Initialize the resource drop-down menu.

        Parameters
        ----------
        selector : QtWidget

        """
        names, spaces = self.conn.list_resources()
        resources = [
            f'{name} / {space}' for name, space in zip(names, spaces)]
        selector.clear()
        selector.addItems(resources)
        default_resc = self.conn.default_resc
        if default_resc in names:
            ridx = names.index(default_resc)
            index = selector.findText(resources[ridx])
            selector.setCurrentIndex(index)

    def enable_buttons(self):
        """Allow buttons to be pressed.

        """
        self.createButton.setEnabled(True)
        self.extractButton.setEnabled(True)

    def disable_buttons(self):
        """Disallow buttons from being pressed.

        """
        self.createButton.setEnabled(False)
        self.extractButton.setEnabled(False)

    def create_data_bundle(self):
        """Run an iRODS bundle rule on selected collection.

        """
        self.setCursor(
            PyQt6.QtGui.QCursor(PyQt6.QtCore.Qt.CursorShape.WaitCursor))
        self.disable_buttons()
        self.statusLabel.clear()
        coll_indexes = self.irodsFsTreeView.selectedIndexes()
        if not len(coll_indexes):
            self.statusLabel.setText(
                'CREATE ERROR: Something must be selected')
            self.setCursor(
                PyQt6.QtGui.QCursor(PyQt6.QtCore.Qt.CursorShape.ArrowCursor))
            self.enable_buttons()
            return
        else:
            coll_name = self.irods_tree_model.irods_path_from_tree_index(coll_indexes[0])
        if not self.conn.collection_exists(coll_name):
            self.statusLabel.setText(
                'CREATE ERROR: A collection must be selected')
            self.setCursor(
                PyQt6.QtGui.QCursor(PyQt6.QtCore.Qt.CursorShape.ArrowCursor))
            self.enable_buttons()
            return
        # TODO find a better test (add permissions too)
        if len(coll_name.split('/')) < 5:
            self.statusLabel.setText(
                'CREATE ERROR: Collection must be within a user/group collection')
            self.setCursor(
                PyQt6.QtGui.QCursor(PyQt6.QtCore.Qt.CursorShape.ArrowCursor))
            self.enable_buttons()
            return
        src_coll = self.conn.get_collection(coll_name)
        src_size = utils.utils.get_coll_size(src_coll)
        if src_size == 0:
            self.statusLabel.setText(
                'CREATE ERROR: Collection must have something in it')
            self.setCursor(
                PyQt6.QtGui.QCursor(PyQt6.QtCore.Qt.CursorShape.ArrowCursor))
            self.enable_buttons()
            return
        resc_name, free_space = self.resourceBox.currentText().split(' / ')
        if 2 * src_size * kw.MULTIPLIER > int(free_space) and not self.conf.get("force_transfers", False):
            self.statusLabel.setText(
                'CREATE ERROR: Resource must have enough free space in it')
            self.setCursor(
                PyQt6.QtGui.QCursor(PyQt6.QtCore.Qt.CursorShape.ArrowCursor))
            self.enable_buttons()
            return
        obj_path = f'{coll_name}.tar'
        force = self.forceCheckBox.isChecked()
        if self.conn.dataobject_exists(obj_path):
            if not force:
                self.statusLabel.setText(
                    f'CREATE ERROR: Destination bundle ({obj_path}) exists.  Use force to override')
                self.setCursor(
                    PyQt6.QtGui.QCursor(PyQt6.QtCore.Qt.CursorShape.ArrowCursor))
                self.enable_buttons()
                return
        force_flag = 'force' if force else ''
        params = {
                '*objPath': f'"{obj_path}"',
                '*collName': f'"{coll_name}"',
                '*rescName': f'"{resc_name}"',
                '*forceFlag': f'"{force_flag}"',
                }
        # XXX can self.thread_create be simply thread
        self.thread_create = PyQt6.QtCore.QThread()
        self.statusLabel.setText(f'CREATE STATUS: Creating {obj_path}')
        self.worker_create = RuleRunner(
            io.StringIO(CREATE_RULE), params, 'CREATE')
        self.worker_create.moveToThread(self.thread_create)
        self.thread_create.started.connect(self.worker_create.run)
        self.worker_create.finished.connect(self.thread_create.quit)
        self.worker_create.finished.connect(self.process_finished)
        self.worker_create.finished.connect(self.worker_create.deleteLater)
        self.thread_create.finished.connect(self.thread_create.deleteLater)
        self.thread_create.start()

    def extract_data_bundle(self):
        """Run an iRODS extract rule on selected collection.

        """
        self.setCursor(
            PyQt6.QtGui.QCursor(PyQt6.QtCore.Qt.CursorShape.WaitCursor))
        self.disable_buttons()
        self.statusLabel.clear()
        obj_indexes = self.irodsFsTreeView.selectedIndexes()
        if not len(obj_indexes):
            self.statusLabel.setText(
                'EXTRACT ERROR: Something must be selected')
            self.setCursor(
                PyQt6.QtGui.QCursor(PyQt6.QtCore.Qt.CursorShape.ArrowCursor))
            self.enable_buttons()
            return
        else:
            obj_path = self.irods_tree_model.irods_path_from_tree_index(obj_indexes[0])
        if not self.conn.dataobject_exists(obj_path):
            self.statusLabel.setText(
                'EXTRACT ERROR: A data object must be selected')
            self.setCursor(
                PyQt6.QtGui.QCursor(PyQt6.QtCore.Qt.CursorShape.ArrowCursor))
            self.enable_buttons()
            return
        obj_path = utils.path.IrodsPath(obj_path)
        file_type = ''.join(obj_path.suffixes)[1:]
        if file_type not in EXTENSIONS:
            self.statusLabel.setText(
                f'EXTRACT ERROR: A bundle file ({", ".join(EXTENSIONS)}) must be selected')
            self.setCursor(
                PyQt6.QtGui.QCursor(PyQt6.QtCore.Qt.CursorShape.ArrowCursor))
            self.enable_buttons()
            return
        force = self.forceCheckBox.isChecked()
        coll_name = obj_path.with_suffix('').with_suffix('')
        if self.conn.collection_exists(coll_name):
            bund_coll = self.conn.get_collection(coll_name)
            if len(bund_coll.subcollections) or len(bund_coll.data_objects):
                if not force:
                    self.statusLabel.setText(
                        f'EXTRACT ERROR: Destination collection ({coll_name}) must be empty.  Use force to override')
                    self.setCursor(
                        PyQt6.QtGui.QCursor(PyQt6.QtCore.Qt.CursorShape.ArrowCursor))
                    self.enable_buttons()
                    return
                else:
                    bund_coll.remove(force=force)
        self.conn.ensure_coll(coll_name)
        resc_name = self.resourceBox.currentText().split(' / ')[0]
        force_flag = 'force' if force else ''
        params = {
                '*objPath': f'"{obj_path}"',
                '*collName': f'"{coll_name}"',
                '*rescName': f'"{resc_name}"',
                '*forceFlag': f'"{force_flag}"',
                }
        self.thread_extract = PyQt6.QtCore.QThread()
        self.statusLabel.setText(
            f'EXTRACT STATUS: Extracting {coll_name}')
        self.worker_extract = RuleRunner(
            io.StringIO(EXTRACT_RULE), params, 'EXTRACT')
        self.worker_extract.moveToThread(self.thread_extract)
        self.thread_extract.started.connect(self.worker_extract.run)
        self.worker_extract.finished.connect(self.thread_extract.quit)
        self.worker_extract.finished.connect(self.process_finished)
        self.worker_extract.finished.connect(self.worker_extract.deleteLater)
        self.thread_extract.finished.connect(self.thread_extract.deleteLater)
        self.thread_extract.start()

    def process_finished(self, success, stdouterr, operation):
        """Round out the process thread.

        success : bool
            Did the process succeed?
        stdouterr : tuple
            Output of the process: (stdout, stderr).
        operation : str
            One of 'CREATE' or 'EXTRACT'.

        """
        self.setCursor(
            PyQt6.QtGui.QCursor(PyQt6.QtCore.Qt.CursorShape.ArrowCursor))
        self.enable_buttons()
        self.statusLabel.clear()
        stdout, stderr = stdouterr
        if success:
            indexes = self.irodsFsTreeView.selectedIndexes()
            if len(indexes):
                self.statusLabel.setText(f'{operation} STATUS: {stdout}')
                parent_index = self.irods_tree_model.get_parent_index(indexes[0])
                self.irods_tree_model.refresh_subtree(parent_index)
        else:
            self.statusLabel.setText(f'{operation} ERROR: {stderr}')


class RuleRunner(PyQt6.QtCore.QObject):
    """Run an iRODS rule in a Qt thread.

    """
    finished = PyQt6.QtCore.pyqtSignal(bool, tuple, str)
    context = utils.context.Context()

    def __init__(self, rule_file, params, operation):
        """
        Parameters
        ----------
        rule_file : str, file-like
            Name of the iRODS rule file, or a file-like object representing it.
        params : dict
            Rule arguments.
        operation : str
            Name of operation for reference.

        """
        super().__init__()

        self.conn = self.context.irods_connector
        self.rule_file = rule_file
        self.params = params
        self.operation = operation

    def run(self):
        """Run the rule and "return" the results.

        """
        stdout, stderr = self.conn.execute_rule(self.rule_file, self.params)
        if stderr == '':
            self.finished.emit(True, (stdout, stderr), self.operation)
        else:
            self.finished.emit(False, (stdout, stderr), self.operation)


CREATE_RULE = '''create_rule {
    *retCre = msiTarFileCreate(*objPath, *collName, *rescName, *forceFlag);
    if(bool(*retCre)) {
        writeLine("stderr", "Error creating *objPath from *collName");
    }
    else {
        writeLine("stdout", "Created *objPath from *collName");
    }
}
OUTPUT ruleExecOut
'''

EXTRACT_RULE = """extract_rule {
    msiTarFileExtract(*objPath, *collName, *rescName, *retExt);
    if(bool(*retExt)) {
        writeLine("stderr", "Error extracting *objPath to *collName");
    }
    else {
        writeLine("stdout", "Extracted *objPath into *collName");
    }
}
OUTPUT ruleExecOut
"""
