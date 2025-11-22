from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit, QComboBox, QHBoxLayout, \
    QGroupBox, QMessageBox, QCheckBox
from PySide6.QtCore import Signal
from core.data_manager import DataManager


class ScenarioTab(QWidget):
    """
    Вкладка для перегляду та надсилання оновлень сценарію під час сесії.
    Додано опцію "Прихований кидок".
    """

    def __init__(self, dm: DataManager, parent=None):
        super().__init__(parent)
        self.dm = dm
        self.is_session_active = False

        layout = QVBoxLayout(self)

        # Статус
        self.status_group = QGroupBox("Поточний Сценарій")
        self.status_group.setStyleSheet("QGroupBox { font-weight: bold; color: #1B5E20; }")
        status_layout = QVBoxLayout(self.status_group)

        self.session_id_label = QLabel("ID Сесії: <b>---</b>")
        self.active_status_label = QLabel("Статус: <b>НЕАКТИВНА</b>")
        self.active_status_label.setStyleSheet("color: red; font-size: 14px;")

        status_layout.addWidget(self.session_id_label)
        status_layout.addWidget(self.active_status_label)
        layout.addWidget(self.status_group)

        # Оновлення
        update_group = QGroupBox("Надіслати Оновлення Гравцям")
        update_group.setStyleSheet("QGroupBox { font-weight: bold; color: #1B5E20; }")
        update_layout = QVBoxLayout(update_group)

        # Тип
        type_hbox = QHBoxLayout()
        type_hbox.addWidget(QLabel("Тип події:"))
        self.type_selector = QComboBox()
        self.type_selector.addItems(["MESSAGE (Опис)", "SCENE_CHANGE (Нова локація)", "COMBAT_START (Бій)", "DM_ANNOUNCEMENT (Оголошення)", "DM_ROLL (Кидок кубиків)"])
        self.type_selector.setStyleSheet("padding: 5px;")
        type_hbox.addWidget(self.type_selector)
        update_layout.addLayout(type_hbox)

        # Чекбокс "Приховано"
        self.secret_cb = QCheckBox("👁️ Приховано (Тільки для ДМ)")
        self.secret_cb.setStyleSheet("color: #D32F2F; font-weight: bold;")
        self.secret_cb.setToolTip("Якщо увімкнено, це повідомлення побачите тільки ви.")
        update_layout.addWidget(self.secret_cb)

        # Вміст
        self.update_content = QTextEdit()
        self.update_content.setPlaceholderText("Введіть текст події або результат кидка...")
        self.update_content.setMinimumHeight(150)
        update_layout.addWidget(self.update_content)

        # Кнопка
        self.send_button = QPushButton("▶️ Надіслати Оновлення")
        self.send_button.setStyleSheet(
            "background-color: #1E88E5; color: white; padding: 10px; border-radius: 6px; font-weight: bold;")
        self.send_button.clicked.connect(self._send_update)
        update_layout.addWidget(self.send_button)

        layout.addWidget(update_group)
        layout.addStretch(1)

        self.update_session_status(False)

    def update_session_status(self, is_active: bool):
        self.is_session_active = is_active
        session_id = self.dm.get_current_session()

        if is_active and session_id:
            self.session_id_label.setText(f"ID Сесії: <b>{session_id}</b>")
            self.active_status_label.setText("Статус: <b>АКТИВНА</b>")
            self.active_status_label.setStyleSheet("color: #2E7D32; font-size: 14px; font-weight: bold;")
            self.send_button.setEnabled(True)
        else:
            self.session_id_label.setText(f"ID Сесії: <b>{session_id if session_id else '---'}</b>")
            self.active_status_label.setText("Статус: <b>НЕАКТИВНА</b>")
            self.active_status_label.setStyleSheet("color: red; font-size: 14px; font-weight: bold;")
            self.send_button.setEnabled(False)

    def _send_update(self):
        session_id = self.dm.get_current_session()
        content = self.update_content.toPlainText().strip()
        type_text = self.type_selector.currentText().split(" (")[0]
        is_secret = self.secret_cb.isChecked()

        if not self.is_session_active or not session_id:
            QMessageBox.warning(self, "Помилка", "Сесія неактивна.")
            return

        if not content:
            QMessageBox.warning(self, "Помилка", "Порожній текст.")
            return

        if self.dm.push_session_update(session_id, content, type_text, is_secret=is_secret):
            status = " (Приховано)" if is_secret else ""
            QMessageBox.information(self, "Успіх", f"Оновлення надіслано!{status}")
            self.update_content.clear()
            # self.secret_cb.setChecked(False) # Можна скидати, а можна ні
        else:
            QMessageBox.critical(self, "Помилка", "Не вдалося надіслати.")