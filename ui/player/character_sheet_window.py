from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QGridLayout, QFrame, QScrollArea, QTabWidget, QWidget
)
from PySide6.QtCore import Qt
import math


class CharacterSheetWindow(QDialog):
    """
    Детальне вікно персонажа (тільки для перегляду).
    """

    def __init__(self, char_data, dm, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Картка Персонажа: {char_data.get('name')}")
        self.resize(700, 800)
        self.char_data = char_data
        self.dm = dm

        self.stats = self.char_data.get('stats', {})
        self.mods = self._calculate_mods(self.stats)
        self.lvl = self.char_data.get('level', 1)

        self.setStyleSheet("""
            QDialog { background-color: #F5F5F5; font-family: 'Segoe UI'; }
            QGroupBox { font-weight: bold; border: 1px solid #BDBDBD; border-radius: 6px; margin-top: 10px; background-color: white; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
            QLabel { color: #333; font-size: 14px; }
            .StatLabel { font-size: 12px; color: #757575; font-weight: bold; text-transform: uppercase; }
            .StatVal { font-size: 20px; font-weight: bold; color: #1565C0; }
            .SectionHeader { font-size: 16px; font-weight: bold; color: #4A148C; margin-top: 10px; border-bottom: 2px solid #E1BEE7; }
        """)

        main_layout = QVBoxLayout(self)

        # Scroll Area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        vbox = QVBoxLayout(content)

        # --- 1. HEADER ---
        self._setup_header(vbox)

        # --- 2. MAIN STATS ---
        self._setup_stats(vbox)

        # --- 3. PROFICIENCIES & SKILLS ---
        self._setup_skills(vbox)

        # --- 4. SPELLS (If any) ---
        if self.char_data.get('spells'):
            self._setup_spells(vbox)

        # --- 5. FEATURES & BACKGROUND ---
        self._setup_features(vbox)

        vbox.addStretch()
        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def _setup_header(self, layout):
        hbox = QHBoxLayout()
        # Avatar placeholder
        img = QLabel("🧙‍♂️")
        img.setFixedSize(80, 80)
        img.setStyleSheet("background-color: #E1BEE7; border-radius: 40px; font-size: 40px;")
        img.setAlignment(Qt.AlignCenter)
        hbox.addWidget(img)

        info = QVBoxLayout()
        name = self.char_data.get('name', 'Unknown')
        race = self.char_data.get('race', '')
        subrace = self.char_data.get('subrace', '')
        cls = self.char_data.get('char_class', '')
        subclass = self.char_data.get('subclass', '')
        bg = self.char_data.get('background', '')

        full_race = f"{subrace} {race}" if subrace else race
        full_class = f"{subclass} {cls}" if subclass else cls

        info.addWidget(QLabel(f"<h1 style='margin:0'>{name}</h1>"))
        info.addWidget(QLabel(f"<b>{full_race} {full_class}</b> (Level {self.lvl})"))
        info.addWidget(QLabel(f"Background: <i>{bg}</i>"))

        hbox.addLayout(info)
        layout.addLayout(hbox)

    def _setup_stats(self, layout):
        grp = QGroupBox("Характеристики")
        grid = QGridLayout(grp)

        keys = ['str', 'dex', 'con', 'int', 'wis', 'cha']
        names = ['STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA']

        for i, key in enumerate(keys):
            val = self.stats.get(key, 10)
            mod = self.mods.get(key, 0)
            sign = "+" if mod >= 0 else ""

            # Frame for stat
            frame = QFrame()
            frame.setStyleSheet("background-color: #E3F2FD; border-radius: 6px;")
            fl = QVBoxLayout(frame)
            fl.setContentsMargins(5, 5, 5, 5)

            fl.addWidget(QLabel(names[i], alignment=Qt.AlignCenter, objectName="StatLabel"))
            fl.addWidget(QLabel(f"{val}", alignment=Qt.AlignCenter, objectName="StatVal"))
            fl.addWidget(QLabel(f"{sign}{mod}", alignment=Qt.AlignCenter))

            grid.addWidget(frame, 0, i)

        layout.addWidget(grp)

        # Combat Stats Row
        hbox = QHBoxLayout()
        ac = 10 + self.mods.get('dex', 0)  # Base
        hp_max = self.dm.get_classes_data().get(self.char_data.get('char_class'), {}).get('hit_die', 8) + self.mods.get(
            'con', 0)  # Simplified
        prof = math.ceil(self.lvl / 4) + 1
        speed = self.dm.get_races_data().get(self.char_data.get('race'), {}).get('speed', 30)

        self._add_mini_stat(hbox, "AC", ac)
        self._add_mini_stat(hbox, "Max HP", hp_max)
        self._add_mini_stat(hbox, "Proficiency", f"+{prof}")
        self._add_mini_stat(hbox, "Speed", f"{speed} ft")
        self._add_mini_stat(hbox, "Initiative", f"{self.mods.get('dex', 0):+}")

        layout.addLayout(hbox)

    def _add_mini_stat(self, layout, title, value):
        f = QFrame()
        f.setStyleSheet("background-color: #FFF3E0; border: 1px solid #FFE0B2; border-radius: 4px;")
        l = QVBoxLayout(f);
        l.setContentsMargins(5, 5, 5, 5)
        l.addWidget(
            QLabel(str(value), alignment=Qt.AlignCenter, styleSheet="font-weight:bold; font-size:16px; color:#E65100;"))
        l.addWidget(QLabel(title, alignment=Qt.AlignCenter, styleSheet="font-size:10px; color:#555;"))
        layout.addWidget(f)

    def _setup_skills(self, layout):
        grp = QGroupBox("Навички (Skills)")
        g_lay = QGridLayout(grp)

        all_skills = self.dm.get_all_skills()
        my_skills = self.char_data.get('skills', [])
        prof_bonus = math.ceil(self.lvl / 4) + 1

        skill_map = {"Athletics": "str", "Acrobatics": "dex", "Stealth": "dex", "Arcana": "int", "History": "int",
                     "Investigation": "int", "Nature": "int", "Religion": "int", "Animal Handling": "wis",
                     "Insight": "wis", "Medicine": "wis", "Perception": "wis", "Survival": "wis", "Deception": "cha",
                     "Intimidation": "cha", "Performance": "cha", "Persuasion": "cha"}

        row, col = 0, 0
        for skill in all_skills:
            short = skill.split('(')[0].strip()
            eng = skill.split('(')[-1].replace(')', '').strip() if '(' in skill else short
            stat = skill_map.get(eng, 'wis')
            mod = self.mods.get(stat, 0)

            is_prof = False
            for s in my_skills:
                if eng in s or short in s: is_prof = True; break

            total = mod + (prof_bonus if is_prof else 0)
            sign = "+" if total >= 0 else ""

            dot = "⚫" if is_prof else "⚪"
            txt = f"{dot} {skill}: <b>{sign}{total}</b>"
            lbl = QLabel(txt)
            if is_prof: lbl.setStyleSheet("color: #2E7D32;")

            g_lay.addWidget(lbl, row, col)
            col += 1
            if col > 2: col = 0; row += 1

        layout.addWidget(grp)

    def _setup_spells(self, layout):
        grp = QGroupBox("Магія")
        v = QVBoxLayout(grp)
        spells = self.char_data.get('spells', [])
        if spells:
            v.addWidget(QLabel(", ".join(spells)))
        else:
            v.addWidget(QLabel("Немає відомих заклять."))
        layout.addWidget(grp)

    def _setup_features(self, layout):
        grp = QGroupBox("Особливості Класу та Раси")
        v = QVBoxLayout(grp)

        # Race features (Bonus)
        race = self.char_data.get('race')
        bonuses = self.dm.get_races_data().get(race, {}).get('bonuses', {})
        bonus_str = ", ".join([f"{k.upper()} +{v}" for k, v in bonuses.items()])
        v.addWidget(QLabel(f"<b>Расові бонуси:</b> {bonus_str}"))

        # Class features
        cls = self.char_data.get('char_class')
        spec = self.char_data.get('specialization')
        v.addWidget(QLabel(f"<b>Спеціалізація:</b> {spec if spec else 'None'}"))

        layout.addWidget(grp)

    def _calculate_mods(self, stats):
        return {k: (v - 10) // 2 for k, v in stats.items()}