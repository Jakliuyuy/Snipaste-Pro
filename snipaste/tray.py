from PyQt6.QtCore import Qt, QPoint, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QPolygon
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from snipaste.utils import get_asset_path

class TrayManager(QSystemTrayIcon):
    """
    System Tray Manager (Recreation of Snipaste AVTrayIcon & AVTrayMenu).
    """
    sig_snip = pyqtSignal()
    sig_paste = pyqtSignal()
    sig_toggle_pasters = pyqtSignal()
    sig_clear_pasters = pyqtSignal()
    sig_open_settings = pyqtSignal()
    sig_quit = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setIcon(self._create_snipaste_icon())
        self.setToolTip("Snipaste (已开启截图实时翻译)")
        self._init_menu()
        self.activated.connect(self._on_activated)

    def _create_snipaste_icon(self) -> QIcon:
        """Loads official icon or draws clean Snipaste pin/snip badge icon."""
        icon_file = get_asset_path("icon.ico")
        if icon_file.exists():
            icon = QIcon(str(icon_file))
            if not icon.isNull():
                return icon

        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Rounded background
        painter.setBrush(QColor(30, 144, 255))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(2, 2, 28, 28, 6, 6)

        # White inner pin / scissors shape
        painter.setPen(QColor(255, 255, 255))
        painter.setBrush(QColor(255, 255, 255))
        painter.drawRect(8, 8, 16, 12)
        poly = QPolygon([QPoint(16, 26), QPoint(12, 20), QPoint(20, 20)])
        painter.drawPolygon(poly)
        painter.end()

        return QIcon(pixmap)

    def _init_menu(self):
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #2D3139;
                color: #FFFFFF;
                border: 1px solid #454B57;
                padding: 4px;
                border-radius: 6px;
            }
            QMenu::item {
                padding: 6px 26px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #1E90FF;
            }
        """)

        act_snip = menu.addAction("✂ 截图 (F1)")
        act_snip.triggered.connect(self.sig_snip.emit)

        act_paste = menu.addAction("📌 贴图 (F3)")
        act_paste.triggered.connect(self.sig_paste.emit)

        menu.addSeparator()

        self.act_toggle_pins = menu.addAction("👁 隐藏所有贴图")
        self.act_toggle_pins.triggered.connect(self.sig_toggle_pasters.emit)

        act_clear_pins = menu.addAction("🗑 销毁所有贴图")
        act_clear_pins.triggered.connect(self.sig_clear_pasters.emit)

        menu.addSeparator()

        act_settings = menu.addAction("⚙ 首选项与实时翻译设置...")
        act_settings.triggered.connect(self.sig_open_settings.emit)

        menu.addSeparator()

        act_quit = menu.addAction("✕ 退出 Snipaste")
        act_quit.triggered.connect(self.sig_quit.emit)

        self.setContextMenu(menu)

    def _on_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.sig_snip.emit()
