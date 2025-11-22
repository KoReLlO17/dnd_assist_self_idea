import sys
import os

# Додаємо поточну директорію в шлях, щоб Python бачив пакети 'core' та 'ui'
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from core.app import App

# Глобальні змінні середовища (Mock)
if '__app_id' not in globals(): globals()['__app_id'] = 'dnd-app-local'

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Запуск Лаунчера
    window = App()
    window.show()

    sys.exit(app.exec())