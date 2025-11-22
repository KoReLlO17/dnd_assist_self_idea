from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QFrame
from PySide6.QtCore import QTimer, Qt
import random
from core.dice_logic import DiceLogic
import math


class DualRollDialog(QDialog):
    """
    Діалог з динамічними порогами криту/провалу (Fuzzy Logic).
    """

    def __init__(self, attack_name, attack_mod, skill_name, skill_mod, maneuver_data, armor_ac=0, crit_range=20,
                 fumble_range=1, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"⚔️ {attack_name} + {skill_name}")
        self.setFixedSize(600, 450)

        self.attack_mod = attack_mod
        self.skill_mod = skill_mod
        self.atk_name = attack_name
        self.sk_name = skill_name
        self.m_data = maneuver_data
        self.crit_range = crit_range
        self.fumble_range = fumble_range

        self.result_msg = ""

        self.setStyleSheet("""
            QDialog { background-color: #263238; color: white; }
            QLabel { font-family: 'Segoe UI'; }
            .DiceBox { background-color: #37474F; border-radius: 10px; border: 2px solid #546E7A; padding: 10px; }
            .DiceVal { font-size: 48px; font-weight: bold; color: white; }
            .FinalLbl { font-size: 24px; font-weight: bold; color: #4FC3F7; }
            .ResultBox { background-color: #212121; border-radius: 8px; padding: 15px; margin-top: 10px; border: 1px solid #424242; }
            .EffectText { font-size: 22px; font-weight: bold; color: #FFD54F; }
            .InfoText { font-size: 12px; color: #B0BEC5; font-style: italic; margin-bottom: 10px;}
            QPushButton { background-color: #00897B; color: white; padding: 12px; border-radius: 6px; font-weight: bold; font-size: 16px; border: none; }
            QPushButton:hover { background-color: #009688; }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(QLabel("БОЙОВИЙ МАНЕВР", alignment=Qt.AlignCenter), 0)

        # Інфо про пороги
        ranges_info = f"Діапазони (Fuzzy): Крит ≥ {self.crit_range} | Провал ≤ {self.fumble_range}"
        main_layout.addWidget(QLabel(ranges_info, alignment=Qt.AlignCenter, objectName="InfoText"))

        # Dice Area
        dice_layout = QHBoxLayout()

        # Attack
        self.atk_frame = QFrame()
        self.atk_frame.setProperty("class", "DiceBox")
        atk_l = QVBoxLayout(self.atk_frame)
        atk_l.addWidget(QLabel(f"⚔️ Атака", alignment=Qt.AlignCenter))
        self.lbl_atk_val = QLabel("...")
        self.lbl_atk_val.setProperty("class", "DiceVal");
        self.lbl_atk_val.setAlignment(Qt.AlignCenter)
        atk_l.addWidget(self.lbl_atk_val)
        sign = "+" if attack_mod >= 0 else ""
        atk_l.addWidget(QLabel(f"1d20 {sign}{attack_mod}", alignment=Qt.AlignCenter))
        self.lbl_atk_final = QLabel("");
        self.lbl_atk_final.setProperty("class", "FinalLbl");
        self.lbl_atk_final.setAlignment(Qt.AlignCenter)
        atk_l.addWidget(self.lbl_atk_final)
        dice_layout.addWidget(self.atk_frame)

        # Skill
        self.skill_frame = QFrame()
        self.skill_frame.setProperty("class", "DiceBox")
        sk_l = QVBoxLayout(self.skill_frame)
        sk_l.addWidget(QLabel(f"✨ {self.sk_name}", alignment=Qt.AlignCenter))
        self.lbl_sk_val = QLabel("...")
        self.lbl_sk_val.setProperty("class", "DiceVal");
        self.lbl_sk_val.setAlignment(Qt.AlignCenter)
        sk_l.addWidget(self.lbl_sk_val)
        sign2 = "+" if skill_mod >= 0 else ""
        self.lbl_sk_mod = QLabel(f"Mod: {sign2}{skill_mod}", alignment=Qt.AlignCenter)
        sk_l.addWidget(self.lbl_sk_mod)
        dice_layout.addWidget(self.skill_frame)

        main_layout.addLayout(dice_layout)

        # Result
        self.res_frame = QFrame()
        self.res_frame.setProperty("class", "ResultBox")
        res_l = QVBoxLayout(self.res_frame)
        self.lbl_effect_val = QLabel("Розрахунок...")
        self.lbl_effect_val.setProperty("class", "EffectText")
        self.lbl_effect_val.setAlignment(Qt.AlignCenter)
        self.lbl_effect_val.setWordWrap(True)
        res_l.addWidget(self.lbl_effect_val)
        main_layout.addWidget(self.res_frame)

        self.close_btn = QPushButton("Зафіксувати")
        self.close_btn.clicked.connect(self.accept)
        self.close_btn.setVisible(False)
        main_layout.addWidget(self.close_btn)

        self.steps = 15
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate)
        self.timer.start(50)

    def _animate(self):
        if self.steps > 0:
            self.lbl_atk_val.setText(str(random.randint(1, 20)))
            self.lbl_sk_val.setText(str(random.randint(1, 20)))
            self.steps -= 1
        else:
            self.timer.stop()
            self._calculate_results()

    def _calculate_results(self):
        raw_atk = random.randint(1, 20)
        raw_skill = random.randint(1, 20)

        self.lbl_atk_val.setText(str(raw_atk))
        self.lbl_sk_val.setText(str(raw_skill))

        total_atk = raw_atk + self.attack_mod
        self.lbl_atk_final.setText(f"= {total_atk}")

        # --- РОЗРАХУНОК ЕФЕКТУ (з урахуванням Fuzzy порогів) ---

        is_crit = (raw_atk >= self.crit_range)  # Динамічний поріг
        is_fumble = (raw_atk <= self.fumble_range)  # Динамічний поріг

        # Базовий ефект
        base_effect = self.skill_mod
        if is_crit: base_effect *= 2

        formula = self.m_data.get('effect_formula', 'mod')

        val1 = 0;
        val2 = 0

        if formula == "mod":
            val1 = base_effect
        elif formula == "mod_plus_armor":
            val1 = base_effect  # (спрощено для демо)
        elif formula == "half_mod_split":
            half = math.floor(base_effect / 2)
            val1 = half;
            val2 = half
        elif formula == "move_special":
            val1 = 1;
            val2 = 1

        hit_status = "Влучання"
        apply_effect = True

        if is_fumble:
            apply_effect = False
            hit_status = f"Провал (1-{self.fumble_range})"
            self.lbl_atk_val.setStyleSheet("color: #FF5252;")
        elif total_atk < 10:
            apply_effect = False
            hit_status = "Промах"
            self.lbl_atk_val.setStyleSheet("color: gray;")
        elif is_crit:
            hit_status = f"КРИТ! ({self.crit_range}-20)"
            self.lbl_atk_val.setStyleSheet("color: #FFD700;")
        else:
            self.lbl_atk_val.setStyleSheet("color: #66BB6A;")

        t_type = self.m_data.get('type')
        res_str = "Нічого"

        if apply_effect and (val1 > 0 or val2 > 0):
            if t_type == "physical":
                res_str = f"💪 -{val1} Фіз. Втоми"
            elif t_type == "morale":
                res_str = f"😱 -{val1} Моралі"
            elif t_type == "hybrid":
                if formula == "move_special":
                    res_str = f"🏃 +1 Втоми ворогу, +1 Підтримки собі"
                else:
                    res_str = f"✨ -{val1} Втоми ТА -{val2} Моралі"
            elif t_type == "support":
                res_str = f"❤️ +{val1} Підтримки"
        elif not apply_effect:
            res_str = "Дія не вдалася"
        else:
            res_str = "Ефект 0"

        final_text = f"{hit_status}\n👉 {res_str}"
        self.lbl_effect_val.setText(final_text)

        self.result_msg = (
            f"⚔️ <b>{self.atk_name}</b> ({total_atk}) + ✨ <b>{self.sk_name}</b><br>"
            f"🎲 Результат: {res_str}"
        )

        self.close_btn.setVisible(True)