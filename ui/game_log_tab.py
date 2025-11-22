from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QListWidgetItem,
    QLabel, QGroupBox, QHBoxLayout
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont


class GameLogTab(QWidget):
    """
    Вкладка для відображення журналу подій гри.
    Підтримує два режими: Player (фільтрує за персонажем) та DM (бачить все).
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.log_data = self._generate_mock_logs()  # Фіктивні дані для прикладу

        main_layout = QVBoxLayout(self)

        # Заголовок
        header_label = QLabel("Журнал Ігрових Подій (Game Log)")
        header_label.setFont(QFont("Arial", 16, QFont.Bold))
        header_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(header_label)

        # QListWidget для відображення логів
        self.log_list = QListWidget()
        self.log_list.setFont(QFont("Monospace", 10))
        main_layout.addWidget(self.log_list)

        # Мітка, що показує поточний режим
        self.mode_label = QLabel("Режим: Очікування...")
        self.mode_label.setStyleSheet("padding: 5px; background-color: #EEE; border-radius: 5px;")
        main_layout.addWidget(self.mode_label)

        # Ініціалізація без логів
        self.load_logs(is_dm=False, character_name="NONE")

    def _generate_mock_logs(self):
        """Створення фіктивних логів для демонстрації."""
        return [
            {"type": "WORLD", "text": "Світ: Насувається темна хмара, віщуючи бурю.", "source": "World"},
            {"type": "PLAYER", "text": "Воїн (Alistair) наносить 12 шкоди по гобліну.", "source": "Alistair",
             "color": "#2196F3"},
            {"type": "PLAYER", "text": "Маг (Elora) провалює кидок на Мудрість (WIS).", "source": "Elora",
             "color": "#FFC107"},
            {"type": "WORLD", "text": "Світ: Гоблін тікає, залишаючи за собою кривавий слід.", "source": "World"},
            {"type": "PLAYER", "text": "Воїн (Alistair) успішно робить чек Спритності (DEX) на 17.",
             "source": "Alistair", "color": "#2196F3"},
            {"type": "DM", "text": "DM: Встановлено складність (DC) 15 для наступного кидка.", "source": "DM",
             "color": "#f44336"},
            {"type": "PLAYER", "text": "Маг (Elora) кидає Вогняну Кулю (Fireball)!", "source": "Elora",
             "color": "#FFC107"},
        ]

    def load_logs(self, is_dm: bool, character_name: str):
        """
        Завантажує логи, фільтруючи їх залежно від режиму (DM/Player).

        :param is_dm: Якщо True, відображаються всі логи.
        :param character_name: Ім'я персонажа, якщо це режим гравця.
        """
        self.log_list.clear()

        if is_dm:
            self.mode_label.setText("Режим: Майстер Підземель (DM) - ВСІ ЛОГИ")
            self.mode_label.setStyleSheet(
                "padding: 5px; background-color: #F8D7DA; color: #721C24; border-radius: 5px; font-weight: bold;")
            logs_to_display = self.log_data
        else:
            self.mode_label.setText(f"Режим: Гравець - {character_name}")
            self.mode_label.setStyleSheet(
                "padding: 5px; background-color: #D4EDDA; color: #155724; border-radius: 5px; font-weight: bold;")

            # Фільтруємо: показуємо лише WORLD та логи поточного персонажа
            logs_to_display = [
                log for log in self.log_data
                if log["type"] == "WORLD" or log["source"] == character_name
            ]

        # Відображення логів у QListWidget
        if not logs_to_display:
            QListWidgetItem("Журнал порожній. Розпочніть пригоду!", self.log_list)
            return

        for log in logs_to_display:
            text = f"[{log.get('source', 'System')}] {log['text']}"
            item = QListWidgetItem(text, self.log_list)

            # Встановлення кольору тексту для кращої візуалізації
            color_hex = log.get('color')
            if color_hex:
                item.setForeground(QColor(color_hex))

            # Світло-сірий для логів світу
            elif log.get('type') == 'WORLD':
                item.setForeground(QColor("#6c757d"))

            # Червоний для DM-коментарів
            elif log.get('type') == 'DM':
                item.setForeground(QColor("#f44336"))