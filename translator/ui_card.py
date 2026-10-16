from PyQt6.QtCore import Qt, QPoint, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap, QGuiApplication, QColor, QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QApplication
)
from translator.ocr_worker import TranslationItem

class FloatingTranslationCard(QWidget):
    """
    Modern floating bilingual card displaying detected text and translation.
    Integrates directly with official Snipaste.exe (e.g. Pin translated image).
    """
    sig_pin_translated = pyqtSignal(QImage)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(400, 460)
        self.items: list[TranslationItem] = []
        self.inplace_image: QImage = None
        self._drag_pos = None
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        self.container = QFrame()
        self.container.setStyleSheet("""
            QFrame {
                background-color: rgba(28, 31, 38, 245);
                border: 1px solid rgba(75, 82, 98, 220);
                border-radius: 10px;
            }
            QLabel {
                color: #FFFFFF;
                font-family: 'Segoe UI', 'Microsoft YaHei';
            }
            QPushButton {
                background-color: #2D313A;
                color: #FFFFFF;
                border: 1px solid #484E5E;
                border-radius: 5px;
                padding: 4px 10px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #3C4353;
                border-color: #007AFF;
            }
            QPushButton:pressed {
                background-color: #007AFF;
            }
        """)
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(12, 12, 12, 12)
        container_layout.setSpacing(8)

        # Header bar
        header_layout = QHBoxLayout()
        title_icon = QLabel("🌐 截图实时翻译")
        title_icon.setStyleSheet("font-weight: bold; font-size: 14px; color: #00A3FF;")
        header_layout.addWidget(title_icon)
        header_layout.addStretch()

        self.btn_copy_all = QPushButton("一键复制全部译文")
        self.btn_copy_all.clicked.connect(self._copy_all_translations)
        header_layout.addWidget(self.btn_copy_all)

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(24, 24)
        btn_close.setStyleSheet("QPushButton { border-radius: 12px; font-weight: bold; color: #BBB; } QPushButton:hover { color: #FF4D4F; }")
        btn_close.clicked.connect(self.close)
        header_layout.addWidget(btn_close)
        container_layout.addLayout(header_layout)

        # Sub-header info
        lang_layout = QHBoxLayout()
        lang_info = QLabel("源语言: 自动检测 ➔ 目标语言: 简体中文")
        lang_info.setStyleSheet("color: #8E93A0; font-size: 11px;")
        lang_layout.addWidget(lang_info)
        container_layout.addLayout(lang_layout)

        # Content scroll area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(4, 4, 4, 4)
        self.content_layout.setSpacing(8)
        self.scroll_area.setWidget(self.content_widget)
        container_layout.addWidget(self.scroll_area)

        # Footer Action Bar
        footer_layout = QHBoxLayout()
        self.status_label = QLabel("正在翻译中...")
        self.status_label.setStyleSheet("color: #9DA3B0; font-size: 11px;")
        footer_layout.addWidget(self.status_label)
        footer_layout.addStretch()

        # Action: Copy translated image (with in-place text replacement)
        self.btn_copy_img = QPushButton("📋 复制译文图片")
        self.btn_copy_img.clicked.connect(self._copy_translated_image)
        footer_layout.addWidget(self.btn_copy_img)

        # Action: Pin translated image using official Snipaste (F3)
        self.btn_pin = QPushButton("📌 贴出译文")
        self.btn_pin.setStyleSheet("background-color: #007AFF; border-color: #0060DF; font-weight: bold;")
        self.btn_pin.clicked.connect(self._pin_translated)
        footer_layout.addWidget(self.btn_pin)

        container_layout.addLayout(footer_layout)
        main_layout.addWidget(self.container)

    def set_loading(self):
        self.status_label.setText("⏳ 正在进行 OCR 识别与极速翻译...")
        while self.content_layout.count():
            child = self.content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def set_results(self, items: list[TranslationItem], inplace_img: QImage):
        self.items = items
        self.inplace_image = inplace_img
        self.status_label.setText(f"✓ 已翻译 {len(items)} 条文本段落")

        while self.content_layout.count():
            child = self.content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if not items:
            empty_lbl = QLabel("未在截图中检测到清晰文字")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_lbl.setStyleSheet("color: #777; margin-top: 40px; font-size: 13px;")
            self.content_layout.addWidget(empty_lbl)
            return

        for idx, item in enumerate(items):
            card = QFrame()
            card.setStyleSheet("""
                QFrame {
                    background-color: #23262E;
                    border: 1px solid #363B47;
                    border-radius: 6px;
                    padding: 6px;
                }
            """)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(8, 8, 8, 8)
            card_layout.setSpacing(4)

            orig_lbl = QLabel(item.original_text)
            orig_lbl.setWordWrap(True)
            orig_lbl.setStyleSheet("color: #959AA8; font-size: 12px;")
            card_layout.addWidget(orig_lbl)

            trans_lbl = QLabel(item.translated_text)
            trans_lbl.setWordWrap(True)
            trans_lbl.setStyleSheet("color: #00A3FF; font-size: 13px; font-weight: bold;")
            card_layout.addWidget(trans_lbl)

            # Copy button for single item
            btn_copy_single = QPushButton("复制")
            btn_copy_single.setFixedSize(48, 22)
            btn_copy_single.clicked.connect(lambda _, t=item.translated_text: self._copy_text(t))
            card_layout.addWidget(btn_copy_single, alignment=Qt.AlignmentFlag.AlignRight)

            self.content_layout.addWidget(card)

        self.content_layout.addStretch()

    def _copy_text(self, text: str):
        QGuiApplication.clipboard().setText(text)
        self.status_label.setText("✓ 已复制单句译文到剪贴板！")

    def _copy_all_translations(self):
        full_text = "\n".join([item.translated_text for item in self.items])
        if full_text:
            QGuiApplication.clipboard().setText(full_text)
            self.status_label.setText("✓ 译文已全部复制到剪贴板！")

    def _copy_translated_image(self):
        if self.inplace_image and not self.inplace_image.isNull():
            QGuiApplication.clipboard().setPixmap(QPixmap.fromImage(self.inplace_image))
            self.status_label.setText("✓ 原位翻译图片已复制，可直接 Ctrl+V 粘贴！")

    def _pin_translated(self):
        if self.inplace_image and not self.inplace_image.isNull():
            self.sig_pin_translated.emit(self.inplace_image)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
