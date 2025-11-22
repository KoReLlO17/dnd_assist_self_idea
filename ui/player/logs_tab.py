from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit, QGroupBox, QHBoxLayout
from PySide6.QtCore import Qt, QTimer, QDateTime
from PySide6.QtGui import QColor
from core.data_manager import DataManager


class LogsTab(QWidget):
    """
    Вкладка логів.
    """

    def __init__(self, dm: DataManager, parent=None):
        super().__init__(parent)
        self.dm = dm
        self.seen_log_ids = set()
        self.first_load = True
        self.my_user_id = self.dm.get_user_id()
        self.session_dm_id = None

        layout = QVBoxLayout(self)

        top_layout = QHBoxLayout()
        header = QLabel("<h2>📜 Логи Сесії</h2>")
        header.setStyleSheet("color: #8D6E63;")
        top_layout.addWidget(header)

        self.status_label = QLabel("⚪ Підключення...")
        self.status_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.status_label.setStyleSheet("font-weight: bold; color: gray;")
        top_layout.addWidget(self.status_label)

        layout.addLayout(top_layout)

        log_group = QGroupBox("Журнал Пригод")
        log_group.setStyleSheet("QGroupBox { font-weight: bold; color: #5D4037; }")
        log_layout = QVBoxLayout(log_group)

        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setFontPointSize(10)
        self.log_display.setText("<i>Очікування даних від сервера...</i>")
        log_layout.addWidget(self.log_display)

        layout.addWidget(log_group)

        self.timer = QTimer(self)
        self.timer.setInterval(2000)
        self.timer.timeout.connect(self._fetch_updates)
        self.timer.start()

    def _fetch_updates(self):
        session_id = self.dm.get_current_session()
        if not session_id:
            self.status_label.setText("⚪ Немає сесії")
            return

        if not self.session_dm_id:
            self.session_dm_id = self.dm.get_dm_id(session_id)

        # ВИПРАВЛЕНО: Тепер ми отримуємо список, а не передаємо callback
        logs = self.dm.get_session_updates(session_id)

        if logs is None:
            self.status_label.setText("🔴 Втрачено зв'язок")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
            return

        self.status_label.setText("🟢 Онлайн")
        self.status_label.setStyleSheet("color: green; font-weight: bold;")

        if self.first_load:
            self.log_display.clear()
            self.first_load = False
            if not logs:
                self.log_display.setText("<i>Журнал поки що порожній.</i>")

        for log_data in logs:
            self._handle_single_log(log_data)

    def _handle_single_log(self, update_data: dict):
        timestamp = update_data.get('timestamp', '')
        content = update_data.get('content', '')
        log_id = f"{timestamp}_{content}"

        if log_id in self.seen_log_ids:
            return

        self.seen_log_ids.add(log_id)

        if "Журнал поки що порожній" in self.log_display.toPlainText():
            self.log_display.clear()

        type_ = update_data.get('type', 'MESSAGE')
        sender_id = update_data.get('sender_id', 'UNKNOWN')
        is_secret = update_data.get('is_secret', False)

        is_my_event = (sender_id == self.my_user_id)
        # Якщо sender_id == SYSTEM, це серверне повідомлення, його бачать всі
        is_system_event = (sender_id == "SYSTEM")
        is_dm_event = (sender_id == self.session_dm_id)

        # 1. Якщо це секрет і я не автор -> ПРИХОВАТИ
        if is_secret and not is_my_event:
            return

        is_world_event = type_ in ["SCENE", "SCENE_CHANGE", "SCENE_UPDATE", "STORY", "COMBAT_START", "COMBAT",
                                   "DM_ANNOUNCEMENT", "DM_ROLL", "JOIN"]

        # 2. Показуємо якщо: Це світ, або це я, або це ДМ, або це система
        if not (is_world_event or is_my_event or is_dm_event or is_system_event):
            return

        color = "black"
        prefix = ""
        secret_prefix = "🔒 " if is_secret else ""

        if type_ in ["SCENE", "SCENE_CHANGE", "SCENE_UPDATE", "STORY"]:
            color = "#2E7D32"
            prefix = "🌍 [СВІТ]"
            content = f"<b>{content}</b>"
        elif type_ in ["COMBAT_START", "COMBAT"]:
            color = "#C62828"
            prefix = "⚔️ [БІЙ]"
        elif type_ == "JOIN":
            color = "#0277BD"
            prefix = "👤 [СИСТЕМА]"
        elif type_ == "DM_ANNOUNCEMENT":
            color = "#6A1B9A"
            prefix = "📣 [DM]"
        elif type_ == "DM_ROLL":
            color = "#7B1FA2"
            prefix = f"{secret_prefix}🎲 [DM КИДОК]"
        elif is_my_event:
            color = "#424242"
            prefix = f"{secret_prefix}👉 [Я]"

        log_entry = (
            f"<span style='color: gray; font-size: 9pt;'>[{timestamp}]</span> "
            f"<span style='font-weight: bold; color: {color};'>{prefix}</span> "
            f"{content}<br>"
        )
        self.log_display.append(log_entry)
        self.log_display.verticalScrollBar().setValue(self.log_display.verticalScrollBar().maximum())

    def closeEvent(self, event):
        self.timer.stop()
        super().closeEvent(event)