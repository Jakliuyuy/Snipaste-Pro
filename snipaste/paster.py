import sys
from PyQt6.QtCore import Qt, QRect, QPoint, QSize, pyqtSignal
from PyQt6.QtGui import (
    QPainter, QPixmap, QImage, QColor, QTransform, QGuiApplication,
    QAction, QCursor
)
from PyQt6.QtWidgets import (
    QWidget, QMenu, QFileDialog, QApplication, QMessageBox
)
from snipaste.utils import calculate_magnetic_snap, play_sound
from snipaste.config import get_config

class PasterWindow(QWidget):
    """
    Floating Pinned Screenshot Window (Recreation of Snipaste AVMagneticWindow / Paster).
    Supports magnetic snapping, wheel zooming, opacity adjustment, rotation, mirroring,
    click-through, and real-time translation.
    """
    sig_closed = pyqtSignal(object)

    def __init__(self, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.Tool |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.original_pixmap = pixmap
        self.current_pixmap = pixmap.copy()
        self.scale_factor = 1.0
        self.rotation_angle = 0
        self.is_mirrored_h = False
        self.is_mirrored_v = False
        self.is_click_through = False

        self._drag_pos = None
        self._all_pasters_ref = []  # Injected reference to other active pasters for magnetic snapping

        self._update_window_size()

    def set_active_pasters_list(self, pasters: list):
        self._all_pasters_ref = pasters

    def _update_window_size(self):
        w = max(20, int(self.current_pixmap.width() * self.scale_factor))
        h = max(20, int(self.current_pixmap.height() * self.scale_factor))
        self.resize(w, h)
        self.update()

    def set_click_through(self, enabled: bool):
        """Sets mouse click-through using Win32 API on Windows, or Qt transparency."""
        self.is_click_through = enabled
        if sys.platform == "win32":
            import ctypes
            hwnd = int(self.winId())
            GWL_EXSTYLE = -20
            WS_EX_TRANSPARENT = 0x00000020
            WS_EX_LAYERED = 0x00080000

            user32 = ctypes.windll.user32
            style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            if enabled:
                style |= (WS_EX_TRANSPARENT | WS_EX_LAYERED)
            else:
                style &= ~WS_EX_TRANSPARENT
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)

        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, enabled)
        play_sound("bubble")

    def toggle_click_through(self):
        self.set_click_through(not self.is_click_through)

    def zoom_in(self):
        self.scale_factor = min(10.0, self.scale_factor * 1.15)
        self._update_window_size()

    def zoom_out(self):
        self.scale_factor = max(0.1, self.scale_factor / 1.15)
        self._update_window_size()

    def change_opacity(self, delta: float):
        current = self.windowOpacity()
        new_op = max(0.1, min(1.0, current + delta))
        self.setWindowOpacity(new_op)

    def rotate_cw(self):
        self.rotation_angle = (self.rotation_angle + 90) % 360
        self._apply_transforms()

    def rotate_ccw(self):
        self.rotation_angle = (self.rotation_angle - 90) % 360
        self._apply_transforms()

    def flip_horizontal(self):
        self.is_mirrored_h = not self.is_mirrored_h
        self._apply_transforms()

    def flip_vertical(self):
        self.is_mirrored_v = not self.is_mirrored_v
        self._apply_transforms()

    def _apply_transforms(self):
        t = QTransform()
        if self.is_mirrored_h:
            t.scale(-1, 1)
        if self.is_mirrored_v:
            t.scale(1, -1)
        if self.rotation_angle != 0:
            t.rotate(self.rotation_angle)

        self.current_pixmap = self.original_pixmap.transformed(t, Qt.TransformationMode.SmoothTransformation)
        self._update_window_size()

    def update_image(self, new_pixmap: QPixmap):
        self.original_pixmap = new_pixmap
        self._apply_transforms()

    # --- Mouse & Wheel Events ---
    def mousePressEvent(self, event):
        if self.is_click_through:
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        elif event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())
            event.accept()

    def mouseMoveEvent(self, event):
        if self.is_click_through or not self._drag_pos:
            return
        if event.buttons() == Qt.MouseButton.LeftButton:
            new_top_left = event.globalPosition().toPoint() - self._drag_pos
            cand_rect = QRect(new_top_left, self.size())

            # Magnetic Snapping
            if get_config().get_bool("Paste", "magnetic_snap", True):
                target_rects = []
                # Add screen boundaries
                for screen in QGuiApplication.screens():
                    target_rects.append(screen.geometry())
                # Add other active paster windows
                for other in self._all_pasters_ref:
                    if other != self and other.isVisible():
                        target_rects.append(other.geometry())

                dx, dy = calculate_magnetic_snap(cand_rect, target_rects, threshold=14)
                new_top_left += QPoint(dx, dy)

            self.move(new_top_left)
            event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self.is_click_through:
            play_sound("bubble")
            self.close()
            event.accept()

    def wheelEvent(self, event):
        if self.is_click_through:
            return
        delta = event.angleDelta().y()
        modifiers = event.modifiers()

        if modifiers & Qt.KeyboardModifier.ControlModifier:
            # Opacity adjustment
            step = 0.08 if delta > 0 else -0.08
            self.change_opacity(step)
        else:
            # Zoom scaling anchored around cursor
            if delta > 0:
                self.zoom_in()
            else:
                self.zoom_out()
        event.accept()

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_1:
            self.change_opacity(-0.1)
        elif key == Qt.Key.Key_2:
            self.change_opacity(0.1)
        elif key == Qt.Key.Key_F4:
            self.toggle_click_through()
        elif key == Qt.Key.Key_Escape:
            self.close()
        elif key == Qt.Key.Key_T:
            self._start_translation()
        elif key == Qt.Key.Key_C and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self._copy_image()
        elif key == Qt.Key.Key_S and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self._save_image()
        else:
            super().keyPressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # Draw drop shadow / border
        rect = self.rect()
        painter.drawPixmap(rect, self.current_pixmap)

        # If click-through, render faint border indicator
        if self.is_click_through:
            painter.setPen(QColor(30, 144, 255, 120))
            painter.drawRect(0, 0, self.width() - 1, self.height() - 1)

    def _show_context_menu(self, global_pos: QPoint):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2D3139;
                color: #FFFFFF;
                border: 1px solid #454B57;
                padding: 4px;
                border-radius: 6px;
            }
            QMenu::item {
                padding: 6px 24px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #1E90FF;
            }
        """)

        act_copy = menu.addAction("📋 复制图像 (Ctrl+C)")
        act_copy.triggered.connect(self._copy_image)

        act_save = menu.addAction("💾 图像另存为... (Ctrl+S)")
        act_save.triggered.connect(self._save_image)

        menu.addSeparator()

        act_trans = menu.addAction("🌐 截图实时翻译 (T)")
        act_trans.triggered.connect(self._start_translation)

        menu.addSeparator()

        act_rot_cw = menu.addAction("↻ 顺时针旋转 90°")
        act_rot_cw.triggered.connect(self.rotate_cw)

        act_rot_ccw = menu.addAction("↺ 逆时针旋转 90°")
        act_rot_ccw.triggered.connect(self.rotate_ccw)

        act_flip_h = menu.addAction("⇄ 水平翻转")
        act_flip_h.triggered.connect(self.flip_horizontal)

        act_flip_v = menu.addAction("⇅ 垂直翻转")
        act_flip_v.triggered.connect(self.flip_vertical)

        menu.addSeparator()

        act_click_thru = menu.addAction("🖱 鼠标穿透 (F4)")
        act_click_thru.setCheckable(True)
        act_click_thru.setChecked(self.is_click_through)
        act_click_thru.triggered.connect(self.toggle_click_through)

        menu.addSeparator()

        act_close = menu.addAction("✕ 销毁贴图 (Esc)")
        act_close.triggered.connect(self.close)

        menu.exec(global_pos)

    def _copy_image(self):
        cb = QGuiApplication.clipboard()
        cb.setPixmap(self.current_pixmap)
        play_sound("bubble")

    def _save_image(self):
        cfg = get_config()
        def_path = cfg.get("General", "save_dir", "")
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存贴图", def_path, "PNG 图像 (*.png);;JPEG 图像 (*.jpg);;所有文件 (*.*)"
        )
        if file_path:
            self.current_pixmap.save(file_path)
            play_sound("bubble")

    def _start_translation(self):
        from snipaste.translator import TranslationWorker, FloatingTranslationCard
        qimg = self.current_pixmap.toImage()

        card = FloatingTranslationCard()
        card.set_loading()
        # Position card next to this paster
        card.move(self.x() + self.width() + 10, self.y())
        card.show()

        worker = TranslationWorker(qimg)

        def on_done(items, inplace_img):
            card.set_results(items)
            card.sig_apply_inplace.connect(lambda: self.update_image(QPixmap.fromImage(inplace_img)))

        def on_err(err_msg):
            card.status_label.setText(f"翻译失败: {err_msg}")

        worker.sig_finished.connect(on_done)
        worker.sig_error.connect(on_err)
        worker.start()
        # keep ref to avoid garbage collection
        self._trans_worker = worker
        self._trans_card = card

    def closeEvent(self, event):
        self.sig_closed.emit(self)
        super().closeEvent(event)
