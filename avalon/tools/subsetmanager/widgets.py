import json
from ...vendor.Qt import QtWidgets


class InstanceDetail(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(InstanceDetail, self).__init__(parent)

        details_widget = QtWidgets.QPlainTextEdit(self)
        details_widget.setReadOnly(True)

        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(details_widget)

        self.details_widget = details_widget

    def set_details(self, container):
        text = "No data"
        if container:
            try:
                text = json.dumps(container, indent=4)
            except Exception:
                pass

        self.details_widget.setPlainText(text)
