"""Data (Un)Bundle window residing in a tab.

"""
import io
import os
import pathlib

import PyQt6.QtCore
import PyQt6.QtGui
import PyQt6.QtWidgets

import gui

CWD = os.getcwd()
EXTENSIONS = [
    'tar',
    'tar.gz',
    'tgz',
    'tar.bz2',
    'tbz2',
    'zip',
]


class IrodsDataBundle():
    """Window for (un)bundling data withing the iRODS system.

    """

    def __init__(self, widget, ic, ienv):
        """Construct the bundle window.

        Parameters
        ----------
        widget : QtWidgets
            Common widget container.
        ic : IrodsConnector
            Connection to an iRODS session.
        ienv : dict
            iRODS environment settings.

        """
        self.widget = widget
        self.ic = ic
        self.ienv = ienv
        self.thread_create = None
        self.thread_extract = None
        self.worker_create = None
        self.worker_extract = None
        self.root_path = f'/{ic.session.zone}'
        self.widget.irodsZoneLabel.setText(f'{self.root_path}:')
        self.irods_tree_model = self.setup_fs_tree(self.widget.irodsFsTreeView)
        self.widget.irodsFsTreeView.expanded.connect(self.irods_tree_model.refresh_subtree)
        self.setup_resource_selector(self.widget.resourceBox)
        self.widget.createButton.clicked.connect(self.create_data_bundle)
        self.widget.extractButton.clicked.connect(self.extract_data_bundle)

    def info_popup(self, message):
        """Display an informational pop-up with the `message`.

        Parameters
        ----------
        message : str
            Text to display in pop-up.

        """
        PyQt6.QtWidgets.QMessageBox.information(self.widget, 'Information', message)

    def setup_fs_tree(self, tree_view):
        """Initialize the iRODS tree view.

        tree_view : QtWidget
            The widget for this tree view.

        Returns
        -------
        IrodsModel
            Constructed tree view.

        """
        model = gui.irodsTreeView.IrodsModel(self.ic, tree_view)
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
        names, spaces = self.ic.list_resources()
        resources = [
            f'{name} / {space}' for name, space in zip(names, spaces)]
        selector.clear()
        selector.addItems(resources)
        default_resc = self.ic.default_resc
        if default_resc in names:
            ridx = names.index(default_resc)
            index = selector.findText(resources[ridx])
            selector.setCurrentIndex(index)

    def enable_buttons(self):
        """Allow buttons to be pressed.

        """
        self.widget.createButton.setEnabled(True)
        self.widget.extractButton.setEnabled(True)

    def disable_buttons(self):
        """Disallow buttons from being pressed.

        """
        self.widget.createButton.setEnabled(False)
        self.widget.extractButton.setEnabled(False)

    def create_data_bundle(self):
        """Run an iRODS bundle rule on selected collection.

        """
        self.widget.setCursor(
            PyQt6.QtGui.QCursor(PyQt6.QtCore.Qt.CursorShape.WaitCursor))
        self.disable_buttons()
        self.widget.statusLabel.clear()
        coll_indexes = self.widget.irodsFsTreeView.selectedIndexes()
        if not len(coll_indexes):
            self.widget.statusLabel.setText(
                'CREATE ERROR: Something must be selected')
            self.widget.setCursor(
                PyQt6.QtGui.QCursor(PyQt6.QtCore.Qt.CursorShape.ArrowCursor))
            self.enable_buttons()
            return
        else:
            coll_name = self.irods_tree_model.irods_path_from_tree_index(coll_indexes[0])
        if not self.ic.collection_exists(coll_name):
            self.widget.statusLabel.setText(
                'CREATE ERROR: A collection must be selected')
            self.widget.setCursor(
                PyQt6.QtGui.QCursor(PyQt6.QtCore.Qt.CursorShape.ArrowCursor))
            self.enable_buttons()
            return
        # TODO find a better test (add permissions too)
        if len(coll_name.split('/')) < 5:
            self.widget.statusLabel.setText(
                'CREATE ERROR: Collection must be within a user/group collection')
            self.widget.setCursor(
                PyQt6.QtGui.QCursor(PyQt6.QtCore.Qt.CursorShape.ArrowCursor))
            self.enable_buttons()
            return
        src_coll = self.ic.get_collection(coll_name)
        src_size = sum((sum((int(obj.size) for obj in objs)) for _, _, objs in src_coll.walk()))
        if src_size == 0:
            self.widget.statusLabel.setText(
                'CREATE ERROR: Collection must have something in it')
            self.widget.setCursor(
                PyQt6.QtGui.QCursor(PyQt6.QtCore.Qt.CursorShape.ArrowCursor))
            self.enable_buttons()
            return
        resc_name, free_space = self.widget.resourceBox.currentText().split(' / ')
        if 2 * src_size * self.ic.multiplier > int(free_space):
            self.widget.statusLabel.setText(
                'CREATE ERROR: Resource must have enough free space in it')
            self.widget.setCursor(
                PyQt6.QtGui.QCursor(PyQt6.QtCore.Qt.CursorShape.ArrowCursor))
            self.enable_buttons()
            return
        obj_path = f'{coll_name}.tar'
        force = self.widget.forceCheckBox.isChecked()
        if self.ic.dataobject_exists(obj_path):
            if not force:
                self.widget.statusLabel.setText(
                    f'CREATE ERROR: Destination bundle ({obj_path}) exists.  Use force to override')
                self.widget.setCursor(PyQt6.QtGui.QCursor(PyQt6.QtCore.Qt.CursorShape.ArrowCursor))
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
        self.widget.statusLabel.setText(
            f'CREATE STATUS: Creating {obj_path}')
        self.worker_create = RuleRunner(
            self.ic, io.StringIO(CREATE_RULE), params, 'CREATE')
        self.worker_create.moveToThread(self.thread_create)
        self.thread_create.started.connect(self.worker_create.run)
        self.worker_create.finished.connect(self.thread_create.quit)
        self.worker_create.finished.connect(self.process_finished)
        self.worker_create.finished.connect(self.worker_create.deleteLater)
        self.thread_create.finished.connect(self.thread_create.deleteLater)
        self.thread_create.start()
        self.enable_buttons()

    def extract_data_bundle(self):
        """Run an iRODS extract rule on selected collection.

        """
        self.widget.setCursor(
            PyQt6.QtGui.QCursor(PyQt6.QtCore.Qt.CursorShape.WaitCursor))
        self.disable_buttons()
        self.widget.statusLabel.clear()
        obj_indexes = self.widget.irodsFsTreeView.selectedIndexes()
        if not len(obj_indexes):
            self.widget.statusLabel.setText(
                'EXTRACT ERROR: Something must be selected')
            self.widget.setCursor(
                PyQt6.QtGui.QCursor(PyQt6.QtCore.Qt.CursorShape.ArrowCursor))
            self.enable_buttons()
            return
        else:
            obj_path = self.irods_tree_model.irods_path_from_tree_index(obj_indexes[0])
        if not self.ic.dataobject_exists(obj_path):
            self.widget.statusLabel.setText(
                'EXTRACT ERROR: A data object must be selected')
            self.widget.setCursor(
                PyQt6.QtGui.QCursor(PyQt6.QtCore.Qt.CursorShape.ArrowCursor))
            self.enable_buttons()
            return
        obj_path = pathlib.Path(obj_path)
        file_type = ''.join(obj_path.suffixes)[1:]
        if file_type not in EXTENSIONS:
            self.widget.statusLabel.setText(
                f'EXTRACT ERROR: A bundle file ({", ".join(EXTENSIONS)}) must be selected')
            self.widget.setCursor(
                PyQt6.QtGui.QCursor(PyQt6.QtCore.Qt.CursorShape.ArrowCursor))
            self.enable_buttons()
            return
        force = self.widget.forceCheckBox.isChecked()
        coll_name = str(obj_path.with_suffix('').with_suffix(''))
        if self.ic.collection_exists(coll_name):
            bund_coll = self.ic.get_collection(coll_name)
            if len(bund_coll.subcollections) or len(bund_coll.data_objects):
                if not force:
                    self.widget.statusLabel.setText(
                        f'EXTRACT ERROR: Destination collection ({coll_name}) must be empty.  Use force to override')
                    self.widget.setCursor(PyQt6.QtGui.QCursor(PyQt6.QtCore.Qt.CursorShape.ArrowCursor))
                    self.enable_buttons()
                    return
                else:
                    bund_coll.remove(force=force)
        self.ic.ensure_coll(coll_name)
        resc_name = self.widget.resourceBox.currentText().split(' / ')[0]
        force_flag = 'force' if force else ''
        params = {
                '*objPath': f'"{obj_path}"',
                '*collName': f'"{coll_name}"',
                '*rescName': f'"{resc_name}"',
                '*forceFlag': f'"{force_flag}"',
                }
        self.thread_extract = PyQt6.QtCore.QThread()
        self.widget.statusLabel.setText(
            f'EXTRACT STATUS: Extracting {coll_name}')
        self.worker_extract = RuleRunner(
            self.ic, io.StringIO(EXTRACT_RULE), params, 'EXTRACT')
        self.worker_extract.moveToThread(self.thread_extract)
        self.thread_extract.started.connect(self.worker_extract.run)
        self.worker_extract.finished.connect(self.thread_extract.quit)
        self.worker_extract.finished.connect(self.process_finished)
        self.worker_extract.finished.connect(self.worker_extract.deleteLater)
        self.thread_extract.finished.connect(self.thread_extract.deleteLater)
        self.thread_extract.start()
        self.enable_buttons()

    def process_finished(self, success, stdouterr, operation):
        """Round out the process thread.

        success : bool
            Did the process succeed?
        stdouterr : tuple
            Output of the process: (stdout, stderr).
        operation : str
            One of 'CREATE' or 'EXTRACT'.

        """
        self.widget.setCursor(
            PyQt6.QtGui.QCursor(PyQt6.QtCore.Qt.CursorShape.ArrowCursor))
        self.enable_buttons()
        self.widget.statusLabel.clear()
        stdout, stderr = stdouterr
        if success:
            indexes = self.widget.irodsFsTreeView.selectedIndexes()
            if len(indexes):
                self.widget.statusLabel.setText(f'{operation} STATUS: {stdout}')
                parent_index = self.irods_tree_model.get_parent_index(indexes[0])
                self.irods_tree_model.refresh_subtree(parent_index)
        else:
            self.widget.statusLabel.setText(f'{operation} ERROR: {stderr}')


class RuleRunner(PyQt6.QtCore.QObject):
    """Run an iRODS rule in a Qt thread.

    """

    finished = PyQt6.QtCore.pyqtSignal(bool, tuple, str)

    def __init__(self, ic, rule_file, params, operation):
        """
        Parameters
        ----------
        ic : IrodsConnector
            Connection to an iRODS session.
        rule_file : str, file-like
            Name of the iRODS rule file, or a file-like object representing it.
        params : dict
            Rule arguments.
        operation : str
            Name of operation for reference.

        """
        super().__init__()
        self.ic = ic
        self.params = params
        self.operation = operation
        self.rule_file = rule_file

    def run(self):
        """Run the rule and "return" the results.

        """
        stdout, stderr = self.ic.execute_rule(self.rule_file, self.params)
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
