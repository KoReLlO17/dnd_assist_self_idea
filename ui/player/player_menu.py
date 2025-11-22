from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QTabWidget, QGridLayout, QFrame, QScrollArea, QPushButton,
    QInputDialog, QMessageBox, QLineEdit, QComboBox, QSpinBox, QProgressBar, QMenu
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCursor, QAction
import math

from core.data_manager import DataManager
from core.fuzzy_logic import FuzzyLogic
from ui.player.inventory_tab import InventoryTab
from ui.player.logs_tab import LogsTab
from ui.dialogs.roll_dialog import RollDialog
from ui.dialogs.dual_roll_dialog import DualRollDialog
from ui.player.character_sheet_window import CharacterSheetWindow  # НОВЕ


class PlayerMenu(QWidget):
    def __init__(self, dm: DataManager, char_data: dict, parent=None):
        super().__init__(parent)
        self.dm = dm
        self.char_data = char_data

        if 'custom_actions' not in self.char_data: self.char_data['custom_actions'] = []
        if 'conditions' not in self.char_data:
            self.char_data['conditions'] = {"physical_exhaustion": 0, "morale": 10}

        self.maneuvers = self.dm.get_combat_maneuvers()

        self.stats = self.char_data.get('stats', {})
        self.mods = self._calculate_mods(self.stats)
        self.lvl = self.char_data.get('level', 1)
        self.max_hp = self._calc_max_hp()
        self.max_fatigue = self.dm.calculate_max_fatigue(self.max_hp)

        self.current_hp = self.max_hp

        self.setStyleSheet("""
            QWidget { background-color: #F5F5F5; color: #333; font-family: 'Segoe UI'; }
            QGroupBox { border: 1px solid #BDBDBD; border-radius: 8px; margin-top: 10px; background-color: white; font-weight: bold; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
            .StatBox { background-color: #EDE7F6; border: 1px solid #D1C4E9; border-radius: 8px; }
            .StatValue { font-size: 22px; font-weight: bold; color: #6A1B9A; }

            QPushButton.ManeuverBtn {
                text-align: left; background-color: #FFF3E0; border: 1px solid #FFB74D;
                border-radius: 6px; padding: 12px; font-size: 15px; font-weight: bold; color: #E65100;
            }
            QPushButton.ManeuverBtn:hover { background-color: #FFE0B2; }

            QPushButton.TurnBtn {
                background-color: #2196F3; color: white; font-weight: bold; 
                border-radius: 4px; padding: 8px; font-size: 14px;
            }
            QPushButton.TurnBtn:hover { background-color: #42A5F5; }

            QProgressBar { border: 1px solid #999; border-radius: 5px; text-align: center; font-weight: bold; height: 18px; }

            #SheetBtn { background-color: #E1BEE7; border: 1px solid #CE93D8; border-radius: 20px; font-size: 20px; }
            #SheetBtn:hover { background-color: #F3E5F5; }
        """)

        main_layout = QVBoxLayout(self)
        self._setup_header(main_layout)
        self._setup_combat_stats(main_layout)

        self.sub_tabs = QTabWidget()
        self.maneuver_tab = QWidget()
        self._setup_maneuvers_tab(self.maneuver_tab)
        self.sub_tabs.addTab(self.maneuver_tab, "⚔️ Тактика")

        self.inventory_tab = InventoryTab(dm=self.dm)
        self.sub_tabs.addTab(self.inventory_tab, "🎒 Інвентар")

        self.logs_tab = LogsTab(dm=self.dm)
        self.sub_tabs.addTab(self.logs_tab, "📜 Логи")

        main_layout.addWidget(self.sub_tabs)
        QTimer.singleShot(500, self._check_starter_gear)

        self._update_fuzzy_status_ui()

    def _calc_max_hp(self):
        cls_name = self.char_data.get('char_class')
        hit_die = self.dm.get_classes_data().get(cls_name, {}).get('hit_die', 8)
        con_mod = self.mods.get('con', 0)
        hp = hit_die + con_mod
        if self.lvl > 1: hp += int(((hit_die / 2) + 1 + con_mod) * (self.lvl - 1))
        return hp

    def _setup_header(self, layout):
        hbox = QHBoxLayout()

        # Кнопка відкриття картки персонажа
        self.btn_sheet = QPushButton("👤")
        self.btn_sheet.setFixedSize(40, 40)
        self.btn_sheet.setObjectName("SheetBtn")
        self.btn_sheet.setToolTip("Відкрити повну картку персонажа")
        self.btn_sheet.clicked.connect(self._open_character_sheet)
        hbox.addWidget(self.btn_sheet)

        info_vbox = QVBoxLayout()
        name = self.char_data.get('name', 'Unknown')
        cls = self.char_data.get('char_class', 'Fighter')
        info_vbox.addWidget(QLabel(f"<h1>{name}</h1>"))

        self.status_lbl = QLabel("Стан: Стабільний")
        self.status_lbl.setStyleSheet("font-weight: bold; color: #388E3C;")
        info_vbox.addWidget(self.status_lbl)

        hbox.addLayout(info_vbox)

        self.btn_start_turn = QPushButton("🔄 ПОЧАТОК ХОДУ")
        self.btn_start_turn.setProperty("class", "TurnBtn")
        self.btn_start_turn.setCursor(Qt.PointingHandCursor)
        self.btn_start_turn.clicked.connect(self._on_start_turn)
        hbox.addWidget(self.btn_start_turn)

        hbox.addStretch(1)

        cond_grp = QGroupBox("Ресурси")
        cond_l = QVBoxLayout(cond_grp)

        ex_hbox = QHBoxLayout()
        ex_hbox.addWidget(QLabel("Втома:"))
        self.ex_bar = QProgressBar()
        self.ex_bar.setRange(0, self.max_fatigue)
        self.ex_bar.setValue(self.char_data['conditions']['physical_exhaustion'])
        self.ex_bar.setStyleSheet("QProgressBar::chunk { background-color: #D32F2F; }")
        self.ex_bar.setFormat(f"%v / {self.max_fatigue}")
        ex_hbox.addWidget(self.ex_bar)
        btn_ex_up = QPushButton("+");
        btn_ex_up.setFixedSize(20, 20);
        btn_ex_up.clicked.connect(lambda: self._upd_cond('physical_exhaustion', 5))
        btn_ex_dn = QPushButton("-");
        btn_ex_dn.setFixedSize(20, 20);
        btn_ex_dn.clicked.connect(lambda: self._upd_cond('physical_exhaustion', -5))
        ex_hbox.addWidget(btn_ex_dn);
        ex_hbox.addWidget(btn_ex_up)
        cond_l.addLayout(ex_hbox)

        mor_hbox = QHBoxLayout()
        mor_hbox.addWidget(QLabel("Мораль:"))
        self.mor_bar = QProgressBar()
        self.mor_bar.setRange(0, 20)
        self.mor_bar.setValue(self.char_data['conditions']['morale'])
        self.mor_bar.setStyleSheet("QProgressBar::chunk { background-color: #FF9800; }")
        self.mor_bar.setFormat("%v")
        mor_hbox.addWidget(self.mor_bar)
        btn_mor_up = QPushButton("+");
        btn_mor_up.setFixedSize(20, 20);
        btn_mor_up.clicked.connect(lambda: self._upd_cond('morale', 1))
        btn_mor_dn = QPushButton("-");
        btn_mor_dn.setFixedSize(20, 20);
        btn_mor_dn.clicked.connect(lambda: self._upd_cond('morale', -1))
        mor_hbox.addWidget(btn_mor_dn);
        mor_hbox.addWidget(btn_mor_up)
        cond_l.addLayout(mor_hbox)

        hbox.addWidget(cond_grp)
        layout.addLayout(hbox)

    def _open_character_sheet(self):
        """Відкриває детальне вікно персонажа."""
        win = CharacterSheetWindow(self.char_data, self.dm, self)
        win.exec()

    def _get_fuzzy_state(self):
        hp = self.max_hp
        return FuzzyLogic.calculate_game_state(
            hp, self.max_hp,
            self.char_data['conditions']['physical_exhaustion'], self.max_fatigue,
            self.char_data['conditions']['morale']
        )

    def _update_fuzzy_status_ui(self):
        state = self._get_fuzzy_state()
        self.status_lbl.setText(state['status_text'])
        if "КРИТИЧНИЙ" in state['status_text'] or "ВИБУВ" in state['status_text']:
            self.status_lbl.setStyleSheet("font-weight: bold; color: #D32F2F;")
        elif "РИЗИК" in state['status_text']:
            self.status_lbl.setStyleSheet("font-weight: bold; color: #F57C00;")
        else:
            self.status_lbl.setStyleSheet("font-weight: bold; color: #388E3C;")

    def _on_start_turn(self):
        state = self._get_fuzzy_state()
        cond = state.get('condition', 'ACTIVE')

        if cond != 'ACTIVE':
            msg = f"Стан: {cond}. Ви не можете діяти."
            QMessageBox.critical(self, "Вибув", msg)
            return

        if state.get('panic_needed', False):
            dc = state['panic_dc']
            wis_mod = self.mods.get('wis', 0)
            bonus_str = f"+{wis_mod}" if wis_mod >= 0 else str(wis_mod)

            dlg = RollDialog("САМОКОНТРОЛЬ", f"1d20{bonus_str}", f"Тест на паніку (DC {dc})", self)
            dlg.exec()

            if dlg.final_total < dc:
                sid = self.dm.get_current_session()
                if sid: self.dm.push_session_update(sid,
                                                    f"❌ ПАНІКА! Гравець провалив тест (Roll {dlg.final_total} < DC {dc}).",
                                                    "SYSTEM")
                QMessageBox.warning(self, "Паніка!", "Ви не можете контролювати себе цього ходу.")
            else:
                QMessageBox.information(self, "Успіх", "Ви опанували себе.")

    def _upd_cond(self, key, delta):
        curr = self.char_data['conditions'].get(key, 0)
        limit = self.max_fatigue if key == 'physical_exhaustion' else 20
        new_val = max(0, min(limit, curr + delta))
        self.char_data['conditions'][key] = new_val

        if key == 'physical_exhaustion':
            self.ex_bar.setValue(new_val)
        else:
            self.mor_bar.setValue(new_val)

        self.dm.update_character_data({"conditions": self.char_data['conditions']})
        self._update_fuzzy_status_ui()

    def _use_potion(self):
        rarities = ["Common (1d4)", "Uncommon (1d6)", "Rare (1d10)", "Very Rare (1d20)"]
        rarity, ok = QInputDialog.getItem(self, "Зілля", "Оберіть рідкість:", rarities, 0, False)
        if ok:
            r_key = rarity.split(" ")[0]
            formula = self.dm.get_potion_recovery(r_key)
            self._perform_recovery_roll("Зілля Зцілення", formula)

    def _take_rest(self):
        formula = self.dm.get_rest_recovery_formula(self.lvl)
        self._perform_recovery_roll("Відпочинок (1 хід)", formula)

    def _perform_recovery_roll(self, title, formula):
        dlg = RollDialog(title, formula, "Відновлення сил", self)
        dlg.exec()
        restored = dlg.final_total
        self._upd_cond('physical_exhaustion', -restored)
        msg = f"<b>[{title}]</b> 🛌 Відновлено <b>{restored}</b> Втоми."
        sid = self.dm.get_current_session()
        if sid: self.dm.push_session_update(sid, msg, "ACTION")

    def _setup_maneuvers_tab(self, tab):
        l = QVBoxLayout(tab)
        l.addWidget(QLabel("Оберіть маневр:"))
        scroll = QScrollArea();
        scroll.setWidgetResizable(True);
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget();
        content.setStyleSheet("background-color: white;")
        vbox = QVBoxLayout(content)
        for m_key, m_data in self.maneuvers.items():
            btn = QPushButton(f"{m_data['name']}\n{m_data['desc']}")
            btn.setProperty("class", "ManeuverBtn")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda ch=False, d=m_data: self._initiate_maneuver(d))
            vbox.addWidget(btn)
        vbox.addStretch()
        scroll.setWidget(content)
        l.addWidget(scroll)

    def _initiate_maneuver(self, data):
        options = [s.upper() for s in data['stat_options']]
        atk_choice, ok1 = QInputDialog.getItem(self, data['name'], "Чим дієте?", options, 0, False)
        if not ok1: return

        allowed_skill_stats = data.get('stat_options', ['str', 'dex'])
        all_skills = self.dm.get_all_skills()
        skill_choice, ok2 = QInputDialog.getItem(self, "Маневр", "Яку навичку використати?", all_skills, 0, False)
        if not ok2: return

        stat_key = atk_choice.lower()
        atk_mod = self.mods.get(stat_key, 0)
        skill_mod = self._get_skill_mod(skill_choice)

        state = self._get_fuzzy_state()
        crit_rng = state['crit_thresh']
        fumble_rng = state['fumble_thresh']

        if state.get('condition', 'ACTIVE') != 'ACTIVE':
            QMessageBox.warning(self, "Увага", "Ви не можете діяти в цьому стані!")
            return

        dlg = DualRollDialog(
            atk_choice, atk_mod,
            skill_choice, skill_mod,
            data,
            crit_range=crit_rng,
            fumble_range=fumble_rng,
            parent=self
        )

        if dlg.exec():
            msg = dlg.result_msg
            sid = self.dm.get_current_session()
            if sid: self.dm.push_session_update(sid, msg, "COMBAT")

    def _get_skill_mod(self, skill_full):
        short = skill_full.split('(')[0].strip()
        eng = skill_full.split('(')[-1].replace(')', '').strip() if '(' in skill_full else short
        s_map = {"Athletics": "str", "Acrobatics": "dex", "Stealth": "dex", "Arcana": "int", "History": "int",
                 "Investigation": "int", "Nature": "int", "Religion": "int", "Animal Handling": "wis", "Insight": "wis",
                 "Medicine": "wis", "Perception": "wis", "Survival": "wis", "Deception": "cha", "Intimidation": "cha",
                 "Performance": "cha", "Persuasion": "cha"}
        stat_key = s_map.get(eng, 'wis')
        base = self.mods.get(stat_key, 0)
        is_prof = any((eng in s or short in s) for s in self.char_data.get('skills', []))
        prof = math.ceil(self.lvl / 4) + 1
        return base + (prof if is_prof else 0)

    def _setup_combat_stats(self, l):
        h = QHBoxLayout()
        dex = self.mods.get('dex', 0)
        self._box(h, "AC", 10 + dex)
        self._box(h, "HP", self.max_hp)
        self._box(h, "Max Fatigue", self.max_fatigue)
        l.addLayout(h)

    def _box(self, l, t, v):
        f = QFrame();
        f.setProperty("class", "StatBox");
        v_l = QVBoxLayout(f);
        v_l.setContentsMargins(5, 5, 5, 5)
        v_l.addWidget(QLabel(str(v), alignment=Qt.AlignCenter))
        v_l.addWidget(QLabel(t, alignment=Qt.AlignCenter))
        l.addWidget(f)

    def _setup_ability_scores(self, l):
        pass

    def _calculate_mods(self, stats):
        mods = {}
        for k, v in stats.items(): mods[k] = (v - 10) // 2
        return mods

    def _check_starter_gear(self):
        pass


class StarterGearDialog(QInputDialog): pass