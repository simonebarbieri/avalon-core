import os
import sys
import datetime
import pprint
import traceback
import collections

from ...vendor.Qt import QtWidgets, QtCore, QtGui
from ... import api
from ... import pipeline
from ...lib import HeroVersionType

from .. import lib as tools_lib
from ..delegates import VersionDelegate, PrettyTimeDelegate
from ..widgets import OptionalMenu
from ..views import TreeViewSpinner, DeselectableTreeView

from .model import (
    SubsetsModel,
    SubsetFilterProxyModel,
    FamiliesFilterProxyModel,
    RepresentationModel,
    RepresentationSortProxyModel
)
from . import lib


class LoadErrorMessageBox(QtWidgets.QDialog):
    def __init__(self, messages, parent=None):
        super(LoadErrorMessageBox, self).__init__(parent)
        self.setWindowTitle("Loading failed")
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

        body_layout = QtWidgets.QVBoxLayout(self)

        main_label = (
            "<span style='font-size:18pt;'>Failed to load items</span>"
        )
        main_label_widget = QtWidgets.QLabel(main_label, self)
        body_layout.addWidget(main_label_widget)

        item_name_template = (
            "<span style='font-weight:bold;'>Subset:</span> {}<br>"
            "<span style='font-weight:bold;'>Version:</span> {}<br>"
            "<span style='font-weight:bold;'>Representation:</span> {}<br>"
        )
        exc_msg_template = "<span style='font-weight:bold'>{}</span>"

        for exc_msg, tb, repre, subset, version in messages:
            line = self._create_line()
            body_layout.addWidget(line)

            item_name = item_name_template.format(subset, version, repre)
            item_name_widget = QtWidgets.QLabel(
                item_name.replace("\n", "<br>"), self
            )
            body_layout.addWidget(item_name_widget)

            exc_msg = exc_msg_template.format(exc_msg.replace("\n", "<br>"))
            message_label_widget = QtWidgets.QLabel(exc_msg, self)
            body_layout.addWidget(message_label_widget)

            if tb:
                tb_widget = QtWidgets.QLabel(tb.replace("\n", "<br>"), self)
                tb_widget.setTextInteractionFlags(
                    QtCore.Qt.TextBrowserInteraction
                )
                body_layout.addWidget(tb_widget)

        footer_widget = QtWidgets.QWidget(self)
        footer_layout = QtWidgets.QHBoxLayout(footer_widget)
        buttonBox = QtWidgets.QDialogButtonBox(QtCore.Qt.Vertical)
        buttonBox.setStandardButtons(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
        )
        buttonBox.accepted.connect(self._on_accept)
        footer_layout.addWidget(buttonBox, alignment=QtCore.Qt.AlignRight)
        body_layout.addWidget(footer_widget)

    def _on_accept(self):
        self.close()

    def _create_line(self):
        line = QtWidgets.QFrame(self)
        line.setFixedHeight(2)
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        return line


class SubsetWidget(QtWidgets.QWidget):
    """A widget that lists the published subsets for an asset"""

    active_changed = QtCore.Signal()    # active index changed
    version_changed = QtCore.Signal()   # version state changed for a subset

    default_widths = (
        ("subset", 200),
        ("asset", 130),
        ("family", 90),
        ("version", 60),
        ("time", 125),
        ("author", 75),
        ("frames", 75),
        ("duration", 60),
        ("handles", 55),
        ("step", 10),
        ("repre_info", 65)
    )

    def __init__(
        self,
        dbcon,
        groups_config,
        family_config_cache,
        enable_grouping=True,
        tool_name=None,
        parent=None
    ):
        super(SubsetWidget, self).__init__(parent=parent)

        self.dbcon = dbcon
        self.tool_name = tool_name

        model = SubsetsModel(
            dbcon,
            groups_config,
            family_config_cache,
            grouping=enable_grouping
        )
        proxy = SubsetFilterProxyModel()
        family_proxy = FamiliesFilterProxyModel(family_config_cache)
        family_proxy.setSourceModel(proxy)

        subset_filter = QtWidgets.QLineEdit()
        subset_filter.setPlaceholderText("Filter subsets..")

        groupable = QtWidgets.QCheckBox("Enable Grouping")
        groupable.setChecked(enable_grouping)

        top_bar_layout = QtWidgets.QHBoxLayout()
        top_bar_layout.addWidget(subset_filter)
        top_bar_layout.addWidget(groupable)

        view = TreeViewSpinner()
        view.setObjectName("SubsetView")
        view.setIndentation(20)
        view.setStyleSheet("""
            QTreeView::item{
                padding: 5px 1px;
                border: 0px;
            }
        """)
        view.setAllColumnsShowFocus(True)

        # Set view delegates
        version_delegate = VersionDelegate(self.dbcon)
        column = model.Columns.index("version")
        view.setItemDelegateForColumn(column, version_delegate)

        time_delegate = PrettyTimeDelegate()
        column = model.Columns.index("time")
        view.setItemDelegateForColumn(column, time_delegate)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(top_bar_layout)
        layout.addWidget(view)

        view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        view.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        view.setSortingEnabled(True)
        view.sortByColumn(1, QtCore.Qt.AscendingOrder)
        view.setAlternatingRowColors(True)

        self.data = {
            "delegates": {
                "version": version_delegate,
                "time": time_delegate
            },
            "state": {
                "groupable": groupable
            }
        }

        self.proxy = proxy
        self.model = model
        self.view = view
        self.filter = subset_filter
        self.family_proxy = family_proxy

        # settings and connections
        self.proxy.setSourceModel(self.model)
        self.proxy.setDynamicSortFilter(True)
        self.proxy.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)

        self.view.setModel(self.family_proxy)
        self.view.customContextMenuRequested.connect(self.on_context_menu)

        for column_name, width in self.default_widths:
            idx = model.Columns.index(column_name)
            view.setColumnWidth(idx, width)

        if not model.sync_server or not model.sync_server.enabled:
            lib.change_visibility(self.model, self.view, "repre_info", False)

        selection = view.selectionModel()
        selection.selectionChanged.connect(self.active_changed)

        version_delegate.version_changed.connect(self.version_changed)

        groupable.stateChanged.connect(self.set_grouping)

        self.filter.textChanged.connect(self.proxy.setFilterRegExp)
        self.filter.textChanged.connect(self.view.expandAll)

        self.model.refresh()

        # Expose this from the widget as a method
        self.set_family_filters = self.family_proxy.setFamiliesFilter

    def is_groupable(self):
        return self.data["state"]["groupable"].checkState()

    def set_grouping(self, state):
        with tools_lib.preserve_selection(tree_view=self.view,
                                          current_index=False):
            self.model.set_grouping(state)

    def set_loading_state(self, loading, empty):
        view = self.view

        if view.is_loading != loading:
            if loading:
                view.spinner.repaintNeeded.connect(view.viewport().update)
            else:
                view.spinner.repaintNeeded.disconnect()

        view.is_loading = loading
        view.is_empty = empty

    def _repre_contexts_for_loaders_filter(self, items):
        version_docs_by_id = {
            item["version_document"]["_id"]: item["version_document"]
            for item in items
        }
        version_docs_by_subset_id = collections.defaultdict(list)
        for item in items:
            subset_id = item["version_document"]["parent"]
            version_docs_by_subset_id[subset_id].append(
                item["version_document"]
            )

        subset_docs = list(self.dbcon.find(
            {
                "_id": {"$in": list(version_docs_by_subset_id.keys())},
                "type": "subset"
            },
            {
                "schema": 1,
                "data.families": 1
            }
        ))
        subset_docs_by_id = {
            subset_doc["_id"]: subset_doc
            for subset_doc in subset_docs
        }
        version_ids = list(version_docs_by_id.keys())
        repre_docs = self.dbcon.find(
            # Query all representations for selected versions at once
            {
                "type": "representation",
                "parent": {"$in": version_ids}
            },
            # Query only name and parent from representation
            {
                "name": 1,
                "parent": 1
            }
        )
        repre_docs_by_version_id = {
            version_id: []
            for version_id in version_ids
        }
        repre_context_by_id = {}
        for repre_doc in repre_docs:
            version_id = repre_doc["parent"]
            repre_docs_by_version_id[version_id].append(repre_doc)

            version_doc = version_docs_by_id[version_id]
            repre_context_by_id[repre_doc["_id"]] = {
                "representation": repre_doc,
                "version": version_doc,
                "subset": subset_docs_by_id[version_doc["parent"]]
            }
        return repre_context_by_id, repre_docs_by_version_id

    def on_context_menu(self, point):
        """Shows menu with loader actions on Right-click.

        Registered actions are filtered by selection and help of
        `loaders_from_representation` from avalon api. Intersection of actions
        is shown when more subset is selected. When there are not available
        actions for selected subsets then special action is shown (works as
        info message to user): "*No compatible loaders for your selection"

        """

        point_index = self.view.indexAt(point)
        if not point_index.isValid():
            return

        # Get selected subsets without groups
        selection = self.view.selectionModel()
        rows = selection.selectedRows(column=0)

        items = lib.get_selected_items(rows, self.model.ItemRole)

        # Get all representation->loader combinations available for the
        # index under the cursor, so we can list the user the options.
        available_loaders = api.discover(api.Loader)
        if self.tool_name:
            available_loaders = lib.remove_tool_name_from_loaders(
                available_loaders, self.tool_name)

        loaders = list()

        # Bool if is selected only one subset
        one_item_selected = (len(items) == 1)

        # Prepare variables for multiple selected subsets
        first_loaders = []
        found_combinations = None

        is_first = True
        repre_context_by_id, repre_docs_by_version_id = (
            self._repre_contexts_for_loaders_filter(items)
        )
        for item in items:
            _found_combinations = []
            version_id = item["version_document"]["_id"]
            repre_docs = repre_docs_by_version_id[version_id]
            for repre_doc in repre_docs:
                repre_context = repre_context_by_id[repre_doc["_id"]]
                for loader in pipeline.loaders_from_repre_context(
                    available_loaders,
                    repre_context
                ):
                    # do not allow download whole repre, select specific repre
                    if tools_lib.is_representation_loader(loader):
                        continue

                    # skip multiple select variant if one is selected
                    if one_item_selected:
                        loaders.append((repre_doc, loader))
                        continue

                    # store loaders of first subset
                    if is_first:
                        first_loaders.append((repre_doc, loader))

                    # store combinations to compare with other subsets
                    _found_combinations.append(
                        (repre_doc["name"].lower(), loader)
                    )

            # skip multiple select variant if one is selected
            if one_item_selected:
                continue

            is_first = False
            # Store first combinations to compare
            if found_combinations is None:
                found_combinations = _found_combinations
            # Intersect found combinations with all previous subsets
            else:
                found_combinations = list(
                    set(found_combinations) & set(_found_combinations)
                )

        if not one_item_selected:
            # Filter loaders from first subset by intersected combinations
            for repre, loader in first_loaders:
                if (repre["name"], loader) not in found_combinations:
                    continue

                loaders.append((repre, loader))

        loaders = lib.sort_loaders(loaders)

        menu = OptionalMenu(self)
        if not loaders:
            action = lib.get_no_loader_action(menu, one_item_selected)
            menu.addAction(action)
        else:
            menu = lib.add_representation_loaders_to_menu(loaders, menu)

        # Show the context action menu
        global_point = self.view.mapToGlobal(point)
        action = menu.exec_(global_point)
        if not action or not action.data():
            return

        # Find the representation name and loader to trigger
        action_representation, loader = action.data()
        representation_name = action_representation["name"]  # extension

        options = lib.get_options(action, loader, self)

        # Run the loader for all selected indices, for those that have the
        # same representation available

        # Trigger
        repre_ids = []
        for item in items:
            representation = self.dbcon.find_one(
                {
                    "type": "representation",
                    "name": representation_name,
                    "parent": item["version_document"]["_id"]
                },
                {"_id": 1}
            )
            if not representation:
                self.echo("Subset '{}' has no representation '{}'".format(
                    item["subset"], representation_name
                ))
                continue
            repre_ids.append(representation["_id"])

        error_info = _load_representations_by_loader(
            loader, repre_ids, self.dbcon,
            options=options
        )

        if error_info:
            box = LoadErrorMessageBox(error_info)
            box.show()

    def selected_subsets(self, _groups=False, _merged=False, _other=True):
        selection = self.view.selectionModel()
        rows = selection.selectedRows(column=0)

        subsets = list()
        if not any([_groups, _merged, _other]):
            self.echo((
                "This is a BUG: Selected_subsets args must contain"
                " at least one value set to True"
            ))
            return subsets

        for row in rows:
            item = row.data(self.model.ItemRole)
            if item.get("isGroup"):
                if not _groups:
                    continue

            elif item.get("isMerged"):
                if not _merged:
                    continue
            else:
                if not _other:
                    continue

            subsets.append(item)

        return subsets

    def group_subsets(self, name, asset_ids, items):
        field = "data.subsetGroup"

        if name:
            update = {"$set": {field: name}}
            self.echo("Group subsets to '%s'.." % name)
        else:
            update = {"$unset": {field: ""}}
            self.echo("Ungroup subsets..")

        subsets = list()
        for item in items:
            subsets.append(item["subset"])

        for asset_id in asset_ids:
            filtr = {
                "type": "subset",
                "parent": asset_id,
                "name": {"$in": subsets},
            }
            self.dbcon.update_many(filtr, update)

    def echo(self, message):
        print(message)


class VersionTextEdit(QtWidgets.QTextEdit):
    """QTextEdit that displays version specific information.

    This also overrides the context menu to add actions like copying
    source path to clipboard or copying the raw data of the version
    to clipboard.

    """
    def __init__(self, dbcon, parent=None):
        super(VersionTextEdit, self).__init__(parent=parent)
        self.dbcon = dbcon

        self.data = {
            "source": None,
            "raw": None
        }

        # Reset
        self.set_version(None)

    def set_version(self, version_doc=None, version_id=None):
        # TODO expect only filling data (do not query them here!)
        if not version_doc and not version_id:
            # Reset state to empty
            self.data = {
                "source": None,
                "raw": None,
            }
            self.setText("")
            self.setEnabled(True)
            return

        self.setEnabled(True)

        print("Querying..")

        if not version_doc:
            version_doc = self.dbcon.find_one({
                "_id": version_id,
                "type": {"$in": ["version", "hero_version"]}
            })
            assert version_doc, "Not a valid version id"

        if version_doc["type"] == "hero_version":
            _version_doc = self.dbcon.find_one({
                "_id": version_doc["version_id"],
                "type": "version"
            })
            version_doc["data"] = _version_doc["data"]
            version_doc["name"] = HeroVersionType(
                _version_doc["name"]
            )

        subset = self.dbcon.find_one({
            "_id": version_doc["parent"],
            "type": "subset"
        })
        assert subset, "No valid subset parent for version"

        # Define readable creation timestamp
        created = version_doc["data"]["time"]
        created = datetime.datetime.strptime(created, "%Y%m%dT%H%M%SZ")
        created = datetime.datetime.strftime(created, "%b %d %Y %H:%M")

        comment = version_doc["data"].get("comment", None) or "No comment"

        source = version_doc["data"].get("source", None)
        source_label = source if source else "No source"

        # Store source and raw data
        self.data["source"] = source
        self.data["raw"] = version_doc

        if version_doc["type"] == "hero_version":
            version_name = "hero"
        else:
            version_name = tools_lib.format_version(version_doc["name"])

        data = {
            "subset": subset["name"],
            "version": version_name,
            "comment": comment,
            "created": created,
            "source": source_label
        }

        self.setHtml((
            "<h2>{subset}</h2>"
            "<h3>{version}</h3>"
            "<b>Comment</b><br>"
            "{comment}<br><br>"

            "<b>Created</b><br>"
            "{created}<br><br>"

            "<b>Source</b><br>"
            "{source}"
        ).format(**data))

    def contextMenuEvent(self, event):
        """Context menu with additional actions"""
        menu = self.createStandardContextMenu()

        # Add additional actions when any text so we can assume
        # the version is set.
        if self.toPlainText().strip():

            menu.addSeparator()
            action = QtWidgets.QAction("Copy source path to clipboard",
                                       menu)
            action.triggered.connect(self.on_copy_source)
            menu.addAction(action)

            action = QtWidgets.QAction("Copy raw data to clipboard",
                                       menu)
            action.triggered.connect(self.on_copy_raw)
            menu.addAction(action)

        menu.exec_(event.globalPos())
        del menu

    def on_copy_source(self):
        """Copy formatted source path to clipboard"""
        source = self.data.get("source", None)
        if not source:
            return

        path = source.format(root=api.registered_root())
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(path)

    def on_copy_raw(self):
        """Copy raw version data to clipboard

        The data is string formatted with `pprint.pformat`.

        """
        raw = self.data.get("raw", None)
        if not raw:
            return

        raw_text = pprint.pformat(raw)
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(raw_text)


class ThumbnailWidget(QtWidgets.QLabel):

    aspect_ratio = (16, 9)
    max_width = 300

    def __init__(self, dbcon, parent=None):
        super(ThumbnailWidget, self).__init__(parent)
        self.dbcon = dbcon

        self.current_thumb_id = None
        self.current_thumbnail = None

        self.setAlignment(QtCore.Qt.AlignCenter)

        # TODO get res path much better way
        loader_path = os.path.dirname(os.path.abspath(__file__))
        avalon_path = os.path.dirname(os.path.dirname(loader_path))
        default_pix_path = os.path.join(
            os.path.dirname(avalon_path),
            "res", "tools", "images", "default_thumbnail.png"
        )
        self.default_pix = QtGui.QPixmap(default_pix_path)

    def height(self):
        width = self.width()
        asp_w, asp_h = self.aspect_ratio

        return (width / asp_w) * asp_h

    def width(self):
        width = super(ThumbnailWidget, self).width()
        if width > self.max_width:
            width = self.max_width
        return width

    def set_pixmap(self, pixmap=None):
        if not pixmap:
            pixmap = self.default_pix
            self.current_thumb_id = None

        self.current_thumbnail = pixmap

        pixmap = self.scale_pixmap(pixmap)
        self.setPixmap(pixmap)

    def resizeEvent(self, _event):
        if not self.current_thumbnail:
            return
        cur_pix = self.scale_pixmap(self.current_thumbnail)
        self.setPixmap(cur_pix)

    def scale_pixmap(self, pixmap):
        return pixmap.scaled(
            self.width(), self.height(), QtCore.Qt.KeepAspectRatio
        )

    def set_thumbnail(self, entity=None):
        if not entity:
            self.set_pixmap()
            return

        if isinstance(entity, (list, tuple)):
            if len(entity) == 1:
                entity = entity[0]
            else:
                self.set_pixmap()
                return

        thumbnail_id = entity.get("data", {}).get("thumbnail_id")
        if thumbnail_id == self.current_thumb_id:
            if self.current_thumbnail is None:
                self.set_pixmap()
            return

        self.current_thumb_id = thumbnail_id
        if not thumbnail_id:
            self.set_pixmap()
            return

        thumbnail_ent = self.dbcon.find_one(
            {"type": "thumbnail", "_id": thumbnail_id}
        )
        if not thumbnail_ent:
            return

        thumbnail_bin = pipeline.get_thumbnail_binary(
            thumbnail_ent, "thumbnail", self.dbcon
        )
        if not thumbnail_bin:
            self.set_pixmap()
            return

        thumbnail = QtGui.QPixmap()
        thumbnail.loadFromData(thumbnail_bin)

        self.set_pixmap(thumbnail)


class VersionWidget(QtWidgets.QWidget):
    """A Widget that display information about a specific version"""
    def __init__(self, dbcon, parent=None):
        super(VersionWidget, self).__init__(parent=parent)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        label = QtWidgets.QLabel("Version", self)
        data = VersionTextEdit(dbcon, self)
        data.setReadOnly(True)

        layout.addWidget(label)
        layout.addWidget(data)

        self.data = data

    def set_version(self, version_doc):
        self.data.set_version(version_doc)


class FamilyListWidget(QtWidgets.QListWidget):
    """A Widget that lists all available families"""

    NameRole = QtCore.Qt.UserRole + 1
    active_changed = QtCore.Signal(list)

    def __init__(self, dbcon, family_config_cache, parent=None):
        super(FamilyListWidget, self).__init__(parent=parent)

        self.family_config_cache = family_config_cache
        self.dbcon = dbcon

        multi_select = QtWidgets.QAbstractItemView.ExtendedSelection
        self.setSelectionMode(multi_select)
        self.setAlternatingRowColors(True)
        # Enable RMB menu
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_right_mouse_menu)

        self.itemChanged.connect(self._on_item_changed)

    def refresh(self):
        """Refresh the listed families.

        This gets all unique families and adds them as checkable items to
        the list.

        """

        family = self.dbcon.distinct("data.family")
        families = self.dbcon.distinct("data.families")
        unique_families = list(set(family + families))

        # Rebuild list
        self.blockSignals(True)
        self.clear()
        for name in sorted(unique_families):

            family = self.family_config_cache.family_config(name)
            if family.get("hideFilter"):
                continue

            label = family.get("label", name)
            icon = family.get("icon", None)

            # TODO: This should be more managable by the artist
            # Temporarily implement support for a default state in the project
            # configuration
            state = family.get("state", True)
            state = QtCore.Qt.Checked if state else QtCore.Qt.Unchecked

            item = QtWidgets.QListWidgetItem(parent=self)
            item.setText(label)
            item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
            item.setData(self.NameRole, name)
            item.setCheckState(state)

            if icon:
                item.setIcon(icon)

            self.addItem(item)
        self.blockSignals(False)

        self.active_changed.emit(self.get_filters())

    def get_filters(self):
        """Return the checked family items"""

        items = [self.item(i) for i in
                 range(self.count())]

        return [item.data(self.NameRole) for item in items if
                item.checkState() == QtCore.Qt.Checked]

    def _on_item_changed(self):
        self.active_changed.emit(self.get_filters())

    def _set_checkstate_all(self, state):
        _state = QtCore.Qt.Checked if state is True else QtCore.Qt.Unchecked
        self.blockSignals(True)
        for i in range(self.count()):
            item = self.item(i)
            item.setCheckState(_state)
        self.blockSignals(False)
        self.active_changed.emit(self.get_filters())

    def show_right_mouse_menu(self, pos):
        """Build RMB menu under mouse at current position (within widget)"""

        # Get mouse position
        globalpos = self.viewport().mapToGlobal(pos)

        menu = QtWidgets.QMenu(self)

        # Add enable all action
        state_checked = QtWidgets.QAction(menu, text="Enable All")
        state_checked.triggered.connect(
            lambda: self._set_checkstate_all(True))
        # Add disable all action
        state_unchecked = QtWidgets.QAction(menu, text="Disable All")
        state_unchecked.triggered.connect(
            lambda: self._set_checkstate_all(False))

        menu.addAction(state_checked)
        menu.addAction(state_unchecked)

        menu.exec_(globalpos)


class RepresentationWidget(QtWidgets.QWidget):

    default_widths = (
        ("name", 120),
        ("subset", 125),
        ("asset", 125),
        ("active_site", 85),
        ("remote_site", 85)
    )

    commands = {'active': 'Download', 'remote': 'Upload'}

    def __init__(self, dbcon, tool_name=None, parent=None):
        super(RepresentationWidget, self).__init__(parent=parent)

        self.dbcon = dbcon
        self.tool_name = tool_name

        headers = [item[0] for item in self.default_widths]

        model = RepresentationModel(dbcon, headers, [])

        proxy_model = RepresentationSortProxyModel(self)
        proxy_model.setSourceModel(model)

        label = QtWidgets.QLabel("Representations", self)

        tree_view = DeselectableTreeView()
        tree_view.setModel(proxy_model)
        tree_view.setAllColumnsShowFocus(True)
        tree_view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        tree_view.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection)
        tree_view.setSortingEnabled(True)
        tree_view.sortByColumn(1, QtCore.Qt.AscendingOrder)
        tree_view.setAlternatingRowColors(True)
        tree_view.setIndentation(20)
        tree_view.setStyleSheet("""
            QTreeView::item{
                padding: 5px 1px;
                border: 0px;
            }
        """)
        tree_view.collapseAll()

        for column_name, width in self.default_widths:
            idx = model.Columns.index(column_name)
            tree_view.setColumnWidth(idx, width)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(label)
        layout.addWidget(tree_view)

        # self.itemChanged.connect(self._on_item_changed)
        tree_view.customContextMenuRequested.connect(self.on_context_menu)

        self.tree_view = tree_view
        self.model = model
        self.proxy_model = proxy_model

        self.sync_server_enabled = model.sync_server.enabled

        self.model.refresh()

    def on_context_menu(self, point):
        """Shows menu with loader actions on Right-click.

        Registered actions are filtered by selection and help of
        `loaders_from_representation` from avalon api. Intersection of actions
        is shown when more subset is selected. When there are not available
        actions for selected subsets then special action is shown (works as
        info message to user): "*No compatible loaders for your selection"

        """
        point_index = self.tree_view.indexAt(point)
        if not point_index.isValid():
            return

        # Get selected subsets without groups
        selection = self.tree_view.selectionModel()
        rows = selection.selectedRows(column=0)

        items = lib.get_selected_items(rows, self.model.ItemRole)

        selected_side = self._get_selected_side(point_index, rows)

        # Get all representation->loader combinations available for the
        # index under the cursor, so we can list the user the options.
        available_loaders = api.discover(api.Loader)

        loaders = list()
        for loader in available_loaders:
            if tools_lib.is_representation_loader(loader):
                if not self.sync_server_enabled:
                    available_loaders.remove(loader)

        if self.tool_name:
            available_loaders = lib.remove_tool_name_from_loaders(
                available_loaders, self.tool_name)

        already_added_loaders = set()
        label_already_in_menu = set()
        for item in items:
            repre_context = pipeline.get_representation_context(item["_id"])
            for loader in pipeline.loaders_from_repre_context(
                    available_loaders,
                    repre_context
            ):
                if tools_lib.is_representation_loader(loader):
                    both_unavailable = item["active_site_progress"] <= 0 and \
                                       item["remote_site_progress"] <= 0
                    if both_unavailable:
                        continue

                    for selected_side in self.commands.keys():
                        item = item.copy()
                        item["custom_label"] = None
                        label = None
                        selected_site_progress = item.get(
                            "{}_site_progress".format(selected_side), -1)

                        # only remove if actually present
                        if tools_lib.is_remove_site_loader(loader):
                            label = "Remove {}".format(selected_side)
                            if selected_site_progress < 1:
                                continue

                        if tools_lib.is_add_site_loader(loader):
                            label = self.commands[selected_side]
                            if selected_site_progress >= 0:
                                label = 'Re-{} {}'.format(label, selected_side)

                        if not label:
                            continue

                        item["selected_side"] = selected_side
                        item["custom_label"] = label

                        if label not in label_already_in_menu:
                            loaders.append((item, loader))
                            already_added_loaders.add(loader)
                            label_already_in_menu.add(label)

                else:
                    item = item.copy()
                    item["custom_label"] = None

                    if loader not in already_added_loaders:
                        loaders.append((item, loader))
                        already_added_loaders.add(loader)

        loaders = lib.sort_loaders(loaders)

        menu = OptionalMenu(self)
        if not loaders:
            action = lib.get_no_loader_action(menu)
            menu.addAction(action)
        else:
            menu = lib.add_representation_loaders_to_menu(loaders, menu)

        self._process_action(items, menu, point)

    def _process_action(self, items, menu, point):
        """
            Show the context action menu and process selected

            Args:
                items(dict): menu items
                menu(OptionalMenu)
                point(PointIndex)
        """
        global_point = self.tree_view.mapToGlobal(point)
        action = menu.exec_(global_point)

        if not action or not action.data():
            return

        # Find the representation name and loader to trigger
        action_representation, loader = action.data()
        repre_ids = []
        data_by_repre_id = {}
        selected_side = action_representation.get("selected_side")

        for item in items:
            if tools_lib.is_representation_loader(loader):
                site_name = "{}_site_name".format(selected_side)
                data = {
                    "_id": item.get("_id"),
                    "site_name": item.get(site_name),
                    "project_name": self.dbcon.Session["AVALON_PROJECT"]
                }

                if not data["site_name"]:
                    continue

                data_by_repre_id[data["_id"]] = data

            repre_ids.append(item.get("_id"))

        errors = _load_representations_by_loader(
            loader, repre_ids, self.dbcon, data_by_repre_id=data_by_repre_id)

        self.model.refresh()
        if errors:
            box = LoadErrorMessageBox(errors)
            box.show()

    def _get_optional_labels(self, loaders, selected_side):
        """Each loader could have specific label

            Args:
                loaders (tuple of dict, dict): (item, loader)
                selected_side(string): active or remote

            Returns:
                (dict) {loader: string}
        """
        optional_labels = {}
        if selected_side:
            if selected_side == 'active':
                txt = "Localize"
            else:
                txt = "Sync to Remote"
            optional_labels = {loader: txt for _, loader in loaders
                               if tools_lib.is_representation_loader(loader)}
        return optional_labels

    def _get_selected_side(self, point_index, rows):
        """Returns active/remote label according to column in 'point_index'"""
        selected_side = None
        if self.sync_server_enabled:
            if rows:
                source_index = self.proxy_model.mapToSource(point_index)
                selected_side = self.model.data(source_index,
                                                self.model.SiteSideRole)
        return selected_side

    def set_version_ids(self, version_ids):
        self.model.set_version_ids(version_ids)

    def _set_download(self):
        pass

    def change_visibility(self, column_name, visible):
        """
            Hides or shows particular 'column_name'.

            "asset" and "subset" columns should be visible only in multiselect
        """
        lib.change_visibility(self.model, self.tree_view, column_name, visible)


def _load_representations_by_loader(loader, repre_ids, dbcon,
                                    options=None,
                                    data_by_repre_id=None):
    """Loops through list of repre ids and loads them with one loader"""
    error_info = []
    repre_contexts = pipeline.get_repres_contexts(repre_ids, dbcon)

    options = options or {}
    for repre_context in repre_contexts.values():
        try:
            if data_by_repre_id:
                _id = repre_context["representation"]["_id"]
                data = data_by_repre_id.get(_id)
                options.update(data)
            pipeline.load_with_repre_context(
                loader,
                repre_context,
                options=options
            )
        except pipeline.IncompatibleLoaderError as exc:
            print(exc)
            error_info.append((
                "Incompatible Loader",
                None,
                repre_context["representation"]["name"],
                repre_context["subset"]["name"],
                repre_context["version"]["name"]
            ))

        except Exception as exc:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            formatted_traceback = "".join(traceback.format_exception(
                exc_type, exc_value, exc_traceback
            ))
            error_info.append((
                str(exc),
                formatted_traceback,
                repre_context["representation"]["name"],
                repre_context["subset"]["name"],
                repre_context["version"]["name"]
            ))
    return error_info
