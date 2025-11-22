import sys
import os

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout,
    QLabel, QPushButton, QStackedWidget, QGridLayout
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont


from ui.player.character_creation_card_tab import CharacterCreationCardTab
from ui.player.character_display_tab import CharacterDisplayTab

class CharacterCreationCardTab(QWidget):
    character_saved = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(QLabel("ERROR: CharacterCreationCardTab not found. Check imports!"))
        btn = QPushButton("Зберегти персонажа (ERROR MOCK)")
        btn.clicked.connect(lambda: self.character_saved.emit("mock/error_data.json"))
        self.layout().addWidget(btn)


class CharacterDisplayTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(QLabel("ERROR: CharacterDisplayTab not found. Check imports!"))

    def load_character(self, file_path):
        print(f"Loading character from {file_path} in Display Tab (ERROR MOCK)")


# --------------------------
# ВІДЖЕТ: Головне меню (для вибору Player/DM)
# --------------------------
class MainMenuWidget(QWidget):
    """Віджет головного меню з вибором 'Player' та 'DM'."""
    player_selected = Signal()
    dm_selected = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)

        # Контейнер для кнопок, центрований на екрані
        content_widget = QWidget()
        content_layout = QGridLayout(content_widget)

        # Загальний стиль для кнопок меню
        button_style = "QPushButton { font-size: 20px; padding: 15px 30px; border: 2px solid #555; border-radius: 10px; background-color: #F0F0F0; }"

        # 1. Кнопка Player
        btn_player = QPushButton("Player")
        btn_player.setFont(QFont("Arial", 18))
        btn_player.setStyleSheet(button_style)
        btn_player.clicked.connect(self.player_selected.emit)

        # 2. Кнопка DM
        btn_dm = QPushButton("DM")
        btn_dm.setFont(QFont("Arial", 18))
        btn_dm.setStyleSheet(button_style)
        btn_dm.clicked.connect(self.dm_selected.emit)

        # 3. Додатковий елемент (Заглушка)
        btn_other = QPushButton("Інші інструменти")
        btn_other.setFont(QFont("Arial", 18))
        btn_other.setStyleSheet(button_style)
        btn_other.setEnabled(False)

        # Розміщення кнопок у сітці
        content_layout.addWidget(btn_player, 0, 0, Qt.AlignCenter)
        content_layout.addWidget(btn_dm, 1, 0, Qt.AlignCenter)
        content_layout.addWidget(btn_other, 2, 0, Qt.AlignCenter)

        # Додаємо сітку до головного вертикального макету і центруємо
        main_layout.addWidget(content_widget, alignment=Qt.AlignCenter)
        main_layout.addStretch(1)

    # --------------------------


# ГОЛОВНЕ ВІКНО: MainWindow
# --------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("D&D Character Assistant")
        self.setGeometry(100, 100, 1000, 800)

        # Головний віджет: QStackedWidget для навігації між секціями
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.setup_main_menu()
        self.setup_player_section()

    def setup_main_menu(self):
        """Створює віджет головного меню та додає його до StackedWidget (Індекс 0)."""
        self.main_menu = MainMenuWidget()
        self.stack.addWidget(self.main_menu)  # Індекс 0

        # Підключення сигналу для переходу на секцію Player
        self.main_menu.player_selected.connect(self.show_player_tabs)
        self.main_menu.dm_selected.connect(lambda: print("DM Section Not Implemented"))

    def setup_player_section(self):
        """Створює QTabWidget для секції Player (Індекс 1)."""

        # Контейнер для Player, включаючи кнопку "Home"
        player_container = QWidget()
        player_layout = QVBoxLayout(player_container)

        # Кнопка 'Головна' для повернення до меню
        self.home_button = QPushButton("🏠 Головне меню")
        self.home_button.clicked.connect(self.show_main_menu)
        self.home_button.setMaximumWidth(200)
        player_layout.addWidget(self.home_button, alignment=Qt.AlignLeft)

        # QTabWidget (містить CharacterCardTab та CharacterDisplayTab)
        self.tab_widget = QTabWidget()
        player_layout.addWidget(self.tab_widget)

        # 1. Вкладка Створення Персонажа
        # Тепер CharacterCardTab повинен сам імпортувати DataManager
        self.create_tab = CharacterCreationCardTab(parent=None)
        self.tab_widget.addTab(self.create_tab, "1. Створення персонажа")

        # 2. Вкладка Дисплея
        self.display_tab = CharacterDisplayTab(parent=None)
        self.tab_widget.addTab(self.display_tab, "2. Картка персонажа")

        # Встановлюємо вкладку дисплея неактивною при старті
        self.tab_widget.setTabEnabled(1, False)

        # ПІДКЛЮЧЕННЯ СИГНАЛУ (зміна вкладки після збереження)
        self.create_tab.character_saved.connect(self.handle_character_saved)

        self.stack.addWidget(player_container)  # Індекс 1

    def show_main_menu(self):
        """Переключає на головне меню (індекс 0)."""
        self.stack.setCurrentIndex(0)

    def show_player_tabs(self):
        """Переключає на секцію Player (індекс 1)."""
        self.stack.setCurrentIndex(1)

    def handle_character_saved(self, file_path):
        """
        Обробник сигналу: викликається після успішного збереження персонажа.
        Активує та перемикає на вкладку відображення.
        """
        print(f"Сигнал отримано: Персонаж збережено у {file_path}")

        # 1. Завантажити дані у вкладку відображення
        self.display_tab.load_character(file_path)

        # 2. Активувати вкладку відображення
        self.tab_widget.setTabEnabled(1, True)

        # 3. Переключити на вкладку відображення (індекс 1)
        self.tab_widget.setCurrentIndex(1)


# --- ЗАПУСК ДОДАТКУ ---
if __name__ == '__main__':
    # Створення фіктивних директорій та файлів для коректного запуску
    # (Це потрібно лише, якщо файли не були створені раніше)
    if not os.path.exists('core'):
        os.makedirs('core')
    if not os.path.exists('ui/player'):
        os.makedirs('ui/player')

    app = QApplication(sys.argv)

    # Створюємо лише екземпляр MainWindow без DataManager
    window = MainWindow()
    window.show()

    sys.exit(app.exec())