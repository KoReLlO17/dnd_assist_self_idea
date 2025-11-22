from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QStackedWidget, QMessageBox
)
from PySide6.QtCore import Qt

# Імпортуємо DataManager
try:
    from core.data_manager import DataManager
except ImportError:
    print("CRITICAL ERROR: Could not import DataManager")


    class DataManager:
        pass  # Fallback

# Імпорти UI (з fallback для запуску з різних папок)
try:
    from ui.player.character_creation_card_tab import CharacterCreationCardTab
    from ui.player.player_menu import PlayerMenu
except ImportError:
    from character_creation_card_tab import CharacterCreationCardTab
    from player_menu import PlayerMenu


class PlayerMainWindow(QMainWindow):
    """
    Головне вікно для гравця.
    Виправлено валідацію вводу для підтримки IP-адрес.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Гравець: Панель Пригод")
        self.resize(900, 700)

        self.dm = DataManager()
        self.current_character_data = None

        self.setStyleSheet("""
            QMainWindow { background-color: #ECEFF1; }
            QStackedWidget { background-color: white; border: 1px solid #CFD8DC; border-radius: 8px; }
            QLabel { color: #263238; font-size: 14px; }
            QLineEdit { border: 1px solid #90A4AE; padding: 10px; border-radius: 5px; font-size: 14px; }
            QPushButton {
                background-color: #00BCD4;
                color: white;
                padding: 12px 25px;
                border-radius: 6px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #00ACC1; }
            #WelcomeHeader { color: #00ACC1; font-size: 28px; font-weight: bold; }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        self.stacked_widget = QStackedWidget()
        main_layout.addWidget(self.stacked_widget, 1)

        # Екрани
        self.join_widget = self._create_join_widget()
        self.stacked_widget.addWidget(self.join_widget)

        self.char_creation_tab = None
        self.player_menu = None

    def _create_join_widget(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignCenter)

        header = QLabel("Ласкаво просимо до D&D Assistant")
        header.setObjectName("WelcomeHeader")
        layout.addWidget(header, alignment=Qt.AlignCenter)

        uid_label = QLabel(f"Ваш UID: {self.dm.get_user_id()}")
        uid_label.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(uid_label, alignment=Qt.AlignCenter)

        layout.addSpacing(30)

        id_hbox = QHBoxLayout()
        id_hbox.setAlignment(Qt.AlignCenter)

        lbl = QLabel("Рядок підключення:")
        lbl.setToolTip("Введіть 'IP/ID' (наприклад 192.168.0.1/SESS_AB12) або просто ID для локальної гри.")
        id_hbox.addWidget(lbl)

        self.session_id_input = QLineEdit()
        # Оновлена підказка
        self.session_id_input.setPlaceholderText("Приклад: 192.168.1.5/SESS_X1Y2")
        self.session_id_input.setFixedWidth(350)
        id_hbox.addWidget(self.session_id_input)

        layout.addLayout(id_hbox)

        self.join_button = QPushButton("🔗 ПРИЄДНАТИСЯ")
        self.join_button.setFixedWidth(200)
        self.join_button.clicked.connect(self._attempt_join)
        layout.addWidget(self.join_button, alignment=Qt.AlignCenter)

        return widget

    def _attempt_join(self):
        # Отримуємо "сирий" рядок (не переводимо в upper() одразу, бо IP може мати літери, хоча IPv4 ні)
        raw_input = self.session_id_input.text().strip()

        connect_str = ""

        # --- НОВА ЛОГІКА ВАЛІДАЦІЇ ---
        if "/" in raw_input:
            # Якщо є слеш, значить це формат IP/ID
            parts = raw_input.split("/")
            if len(parts) != 2:
                QMessageBox.warning(self, "Формат", "Невірний формат. Має бути: IP_АДРЕСА/ID_СЕСІЇ")
                return

            ip_part = parts[0].strip()
            id_part = parts[1].strip().upper()

            if not id_part.startswith("SESS_"):
                QMessageBox.warning(self, "Помилка ID", "ID сесії (частина після /) має починатися з 'SESS_'")
                return

            # Збираємо правильний рядок для DataManager
            connect_str = f"{ip_part}/{id_part}"

        else:
            # Якщо слеша немає, вважаємо що це тільки ID (для локалхосту)
            id_part = raw_input.upper()
            if not id_part.startswith("SESS_"):
                QMessageBox.warning(self, "Помилка",
                                    "Якщо ви вводите тільки ID, він має починатися з 'SESS_'.\n"
                                    "Для мережевої гри введіть: IP/ID")
                return
            connect_str = id_part

        # Спроба підключення
        if self.dm.join_session(connect_str):
            QMessageBox.information(self, "Успіх", f"Підключено до {connect_str}")
            self._switch_to_creation()
        else:
            QMessageBox.critical(self, "Помилка Підключення",
                                 f"Не вдалося підключитися до '{connect_str}'.\n"
                                 f"1. Перевірте правильність IP та ID.\n"
                                 f"2. Переконайтеся, що ДМ запустив сесію.\n"
                                 f"3. Перевірте, чи не блокує брандмауер (Firewall) з'єднання.")

    def _switch_to_creation(self):
        if self.char_creation_tab is None:
            self.char_creation_tab = CharacterCreationCardTab(dm=self.dm)
            self.char_creation_tab.character_saved.connect(self._switch_to_player_menu)
            self.stacked_widget.addWidget(self.char_creation_tab)

        self.stacked_widget.setCurrentWidget(self.char_creation_tab)
        current_session = self.dm.get_current_session()
        self.setWindowTitle(f"Створення Персонажа - {current_session}")

    def _switch_to_player_menu(self, char_data: dict):
        self.current_character_data = char_data

        if self.player_menu is not None:
            self.stacked_widget.removeWidget(self.player_menu)

        self.player_menu = PlayerMenu(dm=self.dm, char_data=char_data)
        self.stacked_widget.addWidget(self.player_menu)
        self.stacked_widget.setCurrentWidget(self.player_menu)

        current_session = self.dm.get_current_session()
        name = char_data.get('name', 'Hero')
        self.setWindowTitle(f"{name} - Сесія {current_session}")