from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTreeWidget, QTreeWidgetItem,
    QPushButton, QHBoxLayout, QLineEdit, QTextEdit, QGroupBox,
    QMessageBox, QInputDialog
)
from PySide6.QtCore import QDateTime
from core.data_manager import DataManager


class ScenarioTreeTab(QWidget):
    """
    Вкладка для детального планування сценаріїв (темна тема).
    """

    def __init__(self, dm: DataManager, parent=None):
        super().__init__(parent)
        self.dm = dm

        self.setStyleSheet("""
            QWidget { background-color: #1E1E1E; color: #E0E0E0; font-family: 'Segoe UI'; }

            QGroupBox {
                border: 1px solid #3E3E42;
                border-radius: 6px;
                margin-top: 10px;
                background-color: #252526;
                font-weight: bold;
                color: #CCC;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #FF7043; /* Orange accent */
            }

            QTreeWidget {
                background-color: #252526;
                color: #E0E0E0;
                border: 1px solid #3E3E42;
                border-radius: 4px;
            }
            QTreeWidget::item:selected {
                background-color: #3E3E42;
                color: #FFF;
            }
            QHeaderView::section {
                background-color: #2D2D2D;
                color: #CCC;
                padding: 4px;
                border: 1px solid #3E3E42;
            }

            QLineEdit {
                background-color: #3C3C3C;
                color: white;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 6px;
            }

            QPushButton {
                background-color: #D84315; /* Dark Orange */
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #F4511E; }
        """)

        main_layout = QVBoxLayout(self)

        header = QLabel("<h1>🌳 Планувальник Сценаріїв</h1>")
        header.setStyleSheet("color: #FF7043;")
        main_layout.addWidget(header)

        # --- Дерево ---
        tree_group = QGroupBox("Структура Сценарію")
        tree_layout = QVBoxLayout(tree_group)

        self.scenario_tree = QTreeWidget()
        self.scenario_tree.setHeaderLabels(["Вузол", "Тип"])
        self.scenario_tree.setColumnCount(2)

        # Demo content
        root = QTreeWidgetItem(self.scenario_tree, ["Кампанія: Темна Вежа", "ROOT"])
        loc1 = QTreeWidgetItem(root, ["Таверна", "Location"])
        QTreeWidgetItem(loc1, ["Розмова з трактирником", "Social"])
        QTreeWidgetItem(root, ["Підземелля", "Dungeon"])
        root.setExpanded(True)

        tree_layout.addWidget(self.scenario_tree)

        # Кнопки
        tree_buttons_hbox = QHBoxLayout()
        self.add_node_btn = QPushButton("➕ Додати")
        self.remove_node_btn = QPushButton("🗑️ Видалити")
        tree_buttons_hbox.addWidget(self.add_node_btn)
        tree_buttons_hbox.addWidget(self.remove_node_btn)
        tree_layout.addLayout(tree_buttons_hbox)

        self.add_node_btn.clicked.connect(self._add_node)
        self.remove_node_btn.clicked.connect(self._remove_node)

        main_layout.addWidget(tree_group)

        # --- Збереження ---
        save_group = QGroupBox("Метадані")
        save_layout = QVBoxLayout(save_group)

        save_layout.addWidget(QLabel("Назва:"))
        self.title_input = QLineEdit()
        self.title_input.setText("Новий Сценарій")
        save_layout.addWidget(self.title_input)

        self.save_button = QPushButton("💾 Зберегти Дерево")
        self.save_button.clicked.connect(self._save_tree)

        save_layout.addWidget(self.save_button)
        main_layout.addWidget(save_group)

    def _add_node(self):
        selected_item = self.scenario_tree.currentItem()
        parent = selected_item if selected_item else self.scenario_tree.invisibleRootItem()

        # Стилізація стандартного діалогу трохи складна, тому просто викликаємо
        node_name, ok = QInputDialog.getText(self, "Додати Вузол", "Назва:")
        if ok and node_name:
            node_type, ok_type = QInputDialog.getItem(
                self, "Тип", "Тип вузла:",
                ["Location", "Event", "Combat", "NPC", "Loot"], 0, False
            )
            if ok_type:
                QTreeWidgetItem(parent, [node_name, node_type])
                parent.setExpanded(True)

    def _remove_node(self):
        selected_item = self.scenario_tree.currentItem()
        if selected_item:
            parent = selected_item.parent()
            if parent:
                parent.removeChild(selected_item)
            else:
                self.scenario_tree.takeTopLevelItem(self.scenario_tree.indexOfTopLevelItem(selected_item))

    def _get_tree_structure(self, parent_item: QTreeWidgetItem) -> list:
        structure = []
        for i in range(parent_item.childCount()):
            child_item = parent_item.child(i)
            node = {
                "name": child_item.text(0),
                "type": child_item.text(1),
                "children": self._get_tree_structure(child_item)
            }
            structure.append(node)
        return structure

    def _save_tree(self):
        title = self.title_input.text().strip()
        if not title:
            QMessageBox.warning(self, "Помилка", "Введіть назву.")
            return

        root = self.scenario_tree.invisibleRootItem()
        tree_structure = self._get_tree_structure(root)

        # Тут можна додати логіку збереження в файл або БД
        QMessageBox.information(self, "Успіх", f"Сценарій '{title}' збережено (локально)!")