from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QApplication, QMainWindow
)
from PySide6.QtCore import Qt

# Імпорти головних вікон для відповідних ролей
# Переконайтеся, що ці файли існують у відповідних папках ui/player/ та ui/dm/
from ui.player.player_main_window import PlayerMainWindow
from ui.dm.dm_main_window import DM_MainWindow


class App(QWidget):
    """
    Головний віджет застосунку (Launcher), який дозволяє користувачу 
    обрати роль (Гравець або Майстер Підземель).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("D&D Assistant: Вибір Ролі")
        self.resize(600, 400)

        # Стилізація інтерфейсу
        self.setStyleSheet("""
            QWidget { 
                background-color: #263238; /* Темно-синій фон */
                color: white; 
            }
            #HeaderLabel {
                font-size: 32px;
                font-weight: bold;
                color: #80DEEA; /* Бірюзовий текст */
                margin-bottom: 20px;
            }
            QPushButton {
                min-width: 200px;
                min-height: 80px;
                font-size: 20px;
                font-weight: bold;
                border-radius: 15px;
                border: 2px solid transparent;
                color: white;
            }
            QPushButton:hover {
                border: 2px solid white;
            }
            #PlayerButton {
                background-color: #00838F; /* Синій для Гравця */
            }
            #PlayerButton:hover {
                background-color: #00ACC1;
            }
            #DMButton {
                background-color: #D84315; /* Помаранчевий для DM */
            }
            #DMButton:hover {
                background-color: #FF7043;
            }
        """)

        # Головний макет
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignCenter)
        main_layout.setSpacing(40)

        # Заголовок
        header = QLabel("Хто ви у цій пригоді?")
        header.setObjectName("HeaderLabel")
        header.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(header)

        # Контейнер для кнопок
        button_layout = QHBoxLayout()
        button_layout.setSpacing(30)
        button_layout.setAlignment(Qt.AlignCenter)

        # 1. Кнопка Гравця
        self.player_button = QPushButton("🧙‍♂️ ГРАВЕЦЬ")
        self.player_button.setObjectName("PlayerButton")
        self.player_button.setCursor(Qt.PointingHandCursor)
        self.player_button.clicked.connect(self._launch_player)
        button_layout.addWidget(self.player_button)

        # 2. Кнопка DM
        self.dm_button = QPushButton("🏰 DM (Майстер)")
        self.dm_button.setObjectName("DMButton")
        self.dm_button.setCursor(Qt.PointingHandCursor)
        self.dm_button.clicked.connect(self._launch_dm)
        button_layout.addWidget(self.dm_button)

        main_layout.addLayout(button_layout)

        # Змінна для зберігання активного вікна, щоб воно не видалилося з пам'яті
        self.active_window = None

    def _launch_player(self):
        """Запускає інтерфейс Гравця і ховає селектор."""
        self._open_sub_window(PlayerMainWindow)

    def _launch_dm(self):
        """Запускає інтерфейс Майстра і ховає селектор."""
        self._open_sub_window(DM_MainWindow)

    def _open_sub_window(self, window_class):
        """Універсальний метод для відкриття дочірнього вікна."""
        # Створюємо нове вікно
        self.active_window = window_class()

        # Підключаємо сигнал: коли дочірнє вікно закривається -> показати цей селектор знову
        # Використовуємо lambda, щоб скинути посилання на active_window
        self.active_window.destroyed.connect(self._on_sub_window_closed)

        # Показуємо нове вікно і ховаємо поточне
        self.active_window.show()
        self.hide()

    def _on_sub_window_closed(self):
        """Викликається, коли дочірнє вікно закрите."""
        self.active_window = None
        self.show()  # Повертаємо меню вибору