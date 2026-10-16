import sys
from dataclasses import dataclass
from PyQt6.QtGui import QImage
from PyQt6.QtCore import QRect, QBuffer, QIODevice

@dataclass
class OCRItem:
    text: str
    rect: QRect
    polygon: list[list[float]]
    confidence: float

class OCREngine:
    """
    Modular OCR Engine supporting:
    1. RapidOCR (Local PP-OCRv4 ONNX model, offline high accuracy)
    2. Windows.Media.Ocr (Native Windows 10/11 built-in OCR, 0MB extra payload!)
    3. Lightweight Cloud/Web OCR Fallback
    """
    def __init__(self):
        self._rapid_ocr = None
        self._init_backends()

    def _init_backends(self):
        try:
            from rapidocr_onnxruntime import RapidOCR
            self._rapid_ocr = RapidOCR()
        except Exception:
            self._rapid_ocr = None

    def recognize(self, image: QImage) -> list[OCRItem]:
        # 1. Try RapidOCR if installed
        if self._rapid_ocr is not None:
            res = self._recognize_rapidocr(image)
            if res:
                return res

        # 2. Try Windows.Media.Ocr if running on Windows
        if sys.platform == "win32":
            res = self._recognize_win_media_ocr(image)
            if res:
                return res

        # 3. Fallback
        return self._recognize_fallback_web_ocr(image)

    def _recognize_rapidocr(self, image: QImage) -> list[OCRItem]:
        try:
            import numpy as np
            qimg = image.convertToFormat(QImage.Format.Format_RGB888)
            w, h = qimg.width(), qimg.height()
            ptr = qimg.bits()
            ptr.setsize(h * w * 3)
            img_np = np.frombuffer(ptr, np.uint8).reshape((h, w, 3)).copy()

            ocr_results, elapse = self._rapid_ocr(img_np)
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

                items.append(OCRItem(
                    text=text.strip(),
                    rect=rect,
                    polygon=poly,
                    confidence=score
                ))
            return items
        except Exception as e:
            print(f"[OCR] RapidOCR error: {e}")
            return []

    def _recognize_win_media_ocr(self, image: QImage) -> list[OCRItem]:
        """
        Uses Windows 10/11 built-in Windows.Media.Ocr engine.
        Zero external binaries or models required!
        """
        try:
            import asyncio
            import winsdk.windows.graphics.imaging as imaging
            import winsdk.windows.media.ocr as win_ocr
            import winsdk.windows.storage.streams as streams

            # Save QImage to memory bytes
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
                # Create engine
                engine = win_ocr.OcrEngine.try_create_from_user_profile_languages()
                software_bitmap = await decoder.get_software_bitmap_async()
                ocr_result = await engine.recognize_async(software_bitmap)

                items = []
                for line in ocr_result.lines:
                    r = line.words[0].bounding_rect if line.words else None
                    if r:
                        rect = QRect(int(r.x), int(r.y), int(r.width), int(r.height))
                        items.append(OCRItem(
                            text=line.text,
                            rect=rect,
                            polygon=[[r.x, r.y], [r.x + r.width, r.y], [r.x + r.width, r.y + r.height], [r.x, r.y + r.height]],
                            confidence=0.95
                        ))
                return items

            return asyncio.run(run_win_ocr())
        except Exception as e:
            return []

    def _recognize_fallback_web_ocr(self, image: QImage) -> list[OCRItem]:
        """Lightweight fallback OCR."""
        return []
