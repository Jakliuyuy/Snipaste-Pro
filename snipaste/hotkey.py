import sys
import threading
from PyQt6.QtCore import QObject, pyqtSignal

class HotkeyManager(QObject):
    """
    Global hotkey listener.
    Supports Win32 RegisterHotKey on Windows and pynput cross-platform fallback.
    """
    sig_snip = pyqtSignal()
    sig_paste = pyqtSignal()
    sig_click_through = pyqtSignal()
    sig_snip_copy = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_windows = sys.platform == "win32"
        self._running = False
        self._thread = None
        self._listener = None

    def start(self):
        self._running = True
        if self.is_windows:
            self._start_win32_hotkeys()
        else:
            self._start_pynput_hotkeys()

    def stop(self):
        self._running = False
        if self._listener:
            try:
                self._listener.stop()
            except Exception:
                pass

    def _start_win32_hotkeys(self):
        """Native Windows RegisterHotKey background message loop."""
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        MOD_ALT = 0x0001
        MOD_CONTROL = 0x0002
        MOD_SHIFT = 0x0004
        MOD_NOREPEAT = 0x4000

        # Virtual key codes
        VK_F1 = 0x70
        VK_F3 = 0x72
        VK_F4 = 0x73

        HOTKEY_SNIP_ID = 1001
        HOTKEY_PASTE_ID = 1002
        HOTKEY_CLICKTHRU_ID = 1003
        HOTKEY_SNIPCOPY_ID = 1004

        def worker():
            # Register hotkeys
            user32.RegisterHotKey(None, HOTKEY_SNIP_ID, MOD_NOREPEAT, VK_F1)
            user32.RegisterHotKey(None, HOTKEY_PASTE_ID, MOD_NOREPEAT, VK_F3)
            user32.RegisterHotKey(None, HOTKEY_CLICKTHRU_ID, MOD_NOREPEAT, VK_F4)
            user32.RegisterHotKey(None, HOTKEY_SNIPCOPY_ID, MOD_CONTROL | MOD_NOREPEAT, VK_F1)

            msg = wintypes.MSG()
            while self._running:
                # Peek or Get message
                if user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
                    if msg.message == 0x0312:  # WM_HOTKEY
                        hk_id = msg.wParam
                        if hk_id == HOTKEY_SNIP_ID:
                            self.sig_snip.emit()
                        elif hk_id == HOTKEY_PASTE_ID:
                            self.sig_paste.emit()
                        elif hk_id == HOTKEY_CLICKTHRU_ID:
                            self.sig_click_through.emit()
                        elif hk_id == HOTKEY_SNIPCOPY_ID:
                            self.sig_snip_copy.emit()
                    user32.TranslateMessage(ctypes.byref(msg))
                    user32.DispatchMessageW(ctypes.byref(msg))

            # Unregister
            user32.UnregisterHotKey(None, HOTKEY_SNIP_ID)
            user32.UnregisterHotKey(None, HOTKEY_PASTE_ID)
            user32.UnregisterHotKey(None, HOTKEY_CLICKTHRU_ID)
            user32.UnregisterHotKey(None, HOTKEY_SNIPCOPY_ID)

        self._thread = threading.Thread(target=worker, daemon=True)
        self._thread.start()

    def _start_pynput_hotkeys(self):
        """Cross-platform pynput Global Hotkey Listener."""
        try:
            from pynput import keyboard

            current_keys = set()

            def on_press(key):
                current_keys.add(key)
                # Check F1
                if key == keyboard.Key.f1:
                    if (keyboard.Key.ctrl in current_keys or
                        keyboard.Key.ctrl_l in current_keys or
                        keyboard.Key.ctrl_r in current_keys):
                        self.sig_snip_copy.emit()
                    else:
                        self.sig_snip.emit()
                # Check F3
                elif key == keyboard.Key.f3:
                    self.sig_paste.emit()
                # Check F4
                elif key == keyboard.Key.f4:
                    self.sig_click_through.emit()

            def on_release(key):
                if key in current_keys:
                    current_keys.remove(key)

            self._listener = keyboard.Listener(on_press=on_press, on_release=on_release)
            self._listener.daemon = True
            self._listener.start()
        except Exception as e:
            print(f"[Hotkey] Failed to start pynput listener: {e}")
