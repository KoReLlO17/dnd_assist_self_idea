from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTabWidget, QLabel, QMessageBox
)
from PySide6.QtGui import QIcon
from core.data_manager import DataManager

try:
    from ui.dm.dm_hosting.hosting_window import HostingTab
    from ui.dm.dm_hosting.scenario_tab import ScenarioTab
    from ui.dm.creature_item_redactor.item_creator_tab import ItemCreatorTab
    from ui.dm.creature_item_redactor.scenario_tree_tab import ScenarioTreeTab
    from ui.dm.inventory_manager_tab import InventoryManagerTab
    from ui.dm.combat_manager_tab import CombatManagerTab  # NEW IMPORT
except ImportError:
    # Fallback for simpler structure if files are flat
    from ui.dm.hosting_window import HostingTab
    from ui.dm.scenario_tab import ScenarioTab
    from ui.dm.item_creator_tab import ItemCreatorTab
    from ui.dm.scenario_tree_tab import ScenarioTreeTab
    from ui.dm.combat_manager_tab import CombatManagerTab


class DM_MainWindow(QMainWindow):
    """
    Головне вікно для Майстра Підземель (DM).
    Глобальна Темна Тема.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Майстер Підземель: Панель Керування")
        self.resize(1200, 850)

        self.dm = DataManager()

        try:
            self.server_ip = self.dm.start_server()
            QMessageBox.information(
                self,
                "Сервер Запущено",
                f"Ваш IP: {self.server_ip}\nГравці вводять: {self.server_ip}/[ID]"
            )
        except Exception as e:
            QMessageBox.warning(self, "Увага", f"Помилка сервера: {e}")

        # --- DARK THEME ---
        self.setStyleSheet("""
            QMainWindow, QWidget { background-color: #121212; color: #E0E0E0; font-family: 'Segoe UI'; }

            QTabWidget::pane { border: 1px solid #333; background: #1E1E1E; }
            QTabBar::tab {
                background: #2D2D2D; color: #AAA; padding: 10px 20px;
                border-top-left-radius: 4px; border-top-right-radius: 4px; margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: #3E3E42; color: #FFF; border-bottom: 2px solid #007ACC; font-weight: bold;
            }
            QTabBar::tab:hover { background: #333; }

            QGroupBox {
                border: 1px solid #3E3E42; border-radius: 6px; margin-top: 20px;
                background-color: #1E1E1E; font-weight: bold; color: #CCC;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #007ACC; }

            QLineEdit, QTextEdit, QListWidget, QComboBox, QSpinBox {
                background-color: #252526; color: white; border: 1px solid #555; border-radius: 4px; padding: 4px;
            }

            QPushButton {
                background-color: #0D47A1; color: white; border: none; padding: 8px 16px;
                border-radius: 4px; font-weight: bold;
            }
            QPushButton:hover { background-color: #1565C0; }
            QPushButton:disabled { background-color: #333; color: #666; }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        header_label = QLabel(f"Dungeon Master Center (IP: {getattr(self, 'server_ip', 'Unknown')})")
        header_label.setStyleSheet("color: #007ACC; font-size: 18px; font-weight: bold; padding: 10px;")
        main_layout.addWidget(header_label)

        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        self.hosting_tab = HostingTab(dm=self.dm)
        self.tabs.addTab(self.hosting_tab, "📡 Хостинг")

        # Додаємо нову вкладку БОЮ
        try:
            self.combat_tab = CombatManagerTab(dm=self.dm)
            self.tabs.addTab(self.combat_tab, "⚔️ Бій")
        except Exception as e:
            print(f"Error loading combat tab: {e}")

        try:
            self.inventory_manager_tab = InventoryManagerTab(dm=self.dm)
            self.tabs.addTab(self.inventory_manager_tab, "📦 Скарбниця")
        except:
            pass

        self.scenario_live_tab = ScenarioTab(dm=self.dm)
        self.tabs.addTab(self.scenario_live_tab, "🎭 Сценарій")

        self.item_creator_tab = ItemCreatorTab(dm=self.dm)
        self.tabs.addTab(self.item_creator_tab, "⚔️ Редактор")

        self.scenario_tree_tab = ScenarioTreeTab(dm=self.dm)
        self.tabs.addTab(self.scenario_tree_tab, "🌳 План")

        self.hosting_tab.session_state_changed.connect(self.scenario_live_tab.update_session_status)