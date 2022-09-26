"""Data (Un)Bundle window residing in a tab.

"""
import io
import os
import pathlib

import PyQt5.QtCore
import PyQt5.QtGui
import PyQt5.QtWidgets

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
        self.widget.indexButton.clicked.connect(self.index_data_bundle)

    def info_popup(self, message):
        """Display an informational pop-up with the `message`.

        Parameters
        ----------
        message : str
            Text to display in pop-up.

        """
        PyQt5.QtWidgets.QMessageBox.information(self.widget, 'Information', message)

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
        self.widget.indexButton.setEnabled(True)

    def disable_buttons(self):
        """Disallow buttons from being pressed.

        """
        self.widget.createButton.setEnabled(False)
        self.widget.extractButton.setEnabled(False)
        self.widget.indexButton.setEnabled(False)

    def create_data_bundle(self):
        """Run an iRODS bundle rule on selected collection.

        """
        self.widget.setCursor(
            PyQt5.QtGui.QCursor(PyQt5.QtCore.Qt.WaitCursor))
        self.disable_buttons()
        self.widget.statusLabel.clear()
        _, source = self.irods_tree_model.get_checked()
        if source is None:
            self.widget.statusLabel.setText(
                'ERROR: Something must be selected')
            self.enable_buttons()
            return
        if not self.ic.collection_exists(source):
            self.widget.statusLabel.setText(
                'ERROR: A collection must be selected')
            self.widget.setCursor(
                PyQt5.QtGui.QCursor(PyQt5.QtCore.Qt.ArrowCursor))
            self.enable_buttons()
            return
        # TODO find a better test (add permissions too)
        if len(source.split('/')) < 5:
            self.widget.statusLabel.setText(
                'ERROR: Collection must be within a user/group collection')
            self.widget.setCursor(
                PyQt5.QtGui.QCursor(PyQt5.QtCore.Qt.ArrowCursor))
            self.enable_buttons()
            return
        src_coll = self.ic.get_collection(source)
        src_size = sum((sum((int(obj.size) for obj in objs)) for _, _, objs in src_coll.walk()))
        if src_size == 0:
            self.widget.statusLabel.setText(
                'ERROR: Collection must have something in it')
            self.widget.setCursor(
                PyQt5.QtGui.QCursor(PyQt5.QtCore.Qt.ArrowCursor))
            self.enable_buttons()
            return
        resc_name, free_space = self.widget.resourceBox.currentText().split(' / ')
        if 2 * src_size * self.ic.multiplier > int(free_space):
            self.widget.statusLabel.setText(
                'ERROR: Resource must have enough free space in it')
            self.widget.setCursor(
                PyQt5.QtGui.QCursor(PyQt5.QtCore.Qt.ArrowCursor))
            self.enable_buttons()
            return
        compress = self.widget.compressCheckBox.isChecked()
        remove = self.widget.removeCheckBox.isChecked()
        params = {
                '*coll': f'"{source}"',
                '*resource': f'"{resc_name}"',
                '*compress': f'"{str(compress).lower()}"',
                '*delete': f'"{str(remove).lower()}"'
                }
        # XXX can self.thread_create be simply thread
        self.thread_create = PyQt5.QtCore.QThread()
        self.widget.statusLabel.setText(
            f'STATUS: compressing {source}')
        self.worker_create = RuleRunner(
            self.ic, io.StringIO(BUNDLE_RULE), params, 'create')
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
            PyQt5.QtGui.QCursor(PyQt5.QtCore.Qt.WaitCursor))
        self.disable_buttons()
        self.widget.statusLabel.clear()
        idx, source = self.irods_tree_model.get_checked()
        if source is None:
            self.widget.statusLabel.setText(
                'ERROR: Nothing selected')
            self.enable_buttons()
            return
        source = pathlib.Path(source)
        file_type = ''.join(source.suffixes)[1:]
        if not idx or file_type not in EXTENSIONS:
            self.widget.statusLabel.setText(
                f'ERROR: No bundle file ({", ".join(EXTENSIONS)}) selected')
            self.widget.setCursor(
                PyQt5.QtGui.QCursor(PyQt5.QtCore.Qt.ArrowCursor))
            self.enable_buttons()
            return
        extract_path = str(source.parent)
        # XXX allow updating/overwriting?
        if self.ic.collection_exists(extract_path):
            extract_coll = self.ic.get_collection(extract_path)
            if extract_coll.subcollections != [] or extract_coll.data_objects != []:
                self.widget.statusLabel.setText(f'ERROR: Destination not empty: {extract_path}')
                self.widget.setCursor(PyQt5.QtGui.QCursor(PyQt5.QtCore.Qt.ArrowCursor))
                self.enable_buttons()
                return
        resc_name = self.widget.resourceBox.currentText().split(' / ')[0]
        params = {
                '*obj': f'"{source}"',
                '*resource': f'"{resc_name}"',
                }
        self.thread_extract = PyQt5.QtCore.QThread()
        self.widget.statusLabel.setText(
            f'STATUS: extracting {source}')
        self.worker_extract = RuleRunner(
            self.ic, io.StringIO(EXTRACT_RULE), params, 'extract')
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
            Did the proceess succeed?
        stdouterr : tuple
            Output of the process: (stdout, stderr).
        operation : str
            One of 'create' or 'extract'.

        """
        self.widget.setCursor(
            PyQt5.QtGui.QCursor(PyQt5.QtCore.Qt.ArrowCursor))
        self.enable_buttons()
        self.widget.statusLabel.clear()
        stdout, stderr = stdouterr
        if success:
            idx, _ = self.irods_tree_model.get_checked()
            self.widget.statusLabel.setText(f'STATUS: {operation} {stdout}')
            parent_index = self.irods_tree_model.get_parent_index(idx)
            self.irods_tree_model.refresh_subtree(parent_index)
        else:
            self.widget.statusLabel.setText(f'ERROR: {operation} {stderr}')

    def index_data_bundle(self):
        """Extract the index listing from a bundle file with an iRODS
        rule.

        """
        self.disable_buttons()
        self.widget.statusLabel.clear()
        _, source = self.irods_tree_model.get_checked()
        if source is None:
            self.widget.statusLabel.setText(
                'ERROR: Nothing selected')
            self.enable_buttons()
            return
        file_type = ''.join(pathlib.Path(source).suffixes)[1:]
        if file_type not in EXTENSIONS:
            self.widget.statusLabel.setText(
                f'ERROR: No bundle file ({", ".join(EXTENSIONS)}) selected')
            self.enable_buttons()
            return
        params = {
                '*path': f'"{source}"'
                }
        self.disable_buttons()
        stdout, _ = self.ic.execute_rule(io.StringIO(INDEX_RULE), params)
        self.widget.statusLabel.setText(f'INFO: Loaded Index of {source}')
        index_popup = gui.popupWidgets.irodsIndexPopup(
            self.ic, stdout, source, self.widget.statusLabel)
        index_popup.exec_()


class RuleRunner(PyQt5.QtCore.QObject):
    """Run an iRODS rule in a Qt thread.

    """

    finished = PyQt5.QtCore.pyqtSignal(bool, tuple, str)

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
        if stderr != []:
            self.finished.emit(False, (stdout, stderr), self.operation)
        else:
            self.finished.emit(True, (stdout, stderr), self.operation)


BUNDLE_RULE = """bundle {
    # msiSplitPath(*coll, *parentColl, *collName);
    # if(bool(*compress)) {
    #     *tarFile = "*parentColl/*collName.zip"
    # }
    # else {
    #     *tarFile = "*parentColl/*collName.tar"
    # }
    *tarFile = "*coll.tar"
    writeLine("stderr", "DEBUG tarFile=*tarFile");
    retVal = msiTarFileCreate(*tarFile, *coll, *resource);
    writeLine("stderr", "DEBUG retVal=*retVal");
    # writeLine("stderr", "outTar=*outTar");
    # if(bool(*delete) && *outTar == 0) {
    #     writeLine("stdout", "DEBUG tarCollection: Delete *coll")
    #     msiRmColl(*coll, "forceFlag=", *out);
    # }
    # if(*outTar!=0) {
    #     writeLine("stderr", "Tar failed.")
    # }
}
OUTPUT ruleExecOut
"""

EXTRACT_RULE = """extract {
    msiGetObjType(*obj, *objType);
    writeLine("stdout", "*obj, *objType");
    msiSplitPath(*obj, *parentColl, *objName);
    *suffix = substr(*obj, strlen(*obj)-9, strlen(*obj));
    *objName = substr(*objName, 0, strlen(*objName)-10);
    writeLine("stdout", "DEBUG tarExtract *parentColl");
    writeLine("stdout", "DEBUG tarExtract *objName, *suffix");
    *run = true;
    if(*objType != '-d') {
        *run = false;
        writeLine("stderr", "ERROR tarExtract: not a data object, *path")
    }
    if(*suffix != "irods.tar" && *suffix != "irods.zip") {
        *run = false;
        writeLine("stderr", "ERROR tarExtract: not an irods.tar file, *path")
    }
    if(*run== true) {
        writeLine("stdout", "STATUS tarExtract: Create collection *parentColl/*objName");
        msiCollCreate("*parentColl/*objName", 1, *collCreateOut);
        if(*collCreateOut == 0) {
            writeLine("stdout", "STATUS tarExtract: Extract *obj to *parentColl/*objName");
            msiArchiveExtract(*obj, "*parentColl/*objName", "null", *resource, *outTarExtract);
            if(*outTarExtract != 0) {
                writeLine("stderr", "ERROR tarExtract: Failed to extract data");
            }
        }
        else {
            writeLine("stderr", "ERROR tarExtract: Failed to create *parentColl/*objName")
        }
    }
    else {
        writeLine("stdout", "DEBUG tarExtract: no action.")
    }
}
OUTPUT ruleExecOut
"""

INDEX_RULE = """index {
    msiGetObjType(*path, *objType);
    *suffix = substr(*path, strlen(*path)-9, strlen(*path));
    *run = true;
    writeLine("stdout", "DEBUG tarReadIndex: *suffix");
    if(*suffix != "irods.tar" && *suffix != "irods.zip") {
        *run = false;
        writeLine("stderr", "ERROR tarReadIndex: not an irods.tar file, *path")
    }
    if(*run == true) {
        msiArchiveIndex(*path, *out);
        writeLine("stdout", *out)
    }
    else {
        writeLine("stdout", "DEBUG tarReadIndex: no action.")
    }
}
OUTPUT ruleExecOut
"""
