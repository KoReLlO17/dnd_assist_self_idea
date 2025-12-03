from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTabWidget, QLabel, QMessageBox, QPushButton, QHBoxLayout
)
from core.data_manager import DataManager

# Imports
try:
    from ui.dm.dm_hosting.hosting_window import HostingTab
    from ui.dm.dm_hosting.scenario_tab import ScenarioTab
    from ui.dm.creature_item_redactor.item_creator_tab import ItemCreatorTab
    from ui.dm.creature_item_redactor.scenario_tree_tab import ScenarioTreeTab
    from ui.dm.inventory_manager_tab import InventoryManagerTab
    from ui.dm.encounter_builder_tab import EncounterBuilderTab  # NEW
    from ui.common.combat_window import CombatWindow  # NEW
except ImportError as e:
    print(f"Import Error: {e}")
    raise e


class DM_MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Майстер Підземель: Панель Керування")
        self.resize(1200, 850)

        self.dm = DataManager()
        self.combat_window = None  # Зберігаємо посилання на вікно

        try:
            self.server_ip = self.dm.start_server()
        except:
            pass

        self.setStyleSheet("""
            QMainWindow, QWidget { background-color: #121212; color: #E0E0E0; font-family: 'Segoe UI'; }
            QTabWidget::pane { border: 1px solid #333; background: #1E1E1E; }
            QTabBar::tab { background: #2D2D2D; color: #AAA; padding: 10px 20px; }
            QTabBar::tab:selected { background: #3E3E42; color: #FFF; border-bottom: 2px solid #007ACC; }
            QPushButton { background-color: #0D47A1; color: white; border: none; padding: 8px; border-radius: 4px; }
            QPushButton:hover { background-color: #1565C0; }
        """)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # --- HEADER З КНОПКОЮ БОЮ ---
        header_layout = QHBoxLayout()
        header_lbl = QLabel(f"Dungeon Master Center (IP: {getattr(self, 'server_ip', 'Unknown')})")
        header_lbl.setStyleSheet("color: #007ACC; font-size: 18px; font-weight: bold;")
        header_layout.addWidget(header_lbl)

        # Кнопка відкриття окремого вікна бою
        self.btn_open_combat = QPushButton("⚔️ ВІДКРИТИ ВІКНО БОЮ")
        self.btn_open_combat.setStyleSheet("background-color: #C62828; font-weight: bold; padding: 10px 20px;")
        self.btn_open_combat.clicked.connect(self._open_combat_window)
        header_layout.addWidget(self.btn_open_combat)

        main_layout.addLayout(header_layout)

        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        self.hosting_tab = HostingTab(dm=self.dm)
        self.tabs.addTab(self.hosting_tab, "📡 Хостинг")

        # ЗАМІСТЬ СТАРОЇ ВКЛАДКИ БОЮ -> КОНСТРУКТОР
        self.builder_tab = EncounterBuilderTab(dm=self.dm)
        self.tabs.addTab(self.builder_tab, "🧱 Конструктор Енкаунтеру")

        try:
            self.tabs.addTab(InventoryManagerTab(dm=self.dm), "📦 Скарбниця")
        except:
            pass

        self.scenario_live_tab = ScenarioTab(dm=self.dm)
        self.tabs.addTab(self.scenario_live_tab, "🎭 Сценарій")

        self.tabs.addTab(ItemCreatorTab(dm=self.dm), "⚔️ Редактор")
        self.tabs.addTab(ScenarioTreeTab(dm=self.dm), "🌳 План")

        self.hosting_tab.session_state_changed.connect(self.scenario_live_tab.update_session_status)

    def _open_combat_window(self):
        if self.combat_window is None:
            # is_dm=True дає права керувати всіма монстрами
            self.combat_window = CombatWindow(self.dm, is_dm=True)
        self.combat_window.show()