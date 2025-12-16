from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSplitter, QWidget, QPushButton, QScrollArea, QGroupBox
)
from PySide6.QtCore import Qt, QTimer
from ui.widgets.battle_map_widget import BattleMapWidget
from ui.widgets.turn_tracker_widget import TurnTrackerWidget
from ui.dialogs.roll_dialog import RollDialog
from ui.dialogs.combatant_details_dialog import CombatantDetailsDialog


class CombatWindow(QDialog):
    """
    Спільне вікно бою для ДМа та Гравців.
    Логіка прав доступу (is_dm) визначає, хто кого може рухати.
    """

    def __init__(self, dm, char_uid=None, is_dm=False, parent=None):
        super().__init__(parent)
        self.dm = dm
        self.char_uid = char_uid
        self.is_dm = is_dm

        role = "ДМ" if is_dm else "Гравець"
        self.setWindowTitle(f"Бойова Сцена - {role}")
        self.resize(1300, 800)
        self.setStyleSheet("background-color: #263238; color: white;")

        layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Horizontal)

        # --- ЛІВА ПАНЕЛЬ (Інфо/Дії) ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        # 1. Turn Tracker
        self.tracker = TurnTrackerWidget()
        self.tracker.show_details_requested.connect(self._show_details)
        left_layout.addWidget(self.tracker)

        # 2. Панель Дій (Змінюється динамічно)
        self.action_group = QGroupBox("Дії")
        self.action_layout = QVBoxLayout(self.action_group)
        self.lbl_status = QLabel("Оберіть токен...")
        self.action_layout.addWidget(self.lbl_status)

        # Скрол для кнопок
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background-color: transparent; border: none;")
        self.btn_container = QWidget()
        self.btn_container.setStyleSheet("background-color: transparent;")
        self.vbox_btns = QVBoxLayout(self.btn_container)
        scroll.setWidget(self.btn_container)
        self.action_layout.addWidget(scroll)

        left_layout.addWidget(self.action_group)
        splitter.addWidget(left_widget)

        # --- ПРАВА ПАНЕЛЬ (Мапа) ---
        map_container = QWidget()
        map_l = QVBoxLayout(map_container)

        self.map_widget = BattleMapWidget(is_dm=self.is_dm, my_uid=self.char_uid)

        # Підключаємо рух
        self.map_widget.token_moved.connect(self._handle_move)
        self.map_widget.token_clicked.connect(self._on_token_click)

        map_l.addWidget(self.map_widget)
        splitter.addWidget(map_container)

        splitter.setSizes([350, 950])
        layout.addWidget(splitter)

        # Синхронізація
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._sync)
        self.timer.start(500)

        # Якщо гравець - додати себе, якщо немає
        if not self.is_dm and self.char_uid:
            QTimer.singleShot(500, self._ensure_player)

    def _ensure_player(self):
        state = self.dm.get_combat_state()
        tokens = state.get("tokens", {})
        if self.char_uid not in tokens:
            # Якщо гравця немає на мапі, додаємо його
            new_token = {self.char_uid: {"name": "Me", "x": 1, "y": 1, "color": "#4CAF50", "type": "player"}}
            self.dm.update_combat_state({"tokens": new_token})

    def _sync(self):
        state = self.dm.get_combat_state()
        self.map_widget.update_state(state.get("tokens", {}))
        self.tracker.update_state(state)

        idx = state.get("current_turn_index", 0)
        order = state.get("turn_order", [])
        if order and idx < len(order):
            self.lbl_status.setText(f"Зараз ходить: {order[idx]['name']}")

    def _handle_move(self, uid, x, y):
        # Передаємо is_dm в DataManager, щоб він знав чи дозволяти рух монстрів
        self.dm.move_token(uid, x, y, is_dm=self.is_dm)

    def _show_details(self, uid, name, data):
        dlg = CombatantDetailsDialog(name, data, self)
        dlg.exec()

    def _on_token_click(self, uid):
        # Оновлення панелі дій (залежить від ролі)
        self._clear_actions()

        st = self.dm.get_combat_state()
        # Use .get with empty dict to avoid crash if tokens is missing
        tokens = st.get("tokens", {})
        token = tokens.get(uid)

        if not token:
            self.lbl_status.setText("Токен не знайдено")
            return

        # Safely get name with default
        token_name = token.get('name', 'Unknown')

        is_owner = (uid == self.char_uid)
        is_enemy = (token.get('type') == 'enemy')

        # ДМ бачить атаки ворогів
        if self.is_dm and is_enemy:
            self.lbl_status.setText(f"Керування: {token_name}")
            for act in token.get('actions', []):
                self._add_action_btn(f"⚔️ {act.get('name', 'Attack')}",
                                     lambda a=act, n=token_name: self._dm_attack(n, a))

        # Гравець бачить свої маневри
        elif not self.is_dm and is_owner:
            self.lbl_status.setText("Мої дії")
            # Тут можна підтягнути маневри гравця (як було в PlayerMenu)
            self._populate_player_actions()

        else:
            self.lbl_status.setText(f"Інфо: {token_name}")

    def _dm_attack(self, name, action):
        desc = action.get('desc', 'Attack')
        dlg = RollDialog(f"{name}: {action.get('name', 'Attack')}", "1d20+5", desc, self)
        dlg.exec()
        self.dm.push_session_update(self.dm.get_current_session(),
                                    f"👹 {name} uses {action.get('name', 'Attack')}! Result: {dlg.final_total}",
                                    "COMBAT")

    def _populate_player_actions(self):
        # Спрощена версія додавання кнопок (можна взяти повну логіку з попереднього PlayerMenu)
        maneuvers = self.dm.get_combat_maneuvers()
        for k, m in maneuvers.items():
            self._add_action_btn(m['name'], lambda d=m: print(f"Player action {d['name']}"))

    def _add_action_btn(self, text, callback):
        btn = QPushButton(text)
        btn.setStyleSheet("background-color: #455A64; padding: 8px; margin: 2px; border-radius: 4px;")
        btn.clicked.connect(callback)
        self.vbox_btns.addWidget(btn)

    def _clear_actions(self):
        while self.vbox_btns.count():
            item = self.vbox_btns.takeAt(0)
            if item.widget(): item.widget().deleteLater()