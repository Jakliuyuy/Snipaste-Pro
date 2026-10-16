import os
import sys
import subprocess
import tempfile
import threading
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap, QGuiApplication

class SnipasteBridge(QObject):
    """
    Bridge connecting official Snipaste.exe and Translator.
    1. Triggers official Snipaste.exe snip --block
    2. Pins translated image via Snipaste.exe paste
    3. Global hotkey listener (Alt+T and F2)
    """
    sig_translate_requested = pyqtSignal(QImage)

    def __init__(self, app_dir: str):
        super().__init__()
        self.app_dir = app_dir
        self.snipaste_exe = os.path.join(app_dir, "Snipaste.exe")
        self._running = False
        self._thread = None
        self._listener = None

    def start_hotkey_listener(self):
        self._running = True
        if sys.platform == "win32":
            self._start_win32_hotkey()
        else:
            self._start_pynput_hotkey()

    def stop_hotkey_listener(self):
        self._running = False
        if self._listener:
            try:
                self._listener.stop()
            except Exception:
                pass

    def _start_win32_hotkey(self):
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        MOD_ALT = 0x0001
        MOD_NOREPEAT = 0x4000
        VK_T = 0x54
        VK_F2 = 0x71

        HOTKEY_ALT_T = 2001
        HOTKEY_F2 = 2002

        def worker():
            # Register Alt+T and F2
            user32.RegisterHotKey(None, HOTKEY_ALT_T, MOD_ALT | MOD_NOREPEAT, VK_T)
            user32.RegisterHotKey(None, HOTKEY_F2, MOD_NOREPEAT, VK_F2)

            msg = wintypes.MSG()
            while self._running:
                if user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
                    if msg.message == 0x0312:  # WM_HOTKEY
                        hk_id = msg.wParam
                        if hk_id in (HOTKEY_ALT_T, HOTKEY_F2):
                            self.trigger_screenshot_and_translate()
                    user32.TranslateMessage(ctypes.byref(msg))
                    user32.DispatchMessageW(ctypes.byref(msg))

            user32.UnregisterHotKey(None, HOTKEY_ALT_T)
            user32.UnregisterHotKey(None, HOTKEY_F2)

        self._thread = threading.Thread(target=worker, daemon=True)
        self._thread.start()

    def _start_pynput_hotkey(self):
        try:
            from pynput import keyboard
            current_keys = set()

            def on_press(key):
                current_keys.add(key)
                # Check F2
                if key == keyboard.Key.f2:
                    self.trigger_screenshot_and_translate()
                # Check Alt+T
                elif hasattr(key, "char") and key.char in ("t", "T"):
                    if keyboard.Key.alt in current_keys or keyboard.Key.alt_l in current_keys or keyboard.Key.alt_r in current_keys:
                        self.trigger_screenshot_and_translate()

            def on_release(key):
                if key in current_keys:
                    current_keys.remove(key)

            self._listener = keyboard.Listener(on_press=on_press, on_release=on_release)
            self._listener.daemon = True
            self._listener.start()
        except Exception as e:
            print(f"[Bridge] pynput hotkey error: {e}")

    def trigger_screenshot_and_translate(self):
        """
        Executes in background thread:
        Calls official Snipaste.exe snip --block -o temp_file
        """
        threading.Thread(target=self._run_snipaste_snip, daemon=True).start()

    def _run_snipaste_snip(self):
        temp_file = os.path.join(tempfile.gettempdir(), "snipaste_trans_temp.png")
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except Exception:
                pass

        # 1. Invoke official Snipaste.exe snip --block -o <temp_file>
        if os.path.exists(self.snipaste_exe):
            cmd = [self.snipaste_exe, "snip", "--block", "-o", temp_file]
            try:
                subprocess.run(cmd, timeout=120)
            except Exception as e:
                print(f"[Bridge] Snipaste invocation error: {e}")
        else:
            # Fallback for testing: grab clipboard image
            pass

        # 2. Check if temp_file was written
        if os.path.exists(temp_file):
            img = QImage(temp_file)
            if not img.isNull():
                self.sig_translate_requested.emit(img)
                try:
                    os.remove(temp_file)
                except Exception:
                    pass
                return

        # 3. Fallback: check clipboard
        cb = QGuiApplication.clipboard()
        if cb.mimeData().hasImage():
            img = cb.image()
            if not img.isNull():
                self.sig_translate_requested.emit(img)

    def pin_image_via_official_snipaste(self, image: QImage):
        """
        Copies image to clipboard and calls official Snipaste.exe paste (F3)
        so official Snipaste pins it on desktop with all native transforms and magnetic snapping!
        """
        cb = QGuiApplication.clipboard()
        cb.setPixmap(QPixmap.fromImage(image))
        if os.path.exists(self.snipaste_exe):
            cmd = [self.snipaste_exe, "paste"]
            try:
                subprocess.Popen(cmd)
            except Exception as e:
                print(f"[Bridge] Snipaste paste error: {e}")
