from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QComboBox, QPushButton,
    QGroupBox, QMessageBox, QSplitter
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont
from core.data_manager import DataManager


class InventoryManagerTab(QWidget):
    """
    Вкладка для ДМа: Управління предметами та видача їх гравцям.
    """

    def __init__(self, dm: DataManager, parent=None):
        super().__init__(parent)
        self.dm = dm
        self.master_items = self.dm.get_master_item_dataset()

        # --- TEMNA TEMA ---
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
                color: #007ACC;
            }

            QLineEdit, QComboBox {
                background-color: #3C3C3C;
                color: white;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 6px;
            }

            QListWidget {
                background-color: #252526;
                color: #E0E0E0;
                border: 1px solid #3E3E42;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background-color: #37373D;
                color: #FFF;
            }
            QListWidget::item:hover {
                background-color: #2A2D2E;
            }

            QPushButton {
                background-color: #0E639C;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #1177BB; }
            QPushButton:disabled { background-color: #333; color: #666; }

            #DetailsLabel {
                background-color: #2D2D2D;
                padding: 15px;
                border-radius: 6px;
                border: 1px solid #3E3E42;
                font-size: 14px;
                line-height: 1.4;
            }

            QSplitter::handle { background-color: #3E3E42; }
        """)

        main_layout = QVBoxLayout(self)

        header = QLabel("<h2>📦 Скарбниця та Видача Предметів</h2>")
        header.setStyleSheet("color: #4FC3F7;")
        main_layout.addWidget(header)

        # Пошук
        filter_group = QGroupBox("Пошук")
        filter_layout = QHBoxLayout(filter_group)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Назва предмета...")
        self.search_input.textChanged.connect(self._refresh_item_list)

        self.type_filter = QComboBox()
        self.type_filter.addItems(["Всі типи", "Weapon", "Armor", "Consumable", "Gear"])
        self.type_filter.currentTextChanged.connect(self._refresh_item_list)

        filter_layout.addWidget(self.search_input)
        filter_layout.addWidget(self.type_filter)
        main_layout.addWidget(filter_group)

        # Спліттер
        splitter = QSplitter(Qt.Horizontal)

        # Список
        self.item_list_widget = QListWidget()
        self.item_list_widget.itemClicked.connect(self._on_item_selected)
        splitter.addWidget(self.item_list_widget)

        # Деталі
        details_widget = QWidget()
        details_layout = QVBoxLayout(details_widget)

        self.item_details_label = QLabel("<i>Оберіть предмет зі списку</i>")
        self.item_details_label.setObjectName("DetailsLabel")
        self.item_details_label.setWordWrap(True)
        self.item_details_label.setAlignment(Qt.AlignTop)
        details_layout.addWidget(self.item_details_label)

        # Видача
        grant_group = QGroupBox("Надати Гравцю")
        grant_layout = QVBoxLayout(grant_group)

        self.player_selector = QComboBox()
        grant_layout.addWidget(QLabel("Оберіть гравця:"))
        grant_layout.addWidget(self.player_selector)

        self.grant_btn = QPushButton("🎁 Відправити в інвентар")
        self.grant_btn.clicked.connect(self._grant_item)
        self.grant_btn.setEnabled(False)
        grant_layout.addWidget(self.grant_btn)

        details_layout.addWidget(grant_group)
        details_layout.addStretch()

        splitter.addWidget(details_widget)
        splitter.setSizes([400, 300])
        main_layout.addWidget(splitter)

        self.timer = QTimer(self)
        self.timer.setInterval(3000)
        self.timer.timeout.connect(self._update_players_combo)
        self.timer.start()

        self._refresh_item_list()

    def _refresh_item_list(self):
        self.item_list_widget.clear()
        search_text = self.search_input.text().lower()
        filter_type = self.type_filter.currentText()

        for key, data in self.master_items.items():
            name = data.get("name", "Unknown")
            itype = data.get("type", "Misc")

            if search_text and search_text not in name.lower(): continue
            if filter_type != "Всі типи" and itype != filter_type: continue

            item = QListWidgetItem(f"{name} [{itype}]")
            item.setData(Qt.UserRole, key)

            # Кольори для темної теми
            if itype == "Weapon":
                item.setForeground(QColor("#FF8A80"))  # Red-ish
            elif itype == "Armor":
                item.setForeground(QColor("#82B1FF"))  # Blue-ish
            elif itype == "Consumable":
                item.setForeground(QColor("#B9F6CA"))  # Green-ish
            else:
                item.setForeground(QColor("#E0E0E0"))

            self.item_list_widget.addItem(item)

    def _on_item_selected(self, item):
        key = item.data(Qt.UserRole)
        data = self.master_items.get(key)

        # HTML для темної теми
        info = f"<h3 style='color:#4FC3F7'>{data.get('name')}</h3>"
        info += f"<b>Type:</b> <span style='color:#B0BEC5'>{data.get('type')}</span><br>"
        if "damage" in data: info += f"<b>Damage:</b> <span style='color:#FF8A80'>{data.get('damage')}</span><br>"
        if "ac" in data: info += f"<b>AC:</b> <span style='color:#82B1FF'>{data.get('ac')}</span><br>"
        if "prop" in data: info += f"<b>Props:</b> {data.get('prop')}<br>"
        if "effect" in data: info += f"<b>Effect:</b> <span style='color:#B9F6CA'>{data.get('effect')}</span><br>"

        self.item_details_label.setText(info)
        self.grant_btn.setEnabled(True)

    def _update_players_combo(self):
        session_id = self.dm.get_current_session()
        if not session_id: return

        players = self.dm.get_session_players(session_id)
        current_selection = self.player_selector.currentData()

        self.player_selector.blockSignals(True)
        self.player_selector.clear()

        if not players:
            self.player_selector.addItem("Немає гравців", None)
            self.player_selector.setEnabled(False)
        else:
            self.player_selector.setEnabled(True)
            for uid, p_data in players.items():
                self.player_selector.addItem(p_data.get("name", "Unknown"), uid)

        if current_selection:
            idx = self.player_selector.findData(current_selection)
            if idx >= 0: self.player_selector.setCurrentIndex(idx)

        self.player_selector.blockSignals(False)

    def _grant_item(self):
        target_uid = self.player_selector.currentData()
        if not target_uid:
            QMessageBox.warning(self, "Помилка", "Оберіть гравця!")
            return

        selected_list_item = self.item_list_widget.currentItem()
        if not selected_list_item: return

        item_key = selected_list_item.data(Qt.UserRole)
        item_data = self.master_items.get(item_key)

        if self.dm.grant_item_to_player(target_uid, item_data):
            QMessageBox.information(self, "Успіх", f"Предмет '{item_data['name']}' відправлено!")
        else:
            QMessageBox.critical(self, "Помилка", "Не вдалося надати предмет.")