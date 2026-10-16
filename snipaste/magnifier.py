from PyQt6.QtCore import Qt, QRect, QPoint
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPixmap, QImage, QGuiApplication
from PyQt6.QtWidgets import QWidget
from snipaste.utils import format_color_string

class MagnifierHUD(QWidget):
    """
    Magnifier and Color Picker HUD (Recreation of Snipaste AVMagnifyPaintItem & AVColorPicker).
    Zooms into the pixels around cursor, renders pixel grid, and displays RGB/HEX color values.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.SubWindow | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.zoom = 8             # Zoom factor per pixel
        self.grid_size = 17       # 17x17 pixel region sampled (odd number for center pixel)
        self.hud_width = 170
        self.hud_height = 230
        self.setFixedSize(self.hud_width, self.hud_height)

        self.color_mode = "HEX"   # HEX, RGB, HSL
        self.current_color = QColor(0, 0, 0)
        self.cursor_pos = QPoint(0, 0)
        self.screen_pixmap: QPixmap = None

    def set_screen_pixmap(self, pixmap: QPixmap):
        self.screen_pixmap = pixmap

    def toggle_color_mode(self):
        modes = ["HEX", "RGB", "HSL"]
        idx = (modes.index(self.color_mode) + 1) % len(modes)
        self.color_mode = modes[idx]
        self.update()

    def get_current_color_string(self) -> str:
        return format_color_string(
            self.current_color.red(),
            self.current_color.green(),
            self.current_color.blue(),
            self.color_mode
        )

    def copy_color_to_clipboard(self):
        text = self.get_current_color_string()
        cb = QGuiApplication.clipboard()
        cb.setText(text)
        return text

    def update_position(self, pos: QPoint, screen_rect: QRect):
        self.cursor_pos = pos

        # Calculate HUD window placement with offset
        offset_x, offset_y = 25, 25
        target_x = pos.x() + offset_x
        target_y = pos.y() + offset_y

        if target_x + self.hud_width > screen_rect.right() - 10:
            target_x = pos.x() - self.hud_width - offset_x
        if target_y + self.hud_height > screen_rect.bottom() - 10:
            target_y = pos.y() - self.hud_height - offset_y

        self.move(target_x, target_y)

        # Sample pixel color
        if self.screen_pixmap and not self.screen_pixmap.isNull():
            img = self.screen_pixmap.toImage()
            if 0 <= pos.x() < img.width() and 0 <= pos.y() < img.height():
                self.current_color = img.pixelColor(pos)

        self.update()

    def paintEvent(self, event):
        if not self.screen_pixmap or self.screen_pixmap.isNull():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # Background card
        painter.setBrush(QBrush(QColor(26, 29, 36, 245)))
        painter.setPen(QPen(QColor(60, 68, 85), 1))
        painter.drawRoundedRect(0, 0, self.width() - 1, self.height() - 1, 8, 8)

        # 1. Draw magnified pixel grid
        grid_pixel_size = 8
        grid_total_w = self.grid_size * grid_pixel_size
        grid_start_x = (self.hud_width - grid_total_w) // 2
        grid_start_y = 10

        half_grid = self.grid_size // 2
        img = self.screen_pixmap.toImage()

        for gy in range(self.grid_size):
            sy = self.cursor_pos.y() - half_grid + gy
            for gx in range(self.grid_size):
                sx = self.cursor_pos.x() - half_grid + gx
                if 0 <= sx < img.width() and 0 <= sy < img.height():
                    pixel_c = img.pixelColor(sx, sy)
                else:
                    pixel_c = QColor(0, 0, 0)

                rx = grid_start_x + gx * grid_pixel_size
                ry = grid_start_y + gy * grid_pixel_size

                painter.fillRect(rx, ry, grid_pixel_size, grid_pixel_size, pixel_c)

                # Light grid lines
                painter.setPen(QColor(50, 50, 50, 80))
                painter.drawRect(rx, ry, grid_pixel_size, grid_pixel_size)

        # Highlight center target pixel
        center_rx = grid_start_x + half_grid * grid_pixel_size
        center_ry = grid_start_y + half_grid * grid_pixel_size
        painter.setPen(QPen(QColor(255, 60, 60), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(center_rx - 1, center_ry - 1, grid_pixel_size + 2, grid_pixel_size + 2)

        # 2. Color swatch and Value Display
        swatch_y = grid_start_y + grid_total_w + 10
        swatch_size = 20
        painter.fillRect(grid_start_x, swatch_y, swatch_size, swatch_size, self.current_color)
        painter.setPen(QColor(200, 200, 200))
        painter.drawRect(grid_start_x, swatch_y, swatch_size, swatch_size)

        font = QFont("Segoe UI", 9)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(255, 255, 255))
        color_str = self.get_current_color_string()
        painter.drawText(grid_start_x + swatch_size + 8, swatch_y + 15, color_str)

        # 3. Position Text
        font_small = QFont("Segoe UI", 8)
        painter.setFont(font_small)
        painter.setPen(QColor(180, 180, 180))
        pos_str = f"POS: ({self.cursor_pos.x()}, {self.cursor_pos.y()})"
        painter.drawText(grid_start_x, swatch_y + 36, pos_str)

        # 4. Helper tip text
        font_tip = QFont("Segoe UI", 7)
        painter.setFont(font_tip)
        painter.setPen(QColor(140, 140, 150))
        painter.drawText(grid_start_x, swatch_y + 52, "C: 复制颜色 | Shift: 切换")
