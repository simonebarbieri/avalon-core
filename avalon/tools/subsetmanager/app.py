import sys

from ... import api, style

from ...vendor import qtawesome
from ...vendor.Qt import QtWidgets, QtCore

from .. import lib as tools_lib
from ..models import RecursiveSortFilterProxyModel
from .model import InstanceModel, InstanceRole
from .widgets import InstanceDetail


module = sys.modules[__name__]
module.window = None


class Window(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(Window, self).__init__(parent=parent)
        self.setWindowTitle("Subset Manger 0.1")
        self.setObjectName("SubsetManger")

        self.resize(780, 430)

        # Trigger refresh on first called show
        self._first_show = True

        left_side_widget = QtWidgets.QWidget(self)

        # Header part
        header_widget = QtWidgets.QWidget(left_side_widget)

        # Filter input
        filter_input = QtWidgets.QLineEdit()
        filter_input.setPlaceholderText("Filter subsets..")

        # Refresh button
        icon = qtawesome.icon("fa.refresh", color="white")
        refresh_btn = QtWidgets.QPushButton()
        refresh_btn.setIcon(icon)

        header_layout = QtWidgets.QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.addWidget(filter_input)
        header_layout.addWidget(refresh_btn)

        # Instances view
        view = QtWidgets.QTreeView(left_side_widget)
        view.setIndentation(0)
        view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

        model = InstanceModel(view)
        proxy = RecursiveSortFilterProxyModel()
        proxy.setSourceModel(model)
        proxy.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)

        view.setModel(proxy)

        left_side_layout = QtWidgets.QVBoxLayout(left_side_widget)
        left_side_layout.setContentsMargins(0, 0, 0, 0)
        left_side_layout.addWidget(header_widget)
        left_side_layout.addWidget(view)

        details_widget = InstanceDetail(self)

        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(left_side_widget, 0)
        layout.addWidget(details_widget, 1)

        filter_input.textChanged.connect(proxy.setFilterFixedString)
        refresh_btn.clicked.connect(self._on_refresh_clicked)
        view.clicked.connect(self._on_activated)
        view.customContextMenuRequested.connect(self.on_context_menu)

        self.model = model
        self.proxy = proxy
        self.view = view
        self.details_widget = details_widget
        self.refresh_btn = refresh_btn

    def _on_refresh_clicked(self):
        self.refresh()

    def _on_activated(self, index):
        if index.isValid():
            container = index.data(InstanceRole)
        else:
            container = None
        self.details_widget.set_details(container)

    def on_context_menu(self, point):
        point_index = self.view.indexAt(point)
        if not point_index.isValid():
            return

        # Prepare menu
        menu = QtWidgets.QMenu(self)
        actions = []
        host = api.registered_host()
        if hasattr(host, "remove_instance"):
            action = QtWidgets.QAction("Remove instance", menu)
            action.setData(host.remove_instance)
            actions.append(action)

        if not actions:
            actions.append(QtWidgets.QAction("* Nothing to do", menu))

        for action in actions:
            menu.addAction(action)

        # Show menu under mouse
        global_point = self.view.mapToGlobal(point)
        action = menu.exec_(global_point)
        if not action or not action.data():
            return

        # Process action
        # TODO catch exceptions
        function = action.data()
        function(point_index.data(InstanceRole))

        # Reset modified data
        self.refresh()

    def refresh(self):
        self.details_widget.set_details(None)
        self.model.refresh()

    def show(self, *args, **kwargs):
        super(Window, self).show(*args, **kwargs)
        if self._first_show:
            self._first_show = False
            self.refresh()


def show(root=None, debug=False, parent=None):
    """Display Scene Inventory GUI

    Arguments:
        debug (bool, optional): Run in debug-mode,
            defaults to False
        parent (QtCore.QObject, optional): When provided parent the interface
            to this QObject.

    """

    try:
        module.window.close()
        del module.window
    except (RuntimeError, AttributeError):
        pass

    with tools_lib.application():
        window = Window(parent)
        window.setStyleSheet(style.load_stylesheet())
        window.show()

        module.window = window

        # Pull window to the front.
        module.window.raise_()
        module.window.activateWindow()
