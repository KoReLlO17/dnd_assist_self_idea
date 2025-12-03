from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, Signal, QRectF, QUrl
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest


class BattleMapWidget(QWidget):
    """
    Віджет бойової мапи.
    Малює сітку та токени. Підтримує вибір (token_clicked) та перетягування.
    Тепер підтримує відображення зображень на токенах.
    """
    token_moved = Signal(str, int, int)
    token_clicked = Signal(str)  # Сигнал вибору токена

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

        # Режим дозволу на перетягування (за замовчуванням False)
        self.drag_enabled = False

        # Кеш для зображень {uid: QPixmap}
        self.image_cache = {}
        self.network_manager = QNetworkAccessManager()
        self.network_manager.finished.connect(self._on_image_loaded)

        # Встановлюємо фіксований розмір або мінімальний
        self.setMinimumSize(self.cols * self.grid_size + 1, self.rows * self.grid_size + 1)
        self.setStyleSheet("background-color: #263238;")

        # Дозволяємо віджету приймати фокус
        self.setFocusPolicy(Qt.StrongFocus)

    def set_drag_mode(self, enabled: bool):
        """Вмикає або вимикає можливість перетягування токенів."""
        self.drag_enabled = enabled
        if enabled:
            self.setCursor(Qt.OpenHandCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

    def update_state(self, tokens_data):
        if tokens_data is None:
            tokens_data = {}

        self.tokens = tokens_data

        # Завантажуємо зображення для нових токенів, якщо є URL
        for uid, data in self.tokens.items():
            img_url = data.get('image_url')
            if img_url and uid not in self.image_cache:
                # Це placeholder, тут має бути запит на завантаження
                # Для простоти можна використовувати локальні файли або QNetworkAccessManager
                # Поки що, якщо це URL, ініціюємо завантаження
                if img_url.startswith("http"):
                    self._start_image_download(uid, img_url)

        self.update()

    def _start_image_download(self, uid, url):
        # Щоб уникнути повторних завантажень, поки чекаємо
        self.image_cache[uid] = None
        request = QNetworkRequest(QUrl(url))
        # Зберігаємо uid в атрибут запиту, щоб знати для кого це
        reply = self.network_manager.get(request)
        reply.setProperty("uid", uid)

    def _on_image_loaded(self, reply):
        uid = reply.property("uid")
        if reply.error():
            print(f"Image load error for {uid}: {reply.errorString()}")
        else:
            data = reply.readAll()
            pixmap = QPixmap()
            pixmap.loadFromData(data)
            if not pixmap.isNull():
                self.image_cache[uid] = pixmap
                self.update()  # Перемалювати мапу з новою картинкою
        reply.deleteLater()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 1. Сітка
        pen = QPen(QColor("#546E7A"))
        pen.setWidth(1)
        painter.setPen(pen)

        # Draw Grid
        for c in range(self.cols + 1):
            x = c * self.grid_size
            painter.drawLine(x, 0, x, self.rows * self.grid_size)
        for r in range(self.rows + 1):
            y = r * self.grid_size
            painter.drawLine(0, y, self.cols * self.grid_size, y)

        # 2. Токени
        if not self.tokens:
            return

        for uid, data in self.tokens.items():
            try:
                grid_x = int(data.get('x', 0))
                grid_y = int(data.get('y', 0))

                x_px = grid_x * self.grid_size
                y_px = grid_y * self.grid_size
                margin = 2
                rect = QRectF(x_px + margin, y_px + margin,
                              self.grid_size - margin * 2, self.grid_size - margin * 2)

                # Підсвітка виділення
                if uid == self.selected_token_uid:
                    painter.setPen(QPen(QColor("#FFEB3B"), 3))
                    painter.setBrush(Qt.NoBrush)
                    halo_rect = rect.adjusted(-2, -2, 2, 2)
                    painter.drawRect(halo_rect)

                # Спробуємо намалювати зображення
                pixmap = self.image_cache.get(uid)
                if pixmap:
                    # Малюємо зображення, масштабуючи його в rect
                    painter.setRenderHint(QPainter.SmoothPixmapTransform)

                    # Створюємо круглу маску (опціонально, для краси)
                    path = QPainterPath()
                    path.addEllipse(rect)
                    painter.setClipPath(path)

                    painter.drawPixmap(rect.toRect(), pixmap)

                    # Скидаємо кліп, щоб не обрізати наступні елементи (рамку)
                    painter.setClipping(False)

                    # Малюємо рамку поверх
                    token_type = data.get('type', 'monster')
                    border_color = Qt.red if token_type == 'enemy' else Qt.green if token_type == 'player' else Qt.gray
                    painter.setPen(QPen(border_color, 2))
                    painter.setBrush(Qt.NoBrush)
                    painter.drawEllipse(rect)

                else:
                    # Fallback: Малюємо кольорове коло з літерою (як раніше)
                    color_hex = data.get('color', '#999')
                    color = QColor(color_hex)
                    if not color.isValid(): color = QColor("#999")

                    painter.setBrush(QBrush(color))
                    painter.setPen(QPen(Qt.black, 2))

                    token_type = data.get('type', 'monster')
                    if token_type == 'object':
                        painter.drawRect(rect)
                    else:
                        painter.drawEllipse(rect)

                    name = str(data.get('name', '?'))
                    symbol = data.get('symbol')
                    if not symbol:
                        symbol = name[:2].upper() if len(name) > 1 else name[:1].upper()

                    painter.setPen(QColor("white"))
                    font = QFont("Arial", 10, QFont.Bold)
                    painter.setFont(font)
                    painter.drawText(rect, Qt.AlignCenter, symbol)

            except Exception as e:
                print(f"Error drawing token {uid}: {e}")

    def mousePressEvent(self, event):
        col = int(event.position().x() // self.grid_size)
        row = int(event.position().y() // self.grid_size)

        clicked_token_uid = None

        # Шукаємо токен на цій клітинці
        for uid, data in list(self.tokens.items()):
            if int(data.get('x', -1)) == col and int(data.get('y', -1)) == row:
                clicked_token_uid = uid
                break

        if clicked_token_uid:
            self.token_clicked.emit(clicked_token_uid)

            can_control = self.is_dm or clicked_token_uid == self.my_uid

            if can_control:
                self.selected_token_uid = clicked_token_uid
                self.update()

                if self.drag_enabled:
                    self.dragging = True
                    self.setCursor(Qt.ClosedHandCursor)
        else:
            self.selected_token_uid = None
            self.update()

    def mouseReleaseEvent(self, event):
        if self.dragging and self.selected_token_uid:
            col = int(event.position().x() // self.grid_size)
            row = int(event.position().y() // self.grid_size)

            col = max(0, min(col, self.cols - 1))
            row = max(0, min(row, self.rows - 1))

            self.token_moved.emit(self.selected_token_uid, col, row)

        self.dragging = False
        if self.drag_enabled:
            self.setCursor(Qt.OpenHandCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
        self.update()