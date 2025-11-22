from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import QTimer, Qt
import random
from core.dice_logic import DiceLogic
from core.fuzzy_logic import FuzzyLogic


class RollDialog(QDialog):
    def __init__(self, title, formula, description="", parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"🎲 {title}")
        self.setFixedSize(450, 320)
        self.formula = formula
        self.description = description

        self.final_total = 0
        self.final_raw = 0
        self.final_mod = 0
        self.final_details = ""

        self.setStyleSheet("""
            QDialog { background-color: #263238; color: #ECEFF1; }
            QLabel { font-family: 'Segoe UI', sans-serif; }

            #TitleLabel { font-size: 20px; font-weight: bold; color: #80DEEA; letter-spacing: 1px; }
            #ContextLabel { font-size: 14px; color: #CFD8DC; font-style: italic; margin: 8px; background-color: #37474F; padding: 5px; border-radius: 4px; }

            #ResultLabel { font-size: 72px; font-weight: bold; color: #FFF; }

            #FuzzyLabel { font-size: 26px; font-weight: bold; margin-top: 10px; text-transform: uppercase; }
            #ReasonLabel { font-size: 14px; color: #B0BEC5; }

            QPushButton { 
                background-color: #00838F; color: white; 
                border: none; padding: 12px; border-radius: 6px; font-weight: bold; font-size: 16px;
            }
            QPushButton:hover { background-color: #0097A7; }
        """)

        layout = QVBoxLayout(self)

        lbl_title = QLabel(f"{title.upper()}")
        lbl_title.setObjectName("TitleLabel")
        lbl_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_title)

        if self.description:
            ctx_lbl = QLabel(f"\"{self.description}\"")
            ctx_lbl.setObjectName("ContextLabel")
            ctx_lbl.setAlignment(Qt.AlignCenter)
            ctx_lbl.setWordWrap(True)
            layout.addWidget(ctx_lbl)

        self.result_label = QLabel("...")
        self.result_label.setObjectName("ResultLabel")
        self.result_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.result_label)

        self.fuzzy_label = QLabel("")
        self.fuzzy_label.setObjectName("FuzzyLabel")
        self.fuzzy_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.fuzzy_label)

        self.reason_label = QLabel("Визначення долі...")
        self.reason_label.setObjectName("ReasonLabel")
        self.reason_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.reason_label)

        self.close_btn = QPushButton("Прийняти Наслідки")
        self.close_btn.clicked.connect(self.accept)
        self.close_btn.setVisible(False)
        layout.addWidget(self.close_btn)

        self.perform_roll()

    def perform_roll(self):
        total, details = DiceLogic.roll(self.formula)
        try:
            parts = details.split(']')
            raw_part = parts[0].replace('[', '')
            raw_roll = int(raw_part.split(',')[0])
            mod = total - raw_roll
        except:
            raw_roll = total
            mod = 0

        self.final_total = total
        self.final_raw = raw_roll
        self.final_mod = mod
        self.final_details = details

        self.animation_steps = 10
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate_step)
        self.timer.start(50)

    def _animate_step(self):
        if self.animation_steps > 0:
            fake = random.randint(1, 20)
            self.result_label.setText(str(fake))
            self.animation_steps -= 1
        else:
            self.timer.stop()
            self.result_label.setText(str(self.final_total))

            fuzzy_res, fuzzy_reason = FuzzyLogic.calculate_outcome(self.final_raw, self.final_mod)

            self.fuzzy_label.setText(fuzzy_res)
            self.reason_label.setText(f"{fuzzy_reason}\n({self.final_details})")

            # Колірна гама (Наративна)
            color = "#B0BEC5"
            if "КРИТИЧНИЙ ПРОВАЛ" in fuzzy_res:
                color = "#D32F2F"  # Deep Red
            elif "Провал з наслідками" in fuzzy_res:
                color = "#E57373"  # Soft Red
            elif "Успіх з ускладненням" in fuzzy_res:
                color = "#FFB74D"  # Orange
            elif "Чистий Успіх" in fuzzy_res:
                color = "#81C784"  # Light Green
            elif "Впевнений" in fuzzy_res:
                color = "#4CAF50"  # Green
            elif "ЛЕГЕНДАРНО" in fuzzy_res:
                color = "#FFD700"  # Gold

            self.fuzzy_label.setStyleSheet(f"color: {color};")
            self.close_btn.setVisible(True)