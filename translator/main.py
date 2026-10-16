#!/usr/bin/env python3
import sys
import os

# Ensure translator directory and base directory in sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(CURRENT_DIR)
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QPoint, QRect
from PyQt6.QtGui import QImage, QGuiApplication

from translator.bridge import SnipasteBridge
from translator.ocr_worker import TranslationWorker
from translator.ui_card import FloatingTranslationCard

class TranslationApp:
    def __init__(self):
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        self.bridge = SnipasteBridge(APP_DIR)
        self.bridge.sig_translate_requested.connect(self.handle_translation)

        self.card = None
        self.worker = None

        self.bridge.start_hotkey_listener()
        print(f"[Translator] Translation Companion started. Listening for Alt+T / F2...")

    def handle_translation(self, image: QImage):
        if image.isNull():
            return

        if self.card is None:
            self.card = FloatingTranslationCard()
            self.card.sig_pin_translated.connect(self.bridge.pin_image_via_official_snipaste)

        self.card.set_loading()

        # Center card on primary screen or cursor
        screen = QGuiApplication.primaryScreen().geometry()
        card_x = max(10, screen.right() - 440)
        card_y = max(10, (screen.height() - 460) // 2)
        self.card.move(card_x, card_y)
        self.card.show()
        self.card.activateWindow()

        worker = TranslationWorker(image)
        def on_done(items, inplace_img):
            self.card.set_results(items, inplace_img)

        def on_err(err_msg):
            self.card.status_label.setText(f"翻译异常: {err_msg}")

        worker.sig_finished.connect(on_done)
        worker.sig_error.connect(on_err)
        worker.start()
        self.worker = worker

    def run(self):
        return self.app.exec()

def main():
    app = TranslationApp()
    sys.exit(app.run())

if __name__ == "__main__":
    main()
