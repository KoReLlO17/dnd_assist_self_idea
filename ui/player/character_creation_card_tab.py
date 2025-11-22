from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QComboBox,
    QPushButton, QGroupBox, QGridLayout, QMessageBox,
    QScrollArea, QSpinBox, QCheckBox, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt, Signal
from core.data_manager import DataManager


class CharacterCreationCardTab(QWidget):
    character_saved = Signal(dict)

    def __init__(self, dm: DataManager, parent=None):
        super().__init__(parent)
        self.dm = dm
        self.races_data = self.dm.get_races_data()
        self.classes_data = self.dm.get_classes_data()
        self.all_skills = self.dm.get_all_skills()
        self.backgrounds = self.dm.get_backgrounds()

        self.setStyleSheet("""
            QWidget { background-color: #FFF3E0; color: #333; } 
            QGroupBox { border: 2px solid #FF9800; border-radius: 8px; margin-top: 15px; background-color: white; }
            QGroupBox::title { subcontrol-origin: margin; padding: 0 10px; color: #E65100; font-weight: bold; }
            QLineEdit, QComboBox, QSpinBox { border: 1px solid #FFCC80; border-radius: 4px; padding: 5px; background-color: #FFF8E1; }
            QPushButton { background-color: #FF9800; color: white; padding: 10px; border-radius: 6px; font-weight: bold; }
            QPushButton:hover { background-color: #FB8C00; }
            QPushButton:disabled { background-color: #CFD8DC; }
        """)

        scroll_area = QScrollArea();
        scroll_area.setWidgetResizable(True)
        container = QWidget()
        self.main_layout = QVBoxLayout(container)

        self.main_layout.addWidget(QLabel("<h1>📝 Створення Персонажа</h1>"))

        self._setup_basic_info_section()
        self._setup_point_buy_section()
        self._setup_skills_section()
        self._setup_spells_section()  # НОВЕ: Секція заклять

        self.save_button = QPushButton("✅ СТВОРИТИ ПЕРСОНАЖА")
        self.save_button.clicked.connect(self._save_character)
        self.main_layout.addWidget(self.save_button)
        self.main_layout.addStretch(1)

        scroll_area.setWidget(container)
        final_layout = QVBoxLayout(self)
        final_layout.addWidget(scroll_area)

        self._update_race_bonuses()
        self._update_class_options()
        self._recalc_points()

    def _setup_basic_info_section(self):
        group = QGroupBox("Базові Відомості")
        layout = QGridLayout(group)

        self.name_input = QLineEdit()
        layout.addWidget(QLabel("Ім'я:"), 0, 0);
        layout.addWidget(self.name_input, 0, 1)

        self.level_spin = QSpinBox();
        self.level_spin.setRange(1, 20);
        self.level_spin.setValue(1)
        self.level_spin.valueChanged.connect(self._update_class_options)
        layout.addWidget(QLabel("Рівень:"), 0, 2);
        layout.addWidget(self.level_spin, 0, 3)

        self.race_combo = QComboBox();
        self.race_combo.addItems(sorted(self.races_data.keys()))
        self.race_combo.currentTextChanged.connect(self._on_race_changed)
        layout.addWidget(QLabel("Раса:"), 1, 0);
        layout.addWidget(self.race_combo, 1, 1)

        self.subrace_combo = QComboBox()
        layout.addWidget(QLabel("Підраса:"), 1, 2);
        layout.addWidget(self.subrace_combo, 1, 3)

        self.class_combo = QComboBox();
        self.class_combo.addItems(sorted(self.classes_data.keys()))
        self.class_combo.currentTextChanged.connect(self._update_class_options)
        layout.addWidget(QLabel("Клас:"), 2, 0);
        layout.addWidget(self.class_combo, 2, 1)

        self.subclass_combo = QComboBox()
        layout.addWidget(QLabel("Підклас:"), 2, 2);
        layout.addWidget(self.subclass_combo, 2, 3)

        self.specialization_combo = QComboBox()
        layout.addWidget(QLabel("Спеціалізація:"), 3, 0);
        layout.addWidget(self.specialization_combo, 3, 1)

        self.background_combo = QComboBox();
        self.background_combo.setEditable(True);
        self.background_combo.addItems(self.backgrounds)
        layout.addWidget(QLabel("Передісторія:"), 3, 2);
        layout.addWidget(self.background_combo, 3, 3)

        self.main_layout.addWidget(group)

    def _setup_point_buy_section(self):
        group = QGroupBox("Характеристики (Point Buy: 25)")
        layout = QGridLayout(group)
        self.stats_widgets = {}
        self.stat_keys = ["str", "dex", "con", "int", "wis", "cha"]
        names = ["Сила", "Спритність", "Витривалість", "Інтелект", "Мудрість", "Харизма"]

        for i, key in enumerate(self.stat_keys):
            layout.addWidget(QLabel(names[i]), i + 1, 0)
            spin = QSpinBox();
            spin.setRange(8, 15);
            spin.setValue(8)
            spin.valueChanged.connect(self._recalc_points)
            layout.addWidget(spin, i + 1, 1)

            bonus_lbl = QLabel("+0");
            bonus_lbl.setStyleSheet("color:green")
            layout.addWidget(bonus_lbl, i + 1, 2)
            total_lbl = QLabel("8");
            total_lbl.setStyleSheet("font-weight:bold")
            layout.addWidget(total_lbl, i + 1, 3)

            self.stats_widgets[key] = {"spin": spin, "bonus": bonus_lbl, "total": total_lbl}

        self.points_label = QLabel("Залишилось: 25")
        layout.addWidget(self.points_label, 8, 0, 1, 4)
        self.main_layout.addWidget(group)

    def _setup_skills_section(self):
        self.skills_group = QGroupBox("Навички")
        self.skills_layout = QGridLayout(self.skills_group)
        self.skills_limit_label = QLabel("Оберіть: 0/2")
        self.skills_layout.addWidget(self.skills_limit_label, 0, 0, 1, 3)

        self.skill_checkboxes = {}
        r, c = 1, 0
        for s in self.all_skills:
            cb = QCheckBox(s)
            cb.stateChanged.connect(self._check_skill_limit)
            self.skill_checkboxes[s] = cb
            self.skills_layout.addWidget(cb, r, c)
            c += 1
            if c > 2: c = 0; r += 1
        self.main_layout.addWidget(self.skills_group)

    def _setup_spells_section(self):
        """Секція заклять (видима тільки для магів)."""
        self.spells_group = QGroupBox("Книга Заклять")
        self.spells_group.setVisible(False)  # Спочатку прихована
        layout = QVBoxLayout(self.spells_group)

        layout.addWidget(QLabel("Оберіть початкові закляття:"))
        self.spells_list_widget = QListWidget()
        layout.addWidget(self.spells_list_widget)

        self.main_layout.addWidget(self.spells_group)

    # --- LOGIC ---
    def _on_race_changed(self, race_name):
        self.subrace_combo.clear()
        subs = self.races_data.get(race_name, {}).get('subraces', [])
        if subs:
            self.subrace_combo.addItems(subs); self.subrace_combo.setEnabled(True)
        else:
            self.subrace_combo.setEnabled(False)
        self._update_race_bonuses()

    def _update_race_bonuses(self):
        race = self.race_combo.currentText()
        bonuses = self.races_data.get(race, {}).get('bonuses', {})
        for k in self.stat_keys:
            val = bonuses.get(k, 0)
            self.stats_widgets[k]['bonus'].setText(f"+{val}")
        self._recalc_points()

    def _update_class_options(self):
        cls_name = self.class_combo.currentText()
        lvl = self.level_spin.value()
        info = self.classes_data.get(cls_name, {})

        # Subclass & Spec
        self.subclass_combo.clear();
        self.specialization_combo.clear()
        if lvl >= info.get('subclass_level', 3):
            self.subclass_combo.addItems(["Subclass A", "Subclass B"])  # Placeholder or from DM
            self.subclass_combo.setEnabled(True)
        else:
            self.subclass_combo.setEnabled(False)

        if info.get('specializations'):
            self.specialization_combo.addItems(info['specializations'])
            self.specialization_combo.setEnabled(True)
        else:
            self.specialization_combo.setEnabled(False)

        # Skills
        allowed = info.get('available_skills', [])
        self.max_skills = info.get('skills_count', 2)
        self.skills_limit_label.setText(f"Оберіть: 0/{self.max_skills}")

        for s, cb in self.skill_checkboxes.items():
            cb.setChecked(False)
            if not allowed or s in allowed:
                cb.setEnabled(True); cb.setStyleSheet("color:black")
            else:
                cb.setEnabled(False); cb.setStyleSheet("color:gray")

        # Spells
        is_caster = info.get('is_caster', False)
        self.spells_group.setVisible(is_caster)
        if is_caster:
            self.spells_list_widget.clear()
            spells = self.dm.get_spells_for_class(cls_name)
            for sp in spells:
                item = QListWidgetItem(sp)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Unchecked)
                self.spells_list_widget.addItem(item)

    def _check_skill_limit(self):
        cnt = sum(1 for cb in self.skill_checkboxes.values() if cb.isChecked())
        self.skills_limit_label.setText(f"Оберіть: {cnt}/{self.max_skills}")
        self.skills_limit_label.setStyleSheet("color:red" if cnt > self.max_skills else "color:black")

    def _recalc_points(self):
        total = 0
        cost_map = {8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9}
        for k, w in self.stats_widgets.items():
            base = w['spin'].value()
            bonus = int(w['bonus'].text().replace('+', ''))
            total += cost_map.get(base, 0)
            w['total'].setText(str(base + bonus))

        rem = 25 - total
        self.points_label.setText(f"Залишилось: {rem}")
        self.points_label.setStyleSheet("color:red" if rem < 0 else "color:green")
        self.save_button.setEnabled(rem >= 0)

    def _save_character(self):
        name = self.name_input.text().strip()
        if not name: return

        stats = {k: int(w['total'].text()) for k, w in self.stats_widgets.items()}
        skills = [s for s, cb in self.skill_checkboxes.items() if cb.isChecked()]

        # Збираємо закляття
        spells = []
        if self.spells_group.isVisible():
            for i in range(self.spells_list_widget.count()):
                item = self.spells_list_widget.item(i)
                if item.checkState() == Qt.Checked:
                    spells.append(item.text())

        char_data = {
            "name": name,
            "level": self.level_spin.value(),
            "race": self.race_combo.currentText(),
            "subrace": self.subrace_combo.currentText(),
            "char_class": self.class_combo.currentText(),
            "subclass": self.subclass_combo.currentText(),
            "specialization": self.specialization_combo.currentText(),
            "background": self.background_combo.currentText(),
            "stats": stats,
            "skills": skills,
            "spells": spells,  # Нове
            "conditions": {"physical_exhaustion": 0, "morale": 10},
            "inventory": {}  # Порожній інвентар
        }

        if self.dm.save_character(char_data):
            self.character_saved.emit(char_data)