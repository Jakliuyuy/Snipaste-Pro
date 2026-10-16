import sys
import argparse
from pathlib import Path
from PyQt6.QtCore import QObject, QPoint, QRect, Qt
from PyQt6.QtGui import (
    QGuiApplication, QPixmap, QImage, QPainter, QColor, QFont
)
from PyQt6.QtWidgets import QApplication

from snipaste.snipper import SnipperWindow
from snipaste.paster import PasterWindow
from snipaste.hotkey import HotkeyManager
from snipaste.tray import TrayManager
from snipaste.settings_dialog import SettingsDialog
from snipaste.config import get_config
from snipaste.utils import play_sound

class SnipasteApp(QObject):
    """
    Central Coordinator Application (Recreation of Snipaste AVSnipaste).
    """
    def __init__(self, argv=None):
        super().__init__()
        self.qapp = QApplication.instance() or QApplication(argv or sys.argv)
        self.qapp.setQuitOnLastWindowClosed(False)

        self.config = get_config()

        # Windows and managers
        self.snipper = SnipperWindow()
        self.active_pasters: list[PasterWindow] = []
        self.paster_history: list[QPixmap] = []
        self.pasters_hidden = False

        self.hotkey_mgr = HotkeyManager()
        self.tray = TrayManager()
        self.settings_dlg = None

        self._setup_connections()
        self.hotkey_mgr.start()
        self.tray.show()

    def _setup_connections(self):
        # Hotkey triggers
        self.hotkey_mgr.sig_snip.connect(self.trigger_snip)
        self.hotkey_mgr.sig_paste.connect(self.trigger_paste)
        self.hotkey_mgr.sig_click_through.connect(self.toggle_click_through)
        self.hotkey_mgr.sig_snip_copy.connect(self.trigger_snip_copy)

        # Snipper signals
        self.snipper.sig_pin_requested.connect(self.create_paster)

        # Tray signals
        self.tray.sig_snip.connect(self.trigger_snip)
        self.tray.sig_paste.connect(self.trigger_paste)
        self.tray.sig_toggle_pasters.connect(self.toggle_all_pasters)
        self.tray.sig_clear_pasters.connect(self.clear_all_pasters)
        self.tray.sig_open_settings.connect(self.open_settings)
        self.tray.sig_quit.connect(self.quit)

    # --- Actions ---
    def trigger_snip(self):
        """Launches the screenshot canvas."""
        self.snipper.start_capture()

    def trigger_snip_copy(self):
        """Quick snip mode."""
        self.snipper.start_capture()

    def trigger_paste(self):
        """
        Pins clipboard image or text to screen (F3).
        If clipboard has nothing new, recovers recently closed pin from history.
        """
        cb = QGuiApplication.clipboard()
        mime = cb.mimeData()

        # 1. Clipboard has Image
        if mime.hasImage():
            pix = cb.pixmap()
            if not pix.isNull():
                cursor_pos = QCursor.pos() if hasattr(self, "QCursor") else QPoint(200, 200)
                self.create_paster(pix, cursor_pos)
                play_sound("bubble")
                return

        # 2. Clipboard has Text: render text as image pin (Snipaste signature feature!)
        if mime.hasText():
            text = mime.text().strip()
            if text:
                pix = self._render_text_to_pixmap(text)
                self.create_paster(pix, QPoint(250, 250))
                play_sound("bubble")
                return

        # 3. Recover from History
        if self.paster_history:
            last_pix = self.paster_history.pop()
            self.create_paster(last_pix, QPoint(300, 300))
            play_sound("bubble")

    def _render_text_to_pixmap(self, text: str) -> QPixmap:
        """Renders arbitrary clipboard text into a clean pinned image card."""
        lines = text.split("\n")
        font = QFont("Consolas" if "\t" in text or "{" in text else "Microsoft YaHei", 12)

        # Calculate bounding box
        temp_img = QImage(1, 1, QImage.Format.Format_RGB32)
        p = QPainter(temp_img)
        p.setFont(font)
        fm = p.fontMetrics()
        max_w = max([fm.horizontalAdvance(line) for line in lines[:40]]) + 32
        max_w = max(180, min(max_w, 900))
        total_h = min(len(lines), 40) * fm.lineSpacing() + 32
        p.end()

        # Draw card
        pix = QPixmap(max_w, total_h)
        pix.fill(QColor(250, 250, 252))
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        # Border
        painter.setPen(QPen(QColor(210, 215, 225), 1))
        painter.drawRect(0, 0, max_w - 1, total_h - 1)

        # Text
        painter.setFont(font)
        painter.setPen(QColor(30, 30, 35))
        y = 24
        for line in lines[:40]:
            painter.drawText(16, y, line)
            y += fm.lineSpacing()
        painter.end()

        return pix

    def create_paster(self, pixmap: QPixmap, pos: QPoint):
        paster = PasterWindow(pixmap)
        paster.set_active_pasters_list(self.active_pasters)
        paster.sig_closed.connect(self._on_paster_closed)
        paster.move(pos)
        paster.show()
        self.active_pasters.append(paster)

    def _on_paster_closed(self, paster: PasterWindow):
        if paster in self.active_pasters:
            self.active_pasters.remove(paster)
            # Store in history
            max_hist = self.config.get_int("Paste", "max_history", 20)
            self.paster_history.append(paster.original_pixmap)
            if len(self.paster_history) > max_hist:
                self.paster_history.pop(0)

    def toggle_click_through(self):
        """
        F4: If an active paster is currently click-through, disable click-through on all.
        Otherwise, toggle click-through for hovered paster.
        """
        has_any_clickthru = any(p.is_click_through for p in self.active_pasters)
        if has_any_clickthru:
            # Disable click-through on all
            for p in self.active_pasters:
                p.set_click_through(False)
        else:
            # Enable click-through on all
            for p in self.active_pasters:
                p.set_click_through(True)

    def toggle_all_pasters(self):
        self.pasters_hidden = not self.pasters_hidden
        for p in self.active_pasters:
            p.setVisible(not self.pasters_hidden)
        self.tray.act_toggle_pins.setText("👁 显示所有贴图" if self.pasters_hidden else "👁 隐藏所有贴图")

    def clear_all_pasters(self):
        for p in list(self.active_pasters):
            p.close()

    def open_settings(self):
        if not self.settings_dlg:
            self.settings_dlg = SettingsDialog()
        self.settings_dlg.show()
        self.settings_dlg.activateWindow()

    def quit(self):
        self.hotkey_mgr.stop()
        self.qapp.quit()

    def run(self):
        return self.qapp.exec()
