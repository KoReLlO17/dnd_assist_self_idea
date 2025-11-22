from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QPushButton, QListWidget, QListWidgetItem, QLineEdit, QTextEdit,
    QGridLayout, QMessageBox, QProgressBar, QFrame, QScrollArea  # <--- QScrollArea тепер тут
)
from PySide6.QtCore import Qt, Signal, QDateTime, QTimer
import socket
from core.data_manager import DataManager


class PlayerStatusWidget(QFrame):
    """Віджет для відображення стану одного гравця в списку ДМа."""

    def __init__(self, name, char_class, conditions, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        # Стиль картки гравця (темний)
        self.setStyleSheet("""
            QFrame { 
                background-color: #2D2D2D; 
                border-radius: 5px; 
                margin-bottom: 4px; 
                border: 1px solid #3E3E42; 
            }
            QLabel { 
                font-weight: bold; 
                color: #E0E0E0; 
                border: none; 
            }
            QProgressBar { 
                border: 1px solid #555; 
                border-radius: 3px; 
                text-align: center; 
                height: 14px; 
                font-size: 10px; 
                background-color: #1E1E1E; 
                color: white; 
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(8, 8, 8, 8)

        # Ім'я та Клас
        top_row = QHBoxLayout()
        lbl_name = QLabel(f"{name} ({char_class})")
        lbl_name.setStyleSheet("font-size: 14px; color: #81D4FA;")
        top_row.addWidget(lbl_name)
        layout.addLayout(top_row)

        # Статус Бари
        # 1. Мораль (Morale)
        mor_val = conditions.get('morale', 10)
        self.mor_bar = self._create_bar("🔥 Morale", mor_val, 20, "#FF9800")
        layout.addWidget(self.mor_bar)

        # 2. Виснаження (Exhaustion)
        ex_val = conditions.get('physical_exhaustion', 0)
        self.ex_bar = self._create_bar("😫 Exhaustion", ex_val, 6, "#D32F2F")
        layout.addWidget(self.ex_bar)

    def _create_bar(self, label, val, max_val, color):
        bar = QProgressBar()
        bar.setRange(0, max_val)
        bar.setValue(val)
        bar.setFormat(f"{label}: %v/{max_val}")
        bar.setStyleSheet(f"QProgressBar::chunk {{ background-color: {color}; }}")
        return bar


class HostingTab(QWidget):
    session_state_changed = Signal(bool)

    def __init__(self, dm: DataManager, parent=None):
        super().__init__(parent)

        self.dm = dm
        self.is_session_active = False
        self.session_id = self.dm.get_current_session()
        self.connected_players = {}

        try:
            self.local_ip = socket.gethostbyname(socket.gethostname())
        except:
            self.local_ip = "127.0.0.1"

        # Стилі для цієї вкладки (темні)
        self.setStyleSheet("""
            QWidget { background-color: #1E1E1E; color: #E0E0E0; }

            QGroupBox { 
                border: 1px solid #3E3E42; 
                border-radius: 8px; 
                margin-top: 10px; 
                background-color: #252526; 
                font-weight: bold; 
                color: #CCC; 
            }
            QGroupBox::title { 
                subcontrol-origin: margin; 
                left: 10px; 
                padding: 0 5px; 
            }

            #SessionIDLabel { 
                font-size: 20px; 
                font-weight: bold; 
                color: #4FC3F7; 
                background-color: #2D2D2D; 
                padding: 8px; 
                border-radius: 5px; 
                border: 1px dashed #4FC3F7; 
            }

            QPushButton { 
                padding: 10px 20px; 
                border-radius: 5px; 
                font-weight: bold; 
                color: white; 
                border: none;
            }
            #StartButton { background-color: #2E7D32; }
            #StartButton:hover { background-color: #388E3C; }
            #StartButton:disabled { background-color: #1B5E20; color: #888; }

            #StopButton { background-color: #C62828; }
            #StopButton:hover { background-color: #D32F2F; }
            #StopButton:disabled { background-color: #5D1013; color: #888; }

            QTextEdit {
                background-color: #121212;
                color: #CCC;
                border: 1px solid #3E3E42;
                font-family: 'Consolas', monospace;
            }
        """)

        main_layout = QVBoxLayout(self)

        # Header
        header = QLabel("<h1>🛠️ Панель Хостингу (Battle Dashboard)</h1>")
        header.setStyleSheet("color: #90CAF9;")
        main_layout.addWidget(header)

        # --- КЕРУВАННЯ СЕСІЄЮ (СТАТИЧНИЙ БЛОК) ---
        session_group = QGroupBox("Сесія")
        sl = QVBoxLayout(session_group)

        btn_row = QHBoxLayout()
        self.start_btn = QPushButton("▶️ СТАРТ")
        self.start_btn.setObjectName("StartButton")
        self.start_btn.clicked.connect(self._start_session)

        self.stop_btn = QPushButton("⏹️ СТОП")
        self.stop_btn.setObjectName("StopButton")
        self.stop_btn.clicked.connect(self._stop_session)
        self.stop_btn.setEnabled(False)

        btn_row.addWidget(self.start_btn)
        btn_row.addWidget(self.stop_btn)
        sl.addLayout(btn_row)

        self.info_lbl = QLabel("Офлайн")
        self.info_lbl.setObjectName("SessionIDLabel")
        self.info_lbl.setAlignment(Qt.AlignCenter)
        sl.addWidget(self.info_lbl)

        sl.addWidget(QLabel("<i>IP адреса для гравців</i>", alignment=Qt.AlignCenter))
        main_layout.addWidget(session_group)

        # --- ГРАВЦІ (ДИНАМІЧНИЙ БЛОК) ---
        player_group = QGroupBox("Стан Групи")
        player_group_layout = QVBoxLayout(player_group)

        # Скрол зона
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")

        # Контейнер для карток
        self.players_container_widget = QWidget()
        self.players_container_widget.setStyleSheet("background-color: transparent;")

        # Лейаут для карток
        self.players_layout = QVBoxLayout(self.players_container_widget)
        self.players_layout.setAlignment(Qt.AlignTop)
        self.players_layout.setSpacing(5)

        self.scroll.setWidget(self.players_container_widget)
        player_group_layout.addWidget(self.scroll)

        main_layout.addWidget(player_group)

        # Logs
        log_group = QGroupBox("Лог Подій")
        ll = QVBoxLayout(log_group)
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        ll.addWidget(self.log_view)
        main_layout.addWidget(log_group)

        # Timer
        self.timer = QTimer(self)
        self.timer.setInterval(2000)
        self.timer.timeout.connect(self._update_dashboard)
        self.timer.start()

    def _start_session(self):
        sid = self.dm.start_new_session()
        if sid:
            self.session_id = sid
            self.is_session_active = True
            self.info_lbl.setText(f"{self.local_ip}/{sid}")
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.session_state_changed.emit(True)
            self._log("Сесію розпочато.")

    def _stop_session(self):
        self.is_session_active = False
        self.info_lbl.setText("Офлайн")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.session_state_changed.emit(False)
        self._clear_players_list()
        self._log("Сесію зупинено.")

    def _clear_players_list(self):
        """Очищає список гравців, не чіпаючи кнопки управління."""
        while self.players_layout.count():
            item = self.players_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _update_dashboard(self):
        if not self.is_session_active or not self.session_id: return

        players = self.dm.get_session_players(self.session_id)

        # Повне оновлення списку
        self._clear_players_list()

        if not players:
            lbl = QLabel("Очікування підключення гравців...")
            lbl.setStyleSheet("color: #757575; font-style: italic;")
            lbl.setAlignment(Qt.AlignCenter)
            self.players_layout.addWidget(lbl)
            return

        for uid, p_data in players.items():
            name = p_data.get('name', '???')
            cls = p_data.get('char_class', '???')
            conds = p_data.get('conditions', {})

            # Створення віджета картки
            card = PlayerStatusWidget(name, cls, conds)
            self.players_layout.addWidget(card)

        # Оновлення логів (опціонально)
        # logs = self.dm.get_session_updates(self.session_id)

    def _log(self, msg):
        self.log_view.append(f"[{QDateTime.currentDateTime().toString('hh:mm')}] {msg}")