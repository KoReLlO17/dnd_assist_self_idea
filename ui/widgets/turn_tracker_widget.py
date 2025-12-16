from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QHeaderView, QHBoxLayout, QLabel
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor


class TurnTrackerWidget(QWidget):
    """
    Віджет таблиці бою (Turn Order).
    Колонки: Name, HP, Morale, Fatigue (порожні), Sheet (кнопка).
    """
    show_details_requested = Signal(str, str, dict)  # uid, name, token_data

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Ім'я", "HP", "Morale", "Fatigue", "Sheet"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)
        self.table.setColumnWidth(4, 60)

        # Робимо таблицю Read-Only, крім кнопки
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        layout.addWidget(self.table)

    def update_state(self, combat_state):
        order = combat_state.get("turn_order", [])
        current_idx = combat_state.get("current_turn_index", 0)
        tokens = combat_state.get("tokens", {})

        self.table.setRowCount(len(order))

        for row, actor in enumerate(order):
            uid = actor['uid']
            name = actor['name']

            # Name Item
            name_item = QTableWidgetItem(name)
            if row == current_idx:
                name_item.setBackground(QColor("#C8E6C9"))  # Зелений фон для активного
                name_item.setForeground(QColor("#1B5E20"))

            self.table.setItem(row, 0, name_item)

            # Empty Stats columns (as requested)
            self.table.setItem(row, 1, QTableWidgetItem(""))
            self.table.setItem(row, 2, QTableWidgetItem(""))
            self.table.setItem(row, 3, QTableWidgetItem(""))

            # Sheet Button
            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(2, 2, 2, 2)
            btn = QPushButton("📄")
            btn.setStyleSheet("background-color: #B0BEC5; border: none; border-radius: 3px;")
            btn.setCursor(Qt.PointingHandCursor)

            # Передаємо дані токена у діалог
            token_data = tokens.get(uid, {})
            # Важливо: використовуємо lambda з фіксацією змінних
            btn.clicked.connect(lambda ch=False, u=uid, n=name, d=token_data: self.show_details_requested.emit(u, n, d))

            btn_layout.addWidget(btn)
            self.table.setCellWidget(row, 4, btn_widget)