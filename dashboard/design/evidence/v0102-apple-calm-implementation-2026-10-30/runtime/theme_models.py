"""Identity-preserving public Qt list models for the theme API.

Only the application calls ``_replace``. Renderers see immutable row DTOs and
roles, never provider objects. Reorders use move notifications, not resets.
"""
from __future__ import annotations

from PySide6.QtCore import QAbstractListModel, QModelIndex, Property, Qt, Signal, Slot


class ThemeListModel(QAbstractListModel):
    countChanged = Signal()
    _type_name = ''
    _item_type = ''
    _identity_role = 'id'
    _fields = {}
    _object_factory = None

    def __init__(self, rows=None, parent=None, *, validated=False):
        super().__init__(parent)
        self._rows = []
        self._roles = {int(Qt.UserRole) + 1: b'item'}
        self._roles.update({int(Qt.UserRole) + 2 + i: name.encode()
                            for i, name in enumerate(self._fields)})
        if rows:
            self._replace(rows, validated=validated)

    def _count(self):
        return len(self._rows)

    count = Property(int, fget=_count, notify=countChanged)

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._rows)

    def roleNames(self):
        return self._roles.copy()

    def data(self, index, role=int(Qt.DisplayRole)):
        if not index.isValid() or not 0 <= index.row() < len(self._rows):
            return None
        row = self._rows[index.row()]
        name = self._roles.get(role, b'').decode()
        return row if name == 'item' else getattr(row, name, None)

    @Slot(int, result='QObject*')
    def get(self, index):
        return self._rows[index] if 0 <= index < len(self._rows) else None

    @Slot(str, result=int)
    def indexOf(self, identity):
        return next((i for i, row in enumerate(self._rows)
                     if getattr(row, self._identity_role) == identity), -1)

    def _snapshot(self):
        return [row._snapshot() for row in self._rows]

    def _replace(self, values, validated=False):
        # Validate before begin* so a bad payload cannot leave a Qt model in a
        # half-open transaction or erase the previous complete snapshot.
        from theme_contexts import CONTRACT, PUBLIC_TYPES
        if not validated:
            CONTRACT.validate_snapshot(self._type_name, values)
        wanted = [row[self._identity_role] for row in values]
        changed = False
        old_count = len(self._rows)
        for i in reversed(range(len(self._rows))):
            if getattr(self._rows[i], self._identity_role) not in wanted:
                self.beginRemoveRows(QModelIndex(), i, i)
                removed = self._rows.pop(i)
                self.endRemoveRows()
                removed.deleteLater()
                changed = True
        for i, value in enumerate(values):
            identity = value[self._identity_role]
            old = self.indexOf(identity)
            if old == -1:
                self.beginInsertRows(QModelIndex(), i, i)
                self._rows.insert(i, PUBLIC_TYPES[self._item_type](value, self, validated=True))
                self.endInsertRows()
                changed = True
            else:
                if old != i:
                    self.beginMoveRows(QModelIndex(), old, old, QModelIndex(), i if old > i else i + 1)
                    self._rows.insert(i, self._rows.pop(old))
                    self.endMoveRows()
                    changed = True
                row = self._rows[i]
                fields = row._update(value, validated=True)
                if fields:
                    roles = [role for role, name in self._roles.items()
                             if name.decode() in fields or name == b'item']
                    self.dataChanged.emit(self.index(i), self.index(i), roles)
                    changed = True
        if len(self._rows) != old_count:
            self.countChanged.emit()
        return changed
