from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QListWidget,
    QListWidgetItem, QHBoxLayout, QPushButton, QMessageBox,
    QLabel, QComboBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont

# Імпортуємо DataManager коректно
from core.data_manager import DataManager


class InventoryTab(QWidget):
    """
    Окрема вкладка для управління інвентарем гравця.
    """

    def __init__(self, is_dm=False, dm: DataManager = None, parent=None):
        super().__init__(parent)

        self.is_dm = is_dm
        # Якщо DM не передано, отримуємо інстанс
        self.dm = dm if dm else DataManager()

        self.current_character_id = self.dm.get_user_id()
        self.master_items_data = self.dm.get_master_item_dataset()

        self.setStyleSheet("""
            QListWidget { 
                border: 1px solid #C0C0C0; 
                border-radius: 5px; 
                min-height: 200px;
                background-color: #f7f7f7;
            }
            QPushButton { 
                padding: 10px; 
                border-radius: 8px; 
                font-weight: bold;
            }
            QPushButton:hover { filter: brightness(1.1); }
            QPushButton:disabled { background-color: #bdbdbd; color: #757575; }
            #EquipButton { background-color: #2196F3; color: white; }
            #UseButton { background-color: #FF9800; color: white; }
            #GrantButton { background-color: #4CAF50; color: white; }
        """)

        main_layout = QVBoxLayout(self)

        # UI для DM
        if self.is_dm:
            dm_label = QLabel("<h2>👁️ Режим DM: Видача предметів</h2>")
            dm_label.setStyleSheet("color: #D84315;")
            main_layout.addWidget(dm_label)
            self._setup_dm_grant_ui(main_layout)

        # Список
        self.item_list = QListWidget()
        self.item_list.setFont(QFont("Segoe UI", 10))
        main_layout.addWidget(self.item_list)

        # Кнопки для Гравця
        if not self.is_dm:
            action_box = QGroupBox("Дії")
            action_layout = QHBoxLayout(action_box)

            self.equip_button = QPushButton("⚔️ Спорядити / Зняти")
            self.equip_button.setObjectName("EquipButton")
            self.equip_button.clicked.connect(self._handle_equip)

            self.use_button = QPushButton("🧪 Використати")
            self.use_button.setObjectName("UseButton")
            self.use_button.clicked.connect(self._handle_use)

            action_layout.addWidget(self.equip_button)
            action_layout.addWidget(self.use_button)
            main_layout.addWidget(action_box)

            self.item_list.currentItemChanged.connect(self._update_action_buttons)
            self.equip_button.setEnabled(False)
            self.use_button.setEnabled(False)

        self._load_inventory_items()
        main_layout.addStretch(1)

    def _setup_dm_grant_ui(self, layout):
        """Блок видачі предметів для DM."""
        grant_box = QGroupBox("Каталог")
        grant_layout = QVBoxLayout(grant_box)

        self.item_select_combo = QComboBox()
        if self.master_items_data:
            for k, v in self.master_items_data.items():
                self.item_select_combo.addItem(f"{v['name']} ({v['type']})", k)

        grant_layout.addWidget(self.item_select_combo)

        btn = QPushButton("Надати предмет")
        btn.setObjectName("GrantButton")
        btn.clicked.connect(lambda: QMessageBox.information(self, "DM", "Предмет надано (Mock)"))
        grant_layout.addWidget(btn)
        layout.addWidget(grant_box)

    def _load_inventory_items(self):
        self.item_list.clear()
        # Отримуємо інвентар (у демо-режимі він статичний у DataManager)
        inventory = self.dm.get_inventory(self.current_character_id)

        for item_key, item_data in inventory.items():
            name = item_data.get('name', '???')
            i_type = item_data.get('type', 'Misc')
            is_equipped = item_data.get('is_equipped', False)

            status = " [ЕКІПОВАНО]" if is_equipped else ""
            display_text = f"[{i_type}] {name}{status}"

            list_item = QListWidgetItem(display_text)
            list_item.setData(Qt.UserRole, item_data)

            if is_equipped:
                list_item.setForeground(QColor("green"))
                list_item.setFont(QFont("Segoe UI", 10, QFont.Bold))

            self.item_list.addItem(list_item)

    def _update_action_buttons(self):
        if self.is_dm: return
        item = self.item_list.currentItem()
        if not item:
            self.equip_button.setEnabled(False)
            self.use_button.setEnabled(False)
            return

        data = item.data(Qt.UserRole)
        i_type = data.get('type')

        self.equip_button.setEnabled(i_type == "Equippable")
        self.use_button.setEnabled(i_type == "Consumable")

    def _handle_equip(self):
        QMessageBox.information(self, "Інвентар", "Логіка спорядження (змінюється статус в БД)")
        # Тут мав би бути виклик self.dm.equip_item(...) і потім _load_inventory_items()

    def _handle_use(self):
        QMessageBox.information(self, "Інвентар", "Логіка використання (видалення зі списку)")