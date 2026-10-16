#!/usr/bin/env python3
import sys
import os

# Ensure current directory is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import argparse
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import QPoint

from snipaste.app import SnipasteApp

def main():
    parser = argparse.ArgumentParser(description="Snipaste Reimplementation with Real-time Translation")
    parser.add_argument("--snip-full", action="store_true", help="立即全屏截图并复制")
    parser.add_argument("--paste-files", nargs="+", help="将指定图片文件贴到屏幕上")
    parser.add_argument("--click-through-toggle", action="store_true", help="切换所有贴图鼠标穿透模式")

    args, unknown = parser.parse_known_args()

    app = SnipasteApp(sys.argv)

    if args.snip_full:
        app.trigger_snip()
    elif args.paste_files:
        for f in args.paste_files:
            pix = QPixmap(f)
            if not pix.isNull():
                app.create_paster(pix, QPoint(200, 200))
    elif args.click_through_toggle:
        app.toggle_click_through()

    sys.exit(app.run())

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        log_file = os.path.join(BASE_DIR, "snipaste_error.log")
        with open(log_file, "w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                0,
                f"Snipaste 启动发生异常:\n{e}\n\n详细崩溃日志已保存至:\n{log_file}",
                "Snipaste 异常提示",
                0x10
            )
        except Exception:
            pass
        sys.exit(1)
