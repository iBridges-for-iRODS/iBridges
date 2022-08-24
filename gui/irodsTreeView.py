"""Tree model for IRODS collections.
The IRODS database is huge and retreiving a complete tree of all files
can take ages.  To improve the loading time the tree is only grown as
far as its shows.

"""
import collections
import logging
import os

import irods
import PyQt5

import PyQt5.QtCore
import PyQt5.QtGui
import PyQt5.QtWidgets


class IrodsModel(PyQt5.QtGui.QStandardItemModel):
    """Model for an iRODS tree view.

    """

    def __init__(self, irods_connector, tree_view):
        """Initializes the tree view with the root node and first level.

        Class variables 'user_groups' and 'base_path' _must_ be
        populated with a list of group names and the path name of the
        iRODS top-level collection (i.e., /<zone name>/home),
        respectively.

        Parameters
        ----------
        irods_connector : IrodsConnector
            iRODS session container.
        tree_view : PyQt5.QtWidgets
            Defined iRODS tree view UI element.

        """
        super().__init__()
        self._checked_indexes = set()
        self.ic = irods_connector
        self.tree_view = tree_view
        try:
            self.user_groups = self.ic.get_user_info()[1]
        except irods.exception.NetworkException:
            logging.info('iRODS FILE TREE ERROR: user info', exc_info=True)
        self.zone_path = f'/{self.ic.session.zone}'
        self.base_path = f'{self.zone_path}/home'
        # Empty tree
        self.clear()

    def data(self, index, role=PyQt5.QtCore.Qt.DisplayRole):
        """Check data?

        Parameters
        ----------
        index : int?
            Index in tree view?
        role : QtCore.Qt.*Role
            Role of caller?

        Returns
        -------
        PyQt5.QtCore.Qt.(Un)checked
            Status of indexes?

        """
        if role == PyQt5.QtCore.Qt.CheckStateRole:
            if index in self._checked_indexes:
                return PyQt5.QtCore.Qt.Checked
            return PyQt5.QtCore.Qt.Unchecked
        return super().data(index, role)

    def flags(self, index):
        """Get result of set flags at `index`?

        Parameters
        ----------
        index : int?
            Index in tree view?

        Returns
        -------
        bool
            Success in getting the tree view flags?

        """
        checkable = PyQt5.QtCore.Qt.ItemIsUserCheckable
        auto_tristate = PyQt5.QtCore.Qt.ItemIsAutoTristate
        return super().flags(index) | checkable | auto_tristate

    def setData(self, index, value, role=PyQt5.QtCore.Qt.EditRole):
        """Set the tree view data?

        Parameters
        ----------
        index : int?
            Index in tree view?
        value : QtCore.Qt.checked
            Status of `index`?
        role : QtCore.Qt.*Role
            Role of caller?

        Returns
        -------
        bool
            Success in setting the tree view data?

        """
        if role == PyQt5.QtCore.Qt.CheckStateRole:
            if value == PyQt5.QtCore.Qt.Checked:
                # Check irods ACLs for access rights.
                path = self.irods_path_from_tree_index(index)
                try:
                    zone = self.ic.session.zone
                    req_acls = []
                    for access_name in ['own', 'write', 'read object']:
                        req_acls.extend([
                            (
                                access_name,
                                path,
                                group,
                                zone,
                            )
                            for group in self.user_groups])
                    acls = {
                        (
                            acl.access_name,
                            acl.path,
                            acl.user_name,
                            acl.user_zone,
                        )
                        for acl in self.ic.get_permissions(path)}
                    # FIXME Block checking of home item (no easy way to
                    # remove the checkbox?)
                    if acls.intersection(req_acls) == set():
                        message = f'ERROR, insufficient rights:\nCannot select {path}'
                        PyQt5.QtWidgets.QMessageBox.information(
                            self.tree_view, 'Error', message)
                        # logging.info("Filedownload:" + message)
                        return False
                # FIXME narrow down exception possibilities
                except Exception:
                    logging.info('IRODS TREE ERROR', exc_info=True)
                    return False
                # Enforce single select.
                while self._checked_indexes:
                    selected_index = self._checked_indexes.pop()
                    super().setData(
                        selected_index, PyQt5.QtCore.Qt.Unchecked, role)
                # Add newly selected item.
                self._checked_indexes.add(index)
            else:
                self._checked_indexes.discard(index)
            # Force refresh.
            self.tree_view.repaint()
            return True
        return super().setData(self, index, value, role)

    def get_checked(self):
        """Get the selected index and its iRODS path.

        Returns
        -------
        tuple
            (<tree index>, <iRODS path>)

        """
        if len(self._checked_indexes) < 1:
            return None, None
        checked_item = list(self._checked_indexes)[0]
        return checked_item, self.irods_path_from_tree_index(checked_item)

    def init_irods_fs_data(self):
        """Retrieve the first levels of an iRODS tree: /zone/home/*.

        The level of 'home' is 0 and its parentID is -1.
        'type' can take values 'C' (collection) or 'd' (data object)

        Returns
        -------
        list
            Key-value dictionaries.

        Example of the return:

        [
            {
                'irodsID': 12345,
                'level': 10,
                'parentID': 54321,
                'shortName': 'myColl',
                'type': 'C'
            },
            {}
        ]

        """
        # Initial tree information.
        try:
            coll = self.ic.session.collections.get(self.base_path)
        # FIXME narrow down exception possibilities
        except Exception:
            logging.info('IRODS TREE INIT ERROR', exc_info=True)
            return
        level = 0
        row = {
            'level': level,
            'irodsID': coll.id,
            'parentID': -1,
            'shortName': coll.name,
            'type': 'C',
        }
        data = [row]
        # Get content of the home collection.
        for sub_coll in coll.subcollections:
            level = 1
            row = {
                'level': level,
                'irodsID': sub_coll.id,
                'parentID': coll.id,
                'shortName': sub_coll.name,
                'type': 'C',
            }
            data.append(row)
            if sub_coll.data_objects != [] or sub_coll.subcollections != []:
                row = {
                    'level': level+1,
                    'irodsID': 'test',
                    'parentID': sub_coll.id,
                    'shortName': 'test',
                    'type': 'd',
                }
                data.append(row)
        for obj in coll.data_objects:
            # level = len(obj.path.split(self.base_path+'/')[1].split('/')) - 1
            level = 1
            row = {
                'level': level,
                'irodsID': obj.id,
                'parentID': coll.id,
                'shortName': obj.name,
                'type': 'd',
            }
            data.append(row)
        return data

    def init_tree(self):
        """Draw the first levels of an iRODS filesystem as a tree.

        """
        icon_provider = PyQt5.QtWidgets.QFileIconProvider()
        self.setRowCount(0)
        root = self.invisibleRootItem()
        # First levels of iRODS data
        irods_fs_data = self.init_irods_fs_data()
        # Build Tree
        nodes_in_tree = {}
        values = collections.deque(irods_fs_data)
        while values:
            value = values.popleft()
            if value['level'] == 0:
                parent = root
            else:
                pid = value['parentID']
                if pid not in nodes_in_tree:
                    values.append(value)
                    continue
                parent = nodes_in_tree[pid]
            irods_id = value['irodsID']
            display = PyQt5.QtGui.QStandardItem(value['shortName'])
            if value['type'] == 'd':
                display.setIcon(icon_provider.icon(
                    PyQt5.QtWidgets.QFileIconProvider.IconType.File))
            if value['type'] == 'C':
                display.setIcon(icon_provider.icon(
                    PyQt5.QtWidgets.QFileIconProvider.IconType.Folder))
            row = [
                display,
                PyQt5.QtGui.QStandardItem(str(value['level'])),
                PyQt5.QtGui.QStandardItem(str(value['irodsID'])),
                PyQt5.QtGui.QStandardItem(str(value['parentID'])),
                PyQt5.QtGui.QStandardItem(value['type']),
            ]
            parent.appendRow(row)
            nodes_in_tree[irods_id] = parent.child(parent.rowCount() - 1)

    def delete_subtree(self, tree_item):
        """Delete subtree?

        Parameters
        ----------
        tree_item : QStandardItem
            Item in the QTreeView

        """
        # Adjust tree view to remove subtree.
        tree_item.removeRows(0, tree_item.rowCount())

    def get_coll_data(self, coll):
        """Retrieves the subcollections and data objects of a collection
        in the form of key-value dictionaries.

        Parameters
        ----------
        coll : iRODSCollection
            Instance of an iRODS collection.

        Returns
        -------
        list
            Key-value dictionaries.

        Example of the return:

        [
            {
                'irodsID': 12345,
                'level': 10,
                'parentID': 54321,
                'shortName': 'myColl',
                'type': 'C'
            },
            {}
        ]

        """
        data = []
        for sub_coll in coll.subcollections:
            level = len(sub_coll.path.split('/')) - len(self.base_path.split('/'))
            row = {
                'level': level,
                'irodsID': sub_coll.id,
                'parentID': coll.id,
                'shortName': sub_coll.name,
                'type': 'C',
            }
            data.append(row)
            if sub_coll.data_objects != [] or sub_coll.subcollections != []:
                row = {
                    'level': level+1,
                    'irodsID': 'test',
                    'parentID': sub_coll.id,
                    'shortName': 'test',
                    'type': 'd',
                }
                data.append(row)
        for obj in coll.data_objects:
            level = len(obj.path.split('/')) - len(self.base_path.split('/'))
            row = {
                'level': level,
                'irodsID': obj.id,
                'parentID': coll.id,
                'shortName': obj.name,
                'type': 'd',
            }
            data.append(row)
        return data

    def add_subtree(self, tree_item, tree_level, irods_fs_subtree_data):
        """Grow tree_view from tree_item

        Parameters
        ----------
        tree_item : ???
            ???
        tree_level : ???
            ???
        irods_fs_subtree_data : ???
            ???

        """
        icon_provider = PyQt5.QtWidgets.QFileIconProvider()
        values = collections.deque(irods_fs_subtree_data)
        nodes_in_tree = {}
        while values:
            value = values.popleft()
            if value['level'] == tree_level:
                parent = tree_item
            else:
                pid = value['parentID']
                if pid not in nodes_in_tree:
                    values.append(value)
                    continue
                parent = nodes_in_tree[pid]
            irods_id = value['irodsID']
            display = PyQt5.QtGui.QStandardItem(value['shortName'])
            if value['type'] == 'd':
                display.setIcon(icon_provider.icon(
                    PyQt5.QtWidgets.QFileIconProvider.IconType.File))
            if value['type'] == 'C':
                display.setIcon(icon_provider.icon(
                    PyQt5.QtWidgets.QFileIconProvider.IconType.Folder))
            row = [
                display,
                PyQt5.QtGui.QStandardItem(str(value['level'])),
                PyQt5.QtGui.QStandardItem(str(value['irodsID'])),
                PyQt5.QtGui.QStandardItem(str(value['parentID'])),
                PyQt5.QtGui.QStandardItem(value['type']),
            ]
            parent.appendRow(row)
            nodes_in_tree[irods_id] = parent.child(parent.rowCount() - 1)

    def get_parent_index(self, position):
        """Get parent index?

        Parameters
        ----------
        position : int?
            Location in tree?

        Returns
        -------
        ???

        """
        try:
            # Index when right mouse clicked.
            model_index = self.tree.indexAt(position)
            if not model_index.isValid():
                return
        # FIXME narrow down exception possibilities
        except Exception:
            # Index when expand is clicked.
            model_index = position
        return self.itemFromIndex(model_index).parent().index()

    def refresh_subtree(self, position):
        """Refresh the tree view?

        Parameters
        ----------
        position : int?
            Location in tree?

        """
        try:
            # Index when right mouse clicked.
            model_index = self.tree.indexAt(position)
            if not model_index.isValid():
                return
        # FIXME narrow down exception possibilities
        except Exception:
            # Index when expand is clicked.
            model_index = position
        tree_item = self.itemFromIndex(model_index)
        parent = tree_item.parent()
        if parent is None:
            parent = self.invisibleRootItem()
        row = tree_item.row()
        tree_item_data = []
        for col in range(parent.columnCount()):
            child = parent.child(row, col)
            tree_item_data.append(child.data(0))
        irods_item_path = self.irods_path_from_tree_index(model_index)
        if tree_item_data[4] == 'C':
            coll = self.ic.session.collections.get(irods_item_path)
        else:
            return
        # Delete subtree in irodsFsdata and the tree_view.
        self.delete_subtree(tree_item)
        # Retrieve updated data from the collection.
        recent_coll_data = self.get_coll_data(coll)
        # Update irods_fs_data and the tree_view.
        level = len(coll.path.split('/')) - len(self.base_path.split('/')) + 1
        self.add_subtree(tree_item, level, recent_coll_data)

    def irods_path_from_tree_index(self, model_index):
        """Convert a tree index to iRODS path

        Parameters
        ----------
        model_index : int?
            Index of the model?

        """
        full_path = model_index.data()
        parent_model = model_index.parent()
        while parent_model.isValid():
            full_path = parent_model.data() + "/" + full_path
            parent_model = parent_model.parent()
        return os.path.dirname(self.base_path) + "/" + full_path
