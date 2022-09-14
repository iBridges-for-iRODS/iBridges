"""Compress/bundle window residing in a tab.

"""
import os
import pathlib

import PyQt5.QtCore
import PyQt5.QtGui
import PyQt5.QtWidgets

import gui

CWD = os.getcwd()


class irodsDataCompression():
    """Main class for window creation.

    """

    def __init__(self, widget, ic, ienv):
        """Create initial window elements.

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
        # TODO convert these to string versions to eliminate this path depenency
        self.bundle_rule_file = pathlib.Path(CWD, 'rules/tarCollection.r')
        self.index_rule_file = pathlib.Path(CWD, 'rules/tarCollection.r')
        self.extract_rule_file = pathlib.Path(CWD, 'rules/tarCollection.r')
        paths = [
            self.bundle_rule_file,
            self.index_rule_file,
            self.extract_rule_file,
        ]
        for path in paths:
            if not path.exists():
                self.info_popup(
                    f'ERROR {path.name} not found in:\n{path.parent}\nDataCompression view not setup.')
                return
        self.root_path = f'/{ic.session.zone}'
        self.widget.irodsZoneLabel1.setText(f'{self.root_path}:')
        self.widget.irodsZoneLabel2.setText(f'{self.root_path}:')
        index = self.widget.decompressRescButton.findText(ic.default_resc)
        self.widget.decompressRescButton.setCurrentIndex(index)
        # irodsCollectionTree
        self.collection_tree_model = self.setup_fs_tree(self.widget.irodsCollectionTree)
        self.widget.irodsCollectionTree.expanded.connect(self.collection_tree_model.refresh_subtree)
        # irodsCompressionTree
        self.compression_tree_model = self.setup_fs_tree(self.widget.irodsCompressionTree)
        self.widget.irodsCompressionTree.expanded.connect(self.compression_tree_model.refresh_subtree)
        # resource buttons
        self.setup_resource_selector(self.widget.compressRescButton)
        self.setup_resource_selector(self.widget.decompressRescButton)
        # Create/Unpack/Index buttons
        self.widget.createButton.clicked.connect(self.create_data_bundle)
        self.widget.unpackButton.clicked.connect(self.unpackDataBundle)
        self.widget.indexButton.clicked.connect(self.getIndex)

    def info_popup(self, message):
        """Display an informational pop-up with the `message`.

        Parameters
        ----------
        message : str
            Text to display in pop-up.

        """
        PyQt5.QtWidgets.QMessageBox.information(self.widget, 'Information', message)

    def setup_fs_tree(self, tree_view):
        """Initialize an iRODS tree view.

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
        """Initialize a resource drop-down menu.

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

    def enable_buttons(self, enable):
        """Allow "buttons" to be pressed.

        Parameters
        ----------
        enable : bool
            Should "buttons" be pressable?

        """
        self.widget.compressRescButton.setEnabled(enable)
        self.widget.decompressRescButton.setEnabled(enable)
        self.widget.createButton.setEnabled(enable)
        self.widget.unpackButton.setEnabled(enable)
        self.widget.indexButton.setEnabled(enable)

    def create_data_bundle(self):
        """Run an iRODS bundle rule on selected collection.

        """
        self.widget.setCursor(PyQt5.QtGui.QCursor(PyQt5.QtCore.Qt.WaitCursor))
        self.enable_buttons(False)
        self.widget.createStatusLabel.clear()
        rule_file = os.path.join(os.getcwd(), 'rules/tarCollection.r')
        _, source = self.collection_tree_model.get_checked()
        if not self.ic.session.collections.exists(source):
            self.widget.createStatusLabel.setText("ERROR: No collection selected.")
            self.widget.setCursor(PyQt5.QtGui.QCursor(PyQt5.QtCore.Qt.ArrowCursor))
            self.enable_buttons(True)
            return
        # TODO find a better test (add permissions too)
        if len(source.split('/')) < 5:
            self.widget.createStatusLabel.setText(
                'ERROR: Collection must be within a user/group collection.')
            self.widget.setCursor(PyQt5.QtGui.QCursor(PyQt5.QtCore.Qt.ArrowCursor))
            self.enable_buttons(True)
            return
        compress = self.widget.compressCheckBox.isChecked()
        remove = self.widget.removeCheckBox.isChecked()
        resc_name = self.widget.compressRescButton.currentText()
        params = {
                '*coll': f'"{source}"',
                '*resource': f'"{resc_name}"',
                '*compress': f'"{str(compress).lower()}"',
                '*delete': f'"{str(remove).lower()}"'
                }
        # XXX can self.thread_create be simply thread
        self.thread_create = PyQt5.QtCore.QThread()
        self.widget.createStatusLabel.setText("STATUS: compressing "+source)
        self.worker_create = dataBundleCreateExtract(self.ic, rule_file, params, "create")
        self.worker_create.moveToThread(self.thread_create)
        self.thread_create.started.connect(self.worker_create.run)
        self.worker_create.finished.connect(self.thread_create.quit)
        self.worker_create.finished.connect(self.dataCreateExtractFinished)
        self.worker_create.finished.connect(self.worker_create.deleteLater)
        self.thread_create.finished.connect(self.thread_create.deleteLater)
        self.thread_create.start()

    def dataCreateExtractFinished(self, success, message, operation):
        self.widget.setCursor(PyQt5.QtGui.QCursor(PyQt5.QtCore.Qt.ArrowCursor))
        self.enable_buttons(True)
        stdout, stderr = message
        if success and operation == "create":
            idx, _ = self.collection_tree_model.get_checked()
            self.widget.createStatusLabel.setText("STATUS: Created " + str(stdout))
            parent_index = self.collection_tree_model.get_parent_index(idx)
            self.collection_tree_model.refresh_subtree(parent_index)
        elif not success and operation == "create":
            self.widget.createStatusLabel.setText("ERROR: Create failed: " + str(stderr))
        elif success and operation == "extract":
            idx, _ = self.compression_tree_model.get_checked()
            stdout, stderr = message
            self.widget.unpackStatusLabel.setText("STATUS: Extracted " + str(stdout))
            parent_index = self.compression_tree_model.get_parent_index(idx)
            self.compression_tree_model.refresh_subtree(parent_index)
        elif not success and operation == "extract":
            self.widget.unpackStatusLabel.setText("ERROR: Create failed: " + str(stderr))


    def unpackDataBundle(self):
        self.widget.setCursor(PyQt5.QtGui.QCursor(PyQt5.QtCore.Qt.WaitCursor))
        idx, source = self.compression_tree_model.get_checked()

        if not idx or (not source.endswith(".irods.tar") and not source.endswith(".irods.zip")):
            self.widget.unpackStatusLabel.setText("ERROR: No *.irods.tar or *.irods.zip selected")
            self.widget.setCursor(PyQt5.QtGui.QCursor(PyQt5.QtCore.Qt.ArrowCursor))
            return
        extractPath = os.path.dirname(source)+'/'+os.path.basename(source).split('.irods')[0]
        if self.ic.session.collections.exists(extractPath):
            extractColl = self.ic.session.collections.get(extractPath)
            if extractColl.subcollections != [] or extractColl.data_objects != []:
                self.widget.unpackStatusLabel.setText("ERROR: Destination not empty: "+extractPath)
                self.widget.setCursor(PyQt5.QtGui.QCursor(PyQt5.QtCore.Qt.ArrowCursor))
                return

        self.enable_buttons(False)

        self.widget.unpackStatusLabel.clear()
        rule_file = os.path.join(os.getcwd(),'rules/tarExtract.r')

        resc_name = self.widget.decompressRescButton.currentText()
        params = {
                '*obj': '"'+source+'"',
                '*resource': '"'+resc_name+'"',
                }

        self.thread_extract = PyQt5.QtCore.QThread()
        self.widget.unpackStatusLabel.setText("STATUS: extracting "+source)
        self.worker_extract = dataBundleCreateExtract(self.ic, rule_file, params, "extract")
        self.worker_extract.moveToThread(self.thread_extract)
        self.thread_extract.started.connect(self.worker_extract.run)
        self.worker_extract.finished.connect(self.thread_extract.quit)
        self.worker_extract.finished.connect(self.dataCreateExtractFinished)
        self.worker_extract.finished.connect(self.worker_extract.deleteLater)
        self.thread_extract.finished.connect(self.thread_extract.deleteLater)
        self.thread_extract.start()


    def getIndex(self):
        self.widget.unpackStatusLabel.clear()
        rule_file = os.path.join(os.getcwd(),'rules/tarReadIndex.r')

        idx, source = self.compression_tree_model.get_checked()
        if source == None:
            self.widget.unpackStatusLabel.setText("ERROR: No *.irods.tar or *.irods.zip selected")
            return
        if not source.endswith(".irods.tar") and not source.endswith(".irods.zip"):
            self.widget.unpackStatusLabel.setText("ERROR: No *.irods.tar or *.irods.zip selected")
            return

        params = {
                '*path': '"'+source+'"'
                }
        stdout, stderr = self.ic.executeRule(rule_file, params)
        self.widget.unpackStatusLabel.setText("INFO: Loaded Index of "+source)
        indexPopup = gui.popupWidgets.irodsIndexPopup(self.ic, stdout[1:], source, self.widget.unpackStatusLabel)
        indexPopup.exec_()


class dataBundleCreateExtract(PyQt5.QtCore.QObject):
    finished = PyQt5.QtCore.pyqtSignal(bool, list, str)
    def __init__(self, ic, rule_file, params, operation):
        super(dataBundleCreateExtract, self).__init__()
        self.rule_file = rule_file
        self.params = params
        self.ic = ic
        self.operation = operation

    def run(self):
        stdout, stderr = self.ic.executeRule(self.rule_file, self.params)
        if stderr != []:
            self.finished.emit(False, [stdout, stderr], self.operation)
        else:
            self.finished.emit(True, [stdout, stderr], self.operation)
