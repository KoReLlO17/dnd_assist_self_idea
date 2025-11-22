from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QPushButton, QListWidget, QListWidgetItem, QLineEdit,
    QTextEdit, QGridLayout, QMessageBox, QScrollBar, QInputDialog
)
from PySide6.QtCore import Qt, Signal, QDateTime, QTimer
from PySide6.QtGui import QFont, QColor

# Ініціалізація DataManager тепер потребує коректного імпорту
from core.data_manager import DataManager


class HostingTab(QWidget):
    """
    Головна вкладка Хостингу для Майстра Підземель (DM).
    Керує запуском, зупинкою сесії, підключеннями та збереженням стану.
    """

    session_state_changed = Signal(bool)  # Сигнал для зміни стану (Запущено/Зупинено)

    def __init__(self, dm: DataManager, parent=None):
        super().__init__(parent)

        self.dm = dm
        # Стан береться з DataManager або ініціалізується
        self.is_session_active = False
        self.session_id = self.dm.get_current_session()  # Може бути None
        self.connected_players = {}  # {userId: playerName, ...}
        self.last_save_timestamp = "---"

        self.setStyleSheet("""
            QWidget { background-color: #E8F5E9; } /* Світло-зелений фон */
            QGroupBox {
                border: 2px solid #2E7D32; /* Темно-зелений для акценту */
                border-radius: 10px;
                margin-top: 20px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 10px;
                color: #2E7D32;
                font-size: 18px;
                font-weight: bold;
            }
            QLabel { color: #1B5E20; }
            QLineEdit, QTextEdit, QListWidget {
                border: 1px solid #A5D6A7;
                border-radius: 5px;
                padding: 5px;
                background-color: #F1F8E9;
            }
            #SessionIDLabel {
                font-size: 24px;
                font-weight: bold;
                color: #2E7D32;
                background-color: #C8E6C9;
                padding: 10px;
                border-radius: 8px;
            }
            #StatusActive { background-color: #4CAF50; color: white; padding: 5px; border-radius: 5px; }
            #StatusInactive { background-color: #F44336; color: white; padding: 5px; border-radius: 5px; }
            QPushButton {
                padding: 12px 25px;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
                color: white;
            }
            #StartButton { background-color: #4CAF50; }
            #StartButton:hover { background-color: #66BB6A; }
            #StopButton { background-color: #E53935; }
            #StopButton:hover { background-color: #EF5350; }
            #SaveButton { background-color: #1E88E5; }
            #SaveButton:hover { background-color: #42A5F5; }
        """)

        main_layout = QVBoxLayout(self)

        header_label = QLabel("<h1>🛠️ Панель Хостингу DM</h1>")
        header_label.setStyleSheet("color: #2E7D32; padding-bottom: 5px; border-bottom: 1px solid #C8E6C9;")
        main_layout.addWidget(header_label)

        # ---------------------------------------------------------------------
        # Секція 1: Управління Сесією та ID
        # ---------------------------------------------------------------------
        session_group = QGroupBox("Керування Сесією")
        session_layout = QVBoxLayout(session_group)

        # Кнопки Старт/Стоп
        button_hbox = QHBoxLayout()
        self.start_button = QPushButton("▶️ Запустити Сесію")
        self.start_button.setObjectName("StartButton")
        self.start_button.clicked.connect(self._start_session)
        self.stop_button = QPushButton("⏹️ Зупинити Сесію")
        self.stop_button.setObjectName("StopButton")
        self.stop_button.clicked.connect(self._stop_session)

        button_hbox.addWidget(self.start_button)
        button_hbox.addWidget(self.stop_button)
        session_layout.addLayout(button_hbox)

        # ID Сесії та Статус
        id_hbox = QHBoxLayout()
        id_hbox.addWidget(QLabel("<b>ID Сесії (для гравців):</b>"))
        self.session_id_label = QLabel(self.session_id if self.session_id else "---")
        self.session_id_label.setObjectName("SessionIDLabel")
        self.session_id_label.setAlignment(Qt.AlignCenter)
        id_hbox.addWidget(self.session_id_label, 1)

        self.status_label = QLabel("Статус: Неактивна")
        self.status_label.setObjectName("StatusInactive")
        id_hbox.addWidget(self.status_label)

        session_layout.addLayout(id_hbox)

        session_layout.addWidget(QLabel("<i>Гравці приєднуються за цим ID.</i>"))
        main_layout.addWidget(session_group)

        # ---------------------------------------------------------------------
        # Секція 2: Гравці та Збереження
        # ---------------------------------------------------------------------
        player_save_group = QGroupBox("Гравці та Стан Гри")
        grid = QGridLayout(player_save_group)

        # Список гравців
        grid.addWidget(QLabel("<b>Підключені Гравці:</b>"), 0, 0)
        self.player_list = QListWidget()
        self.player_list.setMaximumHeight(150)
        grid.addWidget(self.player_list, 1, 0)

        # Логіка Збереження
        save_vbox = QVBoxLayout()
        self.save_button = QPushButton("💾 Зберегти Стан Гри")
        self.save_button.setObjectName("SaveButton")
        self.save_button.clicked.connect(self._save_state)

        self.load_button = QPushButton("Завантажити Стан")
        self.load_button.clicked.connect(self._load_state_dialog)

        self.last_save_label = QLabel(f"Останнє збереження: {self.last_save_timestamp}")

        save_vbox.addWidget(self.last_save_label)
        save_vbox.addWidget(self.save_button)
        save_vbox.addWidget(self.load_button)

        grid.addLayout(save_vbox, 1, 1)

        # Розміщення груп у ґріді
        grid.setColumnStretch(0, 2)
        grid.setColumnStretch(1, 1)

        main_layout.addWidget(player_save_group)

        # ---------------------------------------------------------------------
        # Секція 3: Лог Сесії (Консоль)
        # ---------------------------------------------------------------------
        log_group = QGroupBox("Лог Сесії (Дії Системи та Гравців)")
        log_layout = QVBoxLayout(log_group)

        self.session_log = QTextEdit()
        self.session_log.setReadOnly(True)
        self.session_log.setFont(QFont("Monospace", 9))
        self.session_log.setText("Система готова. Очікування запуску сесії...")
        log_layout.addWidget(self.session_log)

        main_layout.addWidget(log_group)
        main_layout.addStretch(1)

        self._update_ui_state()  # Ініціалізація стану UI

        # ---------------------------------------------------------------------
        # Підключення до DataManager для реального часу
        # ---------------------------------------------------------------------
        # Використовуємо QTimer для імітації "пульсу" бекенду
        self.update_timer = QTimer(self)
        self.update_timer.setInterval(5000)  # Оновлення кожні 5 секунд
        self.update_timer.timeout.connect(self._check_mock_updates)
        self.update_timer.start()

        self._log_event(f"DataManager ініціалізовано. UID DM: {self.dm.get_user_id()}", is_error=False)

    # =========================================================================
    # ЛОГІКА СЕСІЇ ТА АВТОРИЗАЦІЯ
    # =========================================================================

    def _update_ui_state(self):
        """Оновлює стан UI відповідно до self.is_session_active."""

        self.start_button.setEnabled(not self.is_session_active)
        self.stop_button.setEnabled(self.is_session_active)
        self.save_button.setEnabled(self.is_session_active)
        self.load_button.setEnabled(not self.is_session_active)

        session_id_text = self.session_id if self.session_id else "---"
        self.session_id_label.setText(session_id_text)

        if self.is_session_active:
            status = "АКТИВНА"
            style_name = "StatusActive"
        else:
            status = "Неактивна"
            style_name = "StatusInactive"

        self.status_label.setText(f"Статус: {status}")
        self.status_label.setObjectName(style_name)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

        if not self.is_session_active and not self.session_id:
            self.player_list.clear()

    def _log_event(self, message: str, is_error=False):
        """Додає повідомлення до логу сесії."""
        timestamp = QDateTime.currentDateTime().toString("hh:mm:ss")
        color = "red" if is_error else "#2E7D32" if "Успішно" in message or "Запущено" in message else "black"

        new_text = f"<span style='color: gray;'>[{timestamp}]</span> <span style='color: {color};'>{message}</span><br>"

        self.session_log.append(new_text)
        self.session_log.verticalScrollBar().setValue(self.session_log.verticalScrollBar().maximum())

    # =========================================================================
    # МЕТОДИ КЕРУВАННЯ
    # =========================================================================

    def _start_session(self):
        """Запуск нової сесії. Викликає DataManager для створення запису в Firebase."""
        self._log_event("Спроба запустити нову сесію...")
        try:
            new_session_id = self.dm.start_new_session()

            if new_session_id:
                self.session_id = new_session_id
                self.is_session_active = True
                self._log_event(
                    f"Сесію Успішно Запущено! ID: <b>{self.session_id}</b>. Очікування підключення гравців...",
                    is_error=False)
                # Підписка на гравців
                self.dm.subscribe_to_players(self.session_id, self._handle_player_update)
            else:
                raise Exception("Не вдалося отримати ID сесії.")

        except Exception as e:
            self._log_event(f"Помилка при запуску сесії: {str(e)}", is_error=True)
            self.is_session_active = False
            self.session_id = None

        self._update_ui_state()
        self.session_state_changed.emit(self.is_session_active)

    def _stop_session(self):
        """Зупинка поточної сесії. Викликає DataManager для оновлення статусу."""
        if not self.is_session_active:
            QMessageBox.warning(self, "Помилка", "Немає активної сесії для зупинки.")
            return

        reply = QMessageBox.question(
            self,
            "Зупинити Сесію",
            "Ви впевнені, що хочете зупинити сесію? Рекомендується спочатку Зберегти Стан Гри.",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                if self.dm.stop_session(self.session_id):
                    self.is_session_active = False
                    self._log_event(f"Сесію ({self.session_id}) Зупинено. Всі підписки відключено.", is_error=False)
                    self.session_id = None
                    self.connected_players = {}
                else:
                    raise Exception("DataManager не підтвердив зупинку сесії.")

            except Exception as e:
                self._log_event(f"Помилка при зупинці сесії: {str(e)}. Спробуйте зупинити вручну.", is_error=True)

            self._update_ui_state()
            self.session_state_changed.emit(self.is_session_active)

    def _save_state(self):
        """Збереження поточного стану гри."""
        if not self.is_session_active:
            self._log_event("Неможливо зберегти. Сесія неактивна.", is_error=True)
            return

        self._log_event("Спроба збереження поточного стану...")

        state_data = {
            "timestamp": QDateTime.currentDateTime().toString(Qt.ISODate),
            "current_scene": "s_dungeon_level_2",
            "dm_notes": "Гравці виглядають стомленими, потрібен відпочинок."
        }

        try:
            if self.dm.save_session_state(self.session_id, state_data):
                self.last_save_timestamp = QDateTime.currentDateTime().toString("dd.MM.yyyy hh:mm:ss")
                self.last_save_label.setText(f"Останнє збереження: {self.last_save_timestamp}")
                self._log_event("Успішно Збережено!", is_error=False)
            else:
                raise Exception("Операція збереження не підтверджена DataManager.")

        except Exception as e:
            self._log_event(f"Помилка при збереженні стану: {str(e)}", is_error=True)

    def _load_state_dialog(self):
        """Викликає діалогове вікно для завантаження сесії за ID."""
        if self.is_session_active:
            QMessageBox.warning(self, "Помилка", "Спочатку зупиніть поточну сесію, щоб завантажити іншу.")
            return

        session_id, ok = QInputDialog.getText(
            self,
            "Завантажити Стан Сесії",
            "Введіть ID сесії для завантаження (наприклад, SESS_XXXXXX):",
            QLineEdit.Normal,
            ""
        )

        if ok and session_id:
            self._load_state(session_id.strip())

    def _load_state(self, session_id):
        """Завантаження стану гри з Firebase за ID сесії."""
        self._log_event(f"Спроба завантаження стану сесії ID: {session_id}...")

        try:
            session_data = self.dm.load_session_state(session_id)

            if session_data and session_data.get('status') == 'INACTIVE':
                self.session_id = session_id
                self.dm.set_current_session(session_id)

                self.last_save_timestamp = session_data.get('last_save', '---')
                self.last_save_label.setText(f"Останнє збереження: {self.last_save_timestamp}")

                self.is_session_active = False
                self._log_event(f"Стан сесії <b>{session_id}</b> успішно завантажено. Готово до запуску.")

                self.connected_players = session_data.get('players_snapshot', {})
                self._update_player_list()

            elif session_data and session_data.get('status') == 'ACTIVE':
                QMessageBox.warning(self, "Помилка", "Ця сесія вже активна. Попросіть іншого DM зупинити її.")
                return
            else:
                QMessageBox.critical(self, "Помилка Завантаження",
                                     f"Сесію ID: {session_id} не знайдено або статус не дозволяє завантаження.")
                raise Exception("Стан гри не знайдено або неможливо завантажити.")

        except Exception as e:
            self._log_event(f"Помилка при завантаженні стану: {str(e)}", is_error=True)
            if self.dm.get_current_session() == session_id: self.dm.set_current_session(None)
            self.session_id = None
            self.connected_players = {}

        self._update_ui_state()

    # =========================================================================
    # ОБРОБНИКИ ПОДІЙ REAL-TIME (ОНОВЛЕННЯ З FIREBASE)
    # =========================================================================

    def _handle_player_update(self, players_data: dict):
        """Обробляє оновлення списку гравців з DataManager (onSnapshot)."""
        if not self.is_session_active:
            return

        newly_connected = set(players_data.keys()) - set(self.connected_players.keys())
        disconnected = set(self.connected_players.keys()) - set(players_data.keys())

        # 1. Логування змін
        for uid in newly_connected:
            player_name = players_data.get(uid, {}).get('name', 'Невідомий Гравець')
            self._log_event(f"Гравець <b>{player_name}</b> підключився (UID: {uid[:5]}...)", is_error=False)

        for uid in disconnected:
            player_name = self.connected_players.get(uid, {}).get('name', 'Невідомий Гравець')
            self._log_event(f"Гравець <b>{player_name}</b> відключився.", is_error=True)

        # 2. Оновлення внутрішнього стану
        self.connected_players = players_data

        # 3. Оновлення списку UI
        self._update_player_list()

    def _update_player_list(self):
        """Оновлює QListWidget гравців."""
        self.player_list.clear()

        if not self.connected_players:
            self.player_list.addItem("Немає підключених гравців.")
            return

        for uid, player_data in self.connected_players.items():
            name = player_data.get('name', 'N/A')
            online_status = player_data.get('status', 'Offline')

            status_symbol = ""
            if online_status == 'Online':
                status_symbol = "🟢"
            elif online_status == 'Offline':
                status_symbol = "⚫"
            else:
                status_symbol = "🟡"

            item_text = f"{status_symbol} {name} (UID: {uid[:5]}...) - {online_status}"
            self.player_list.addItem(item_text)

    # =========================================================================
    # ДОПОМІЖНІ МЕТОДИ (Імітація оновлень у реальному часі)
    # =========================================================================
    def _check_mock_updates(self):
        """Імітація підписки, щоб DM бачив, що система 'працює'."""
        if self.is_session_active and not self.connected_players:
            # Запускаємо первинну підписку, якщо гравці ще не з'явилися
            self.dm.subscribe_to_players(self.session_id, self._handle_player_update)

    def closeEvent(self, event):
        """Очищення ресурсів при закритті вкладки."""
        self.update_timer.stop()
        super().closeEvent(event)