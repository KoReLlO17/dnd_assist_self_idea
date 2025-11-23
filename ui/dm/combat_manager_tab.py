from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QPushButton, QComboBox, QGroupBox, QSplitter, QListWidgetItem, QScrollArea
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from core.data_manager import DataManager
from ui.widgets.battle_map_widget import BattleMapWidget
from ui.dialogs.roll_dialog import RollDialog


class CombatManagerTab(QWidget):
    def __init__(self, dm: DataManager, parent=None):
        super().__init__(parent)
        self.dm = dm
        self.selected_uid = None

        layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Horizontal)

        left_panel = QWidget()
        l_layout = QVBoxLayout(left_panel)

        # INIT
        init_grp = QGroupBox("Черга")
        il = QVBoxLayout(init_grp)
        self.init_list = QListWidget()
        il.addWidget(self.init_list)
        btn_next = QPushButton("▶️ Next")
        btn_next.clicked.connect(self._next_turn)
        il.addWidget(btn_next)
        l_layout.addWidget(init_grp)

        # ACTIONS
        act_grp = QGroupBox("Дії Вибраного")
        self.act_layout = QVBoxLayout(act_grp)
        self.lbl_sel = QLabel("...")
        self.act_layout.addWidget(self.lbl_sel)
        self.act_scroll = QScrollArea()
        self.act_scroll.setWidgetResizable(True)
        self.act_w = QWidget()
        self.act_vbox = QVBoxLayout(self.act_w)
        self.act_scroll.setWidget(self.act_w)
        self.act_layout.addWidget(self.act_scroll)
        l_layout.addWidget(act_grp)

        # SPAWN
        sp_grp = QGroupBox("Спавн")
        sl = QHBoxLayout(sp_grp)
        self.combo = QComboBox()
        # Populate combo from bestiary (keys)
        for k in self.dm.get_bestiary().keys():
            self.combo.addItem(k)
        btn_add = QPushButton("➕")
        btn_add.clicked.connect(self._spawn)
        btn_roll = QPushButton("🎲 Init")
        btn_roll.clicked.connect(self._roll_init)
        sl.addWidget(self.combo)
        sl.addWidget(btn_add)
        sl.addWidget(btn_roll)
        l_layout.addWidget(sp_grp)

        splitter.addWidget(left_panel)

        # MAP
        map_cont = QWidget()
        ml = QVBoxLayout(map_cont)
        self.map = BattleMapWidget(is_dm=True)
        self.map.token_moved.connect(self.dm.move_token)
        self.map.token_clicked.connect(self._on_select)
        ml.addWidget(self.map)
        splitter.addWidget(map_cont)

        splitter.setSizes([300, 800])
        layout.addWidget(splitter)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._refresh)
        self.timer.start(1000)

    def _spawn(self):
        self.dm.add_creature_to_combat(self.combo.currentText())
        self._refresh()

    def _roll_init(self):
        self.dm.roll_initiative()
        self.dm.start_combat()
        self._refresh()

    def _next_turn(self):
        st = self.dm.get_combat_state()
        if not st.get("turn_order"): return
        idx = (st.get("current_turn_index", 0) + 1) % len(st["turn_order"])
        self.dm.update_combat_state({"current_turn_index": idx})
        actor = st["turn_order"][idx]
        self.dm.push_session_update(self.dm.get_current_session(), f"👉 Хід: {actor['name']}", "COMBAT")
        self._refresh()

    def _on_select(self, uid):
        self.selected_uid = uid
        self._update_acts()

    def _update_acts(self):
        for i in reversed(range(self.act_vbox.count())):
            self.act_vbox.itemAt(i).widget().deleteLater()

        st = self.dm.get_combat_state()
        tok = st.get("tokens", {}).get(self.selected_uid)
        if not tok: return

        self.lbl_sel.setText(tok['name'])

        if tok.get('type') == 'enemy':
            actions = tok.get('actions', [])
            for a in actions:
                btn = QPushButton(f"⚔️ {a['name']}")
                btn.setToolTip(a['desc'])
                btn.clicked.connect(lambda ch=False, act=a, n=tok['name']: self._atk(n, act))
                self.act_vbox.addWidget(btn)
        else:
            self.act_vbox.addWidget(QLabel("Player character"))

    def _atk(self, name, action):
        dlg = RollDialog(f"{name}: {action['name']}", "1d20+5", action['desc'], self)
        dlg.exec()
        self.dm.push_session_update(self.dm.get_current_session(),
                                    f"👹 {name} uses {action['name']}! Result: {dlg.final_total}", "COMBAT")

    def _refresh(self):
        st = self.dm.get_combat_state()
        self.map.update_state(st.get("tokens", {}))

        self.init_list.clear()
        cur = st.get("current_turn_index", 0)
        for i, a in enumerate(st.get("turn_order", [])):
            it = QListWidgetItem(f"{a['total']} : {a['name']}")
            if i == cur:
                it.setBackground(QColor("#2E7D32"))
                it.setForeground(QColor("white"))
            self.init_list.addItem(it)