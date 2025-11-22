import json
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QTextEdit, QComboBox, QGridLayout, QGroupBox, QMessageBox
)
from core.data_manager import DataManager


class ItemCreatorTab(QWidget):
    """
    Вкладка для створення, редагування та каталогізації ігрових предметів (приватні дані DM).
    """

    def __init__(self, dm: DataManager, parent=None):
        super().__init__(parent)
        self.dm = dm

        main_layout = QVBoxLayout(self)

        header = QLabel("<h1>✨ Створення Ігрового Предмета</h1>")
        header.setStyleSheet("color: #00796B;")
        main_layout.addWidget(header)

        # ---------------------------------------------------------------------
        # Форма створення
        # ---------------------------------------------------------------------
        form_group = QGroupBox("Деталі Предмета")
        form_group.setStyleSheet("QGroupBox { font-weight: bold; color: #1B5E20; }")
        form_layout = QGridLayout(form_group)

        # 1. Назва
        form_layout.addWidget(QLabel("Назва Предмета:"), 0, 0)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Наприклад: Меч Вічної Зорі")
        form_layout.addWidget(self.name_input, 0, 1)

        # 2. Тип
        form_layout.addWidget(QLabel("Тип:"), 1, 0)
        self.type_selector = QComboBox()
        self.type_selector.addItems(["Зброя", "Броня", "Зілля", "Магічний предмет", "Звичайний предмет"])
        form_layout.addWidget(self.type_selector, 1, 1)

        # 3. Рідкість
        form_layout.addWidget(QLabel("Рідкість:"), 2, 0)
        self.rarity_selector = QComboBox()
        self.rarity_selector.addItems(["Звичайний", "Незвичайний", "Рідкісний", "Епічний", "Легендарний"])
        form_layout.addWidget(self.rarity_selector, 2, 1)

        # 4. Опис
        form_layout.addWidget(QLabel("Опис:"), 3, 0)
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Детальний опис та історія предмета...")
        self.description_input.setMinimumHeight(100)
        form_layout.addWidget(self.description_input, 3, 1)

        # 5. Властивості/Ефекти
        form_layout.addWidget(QLabel("Властивості (JSON):"), 4, 0)
        self.properties_input = QTextEdit()
        self.properties_input.setPlaceholderText('Наприклад: {"Damage": "1d8+2", "Effect": "Fire Resistance"}')
        self.properties_input.setMinimumHeight(80)
        form_layout.addWidget(self.properties_input, 4, 1)

        form_group.setLayout(form_layout)
        main_layout.addWidget(form_group)

        # ---------------------------------------------------------------------
        # Кнопки Дій
        # ---------------------------------------------------------------------
        self.save_button = QPushButton("💾 Зберегти Предмет")
        self.save_button.setStyleSheet(
            "background-color: #00796B; color: white; padding: 15px; border-radius: 8px; font-weight: bold;")
        self.save_button.clicked.connect(self._save_item)

        main_layout.addWidget(self.save_button)
        main_layout.addStretch(1)

    def _save_item(self):
        """Збирає дані форми та зберігає предмет через DataManager."""
        name = self.name_input.text().strip()
        description = self.description_input.toPlainText().strip()
        type_val = self.type_selector.currentText()
        rarity_val = self.rarity_selector.currentText()
        properties_json = self.properties_input.toPlainText().strip()

        if not name or not description:
            QMessageBox.warning(self, "Помилка", "Назва та Опис є обов'язковими.")
            return

        properties_data = {}
        if properties_json:
            try:
                properties_data = json.loads(properties_json)
            except json.JSONDecodeError:
                QMessageBox.critical(self, "Помилка JSON", "Властивості мають бути у коректному JSON форматі.")
                return

        item_data = {
            "name": name,
            "type": type_val,
            "rarity": rarity_val,
            "description": description,
            "properties": properties_data,
            "createdBy": self.dm.get_user_id()
        }

        if self.dm.save_item(item_data):
            QMessageBox.information(self, "Успіх", f"Предмет '{name}' успішно збережено у вашому каталозі.")
            self._clear_form()
        else:
            QMessageBox.critical(self, "Помилка", "Не вдалося зберегти предмет через DataManager.")

    def _clear_form(self):
        """Очищує форму після збереження."""
        self.name_input.clear()
        self.description_input.clear()
        self.properties_input.clear()
        self.type_selector.setCurrentIndex(0)
        self.rarity_selector.setCurrentIndex(0)