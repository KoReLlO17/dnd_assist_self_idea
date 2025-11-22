from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QTabWidget, QGridLayout, QFrame, QScrollArea, QProgressBar
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QIcon
import math

# Імпортуємо дочірні вкладки
from core.data_manager import DataManager
from ui.player.inventory_tab import InventoryTab
from ui.player.logs_tab import LogsTab


class CharacterDisplayTab(QWidget):
    """
    Головна вкладка (Character Sheet).
    Автоматично розраховує AC, HP, Proficiency, Speed.
    """

    def __init__(self, dm: DataManager, char_data: dict, parent=None):
        super().__init__(parent)
        self.dm = dm
        self.char_data = char_data

        # Завантажуємо довідкові дані для розрахунків
        self.classes_info = self.dm.get_classes_data()
        self.races_info = self.dm.get_races_data()

        self.setStyleSheet("""
            QWidget { background-color: #F3E5F5; }
            QLabel { color: #4A148C; }
            QGroupBox {
                border: 2px solid #8E24AA;
                border-radius: 8px;
                margin-top: 15px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 10px;
                color: #8E24AA;
                font-size: 16px;
                font-weight: bold;
            }
            .StatBox {
                background-color: #E1BEE7;
                border-radius: 10px;
                padding: 10px;
                min-width: 60px;
            }
            .StatValue { font-size: 24px; font-weight: bold; color: #4A148C; }
            .StatLabel { font-size: 12px; font-weight: bold; color: #7B1FA2; }
            .SkillRow { font-size: 14px; padding: 2px; }
            .SkillProf { color: #2E7D32; font-weight: bold; }
        """)

        main_layout = QVBoxLayout(self)

        # --- Header (Info) ---
        header_hbox = QHBoxLayout()

        # Avatar
        self.image_label = QLabel("📷")
        self.image_label.setFixedSize(100, 100)
        self.image_label.setStyleSheet("background-color: #E1BEE7; border-radius: 5px; font-size: 40px;")
        self.image_label.setAlignment(Qt.AlignCenter)
        header_hbox.addWidget(self.image_label)

        # Name & Class
        info_vbox = QVBoxLayout()
        name = self.char_data.get('name', 'Unknown')
        race = self.char_data.get('race', 'Human')
        cls = self.char_data.get('char_class', 'Fighter')
        lvl = self.char_data.get('level', 1)
        bg = self.char_data.get('background', 'None')

        info_vbox.addWidget(QLabel(f"<h1>{name}</h1>"))
        info_vbox.addWidget(QLabel(f"<b>{race} {cls} (Level {lvl})</b>"))
        info_vbox.addWidget(QLabel(f"<i>{bg}</i>"))
        header_hbox.addLayout(info_vbox)
        header_hbox.addStretch(1)

        main_layout.addLayout(header_hbox)

        # --- Combat Stats (AC, HP, Speed, Prof) ---
        self._setup_combat_stats(main_layout)

        # --- Main Stats (STR, DEX...) ---
        self._setup_ability_scores(main_layout)

        # --- Tabs (Skills, Inventory, Logs) ---
        self.sub_tabs = QTabWidget()

        # 1. Skills Tab (Generated)
        self.skills_tab = QWidget()
        self._setup_skills_tab(self.skills_tab)
        self.sub_tabs.addTab(self.skills_tab, "🧠 Навички")

        # 2. Inventory
        self.inventory_tab = InventoryTab(dm=self.dm)
        self.sub_tabs.addTab(self.inventory_tab, "🎒 Інвентар")

        # 3. Logs
        self.logs_tab = LogsTab(dm=self.dm)
        self.sub_tabs.addTab(self.logs_tab, "📜 Логи")

        main_layout.addWidget(self.sub_tabs)

    def _setup_combat_stats(self, parent_layout):
        hbox = QHBoxLayout()

        # Розрахунки
        lvl = self.char_data.get('level', 1)
        stats = self.char_data.get('stats', {})
        mods = self._calculate_mods(stats)

        # 1. Proficiency Bonus
        prof_bonus = math.ceil(lvl / 4) + 1
        self._create_stat_box(hbox, "Proficiency", f"+{prof_bonus}")

        # 2. Armor Class (AC) = 10 + DEX (Base)
        # В майбутньому тут треба додавати броню з інвентаря
        ac = 10 + mods.get('dex', 0)
        self._create_stat_box(hbox, "AC (Armor)", str(ac))

        # 3. Initiative = DEX
        init = mods.get('dex', 0)
        init_str = f"+{init}" if init >= 0 else str(init)
        self._create_stat_box(hbox, "Initiative", init_str)

        # 4. Speed (From Race)
        race_name = self.char_data.get('race')
        speed = self.races_info.get(race_name, {}).get('speed', 30)
        self._create_stat_box(hbox, "Speed", f"{speed} ft")

        # 5. HP (Hit Points)
        cls_name = self.char_data.get('char_class')
        hit_die = self.classes_info.get(cls_name, {}).get('hit_die', 8)
        con_mod = mods.get('con', 0)

        # HP на 1 рівні = Max Hit Die + CON
        max_hp = hit_die + con_mod

        # HP на наступних рівнях = (Avg Hit Die + CON) * (Level - 1)
        if lvl > 1:
            avg_die = (hit_die / 2) + 1
            max_hp += int((avg_die + con_mod) * (lvl - 1))

        self._create_stat_box(hbox, "Max HP", str(max_hp))

        parent_layout.addLayout(hbox)

    def _create_stat_box(self, layout, title, value):
        container = QFrame()
        container.setProperty("class", "StatBox")
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(5, 5, 5, 5)

        val_lbl = QLabel(value)
        val_lbl.setAlignment(Qt.AlignCenter)
        val_lbl.setProperty("class", "StatValue")

        title_lbl = QLabel(title)
        title_lbl.setAlignment(Qt.AlignCenter)
        title_lbl.setProperty("class", "StatLabel")

        vbox.addWidget(val_lbl)
        vbox.addWidget(title_lbl)
        layout.addWidget(container)

    def _setup_ability_scores(self, parent_layout):
        grp = QGroupBox("Характеристики")
        grid = QGridLayout(grp)

        stats = self.char_data.get('stats', {})
        mods = self._calculate_mods(stats)

        keys = ['str', 'dex', 'con', 'int', 'wis', 'cha']
        names = ['STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA']

        for i, key in enumerate(keys):
            val = stats.get(key, 10)
            mod = mods.get(key, 0)
            mod_str = f"+{mod}" if mod >= 0 else str(mod)

            # Відображення: STR 16 (+3)
            lbl = QLabel(f"<b>{names[i]}</b>")
            lbl.setAlignment(Qt.AlignCenter)
            grid.addWidget(lbl, 0, i)

            val_lbl = QLabel(f"{val} <span style='color:#2E7D32'>({mod_str})</span>")
            val_lbl.setAlignment(Qt.AlignCenter)
            val_lbl.setStyleSheet("font-size: 16px; background-color: white; border-radius: 5px; padding: 5px;")
            grid.addWidget(val_lbl, 1, i)

        parent_layout.addWidget(grp)

    def _setup_skills_tab(self, tab):
        layout = QVBoxLayout(tab)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        form = QGridLayout(content)

        all_skills = self.dm.get_all_skills()
        my_skills = self.char_data.get('skills', [])
        stats = self.char_data.get('stats', {})
        mods = self._calculate_mods(stats)
        lvl = self.char_data.get('level', 1)
        prof_bonus = math.ceil(lvl / 4) + 1

        # Мапінг навичок до статів
        skill_map = {
            "Athletics": "str", "Acrobatics": "dex", "Sleight of Hand": "dex", "Stealth": "dex",
            "Arcana": "int", "History": "int", "Investigation": "int", "Nature": "int", "Religion": "int",
            "Animal Handling": "wis", "Insight": "wis", "Medicine": "wis", "Perception": "wis", "Survival": "wis",
            "Deception": "cha", "Intimidation": "cha", "Performance": "cha", "Persuasion": "cha"
        }

        row = 0
        for skill_full in all_skills:
            # Витягуємо коротку назву (наприклад "History" з "Історія (History)")
            # Припускаємо формат "Назва (Key)" або просто "Key"
            short_name = skill_full.split('(')[-1].replace(')', '').strip()
            stat_key = skill_map.get(short_name, 'wis')  # Default wis if not found

            is_prof = skill_full in my_skills or short_name in my_skills  # Перевірка за повною або короткою назвою

            base_mod = mods.get(stat_key, 0)
            total = base_mod + (prof_bonus if is_prof else 0)
            sign = "+" if total >= 0 else ""

            # UI
            dot = "⚫" if is_prof else "⚪"
            style = "SkillProf" if is_prof else "SkillRow"

            name_lbl = QLabel(f"{dot} {skill_full}")
            name_lbl.setProperty("class", style)

            val_lbl = QLabel(f"{sign}{total}")
            val_lbl.setAlignment(Qt.AlignRight)
            val_lbl.setStyleSheet("font-weight: bold;")

            form.addWidget(name_lbl, row, 0)
            form.addWidget(val_lbl, row, 1)
            row += 1

        form.setColumnStretch(0, 1)
        scroll.setWidget(content)
        layout.addWidget(scroll)

        # Passive Perception
        wis_mod = mods.get('wis', 0)
        # Шукаємо чи є Perception у списку навичок
        has_perc = any("Perception" in s for s in my_skills)
        passive_perc = 10 + wis_mod + (prof_bonus if has_perc else 0)

        pp_lbl = QLabel(f"Passive Perception: <b>{passive_perc}</b>")
        pp_lbl.setStyleSheet("font-size: 16px; color: #333; margin: 10px;")
        layout.addWidget(pp_lbl)

    def _calculate_mods(self, stats):
        mods = {}
        for k, v in stats.items():
            mods[k] = (v - 10) // 2
        return mods