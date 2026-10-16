from PyQt6.QtCore import Qt, QPoint, QRect, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QColor
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QButtonGroup,
    QColorDialog, QFrame
)
from snipaste.icons import get_svg_icon

# Iconic Snipaste Palette Colors
PALETTE_COLORS = [
    "#FF3B30",  # Red
    "#FF9500",  # Orange
    "#FFCC00",  # Yellow
    "#34C759",  # Green
    "#007AFF",  # Blue
    "#5856D6",  # Purple
    "#AF52DE",  # Magenta
    "#FFFFFF",  # White
    "#000000",  # Black
]

STROKE_WIDTHS = [2, 4, 8, 14]

class SubPaletteBar(QWidget):
    """Sub-palette for picking stroke color and stroke width."""
    sig_color_changed = pyqtSignal(QColor)
    sig_width_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_color = QColor(PALETTE_COLORS[0])
        self.current_width = STROKE_WIDTHS[1]

        self.setStyleSheet("""
            QWidget {
                background-color: rgba(32, 35, 42, 250);
                border: 1px solid rgba(75, 82, 98, 200);
                border-radius: 6px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        # Color buttons
        for hex_c in PALETTE_COLORS:
            btn = QPushButton()
            btn.setFixedSize(18, 18)
            border_style = "border: 1px solid #777;" if hex_c != "#FFFFFF" else "border: 1px solid #BBB;"
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {hex_c};
                    {border_style}
                    border-radius: 9px;
                }}
                QPushButton:hover {{
                    border: 2px solid white;
                }}
            """)
            btn.clicked.connect(lambda _, c=hex_c: self._on_color_click(c))
            layout.addWidget(btn)

        layout.addSpacing(6)

        # Width buttons (sizes 2, 4, 8, 14)
        for w in STROKE_WIDTHS:
            btn = QPushButton()
            btn.setFixedSize(20, 20)
            dot_size = max(4, min(14, w))
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #2D313A;
                    border: 1px solid #4C5364;
                    border-radius: 10px;
                }}
                QPushButton:hover {{
                    background-color: #3F4756;
                    border-color: #007AFF;
                }}
            """)
            btn.setToolTip(f"线条粗细: {w}px")
            btn.clicked.connect(lambda _, width=w: self.sig_width_changed.emit(width))
            layout.addWidget(btn)

    def _on_color_click(self, hex_c: str):
        self.current_color = QColor(hex_c)
        self.sig_color_changed.emit(self.current_color)


class PaintBar(QWidget):
    """
    Floating annotation toolbar (Recreation of Snipaste AVPaintBar).
    """
    sig_tool_changed = pyqtSignal(str)
    sig_undo = pyqtSignal()
    sig_redo = pyqtSignal()
    sig_translate = pyqtSignal()
    sig_pin = pyqtSignal()
    sig_save = pyqtSignal()
    sig_copy = pyqtSignal()
    sig_close = pyqtSignal()
    sig_color_changed = pyqtSignal(QColor)
    sig_width_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.SubWindow | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.active_tool = None
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(4)

        # Main Toolbar Frame
        self.bar_frame = QFrame()
        self.bar_frame.setStyleSheet("""
            QFrame#mainBar {
                background-color: rgba(30, 33, 40, 248);
                border: 1px solid rgba(80, 88, 105, 220);
                border-radius: 6px;
            }
            QPushButton {
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 3px;
                min-width: 26px;
                min-height: 26px;
                max-width: 26px;
                max-height: 26px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.12);
                border-color: rgba(255, 255, 255, 0.2);
            }
            QPushButton:checked {
                background-color: #007AFF;
                border-color: #0062CC;
            }
        """)
        self.bar_frame.setObjectName("mainBar")
        bar_layout = QHBoxLayout(self.bar_frame)
        bar_layout.setContentsMargins(5, 5, 5, 5)
        bar_layout.setSpacing(2)

        # Drawing Tool Buttons
        self.tools = [
            ("rect", "矩形 (1)"),
            ("ellipse", "椭圆 (2)"),
            ("arrow", "箭头 (3)"),
            ("line", "折线/直线 (4)"),
            ("pencil", "画笔 (5)"),
            ("marker", "记号笔 (6)"),
            ("text", "文本 (7)"),
            ("number", "序号标号 (8)"),
            ("mosaic", "马赛克脱敏 (9)"),
            ("blur", "高斯模糊 (0)"),
            ("eraser", "橡皮擦 (E)")
        ]

        self.tool_buttons = {}
        for tool_id, tip in self.tools:
            btn = QPushButton()
            btn.setIcon(get_svg_icon(tool_id, "#DCE0E8"))
            btn.setIconSize(QSize(18, 18))
            btn.setCheckable(True)
            btn.setToolTip(tip)
            btn.clicked.connect(lambda checked, t=tool_id: self._select_tool(t))
            bar_layout.addWidget(btn)
            self.tool_buttons[tool_id] = btn

        bar_layout.addSpacing(4)

        # Separator line
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.VLine)
        sep1.setStyleSheet("color: #4A5060; max-width: 1px;")
        bar_layout.addWidget(sep1)

        bar_layout.addSpacing(4)

        # Undo / Redo
        self.btn_undo = QPushButton()
        self.btn_undo.setIcon(get_svg_icon("undo", "#DCE0E8"))
        self.btn_undo.setIconSize(QSize(18, 18))
        self.btn_undo.setToolTip("撤销 (Ctrl+Z)")
        self.btn_undo.clicked.connect(self.sig_undo.emit)
        bar_layout.addWidget(self.btn_undo)

        self.btn_redo = QPushButton()
        self.btn_redo.setIcon(get_svg_icon("redo", "#DCE0E8"))
        self.btn_redo.setIconSize(QSize(18, 18))
        self.btn_redo.setToolTip("重做 (Ctrl+Y)")
        self.btn_redo.clicked.connect(self.sig_redo.emit)
        bar_layout.addWidget(self.btn_redo)

        bar_layout.addSpacing(4)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.VLine)
        sep2.setStyleSheet("color: #4A5060; max-width: 1px;")
        bar_layout.addWidget(sep2)

        bar_layout.addSpacing(4)

        # Real-time Translation Button (Signature Feature)
        self.btn_translate = QPushButton()
        self.btn_translate.setIcon(get_svg_icon("translate", "#00A3FF"))
        self.btn_translate.setIconSize(QSize(19, 19))
        self.btn_translate.setToolTip("截图实时翻译 (T)")
        self.btn_translate.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 122, 255, 0.15);
                border: 1px solid rgba(0, 122, 255, 0.4);
            }
            QPushButton:hover {
                background-color: rgba(0, 122, 255, 0.35);
                border-color: #00A3FF;
            }
        """)
        self.btn_translate.clicked.connect(self.sig_translate.emit)
        bar_layout.addWidget(self.btn_translate)

        # Pin (贴图 F3 / Ctrl+T)
        self.btn_pin = QPushButton()
        self.btn_pin.setIcon(get_svg_icon("pin", "#DCE0E8"))
        self.btn_pin.setIconSize(QSize(18, 18))
        self.btn_pin.setToolTip("贴图到屏幕 (F3 / Ctrl+T)")
        self.btn_pin.clicked.connect(self.sig_pin.emit)
        bar_layout.addWidget(self.btn_pin)

        # Save to File (Ctrl+S)
        self.btn_save = QPushButton()
        self.btn_save.setIcon(get_svg_icon("save", "#DCE0E8"))
        self.btn_save.setIconSize(QSize(18, 18))
        self.btn_save.setToolTip("保存图片 (Ctrl+S)")
        self.btn_save.clicked.connect(self.sig_save.emit)
        bar_layout.addWidget(self.btn_save)

        # Copy to Clipboard (Ctrl+C / Enter) - Iconic Green Button
        self.btn_copy = QPushButton()
        self.btn_copy.setIcon(get_svg_icon("done", "#FFFFFF"))
        self.btn_copy.setIconSize(QSize(18, 18))
        self.btn_copy.setToolTip("完成截图并复制 (Enter / Ctrl+C)")
        self.btn_copy.setStyleSheet("""
            QPushButton {
                background-color: #22C55E;
                border: 1px solid #16A34A;
            }
            QPushButton:hover {
                background-color: #16A34A;
            }
        """)
        self.btn_copy.clicked.connect(self.sig_copy.emit)
        bar_layout.addWidget(self.btn_copy)

        # Cancel / Close (Esc)
        self.btn_close = QPushButton()
        self.btn_close.setIcon(get_svg_icon("close", "#FF5C5C"))
        self.btn_close.setIconSize(QSize(18, 18))
        self.btn_close.setToolTip("退出截图 (Esc)")
        self.btn_close.setStyleSheet("""
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.25);
                border-color: #EF4444;
            }
        """)
        self.btn_close.clicked.connect(self.sig_close.emit)
        bar_layout.addWidget(self.btn_close)

        main_layout.addWidget(self.bar_frame)

        # Sub-palette
        self.sub_palette = SubPaletteBar()
        self.sub_palette.sig_color_changed.connect(self.sig_color_changed.emit)
        self.sub_palette.sig_width_changed.connect(self.sig_width_changed.emit)
        self.sub_palette.setVisible(False)
        main_layout.addWidget(self.sub_palette)

    def _select_tool(self, tool_id: str):
        if self.active_tool == tool_id:
            # Deselect tool
            self.active_tool = None
            self.tool_buttons[tool_id].setChecked(False)
            self.sub_palette.setVisible(False)
            self.sig_tool_changed.emit("")
        else:
            self.active_tool = tool_id
            for tid, btn in self.tool_buttons.items():
                btn.setChecked(tid == tool_id)
            self.sub_palette.setVisible(tool_id not in ("eraser", "mosaic", "blur"))
            self.sig_tool_changed.emit(tool_id)
        self.adjustSize()

    def update_position(self, target_rect: QRect, screen_rect: QRect):
        """Positions the toolbar just below or above the snipping selection rectangle."""
        self.adjustSize()
        w, h = self.width(), self.height()

        x = target_rect.right() - w
        y = target_rect.bottom() + 8

        if y + h > screen_rect.bottom() - 10:
            y = target_rect.top() - h - 8

        x = max(screen_rect.left() + 10, min(x, screen_rect.right() - w - 10))
        y = max(screen_rect.top() + 10, min(y, screen_rect.bottom() - h - 10))

        self.move(x, y)
