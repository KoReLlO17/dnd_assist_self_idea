from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont


class BattleMapWidget(QWidget):
    token_moved = Signal(str, int, int)
    token_clicked = Signal(str)

    def __init__(self, is_dm=False, my_uid=None, parent=None):
        super().__init__(parent)
        self.is_dm = is_dm
        self.my_uid = my_uid
        self.grid_size = 40
        self.cols = 20
        self.rows = 15
        self.tokens = {}
        self.selected_token_uid = None
        self.dragging = False
        self.setMinimumSize(self.cols * self.grid_size + 1, self.rows * self.grid_size + 1)
        self.setStyleSheet("background-color: #263238;")

    def update_state(self, tokens_data):
        self.tokens = tokens_data
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor("#546E7A"))
        pen.setWidth(1)
        painter.setPen(pen)

        for c in range(self.cols + 1):
            x = c * self.grid_size
            painter.drawLine(x, 0, x, self.rows * self.grid_size)
        for r in range(self.rows + 1):
            y = r * self.grid_size
            painter.drawLine(0, y, self.cols * self.grid_size, y)

        for uid, data in self.tokens.items():
            x_px = data.get('x', 0) * self.grid_size
            y_px = data.get('y', 0) * self.grid_size
            color = QColor(data.get('color', '#999'))
            if uid == self.selected_token_uid:
                color = color.lighter(150)

            painter.setBrush(QBrush(color))
            painter.setPen(Qt.NoPen)
            rect = QRectF(x_px + 4, y_px + 4, self.grid_size - 8, self.grid_size - 8)
            painter.drawEllipse(rect)

            name = data.get('name', '?')
            painter.setPen(QColor("white"))
            painter.setFont(QFont("Arial", 10, QFont.Bold))
            painter.drawText(rect, Qt.AlignCenter, name[:1].upper() if name else "?")

    def mousePressEvent(self, event):
        col = int(event.position().x() // self.grid_size)
        row = int(event.position().y() // self.grid_size)
        clicked_token_uid = None
        for uid, data in self.tokens.items():
            if data.get('x') == col and data.get('y') == row:
                clicked_token_uid = uid
                break

        if clicked_token_uid:
            self.token_clicked.emit(clicked_token_uid)
            if self.is_dm or clicked_token_uid == self.my_uid:
                self.selected_token_uid = clicked_token_uid
                self.dragging = True
                self.update()

    def mouseReleaseEvent(self, event):
        if self.dragging and self.selected_token_uid:
            col = max(0, min(int(event.position().x() // self.grid_size), self.cols - 1))
            row = max(0, min(int(event.position().y() // self.grid_size), self.rows - 1))
            self.token_moved.emit(self.selected_token_uid, col, row)
        self.dragging = False
        self.update()