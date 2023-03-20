"""Tree model for IRODS collections.
The IRODS database is huge and retrieving a complete tree of all files
can take ages.  To improve the loading time the tree is only grown as
far as it displays.

"""
import collections
import logging
import os

import irods
import PyQt6
import PyQt6.QtCore
import PyQt6.QtGui
import PyQt6.QtWidgets

ACCESS_NAMES = [
    'own',
    'modify object',
    'read object',
    'modify_object',
    'read_object',
]


class IrodsModel(PyQt6.QtGui.QStandardItemModel):
    """Model for an iRODS tree view.

    """

    def __init__(self, irods_connector, tree_view, parent=None):
        """Initializes the tree view with the root node and first level.

        Class variables 'user_groups' and 'base_path' _must_ be
        populated with a list of group names and the path name of the
        iRODS top-level collection (i.e., /<zone name>/home),
        respectively.

        Parameters
        ----------
        irods_connector : IrodsConnector
            iRODS session container.
        tree_view : PyQt6.QtWidgets
            Defined iRODS tree view UI element.
        parent : ???
            ???

        """
        super().__init__(parent)
        self.ic = irods_connector
        self.tree_view = tree_view
        try:
            self.user_groups = self.ic.get_user_info()[1]
        except irods.exception.NetworkException:
            logging.info('iRODS FILE TREE ERROR: user info', exc_info=True)
        self.zone_path = f'/{self.ic.get_zone}'
        self.base_path = f'{self.zone_path}/home'
        # Empty tree
        self.clear()

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
            coll = self.ic.get_collection(self.base_path)
        except irods.exception.CollectionDoesNotExist:
            self.base_path = self.base_path+'/'+self.ic.username
            coll = self.ic.get_collection(self.base_path)
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
        icon_provider = PyQt6.QtWidgets.QFileIconProvider()
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
            display = PyQt6.QtGui.QStandardItem(value['shortName'])
            if value['type'] == 'd':
                display.setIcon(icon_provider.icon(
                    PyQt6.QtWidgets.QFileIconProvider.IconType.File))
            if value['type'] == 'C':
                display.setIcon(icon_provider.icon(
                    PyQt6.QtWidgets.QFileIconProvider.IconType.Folder))
            row = [
                display,
                PyQt6.QtGui.QStandardItem(str(value['level'])),
                PyQt6.QtGui.QStandardItem(str(value['irodsID'])),
                PyQt6.QtGui.QStandardItem(str(value['parentID'])),
                PyQt6.QtGui.QStandardItem(value['type']),
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
        icon_provider = PyQt6.QtWidgets.QFileIconProvider()
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
            display = PyQt6.QtGui.QStandardItem(value['shortName'])
            if value['type'] == 'd':
                display.setIcon(icon_provider.icon(
                    PyQt6.QtWidgets.QFileIconProvider.IconType.File))
            if value['type'] == 'C':
                display.setIcon(icon_provider.icon(
                    PyQt6.QtWidgets.QFileIconProvider.IconType.Folder))
            row = [
                display,
                PyQt6.QtGui.QStandardItem(str(value['level'])),
                PyQt6.QtGui.QStandardItem(str(value['irodsID'])),
                PyQt6.QtGui.QStandardItem(str(value['parentID'])),
                PyQt6.QtGui.QStandardItem(value['type']),
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
            coll = self.ic.get_collection(irods_item_path)
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
