import requests
import json
from dataclasses import dataclass
from PyQt6.QtCore import Qt, QRect, QPoint, QThread, pyqtSignal, QObject
from PyQt6.QtGui import QImage, QPainter, QColor, QFont, QPen, QBrush, QGuiApplication
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QComboBox, QScrollArea, QFrame, QApplication
)
from snipaste.ocr_engine import OCREngine, OCRItem
from snipaste.config import get_config

@dataclass
class TranslationItem:
    ocr_item: OCRItem
    original_text: str
    translated_text: str

class TranslationService:
    """Multi-backend translation service."""

    @staticmethod
    def translate_google_free(text: str, source_lang: str = "auto", target_lang: str = "zh-CN") -> str:
        try:
            url = "https://translate.googleapis.com/translate_a/single"
            params = {
                "client": "gtx",
                "sl": source_lang,
                "tl": target_lang,
                "dt": "t",
                "q": text
            }
            resp = requests.get(url, params=params, timeout=6)
            data = resp.json()
            translated = "".join([segment[0] for segment in data[0] if segment and segment[0]])
            return translated if translated else text
        except Exception as e:
            print(f"[Translation] Google translate error: {e}")
            return text

    @staticmethod
    def translate_llm(text: str, api_key: str, api_base: str, model: str, target_lang: str = "zh-CN") -> str:
        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            prompt = f"Translate the following text accurately and naturally into {target_lang}. Output only the translation without explanation:\n\n{text}"
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3
            }
            endpoint = f"{api_base.rstrip('/')}/chat/completions"
            resp = requests.post(endpoint, json=payload, headers=headers, timeout=12)
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"[Translation] LLM translate error: {e}")
            return text

    @classmethod
    def translate(cls, text: str, source_lang="auto", target_lang="zh-CN") -> str:
        cfg = get_config()
        engine = cfg.get("Translation", "engine", "google_free")
        if engine == "openai_compatible":
            api_key = cfg.get("Translation", "api_key", "")
            api_base = cfg.get("Translation", "api_base", "https://api.openai.com/v1")
            model = cfg.get("Translation", "model", "gpt-4o-mini")
            if api_key:
                return cls.translate_llm(text, api_key, api_base, model, target_lang)
        return cls.translate_google_free(text, source_lang, target_lang)


class TranslationWorker(QThread):
    sig_finished = pyqtSignal(list, QImage)  # (list[TranslationItem], in_place_image)
    sig_error = pyqtSignal(str)

    def __init__(self, image: QImage, source_lang="auto", target_lang="zh-CN"):
        super().__init__()
        self.image = image
        self.source_lang = source_lang
        self.target_lang = target_lang

    def run(self):
        try:
            ocr = OCREngine()
            ocr_items = ocr.recognize(self.image)
            if not ocr_items:
                self.sig_finished.emit([], self.image)
                return

            results = []
            for item in ocr_items:
                orig = item.text
                trans = TranslationService.translate(orig, self.source_lang, self.target_lang)
                results.append(TranslationItem(ocr_item=item, original_text=orig, translated_text=trans))

            # Generate In-place translated image
            inplace_img = self._generate_inplace_image(self.image, results)
            self.sig_finished.emit(results, inplace_img)
        except Exception as e:
            self.sig_error.emit(str(e))

    def _generate_inplace_image(self, base_img: QImage, items: list[TranslationItem]) -> QImage:
        """
        Covers original text bounding boxes with sampled background color,
        and renders translated text with auto-fitting font size.
        """
        img = base_img.copy()
        painter = QPainter(img)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        for item in items:
            rect = item.ocr_item.rect
            # Expand rect slightly for clean text erasure
            pad = 2
            erase_rect = rect.adjusted(-pad, -pad, pad, pad).intersected(img.rect())

            # Sample background color around bounding box boundary
            bg_color = self._sample_bg_color(base_img, erase_rect)

            # Determine text color (contrast against background)
            brightness = (bg_color.red() * 299 + bg_color.green() * 587 + bg_color.blue() * 114) / 1000
            text_color = QColor(20, 20, 20) if brightness > 128 else QColor(245, 245, 245)

            # Fill background
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(bg_color))
            painter.drawRoundedRect(erase_rect, 3, 3)

            # Auto-calculate font size to fit inside bounding box
            text = item.translated_text
            font_size = max(8, min(rect.height() - 4, 28))
            font = QFont("Microsoft YaHei", font_size)
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(QPen(text_color))

            painter.drawText(
                erase_rect,
                Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                text
            )

        painter.end()
        return img

    def _sample_bg_color(self, img: QImage, rect: QRect) -> QColor:
        # Sample the 4 outer corner pixels around the box
        coords = [
            (max(0, rect.left() - 2), max(0, rect.top() - 2)),
            (min(img.width() - 1, rect.right() + 2), max(0, rect.top() - 2)),
            (max(0, rect.left() - 2), min(img.height() - 1, rect.bottom() + 2)),
            (min(img.width() - 1, rect.right() + 2), min(img.height() - 1, rect.bottom() + 2))
        ]
        r, g, b = 0, 0, 0
        for x, y in coords:
            c = img.pixelColor(x, y)
            r += c.red()
            g += c.green()
            b += c.blue()
        return QColor(r // 4, g // 4, b // 4)


class FloatingTranslationCard(QWidget):
    """
    Modern floating bilingual card displaying detected text and translation.
    """
    sig_apply_inplace = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(380, 420)
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        self.container = QFrame()
        self.container.setStyleSheet("""
            QFrame {
                background-color: rgba(30, 32, 40, 245);
                border: 1px solid rgba(80, 85, 100, 180);
                border-radius: 10px;
            }
            QLabel {
                color: #FFFFFF;
                font-family: 'Segoe UI', 'Microsoft YaHei';
            }
            QPushButton {
                background-color: #2D3139;
                color: #FFFFFF;
                border: 1px solid #4A5060;
                border-radius: 5px;
                padding: 4px 10px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #3E4452;
                border-color: #1E90FF;
            }
            QPushButton:pressed {
                background-color: #1E90FF;
            }
        """)
        container_layout = QVBoxLayout(self.container)

        # Header bar
        header_layout = QHBoxLayout()
        title_icon = QLabel("🌐 截图实时翻译")
        title_icon.setStyleSheet("font-weight: bold; font-size: 14px; color: #1E90FF;")
        header_layout.addWidget(title_icon)
        header_layout.addStretch()

        self.btn_copy_all = QPushButton("一键复制译文")
        self.btn_copy_all.clicked.connect(self._copy_all_translations)
        header_layout.addWidget(self.btn_copy_all)

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(24, 24)
        btn_close.setStyleSheet("QPushButton { border-radius: 12px; font-weight: bold; }")
        btn_close.clicked.connect(self.close)
        header_layout.addWidget(btn_close)
        container_layout.addLayout(header_layout)

        # Language indicator
        lang_layout = QHBoxLayout()
        lang_info = QLabel("源语言: 自动检测 ➔ 目标语言: 简体中文")
        lang_info.setStyleSheet("color: #8E9297; font-size: 11px;")
        lang_layout.addWidget(lang_info)
        container_layout.addLayout(lang_layout)

        # Content scroll area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(4, 4, 4, 4)
        self.content_layout.setSpacing(10)
        self.scroll_area.setWidget(self.content_widget)
        container_layout.addWidget(self.scroll_area)

        # Status & Action bar
        footer_layout = QHBoxLayout()
        self.status_label = QLabel("正在翻译中...")
        self.status_label.setStyleSheet("color: #A0A5B0; font-size: 11px;")
        footer_layout.addWidget(self.status_label)
        footer_layout.addStretch()

        self.btn_inplace = QPushButton("原位图片替换")
        self.btn_inplace.setStyleSheet("background-color: #1E90FF; border: none; font-weight: bold;")
        self.btn_inplace.clicked.connect(self.sig_apply_inplace.emit)
        footer_layout.addWidget(self.btn_inplace)
        container_layout.addLayout(footer_layout)

        main_layout.addWidget(self.container)
        self.items = []

    def set_loading(self):
        self.status_label.setText("⏳ 正在进行 OCR 识别与实时翻译...")
        # Clear existing items
        while self.content_layout.count():
            child = self.content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def set_results(self, items: list[TranslationItem]):
        self.items = items
        self.status_label.setText(f"✓ 已翻译 {len(items)} 条文本段落")

        while self.content_layout.count():
            child = self.content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if not items:
            empty_lbl = QLabel("未在截图区域检测到可识别文字")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_lbl.setStyleSheet("color: #777; margin-top: 30px;")
            self.content_layout.addWidget(empty_lbl)
            return

        for idx, item in enumerate(items):
            card = QFrame()
            card.setStyleSheet("""
                QFrame {
                    background-color: #242730;
                    border: 1px solid #363B47;
                    border-radius: 6px;
                    padding: 6px;
                }
            """)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(6, 6, 6, 6)
            card_layout.setSpacing(4)

            orig_lbl = QLabel(item.original_text)
            orig_lbl.setWordWrap(True)
            orig_lbl.setStyleSheet("color: #9BA1B0; font-size: 12px;")
            card_layout.addWidget(orig_lbl)

            trans_lbl = QLabel(item.translated_text)
            trans_lbl.setWordWrap(True)
            trans_lbl.setStyleSheet("color: #4BB5FF; font-size: 13px; font-weight: bold;")
            card_layout.addWidget(trans_lbl)

            # Copy button for single item
            btn_copy_single = QPushButton("复制")
            btn_copy_single.setFixedSize(50, 22)
            btn_copy_single.clicked.connect(lambda _, t=item.translated_text: self._copy_text(t))
            card_layout.addWidget(btn_copy_single, alignment=Qt.AlignmentFlag.AlignRight)

            self.content_layout.addWidget(card)

        self.content_layout.addStretch()

    def _copy_text(self, text: str):
        QGuiApplication.clipboard().setText(text)

    def _copy_all_translations(self):
        full_text = "\n".join([item.translated_text for item in self.items])
        if full_text:
            QGuiApplication.clipboard().setText(full_text)
            self.status_label.setText("✓ 译文已全部复制到剪贴板！")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and hasattr(self, "_drag_pos"):
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
