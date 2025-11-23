from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QTabWidget, QGridLayout, QFrame, QScrollArea, QPushButton,
    QInputDialog, QMessageBox, QLineEdit, QComboBox, QSpinBox, QProgressBar, QDialog, QSplitter
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCursor, QAction, QColor
import math

from core.data_manager import DataManager
from core.fuzzy_logic import FuzzyLogic
from ui.player.inventory_tab import InventoryTab
from ui.player.logs_tab import LogsTab
from ui.dialogs.roll_dialog import RollDialog
from ui.dialogs.dual_roll_dialog import DualRollDialog
from ui.player.character_sheet_window import CharacterSheetWindow
from ui.widgets.battle_map_widget import BattleMapWidget


class PlayerMapWindow(QDialog):
    def __init__(self, dm, char_uid, char_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Бойова Мапа")
        self.resize(1000, 700)
        self.dm = dm
        self.char_uid = char_uid
        self.char_data = char_data
        self.setStyleSheet("background-color: #263238; color: white;")

        l = QHBoxLayout(self)
        spl = QSplitter(Qt.Horizontal)

        # ACTIONS
        aw = QWidget()
        aw.setStyleSheet("background-color: #37474F;")
        al = QVBoxLayout(aw)
        al.addWidget(QLabel("<h3>Маневри</h3>"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background-color: transparent; border: none;")
        bc = QWidget()
        bc.setStyleSheet("background-color: transparent;")
        self.vbox = QVBoxLayout(bc)

        self._populate()

        self.vbox.addStretch()
        scroll.setWidget(bc)
        al.addWidget(scroll)
        self.lbl_st = QLabel("...")
        al.addWidget(self.lbl_st)
        spl.addWidget(aw)

        # MAP
        mc = QWidget()
        ml = QVBoxLayout(mc)
        self.map = BattleMapWidget(is_dm=False, my_uid=char_uid)
        self.map.token_moved.connect(self._on_move)
        ml.addWidget(self.map)
        spl.addWidget(mc)
        spl.setSizes([300, 700])
        l.addWidget(spl)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._sync)
        self.timer.start(500)

    def _populate(self):
        inv = self.dm.get_inventory(self.char_uid)
        man = self.dm.get_combat_maneuvers()

        # Check inventory
        has_wep = any(i.get('type') == 'Weapon' for i in inv.values())
        has_focus = any(i.get('type') == 'Focus' for i in inv.values())
        has_ranged = any(i.get('type') == 'RangedWeapon' for i in inv.values())

        for k, m in man.items():
            req = m.get('req_item_type')
            avail = True
            reason = ""

            if req == 'Weapon' and not has_wep: avail = False; reason = "Need Weapon"
            if req == 'RangedWeapon' and not has_ranged: avail = False; reason = "Need Bow"
            if req == 'Focus' and not has_focus: avail = False; reason = "Need Focus"

            txt = f"{m['name']}\n{m['desc']}"
            if not avail: txt += f"\n🚫 {reason}"

            btn = QPushButton(txt)
            btn.setStyleSheet(
                "text-align:left; padding:8px; border:1px solid #777; background:#455A64; border-radius:4px; font-weight:bold;")

            if avail:
                btn.setCursor(Qt.PointingHandCursor)
                btn.clicked.connect(lambda ch=False, d=m: self.parent()._initiate_maneuver(d))
            else:
                btn.setEnabled(False)
                btn.setStyleSheet(
                    "text-align:left; padding:8px; border:1px dashed #555; background:#263238; color:#78909C;")

            self.vbox.addWidget(btn)

    def _sync(self):
        st = self.dm.get_combat_state()
        self.map.update_state(st.get("tokens", {}))
        idx = st.get("current_turn_index", 0)
        order = st.get("turn_order", [])
        if order: self.lbl_st.setText(f"Хід: {order[idx]['name']}")

    def _on_move(self, uid, x, y):
        self.dm.move_token(uid, x, y)


class PlayerMenu(QWidget):
    def __init__(self, dm: DataManager, char_data: dict, parent=None):
        super().__init__(parent)
        self.dm = dm
        self.char_data = char_data
        if 'conditions' not in self.char_data: self.char_data['conditions'] = {"physical_exhaustion": 0, "morale": 10}

        self.stats = self.char_data.get('stats', {})
        self.mods = self._calculate_mods(self.stats)
        self.lvl = self.char_data.get('level', 1)
        self.max_hp = 20
        self.max_fatigue = self.dm.calculate_max_fatigue(self.max_hp)

        self.setStyleSheet("""
            QWidget { background-color: #F5F5F5; color: #333; font-family: 'Segoe UI'; }
            QPushButton { padding: 8px; border-radius: 4px; font-weight: bold; }
            #MapBtn { background-color: #D32F2F; color: white; font-size: 16px; padding: 12px; }
            #MapBtn:hover { background-color: #B71C1C; }
        """)

        main = QVBoxLayout(self)

        # Header
        h = QHBoxLayout()
        h.addWidget(QLabel(f"<h1>{self.char_data.get('name')}</h1>"))
        btn_map = QPushButton("⚔️ БІЙ / МАПА")
        btn_map.setObjectName("MapBtn")
        btn_map.clicked.connect(self._open_map)
        h.addWidget(btn_map)
        main.addLayout(h)

        # Stats
        st_lay = QHBoxLayout()
        st_lay.addWidget(QLabel(f"HP: {self.max_hp}"))
        st_lay.addWidget(QLabel(f"Fatigue: {self.char_data['conditions']['physical_exhaustion']}/{self.max_fatigue}"))
        main.addLayout(st_lay)

        # Tabs
        tabs = QTabWidget()
        tabs.addTab(InventoryTab(dm=self.dm), "Інвентар")
        tabs.addTab(LogsTab(dm=self.dm), "Логи")
        main.addWidget(tabs)

    def _open_map(self):
        win = PlayerMapWindow(self.dm, self.dm.get_user_id(), self.char_data, self)
        win.show()

    def _calculate_mods(self, stats):
        return {k: (v - 10) // 2 for k, v in stats.items()}

    def _initiate_maneuver(self, data):
        # Logic for rolling maneuver
        stat = data['stat_options'][0]  # Simplified
        mod = self.mods.get(stat, 0)
        dlg = DualRollDialog(data['name'], mod, "Skill", 0, data, parent=self)
        if dlg.exec():
            self.dm.push_session_update(self.dm.get_current_session(), dlg.result_msg, "COMBAT")

    def _check_starter_gear(self):
        pass

    def _upd_cond(self, k, v):
        pass

    def _on_start_turn(self):
        pass

    def _open_character_sheet(self):
        pass

    def _update_fuzzy_status_ui(self):
        pass