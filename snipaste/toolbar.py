from PyQt6.QtCore import Qt, QPoint, QRect, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QColor
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QButtonGroup,
    QColorDialog, QFrame
)

PALETTE_COLORS = [
    "#FF3B30",  # Red
    "#FF9500",  # Orange
    "#FFCC00",  # Yellow
    "#34C759",  # Green
    "#007AFF",  # Blue
    "#5856D6",  # Purple
    "#AF52DE",  # Magenta
    "#000000",  # Black
    "#FFFFFF"   # White
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

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(6)

        # Color buttons
        self.color_group = QButtonGroup(self)
        for hex_c in PALETTE_COLORS:
            btn = QPushButton()
            btn.setFixedSize(18, 18)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {hex_c};
                    border: 1px solid #555;
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
            btn.setFixedSize(18, 18)
            circle_r = max(2, min(14, w))
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #444;
                    border: 1px solid #666;
                    border-radius: 9px;
                }}
                QPushButton:hover {{
                    background-color: #666;
                    border-color: white;
                }}
            """)
            btn.setToolTip(f"粗细: {w}px")
            btn.clicked.connect(lambda _, width=w: self.sig_width_changed.emit(width))
            layout.addWidget(btn)

    def _on_color_click(self, hex_c: str):
        self.current_color = QColor(hex_c)
        self.sig_color_changed.emit(self.current_color)


class PaintBar(QWidget):
    """
    Floating annotation toolbar (Recreation of Snipaste AVPaintBar).
    """
    sig_tool_changed = pyqtSignal(str)   # rect, ellipse, arrow, line, pencil, marker, text, number, mosaic, blur, eraser
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
        self.active_tool = None
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(2)

        # Main Toolbar Frame
        self.bar_frame = QFrame()
        self.bar_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(30, 32, 40, 245);
                border: 1px solid rgba(80, 85, 100, 180);
                border-radius: 6px;
            }
            QPushButton {
                background-color: transparent;
                color: #EEE;
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 4px 6px;
                font-size: 13px;
                min-width: 24px;
                min-height: 24px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.15);
                border-color: rgba(255, 255, 255, 0.3);
            }
            QPushButton:checked {
                background-color: #1E90FF;
                color: white;
            }
        """)
        bar_layout = QHBoxLayout(self.bar_frame)
        bar_layout.setContentsMargins(4, 4, 4, 4)
        bar_layout.setSpacing(2)

        # Drawing Tool Buttons
        self.tools = [
            ("rect", "▭", "矩形"),
            ("ellipse", "◯", "椭圆"),
            ("arrow", "➔", "箭头"),
            ("line", "╱", "折线/直线"),
            ("pencil", "✎", "画笔"),
            ("marker", "🖌", "荧光记号笔"),
            ("text", "T", "文本"),
            ("number", "①", "序号标号"),
            ("mosaic", "▦", "马赛克"),
            ("blur", "≋", "高斯模糊"),
            ("eraser", "⌫", "橡皮擦")
        ]

        self.tool_buttons = {}
        for tool_id, icon_text, tip in self.tools:
            btn = QPushButton(icon_text)
            btn.setCheckable(True)
            btn.setToolTip(tip)
            btn.clicked.connect(lambda checked, t=tool_id: self._select_tool(t))
            bar_layout.addWidget(btn)
            self.tool_buttons[tool_id] = btn

        bar_layout.addSpacing(6)

        # Separator line
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.VLine)
        sep1.setStyleSheet("color: #555;")
        bar_layout.addWidget(sep1)

        bar_layout.addSpacing(6)

        # Undo / Redo
        self.btn_undo = QPushButton("↶")
        self.btn_undo.setToolTip("撤销 (Ctrl+Z)")
        self.btn_undo.clicked.connect(self.sig_undo.emit)
        bar_layout.addWidget(self.btn_undo)

        self.btn_redo = QPushButton("↷")
        self.btn_redo.setToolTip("重做 (Ctrl+Y)")
        self.btn_redo.clicked.connect(self.sig_redo.emit)
        bar_layout.addWidget(self.btn_redo)

        bar_layout.addSpacing(6)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.VLine)
        sep2.setStyleSheet("color: #555;")
        bar_layout.addWidget(sep2)

        bar_layout.addSpacing(6)

        # Real-time Translation Button (New Feature!)
        self.btn_translate = QPushButton("🌐")
        self.btn_translate.setToolTip("截图实时翻译 (T)")
        self.btn_translate.setStyleSheet("""
            QPushButton {
                color: #4BB5FF;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(75, 181, 255, 0.25);
            }
        """)
        self.btn_translate.clicked.connect(self.sig_translate.emit)
        bar_layout.addWidget(self.btn_translate)

        # Pin (贴图 F3)
        self.btn_pin = QPushButton("📌")
        self.btn_pin.setToolTip("贴图到屏幕 (F3 / Ctrl+T)")
        self.btn_pin.clicked.connect(self.sig_pin.emit)
        bar_layout.addWidget(self.btn_pin)

        # Save to File (Ctrl+S)
        self.btn_save = QPushButton("💾")
        self.btn_save.setToolTip("保存图片 (Ctrl+S)")
        self.btn_save.clicked.connect(self.sig_save.emit)
        bar_layout.addWidget(self.btn_save)

        # Copy to Clipboard (Ctrl+C / Enter)
        self.btn_copy = QPushButton("✓")
        self.btn_copy.setToolTip("复制到剪贴板 (Enter / Ctrl+C)")
        self.btn_copy.setStyleSheet("""
            QPushButton {
                background-color: #28A745;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #34C759;
            }
        """)
        self.btn_copy.clicked.connect(self.sig_copy.emit)
        bar_layout.addWidget(self.btn_copy)

        # Cancel / Close (Esc)
        self.btn_close = QPushButton("✕")
        self.btn_close.setToolTip("退出截图 (Esc)")
        self.btn_close.setStyleSheet("""
            QPushButton {
                color: #FF5555;
            }
            QPushButton:hover {
                background-color: rgba(255, 85, 85, 0.2);
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
            # Show sub-palette for non-eraser/mosaic tools if needed
            self.sub_palette.setVisible(tool_id not in ("eraser", "mosaic", "blur"))
            self.sig_tool_changed.emit(tool_id)
        self.adjustSize()

    def update_position(self, target_rect: QRect, screen_rect: QRect):
        """Positions the toolbar just below or above the snipping selection rectangle."""
        self.adjustSize()
        w, h = self.width(), self.height()

        # By default, put toolbar 8px below bottom-right of selection rect
        x = target_rect.right() - w
        y = target_rect.bottom() + 8

        # If too close to screen bottom, flip to top
        if y + h > screen_rect.bottom() - 10:
            y = target_rect.top() - h - 8

        # Keep within screen horizontal bounds
        x = max(screen_rect.left() + 10, min(x, screen_rect.right() - w - 10))
        y = max(screen_rect.top() + 10, min(y, screen_rect.bottom() - h - 10))

        self.move(x, y)
