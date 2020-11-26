from ... import api
from ...vendor.Qt import QtCore
from ..models import TreeModel, Item

InstanceRole = QtCore.Qt.UserRole + 1


class InstanceModel(TreeModel):
    column_label_mapping = {
        "subset": "Subset"
    }
    Columns = list(column_label_mapping.keys())

    def refresh(self):
        self.clear()

        instances = None

        host = api.registered_host()
        list_instances = getattr(host, "list_instances", None)
        if list_instances:
            instances = list_instances()

        if not instances:
            return

        self.beginResetModel()

        for instance_data in instances:
            item = Item({
                "subset": instance_data["subset"],
                "instance": instance_data
            })
            self.add_child(item)

        self.endResetModel()

    def data(self, index, role):
        if not index.isValid():
            return

        if role == InstanceRole:
            item = index.internalPointer()
            return item.get("instance", None)

        return super(InstanceModel, self).data(index, role)

    def headerData(self, section, orientation, role):
        if role == QtCore.Qt.DisplayRole:
            if section < len(self.Columns):
                return self.column_label_mapping[self.Columns[section]]

        return super(InstanceModel, self).headerData(
            section, orientation, role
        )
