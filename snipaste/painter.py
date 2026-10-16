import math
from PyQt6.QtCore import Qt, QPoint, QRect, QLineF
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QPainterPath, QImage, QPolygon
)
from snipaste.utils import apply_mosaic_to_image, apply_blur_to_image

class AnnotationItem:
    def draw(self, painter: QPainter, image: QImage):
        pass

class RectItem(AnnotationItem):
    def __init__(self, rect: QRect, color: QColor, width: int = 3, filled: bool = False):
        self.rect = rect
        self.color = color
        self.width = width
        self.filled = filled

    def draw(self, painter: QPainter, image: QImage):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(self.color, self.width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(QBrush(self.color) if self.filled else Qt.BrushStyle.NoBrush)
        painter.drawRect(self.rect)

class EllipseItem(AnnotationItem):
    def __init__(self, rect: QRect, color: QColor, width: int = 3, filled: bool = False):
        self.rect = rect
        self.color = color
        self.width = width
        self.filled = filled

    def draw(self, painter: QPainter, image: QImage):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(self.color, self.width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(QBrush(self.color) if self.filled else Qt.BrushStyle.NoBrush)
        painter.drawEllipse(self.rect)

class LineItem(AnnotationItem):
    def __init__(self, start: QPoint, end: QPoint, color: QColor, width: int = 3):
        self.start = start
        self.end = end
        self.color = color
        self.width = width

    def draw(self, painter: QPainter, image: QImage):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(self.color, self.width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawLine(self.start, self.end)

class ArrowItem(AnnotationItem):
    def __init__(self, start: QPoint, end: QPoint, color: QColor, width: int = 3):
        self.start = start
        self.end = end
        self.color = color
        self.width = width

    def draw(self, painter: QPainter, image: QImage):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(self.color, self.width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.MiterJoin)
        painter.setPen(pen)

        # Draw main stem
        painter.drawLine(self.start, self.end)

        # Draw arrow head
        dx = self.end.x() - self.start.x()
        dy = self.end.y() - self.start.y()
        angle = math.atan2(dy, dx)
        arrow_len = max(14, self.width * 3.5)
        arrow_angle = math.pi / 6.0  # 30 deg

        p1 = QPoint(
            int(self.end.x() - arrow_len * math.cos(angle - arrow_angle)),
            int(self.end.y() - arrow_len * math.sin(angle - arrow_angle))
        )
        p2 = QPoint(
            int(self.end.x() - arrow_len * math.cos(angle + arrow_angle)),
            int(self.end.y() - arrow_len * math.sin(angle + arrow_angle))
        )

        arrow_poly = QPolygon([self.end, p1, p2])
        painter.setBrush(QBrush(self.color))
        painter.drawPolygon(arrow_poly)

class PencilItem(AnnotationItem):
    def __init__(self, points: list[QPoint], color: QColor, width: int = 3):
        self.points = list(points)
        self.color = color
        self.width = width

    def draw(self, painter: QPainter, image: QImage):
        if len(self.points) < 2:
            return
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(self.color, self.width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)

        path = QPainterPath()
        p0 = self.points[0]
        path.moveTo(float(p0.x()), float(p0.y()))
        for p in self.points[1:]:
            path.lineTo(float(p.x()), float(p.y()))
        painter.drawPath(path)

class MarkerItem(AnnotationItem):
    def __init__(self, points: list[QPoint], color: QColor, width: int = 14):
        self.points = list(points)
        self.color = QColor(color)
        self.color.setAlpha(90)  # Semi-transparent highlighter
        self.width = width

    def draw(self, painter: QPainter, image: QImage):
        if len(self.points) < 2:
            return
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(self.color, self.width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.SquareCap, Qt.PenJoinStyle.BevelJoin)
        painter.setPen(pen)

        path = QPainterPath()
        p0 = self.points[0]
        path.moveTo(float(p0.x()), float(p0.y()))
        for p in self.points[1:]:
            path.lineTo(float(p.x()), float(p.y()))
        painter.drawPath(path)

class TextItem(AnnotationItem):
    def __init__(self, pos: QPoint, text: str, color: QColor, font_size: int = 16):
        self.pos = pos
        self.text = text
        self.color = color
        self.font_size = font_size

    def draw(self, painter: QPainter, image: QImage):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        font = QFont("Microsoft YaHei", self.font_size)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QPen(self.color))
        painter.drawText(self.pos, self.text)

class NumberItem(AnnotationItem):
    def __init__(self, center: QPoint, number: int, color: QColor, radius: int = 13):
        self.center = center
        self.number = number
        self.color = color
        self.radius = radius

    def draw(self, painter: QPainter, image: QImage):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        # Background badge circle
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self.color))
        painter.drawEllipse(self.center, self.radius, self.radius)

        # White inner text
        font = QFont("Arial", max(9, int(self.radius * 0.9)))
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QPen(Qt.GlobalColor.white))

        num_str = str(self.number)
        rect = QRect(
            self.center.x() - self.radius,
            self.center.y() - self.radius,
            self.radius * 2,
            self.radius * 2
        )
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, num_str)

class MosaicItem(AnnotationItem):
    def __init__(self, rect: QRect, block_size: int = 10):
        self.rect = rect
        self.block_size = block_size

    def draw(self, painter: QPainter, image: QImage):
        # Mosaics modify the pixel buffer directly in compositing pass
        pass

class BlurItem(AnnotationItem):
    def __init__(self, rect: QRect, radius: int = 8):
        self.rect = rect
        self.radius = radius

    def draw(self, painter: QPainter, image: QImage):
        pass


class AnnotationManager:
    """Manages drawing commands, undo/redo history, and composite rendering."""
    def __init__(self):
        self.items: list[AnnotationItem] = []
        self.redo_stack: list[AnnotationItem] = []
        self.step_counter = 1

    def add_item(self, item: AnnotationItem):
        self.items.append(item)
        self.redo_stack.clear()
        if isinstance(item, NumberItem):
            self.step_counter += 1

    def undo(self):
        if self.items:
            popped = self.items.pop()
            self.redo_stack.append(popped)
            if isinstance(popped, NumberItem):
                self.step_counter = max(1, self.step_counter - 1)

    def redo(self):
        if self.redo_stack:
            item = self.redo_stack.pop()
            self.items.append(item)
            if isinstance(item, NumberItem):
                self.step_counter += 1

    def clear(self):
        self.items.clear()
        self.redo_stack.clear()
        self.step_counter = 1

    def render_to_image(self, base_cropped_img: QImage) -> QImage:
        """Renders all annotations on top of the base cropped image."""
        result_img = base_cropped_img.copy()

        # 1. Apply image-level filter items (Mosaic & Blur) first
        for item in self.items:
            if isinstance(item, MosaicItem):
                result_img = apply_mosaic_to_image(result_img, item.rect, item.block_size)
            elif isinstance(item, BlurItem):
                result_img = apply_blur_to_image(result_img, item.rect, item.radius)

        # 2. Draw vector items
        painter = QPainter(result_img)
        for item in self.items:
            if not isinstance(item, (MosaicItem, BlurItem)):
                item.draw(painter, result_img)
        painter.end()

        return result_img
