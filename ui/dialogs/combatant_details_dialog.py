from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QFrame
from PySide6.QtCore import Qt


class CombatantDetailsDialog(QDialog):
    def __init__(self, name, token_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Інфо: {name}")
        self.setFixedSize(300, 200)

        layout = QVBoxLayout(self)

        # Avatar / Icon placeholder
        icon_lbl = QLabel(name[:1].upper())
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet(
            f"font-size: 40px; font-weight: bold; color: {token_data.get('color', 'black')}; border: 2px solid gray; border-radius: 10px;")
        icon_lbl.setFixedSize(60, 60)

        h_top = QHBoxLayout()
        h_top.addWidget(icon_lbl)
        h_top.addWidget(QLabel(f"<b>{name}</b>"))
        layout.addLayout(h_top)

        # Status Info
        info_frame = QFrame()
        info_frame.setStyleSheet("background-color: #ECEFF1; border-radius: 5px; padding: 5px;")
        i_lay = QVBoxLayout(info_frame)
        i_lay.addWidget(QLabel(f"Тип: {token_data.get('type', 'Unknown').upper()}"))
        # Тут можна додати реальні HP, якщо вони є в token_data
        hp = token_data.get('hp', '???')
        i_lay.addWidget(QLabel(f"HP: {hp}"))
        layout.addWidget(info_frame)

        # Full Sheet Button
        btn_sheet = QPushButton("Відкрити Повний Лист")
        btn_sheet.setStyleSheet("background-color: #607D8B; color: white; font-weight: bold; padding: 8px;")
        layout.addWidget(btn_sheet)

        btn_close = QPushButton("Закрити")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)