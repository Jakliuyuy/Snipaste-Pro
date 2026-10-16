import sys
from PyQt6.QtCore import Qt, QRect, QPoint, QSize, pyqtSignal
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QPixmap, QImage, QFont,
    QGuiApplication, QCursor
)
from PyQt6.QtWidgets import QWidget, QFileDialog, QInputDialog

from snipaste.magnifier import MagnifierHUD
from snipaste.toolbar import PaintBar
from snipaste.detector import WindowDetector
from snipaste.painter import (
    AnnotationManager, RectItem, EllipseItem, ArrowItem, LineItem,
    PencilItem, MarkerItem, TextItem, NumberItem, MosaicItem, BlurItem
)
from snipaste.translator import TranslationWorker, FloatingTranslationCard
from snipaste.utils import play_sound
from snipaste.config import get_config

# Snipper interaction states
STATE_IDLE = 0        # Detecting windows / hover
STATE_DRAGGING = 1    # Dragging selection box
STATE_SELECTED = 2    # Selection chosen, drawing or resizing
STATE_RESIZING = 3    # Dragging resize anchor

class SnipperWindow(QWidget):
    """
    Full-screen multi-monitor snipping overlay (Recreation of Snipaste AVSnipper).
    """
    sig_pin_requested = pyqtSignal(QPixmap, QPoint)
    sig_finished = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.SubWindow
        )
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)

        self.detector = WindowDetector()
        self.annotation_mgr = AnnotationManager()

        self.state = STATE_IDLE
        self.screen_pixmap: QPixmap = None
        self.virtual_rect = QRect()

        self.start_pos = QPoint()
        self.current_pos = QPoint()
        self.selected_rect = QRect()
        self.detected_rect = None

        self.active_tool = ""
        self.current_color = QColor(255, 59, 48)  # Default Red
        self.current_width = 4
        self.current_drawing_points = []
        self.resize_handle_idx = -1

        # Sub-widgets
        self.magnifier = MagnifierHUD(self)
        self.toolbar = PaintBar(self)
        self._setup_toolbar_signals()

        self.trans_card = None
        self.trans_worker = None

    def _setup_toolbar_signals(self):
        self.toolbar.sig_tool_changed.connect(self._on_tool_changed)
        self.toolbar.sig_color_changed.connect(self._on_color_changed)
        self.toolbar.sig_width_changed.connect(self._on_width_changed)
        self.toolbar.sig_undo.connect(self._on_undo)
        self.toolbar.sig_redo.connect(self._on_redo)
        self.toolbar.sig_translate.connect(self._on_translate)
        self.toolbar.sig_pin.connect(self._on_pin)
        self.toolbar.sig_save.connect(self._on_save)
        self.toolbar.sig_copy.connect(self._on_copy)
        self.toolbar.sig_close.connect(self.close)

    def start_capture(self):
        """Grabs virtual desktop across all monitors and displays full-screen canvas."""
        # 1. Compute bounding rect of all screens
        screens = QGuiApplication.screens()
        v_rect = QRect()
        for s in screens:
            v_rect = v_rect.united(s.geometry())
        self.virtual_rect = v_rect

        # 2. Grab screen pixmap
        primary = QGuiApplication.primaryScreen()
        self.screen_pixmap = primary.grabWindow(0, v_rect.x(), v_rect.y(), v_rect.width(), v_rect.height())

        # 3. Reset state
        self.state = STATE_IDLE
        self.selected_rect = QRect()
        self.detected_rect = None
        self.annotation_mgr.clear()
        self.toolbar.hide()

        # Update detector and magnifier
        self.detector.refresh()
        self.magnifier.set_screen_pixmap(self.screen_pixmap)
        self.magnifier.show()

        self.setGeometry(v_rect)
        self.show()
        self.activateWindow()
        self.setCursor(Qt.CursorShape.CrossCursor)

    def _get_cropped_composite_image(self) -> QImage:
        """Returns the cropped selection QImage with all drawn annotations composited."""
        if self.selected_rect.isEmpty():
            return QImage()
        norm_rect = self.selected_rect.normalized()
        base_cropped = self.screen_pixmap.copy(norm_rect).toImage()
        return self.annotation_mgr.render_to_image(base_cropped)

    # --- Mouse Events ---
    def mousePressEvent(self, event):
        pos = event.position().toPoint()

        if event.button() == Qt.MouseButton.RightButton:
            # If in drawing/selected mode, right click cancels tool or selection
            if self.active_tool:
                self.toolbar._select_tool(self.active_tool)  # deselect
            elif self.state == STATE_SELECTED:
                self.state = STATE_IDLE
                self.selected_rect = QRect()
                self.toolbar.hide()
                self.magnifier.show()
                self.update()
            else:
                self.close()
            event.accept()
            return

        if event.button() == Qt.MouseButton.LeftButton:
            if self.state == STATE_IDLE:
                # If window was detected, click immediately selects it!
                if self.detected_rect and self.detected_rect.contains(pos):
                    self.selected_rect = self.detected_rect
                    self.state = STATE_SELECTED
                    self.magnifier.hide()
                    self._show_toolbar()
                else:
                    self.state = STATE_DRAGGING
                    self.start_pos = pos
                    self.current_pos = pos
                    self.selected_rect = QRect(pos, QSize(1, 1))
                    self.magnifier.hide()
                self.update()
                event.accept()
                return

            elif self.state == STATE_SELECTED:
                # Check 8-point resize handles first
                h_idx = self._get_handle_under_pos(pos)
                if h_idx != -1:
                    self.state = STATE_RESIZING
                    self.resize_handle_idx = h_idx
                    self.start_pos = pos
                    event.accept()
                    return

                # If a drawing tool is selected, initiate drawing item inside selection
                if self.active_tool and self.selected_rect.contains(pos):
                    rel_pos = pos - self.selected_rect.topLeft()
                    self.current_drawing_points = [rel_pos]

                    if self.active_tool == "text":
                        text, ok = QInputDialog.getText(self, "添加文字", "输入标注文本:")
                        if ok and text.strip():
                            item = TextItem(rel_pos, text.strip(), self.current_color, font_size=16)
                            self.annotation_mgr.add_item(item)
                            self.update()
                    elif self.active_tool == "number":
                        item = NumberItem(rel_pos, self.annotation_mgr.step_counter, self.current_color)
                        self.annotation_mgr.add_item(item)
                        self.update()
                    event.accept()
                    return

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint()
        self.current_pos = pos

        if self.state == STATE_IDLE:
            # Update Magnifier HUD position and color
            self.magnifier.update_position(pos, self.virtual_rect)
            # Find window under cursor
            if get_config().get_bool("Snip", "auto_detect_windows", True):
                self.detected_rect = self.detector.find_best_rect(pos)
            self.update()

        elif self.state == STATE_DRAGGING:
            self.selected_rect = QRect(self.start_pos, pos).normalized()
            self.update()

        elif self.state == STATE_RESIZING:
            self._handle_resizing(pos)
            self.update()

        elif self.state == STATE_SELECTED:
            # Update cursor if hovering over resize handles
            h_idx = self._get_handle_under_pos(pos)
            if h_idx in (0, 4):
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            elif h_idx in (1, 5):
                self.setCursor(Qt.CursorShape.SizeVerCursor)
            elif h_idx in (2, 6):
                self.setCursor(Qt.CursorShape.SizeBDiagCursor)
            elif h_idx in (3, 7):
                self.setCursor(Qt.CursorShape.SizeHorCursor)
            elif self.active_tool:
                self.setCursor(Qt.CursorShape.CrossCursor)
            else:
                self.setCursor(Qt.CursorShape.SizeAllCursor if self.selected_rect.contains(pos) else Qt.CursorShape.ArrowCursor)

            # Active drawing drag
            if event.buttons() & Qt.MouseButton.LeftButton and self.active_tool:
                rel_pos = pos - self.selected_rect.topLeft()
                self.current_drawing_points.append(rel_pos)
                self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.state == STATE_DRAGGING:
                if self.selected_rect.width() > 10 and self.selected_rect.height() > 10:
                    self.state = STATE_SELECTED
                    self._show_toolbar()
                else:
                    self.state = STATE_IDLE
                    self.magnifier.show()
                self.update()

            elif self.state == STATE_RESIZING:
                self.state = STATE_SELECTED
                self.resize_handle_idx = -1
                self._show_toolbar()
                self.update()

            elif self.state == STATE_SELECTED and self.active_tool and self.current_drawing_points:
                self._commit_drawing()
                self.current_drawing_points = []
                self.update()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.state == STATE_SELECTED:
            # Double click copies to clipboard directly
            self._on_copy()

    # --- Drawing Commit ---
    def _commit_drawing(self):
        pts = self.current_drawing_points
        if not pts:
            return

        p_start, p_end = pts[0], pts[-1]
        t = self.active_tool
        bound_rect = QRect(p_start, p_end).normalized()

        if t == "rect":
            self.annotation_mgr.add_item(RectItem(bound_rect, self.current_color, self.current_width))
        elif t == "ellipse":
            self.annotation_mgr.add_item(EllipseItem(bound_rect, self.current_color, self.current_width))
        elif t == "line":
            self.annotation_mgr.add_item(LineItem(p_start, p_end, self.current_color, self.current_width))
        elif t == "arrow":
            self.annotation_mgr.add_item(ArrowItem(p_start, p_end, self.current_color, self.current_width))
        elif t == "pencil":
            self.annotation_mgr.add_item(PencilItem(pts, self.current_color, self.current_width))
        elif t == "marker":
            self.annotation_mgr.add_item(MarkerItem(pts, self.current_color, width=max(12, self.current_width * 3)))
        elif t == "mosaic":
            self.annotation_mgr.add_item(MosaicItem(bound_rect, block_size=10))
        elif t == "blur":
            self.annotation_mgr.add_item(BlurItem(bound_rect, radius=8))

    # --- Resize Handles ---
    def _get_handles_rects(self) -> list[QRect]:
        r = self.selected_rect
        hs = 8  # handle size
        hh = hs // 2
        return [
            QRect(r.left() - hh, r.top() - hh, hs, hs),          # 0: Top-Left
            QRect(r.center().x() - hh, r.top() - hh, hs, hs),    # 1: Top-Center
            QRect(r.right() - hh, r.top() - hh, hs, hs),         # 2: Top-Right
            QRect(r.right() - hh, r.center().y() - hh, hs, hs),  # 3: Right-Center
            QRect(r.right() - hh, r.bottom() - hh, hs, hs),      # 4: Bottom-Right
            QRect(r.center().x() - hh, r.bottom() - hh, hs, hs), # 5: Bottom-Center
            QRect(r.left() - hh, r.bottom() - hh, hs, hs),       # 6: Bottom-Left
            QRect(r.left() - hh, r.center().y() - hh, hs, hs)    # 7: Left-Center
        ]

    def _get_handle_under_pos(self, pos: QPoint) -> int:
        for idx, h_rect in enumerate(self._get_handles_rects()):
            if h_rect.contains(pos):
                return idx
        return -1

    def _handle_resizing(self, pos: QPoint):
        idx = self.resize_handle_idx
        r = self.selected_rect
        if idx == 0:
            self.selected_rect = QRect(pos, r.bottomRight()).normalized()
        elif idx == 1:
            self.selected_rect = QRect(QPoint(r.left(), pos.y()), r.bottomRight()).normalized()
        elif idx == 2:
            self.selected_rect = QRect(QPoint(r.left(), pos.y()), QPoint(pos.x(), r.bottom())).normalized()
        elif idx == 3:
            self.selected_rect = QRect(r.topLeft(), QPoint(pos.x(), r.bottom())).normalized()
        elif idx == 4:
            self.selected_rect = QRect(r.topLeft(), pos).normalized()
        elif idx == 5:
            self.selected_rect = QRect(r.topLeft(), QPoint(r.right(), pos.y())).normalized()
        elif idx == 6:
            self.selected_rect = QRect(QPoint(pos.x(), r.top()), QPoint(r.right(), pos.y())).normalized()
        elif idx == 7:
            self.selected_rect = QRect(QPoint(pos.x(), r.top()), r.bottomRight()).normalized()

    def _show_toolbar(self):
        self.toolbar.show()
        self.toolbar.update_position(self.selected_rect, self.virtual_rect)

    # --- Keyboard Shortcuts ---
    def keyPressEvent(self, event):
        key = event.key()
        modifiers = event.modifiers()

        if key == Qt.Key.Key_Escape:
            self.close()
        elif key == Qt.Key.Key_C and self.state == STATE_IDLE:
            # Copy color hex under cursor
            text = self.magnifier.copy_color_to_clipboard()
            play_sound("bubble")
        elif key == Qt.Key.Key_Shift and self.state == STATE_IDLE:
            self.magnifier.toggle_color_mode()
        elif key == Qt.Key.Key_Z and (modifiers & Qt.KeyboardModifier.ControlModifier):
            self._on_undo()
        elif key == Qt.Key.Key_Y and (modifiers & Qt.KeyboardModifier.ControlModifier):
            self._on_redo()
        elif key == Qt.Key.Key_T and self.state == STATE_SELECTED:
            self._on_translate()
        elif (key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter) and self.state == STATE_SELECTED:
            self._on_copy()
        elif key == Qt.Key.Key_C and (modifiers & Qt.KeyboardModifier.ControlModifier) and self.state == STATE_SELECTED:
            self._on_copy()
        elif key == Qt.Key.Key_S and (modifiers & Qt.KeyboardModifier.ControlModifier) and self.state == STATE_SELECTED:
            self._on_save()
        elif self.state == STATE_SELECTED:
            # Fine-tune position / size with arrow keys
            step = 10 if (modifiers & Qt.KeyboardModifier.ShiftModifier) else 1
            if key == Qt.Key.Key_Left:
                self.selected_rect.translate(-step, 0)
            elif key == Qt.Key.Key_Right:
                self.selected_rect.translate(step, 0)
            elif key == Qt.Key.Key_Up:
                self.selected_rect.translate(0, -step)
            elif key == Qt.Key.Key_Down:
                self.selected_rect.translate(0, step)
            self._show_toolbar()
            self.update()
        else:
            super().keyPressEvent(event)

    # --- Toolbar Actions ---
    def _on_tool_changed(self, tool_id: str):
        self.active_tool = tool_id

    def _on_color_changed(self, color: QColor):
        self.current_color = color

    def _on_width_changed(self, width: int):
        self.current_width = width

    def _on_undo(self):
        self.annotation_mgr.undo()
        self.update()

    def _on_redo(self):
        self.annotation_mgr.redo()
        self.update()

    def _on_translate(self):
        """Triggers Real-time Screenshot OCR & Translation on selection."""
        cropped_img = self._get_cropped_composite_image()
        if cropped_img.isNull():
            return

        if self.trans_card is None:
            self.trans_card = FloatingTranslationCard(self)

        self.trans_card.set_loading()
        # Move card next to selection
        card_x = min(self.virtual_rect.right() - 400, self.selected_rect.right() + 10)
        card_y = max(self.virtual_rect.top() + 10, self.selected_rect.top())
        self.trans_card.move(card_x, card_y)
        self.trans_card.show()

        worker = TranslationWorker(cropped_img)

        def on_done(items, inplace_img):
            self.trans_card.set_results(items)
            # If in-place replacement requested:
            self.trans_card.sig_apply_inplace.connect(lambda: self._apply_inplace_translated_image(inplace_img))

        def on_err(err_msg):
            self.trans_card.status_label.setText(f"翻译异常: {err_msg}")

        worker.sig_finished.connect(on_done)
        worker.sig_error.connect(on_err)
        worker.start()
        self.trans_worker = worker

    def _apply_inplace_translated_image(self, inplace_img: QImage):
        """Draws the in-place translated image over the background canvas within selected_rect."""
        painter = QPainter(self.screen_pixmap)
        painter.drawImage(self.selected_rect.topLeft(), inplace_img)
        painter.end()
        self.update()

    def _on_pin(self):
        """Pins the current selection directly to screen as an AVMagneticWindow."""
        comp_img = self._get_cropped_composite_image()
        if not comp_img.isNull():
            pix = QPixmap.fromImage(comp_img)
            play_sound("snip")
            self.sig_pin_requested.emit(pix, self.selected_rect.topLeft())
            self.close()

    def _on_copy(self):
        """Copies the composite image to system clipboard and closes."""
        comp_img = self._get_cropped_composite_image()
        if not comp_img.isNull():
            cb = QGuiApplication.clipboard()
            cb.setPixmap(QPixmap.fromImage(comp_img))
            play_sound("snip")
            self.close()

    def _on_save(self):
        """Saves composite image to file."""
        comp_img = self._get_cropped_composite_image()
        if comp_img.isNull():
            return

        cfg = get_config()
        def_path = cfg.get("General", "save_dir", "")
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存截图", def_path, "PNG 图像 (*.png);;JPEG 图像 (*.jpg);;所有文件 (*.*)"
        )
        if file_path:
            comp_img.save(file_path)
            play_sound("snip")
            self.close()

    # --- Paint Event ---
    def paintEvent(self, event):
        if not self.screen_pixmap or self.screen_pixmap.isNull():
            return

        painter = QPainter(self)

        # 1. Draw full screen capture pristine pixels
        painter.drawPixmap(0, 0, self.screen_pixmap)

        dim_opacity = get_config().get_int("Snip", "dim_opacity", 140)
        dim_color = QColor(0, 0, 0, dim_opacity)
        w = self.width()
        h = self.height()

        if self.state == STATE_IDLE:
            # If a window is detected under cursor, highlight it without erasing its pixels
            if self.detected_rect:
                dr = self.detected_rect
                if dr.top() > 0:
                    painter.fillRect(0, 0, w, dr.top(), dim_color)
                if dr.bottom() < h - 1:
                    painter.fillRect(0, dr.bottom() + 1, w, h - (dr.bottom() + 1), dim_color)
                if dr.left() > 0:
                    painter.fillRect(0, dr.top(), dr.left(), dr.height(), dim_color)
                if dr.right() < w - 1:
                    painter.fillRect(dr.right() + 1, dr.top(), w - (dr.right() + 1), dr.height(), dim_color)

                # Draw crisp Snipaste bounding box
                painter.setPen(QPen(QColor(0, 122, 255), 2))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(dr)
            else:
                # Dim screen slightly
                painter.fillRect(self.rect(), QColor(0, 0, 0, 45))

            # Fullscreen crosshairs extending across entire screen
            painter.setPen(QPen(QColor(0, 122, 255, 160), 1, Qt.PenStyle.DashLine))
            painter.drawLine(0, self.current_pos.y(), w, self.current_pos.y())
            painter.drawLine(self.current_pos.x(), 0, self.current_pos.x(), h)

        elif self.state in (STATE_DRAGGING, STATE_SELECTED, STATE_RESIZING):
            norm_rect = self.selected_rect.normalized()

            # Dim ONLY the 4 regions outside norm_rect (never clear or paint over norm_rect!)
            if norm_rect.top() > 0:
                painter.fillRect(0, 0, w, norm_rect.top(), dim_color)
            if norm_rect.bottom() < h - 1:
                painter.fillRect(0, norm_rect.bottom() + 1, w, h - (norm_rect.bottom() + 1), dim_color)
            if norm_rect.left() > 0:
                painter.fillRect(0, norm_rect.top(), norm_rect.left(), norm_rect.height(), dim_color)
            if norm_rect.right() < w - 1:
                painter.fillRect(norm_rect.right() + 1, norm_rect.top(), w - (norm_rect.right() + 1), norm_rect.height(), dim_color)

            # Draw selection border
            border_color = QColor(get_config().get("Snip", "border_color", "#007AFF"))
            border_width = get_config().get_int("Snip", "border_width", 2)
            painter.setPen(QPen(border_color, border_width))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(norm_rect)

            # 3. Draw annotations inside selection
            painter.save()
            painter.translate(norm_rect.topLeft())
            for item in self.annotation_mgr.items:
                item.draw(painter, None)

            # Draw live in-progress drawing item
            if self.current_drawing_points and self.active_tool:
                self._draw_in_progress(painter)
            painter.restore()

            # 4. Draw 8 resize handles
            if self.state == STATE_SELECTED:
                painter.setPen(QPen(border_color, 1))
                painter.setBrush(QBrush(Qt.GlobalColor.white))
                for handle_rect in self._get_handles_rects():
                    painter.drawRect(handle_rect)

            # 5. Draw size badge: "W × H (X, Y)"
            badge_text = f"{norm_rect.width()} × {norm_rect.height()}"
            font = QFont("Segoe UI", 9)
            font.setBold(True)
            painter.setFont(font)
            badge_w, badge_h = 104, 24
            badge_x = norm_rect.left()
            badge_y = norm_rect.top() - badge_h - 4
            if badge_y < 10:
                badge_y = norm_rect.top() + 6
            painter.setPen(QPen(QColor(55, 62, 75), 1))
            painter.setBrush(QBrush(QColor(22, 25, 32, 235)))
            painter.drawRoundedRect(badge_x, badge_y, badge_w, badge_h, 4, 4)
            painter.setPen(QPen(Qt.GlobalColor.white))
            painter.drawText(QRect(badge_x, badge_y, badge_w, badge_h), Qt.AlignmentFlag.AlignCenter, badge_text)

    def _draw_in_progress(self, painter: QPainter):
        pts = self.current_drawing_points
        if not pts:
            return
        p_start, p_end = pts[0], pts[-1]
        bound_rect = QRect(p_start, p_end).normalized()
        t = self.active_tool

        if t == "rect":
            RectItem(bound_rect, self.current_color, self.current_width).draw(painter, None)
        elif t == "ellipse":
            EllipseItem(bound_rect, self.current_color, self.current_width).draw(painter, None)
        elif t == "line":
            LineItem(p_start, p_end, self.current_color, self.current_width).draw(painter, None)
        elif t == "arrow":
            ArrowItem(p_start, p_end, self.current_color, self.current_width).draw(painter, None)
        elif t == "pencil":
            PencilItem(pts, self.current_color, self.current_width).draw(painter, None)
        elif t == "marker":
            MarkerItem(pts, self.current_color, width=max(12, self.current_width * 3)).draw(painter, None)

    def closeEvent(self, event):
        self.magnifier.close()
        self.toolbar.close()
        if self.trans_card:
            self.trans_card.close()
        self.sig_finished.emit()
        super().closeEvent(event)
