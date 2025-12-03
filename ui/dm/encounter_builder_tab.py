import json
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
    QGroupBox, QSplitter, QMessageBox, QRadioButton, QButtonGroup, QApplication, QFrame
)
from PySide6.QtCore import Qt, QTimer, QMimeData, QPoint
from PySide6.QtGui import QDrag, QPixmap, QPainter, QColor, QBrush, QPen
from core.data_manager import DataManager
from ui.widgets.battle_map_widget import BattleMapWidget


class DraggableTokenLabel(QLabel):
    """
    Віджет-токен, який можна перетягувати мишкою на мапу.
    Відображає попередній вигляд (колір, літеру).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(60, 60)
        self.data_type = "monster"  # 'monster' or 'object'
        self.data_key = ""
        self.token_color = "#999"
        self.token_text = "?"
        self.setStyleSheet("border: 2px dashed #555; border-radius: 30px; background-color: #333;")
        self.setCursor(Qt.OpenHandCursor)
        self.setToolTip("Перетягніть мене на мапу!")
        self.drag_start_pos = None  # Ініціалізація

    def configure(self, data_type, key, name, color):
        self.data_type = data_type
        self.data_key = key
        self.token_text = name[:1].upper() if name else "?"
        self.token_color = color
        self.update()  # Перемалювати

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Малюємо коло
        painter.setBrush(QBrush(QColor(self.token_color)))
        painter.setPen(QPen(Qt.black, 2))
        rect = self.rect().adjusted(2, 2, -2, -2)
        painter.drawEllipse(rect)

        # Малюємо літеру
        painter.setPen(QColor("white"))
        font = painter.font()
        font.setBold(True)
        font.setPointSize(20)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignCenter, self.token_text)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)

    def mouseReleaseEvent(self, event):
        self.setCursor(Qt.OpenHandCursor)
        self.drag_start_pos = None

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton): return
        if not self.drag_start_pos: return

        if (event.pos() - self.drag_start_pos).manhattanLength() < QApplication.startDragDistance(): return

        # Починаємо перетягування
        drag = QDrag(self)
        mime_data = QMimeData()

        # Передаємо дані у форматі "type:key" (наприклад "monster:goblin")
        mime_data.setText(f"{self.data_type}:{self.data_key}")
        drag.setMimeData(mime_data)

        # Створюємо напівпрозору картинку для візуалізації процесу
        pixmap = QPixmap(self.size())
        pixmap.fill(Qt.transparent)
        self.render(pixmap)
        drag.setPixmap(pixmap)
        # Центруємо хотспот (курсор по центру картинки)
        drag.setHotSpot(QPoint(pixmap.width() // 2, pixmap.height() // 2))

        drag.exec(Qt.CopyAction)
        self.setCursor(Qt.OpenHandCursor)


class DroppableBattleMapWidget(BattleMapWidget):
    """
    Розширена версія мапи, яка вміє приймати Drop події.
    """

    def __init__(self, dm, is_dm=True, parent=None):
        super().__init__(is_dm=is_dm, parent=parent)
        self.dm = dm
        self.setAcceptDrops(True)  # Обов'язково дозволяємо кидати сюди об'єкти

    def dragEnterEvent(self, event):
        # Перевіряємо, чи є текст у перетягуваному об'єкті
        if event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        # Потрібно для того, щоб курсор показував "можна кидати"
        event.acceptProposedAction()

    def dropEvent(self, event):
        text_data = event.mimeData().text()
        if ":" not in text_data:
            event.ignore()
            return

        dtype, key = text_data.split(":", 1)

        # Визначаємо координати клітинки, куди кинули
        pos = event.position()
        col = int(pos.x() // self.grid_size)
        row = int(pos.y() // self.grid_size)

        # Обмеження межами поля
        col = max(0, min(col, self.cols - 1))
        row = max(0, min(row, self.rows - 1))

        uid = None
        if dtype == "monster":
            # Викликаємо метод додавання істоти з вказанням позиції
            uid = self.dm.add_creature_to_combat(key)
        elif dtype == "object":
            try:
                uid = self.dm.add_object_to_combat(key)
            except AttributeError:
                print("DataManager missing add_object_to_combat")

        if uid:
            # Одразу переміщуємо створений токен на правильну клітинку
            self.dm.move_token(uid, col, row, is_dm=True)

            # Примусово оновлюємо відображення, щоб уникнути затримки
            st = self.dm.get_combat_state()
            self.update_state(st.get("tokens", {}))

            print(f"Dropped {dtype} '{key}' at {col}, {row}")  # Debug log

        event.acceptProposedAction()


class EncounterBuilderTab(QWidget):
    """
    Вкладка підготовки до бою (Drag & Drop версія).
    """

    def __init__(self, dm: DataManager, parent=None):
        super().__init__(parent)
        self.dm = dm

        layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Horizontal)

        # --- ПАНЕЛЬ ІНСТРУМЕНТІВ ---
        tools_widget = QWidget()
        tools_layout = QVBoxLayout(tools_widget)

        tools_layout.addWidget(QLabel("<h3>🛠️ Палітра</h3>"))

        # --- ГРУПА 1: МОНСТРИ ---
        mon_grp = QGroupBox("Монстри")
        mon_l = QVBoxLayout(mon_grp)

        # Секція вибору
        mon_h = QHBoxLayout()
        self.combo_monsters = QComboBox()
        # Заповнюємо список монстрів (безпечно)
        bestiary = self.dm.get_bestiary()
        if bestiary:
            self.combo_monsters.addItems(sorted(bestiary.keys()))
        else:
            self.combo_monsters.addItem("No Monsters Loaded")

        self.combo_monsters.currentTextChanged.connect(self._update_monster_preview)

        # Токен для перетягування
        self.token_monster = DraggableTokenLabel()

        mon_h.addWidget(self.combo_monsters, 1)
        mon_h.addWidget(self.token_monster)

        mon_l.addLayout(mon_h)
        mon_l.addWidget(QLabel("<small><i>Перетягніть кружечок на мапу -></i></small>", alignment=Qt.AlignRight))
        tools_layout.addWidget(mon_grp)

        # --- ГРУПА 2: ОБ'ЄКТИ ---
        obj_grp = QGroupBox("Об'єкти")
        obj_l = QVBoxLayout(obj_grp)

        obj_h = QHBoxLayout()
        self.combo_objects = QComboBox()
        self.combo_objects.addItems(["wall", "barrel", "trap", "chest"])
        self.combo_objects.currentTextChanged.connect(self._update_object_preview)

        self.token_object = DraggableTokenLabel()

        obj_h.addWidget(self.combo_objects, 1)
        obj_h.addWidget(self.token_object)

        obj_l.addLayout(obj_h)
        obj_l.addWidget(QLabel("<small><i>Стіни, пастки, скрині...</i></small>", alignment=Qt.AlignRight))
        tools_layout.addWidget(obj_grp)

        # --- ІНСТРУМЕНТИ МАПИ ---
        mode_grp = QGroupBox("Інструменти Мапи")
        mode_l = QVBoxLayout(mode_grp)

        self.btn_select = QPushButton("👆 Курсор (Вибір)")
        self.btn_select.setCheckable(True)
        self.btn_select.setChecked(True)
        self.btn_select.clicked.connect(lambda: self._set_drag_mode(False))

        self.btn_move = QPushButton("✋ Рука (Переміщення)")
        self.btn_move.setCheckable(True)
        self.btn_move.clicked.connect(lambda: self._set_drag_mode(True))

        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.btn_select)
        self.mode_group.addButton(self.btn_move)
        # Підключення методу _update_btn_style
        self.mode_group.buttonToggled.connect(self._update_btn_style)

        mode_l.addWidget(self.btn_select)
        mode_l.addWidget(self.btn_move)

        btn_clear = QPushButton("🗑️ Очистити все")
        btn_clear.setStyleSheet("background-color: #D32F2F; color: white; margin-top: 10px;")
        btn_clear.clicked.connect(self._clear_map)
        mode_l.addWidget(btn_clear)

        tools_layout.addWidget(mode_grp)
        tools_layout.addStretch()

        splitter.addWidget(tools_widget)

        # --- МАПА ---
        map_cont = QWidget()
        map_l = QVBoxLayout(map_cont)
        self.lbl_hint = QLabel("Режим вибору", alignment=Qt.AlignCenter)
        map_l.addWidget(self.lbl_hint)

        # Використовуємо наш новий клас з підтримкою Drop
        self.map_widget = DroppableBattleMapWidget(dm=self.dm, is_dm=True)
        self.map_widget.token_moved.connect(lambda u, x, y: self.dm.move_token(u, x, y, is_dm=True))
        self.map_widget.token_clicked.connect(self._on_token_click)

        map_l.addWidget(self.map_widget)
        splitter.addWidget(map_cont)

        splitter.setSizes([300, 900])
        layout.addWidget(splitter)

        # Таймер оновлення
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._refresh_map)
        self.timer.start(500)

        # Ініціалізація прев'ю
        self._update_monster_preview()
        self._update_object_preview()
        self._set_drag_mode(False)  # Default state

    # --- МЕТОДИ КЛАСУ ---

    def _update_monster_preview(self):
        key = self.combo_monsters.currentText()
        bestiary = self.dm.get_bestiary()
        if bestiary:
            data = bestiary.get(key)
            if data:
                self.token_monster.configure("monster", key, data['name'], "#D32F2F")
            else:
                self.token_monster.configure("monster", key, "?", "#999")

    def _update_object_preview(self):
        key = self.combo_objects.currentText()
        colors = {"wall": "#607D8B", "barrel": "#FF5722", "trap": "#9E9E9E", "chest": "#FFC107"}
        name_map = {"wall": "Стіна", "barrel": "Бочка", "trap": "Пастка", "chest": "Скриня"}
        self.token_object.configure("object", key, name_map.get(key, key), colors.get(key, "#AAA"))

    def _set_drag_mode(self, enabled):
        self.map_widget.set_drag_mode(enabled)
        self.btn_select.setChecked(not enabled)
        self.btn_move.setChecked(enabled)

        if enabled:
            self.lbl_hint.setText("✋ Режим переміщення АКТИВНИЙ. Можна совати токени на мапі.")
            self.lbl_hint.setStyleSheet("color: #4CAF50; font-weight: bold;")
        else:
            self.lbl_hint.setText("👆 Режим вибору. Перетягування токенів на мапі заблоковано.")
            self.lbl_hint.setStyleSheet("color: #757575;")

    def _update_btn_style(self, btn, checked):
        """Оновлює стиль активної кнопки режиму."""
        if checked:
            btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        else:
            btn.setStyleSheet("")

    def _clear_map(self):
        if QMessageBox.question(self, "Очистити", "Видалити ВСІ об'єкти з мапи?") == QMessageBox.Yes:
            self.dm.update_combat_state({"tokens": {}})
            self._refresh_map()

    def _on_token_click(self, uid):
        pass

    def _refresh_map(self):
        st = self.dm.get_combat_state()
        self.map_widget.update_state(st.get("tokens", {}))