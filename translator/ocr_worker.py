import sys
import requests
import json
from dataclasses import dataclass
from PyQt6.QtCore import Qt, QRect, QPoint, QThread, pyqtSignal, QBuffer, QIODevice
from PyQt6.QtGui import QImage, QPainter, QColor, QFont, QPen, QBrush

@dataclass
class OCRItem:
    text: str
    rect: QRect
    polygon: list[list[float]]
    confidence: float

@dataclass
class TranslationItem:
    ocr_item: OCRItem
    original_text: str
    translated_text: str

class OCREngine:
    """
    Modular OCR Engine supporting:
    1. Windows.Media.Ocr (Native Windows 10/11 built-in OCR, 0MB overhead, highly accurate)
    2. RapidOCR (Local PP-OCR ONNX if installed)
    3. Lightweight Cloud/Web OCR Fallback
    """
    def __init__(self):
        self._rapid_ocr = None
        try:
            from rapidocr_onnxruntime import RapidOCR
            self._rapid_ocr = RapidOCR()
        except Exception:
            self._rapid_ocr = None

    def recognize(self, image: QImage) -> list[OCRItem]:
        # 1. RapidOCR if available
        if self._rapid_ocr is not None:
            res = self._recognize_rapidocr(image)
            if res:
                return res

        # 2. Windows 10/11 native WinRT OCR
        if sys.platform == "win32":
            res = self._recognize_win_media_ocr(image)
            if res:
                return res

        return []

    def _recognize_rapidocr(self, image: QImage) -> list[OCRItem]:
        try:
            import numpy as np
            qimg = image.convertToFormat(QImage.Format.Format_RGB888)
            w, h = qimg.width(), qimg.height()
            ptr = qimg.bits()
            ptr.setsize(h * w * 3)
            img_np = np.frombuffer(ptr, np.uint8).reshape((h, w, 3)).copy()

            ocr_results, _ = self._rapid_ocr(img_np)
            if not ocr_results:
                return []

            items = []
            for entry in ocr_results:
                poly, text, score = entry[0], entry[1], float(entry[2])
                xs = [p[0] for p in poly]
                ys = [p[1] for p in poly]
                min_x, max_x = min(xs), max(xs)
                min_y, max_y = min(ys), max(ys)
                rect = QRect(int(min_x), int(min_y), int(max_x - min_x), int(max_y - min_y))
                items.append(OCRItem(text=text.strip(), rect=rect, polygon=poly, confidence=score))
            return items
        except Exception as e:
            print(f"[OCR] RapidOCR error: {e}")
            return []

    def _recognize_win_media_ocr(self, image: QImage) -> list[OCRItem]:
        try:
            import asyncio
            import winsdk.windows.graphics.imaging as imaging
            import winsdk.windows.media.ocr as win_ocr
            import winsdk.windows.storage.streams as streams

            ba = QBuffer()
            ba.open(QIODevice.OpenModeFlag.WriteOnly)
            image.save(ba, "PNG")
            img_bytes = bytes(ba.data())
            ba.close()

            async def run_win_ocr():
                writer = streams.DataWriter()
                writer.write_bytes(img_bytes)
                buf = writer.detach_buffer()

                decoder = await imaging.BitmapDecoder.create_async(streams.InMemoryRandomAccessStream())
                engine = win_ocr.OcrEngine.try_create_from_user_profile_languages()
                if not engine:
                    engine = win_ocr.OcrEngine.try_create_from_language_tag("zh-Hans-CN")
                if not engine:
                    return []

                software_bitmap = await decoder.get_software_bitmap_async()
                ocr_result = await engine.recognize_async(software_bitmap)

                items = []
                for line in ocr_result.lines:
                    if line.words:
                        r = line.words[0].bounding_rect
                        min_x = min(w.bounding_rect.x for w in line.words)
                        min_y = min(w.bounding_rect.y for w in line.words)
                        max_x = max(w.bounding_rect.x + w.bounding_rect.width for w in line.words)
                        max_y = max(w.bounding_rect.y + w.bounding_rect.height for w in line.words)
                        rect = QRect(int(min_x), int(min_y), int(max_x - min_x), int(max_y - min_y))
                        items.append(OCRItem(
                            text=line.text.strip(),
                            rect=rect,
                            polygon=[[min_x, min_y], [max_x, min_y], [max_x, max_y], [min_x, max_y]],
                            confidence=0.95
                        ))
                return items

            return asyncio.run(run_win_ocr())
        except Exception as e:
            print(f"[OCR] WinRT OCR error: {e}")
            return []


class TranslationService:
    @staticmethod
    def translate(text: str, source_lang="auto", target_lang="zh-CN") -> str:
        if not text.strip():
            return ""
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
            print(f"[Translation] Error: {e}")
            return text


class TranslationWorker(QThread):
    sig_finished = pyqtSignal(list, QImage)  # (items, inplace_img)
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

            inplace_img = self._generate_inplace_image(self.image, results)
            self.sig_finished.emit(results, inplace_img)
        except Exception as e:
            self.sig_error.emit(str(e))

    def _generate_inplace_image(self, base_img: QImage, items: list[TranslationItem]) -> QImage:
        img = base_img.copy()
        painter = QPainter(img)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        for item in items:
            rect = item.ocr_item.rect
            pad = 2
            erase_rect = rect.adjusted(-pad, -pad, pad, pad).intersected(img.rect())
            bg_color = self._sample_bg_color(base_img, erase_rect)

            brightness = (bg_color.red() * 299 + bg_color.green() * 587 + bg_color.blue() * 114) / 1000
            text_color = QColor(20, 20, 20) if brightness > 128 else QColor(245, 245, 245)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(bg_color))
            painter.drawRoundedRect(erase_rect, 2, 2)

            text = item.translated_text
            font_size = max(8, min(rect.height() - 4, 26))
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
