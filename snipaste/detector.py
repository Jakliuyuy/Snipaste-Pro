import sys
import ctypes
from PyQt6.QtCore import QRect, QPoint

class WindowDetector:
    """
    Intelligent window and UI element boundary detector (Recreation of Snipaste AVWindowDetector).
    Uses Win32 DwmGetWindowAttribute + EnumChildWindows to discover exact element bounding boxes.
    """
    def __init__(self):
        self.is_windows = sys.platform == "win32"
        self._cached_rects = []

    def refresh(self):
        """Scans all visible windows and UI elements to update cache."""
        if not self.is_windows:
            return

        self._cached_rects.clear()

        user32 = ctypes.windll.user32
        dwmapi = ctypes.windll.dwmapi

        # RECT structure
        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long)
            ]

        # Callback types
        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

        def get_window_bounds(hwnd):
            rect = RECT()
            # Try DwmGetWindowAttribute(DWMWA_EXTENDED_FRAME_BOUNDS=9)
            DWMWA_EXTENDED_FRAME_BOUNDS = 9
            hr = dwmapi.DwmGetWindowAttribute(
                hwnd,
                DWMWA_EXTENDED_FRAME_BOUNDS,
                ctypes.byref(rect),
                ctypes.sizeof(rect)
            )
            if hr != 0:
                user32.GetWindowRect(hwnd, ctypes.byref(rect))
            w = rect.right - rect.left
            h = rect.bottom - rect.top
            if w > 10 and h > 10:
                return QRect(rect.left, rect.top, w, h)
            return None

        # Child windows enum
        def enum_child_callback(hwnd, lparam):
            if user32.IsWindowVisible(hwnd):
                r = get_window_bounds(hwnd)
                if r and r.width() > 10 and r.height() > 10:
                    self._cached_rects.append(r)
            return True

        child_proc = WNDENUMPROC(enum_child_callback)

        # Top-level windows enum
        def enum_windows_callback(hwnd, lparam):
            if not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd):
                return True

            # Skip Cloaked windows
            is_cloaked = ctypes.c_int(0)
            DWMWA_CLOAKED = 14
            dwmapi.DwmGetWindowAttribute(
                hwnd, DWMWA_CLOAKED, ctypes.byref(is_cloaked), ctypes.sizeof(is_cloaked)
            )
            if is_cloaked.value != 0:
                return True

            r = get_window_bounds(hwnd)
            if r:
                self._cached_rects.append(r)
                # Also enum direct children / controls (buttons, toolbars, etc.)
                user32.EnumChildWindows(hwnd, child_proc, 0)
            return True

        enum_proc = WNDENUMPROC(enum_windows_callback)
        user32.EnumWindows(enum_proc, 0)

    def find_best_rect(self, point: QPoint) -> QRect | None:
        """
        Finds the smallest (most specific) visible window or control rectangle containing the point.
        """
        if not self._cached_rects:
            self.refresh()

        best_rect = None
        min_area = float("inf")

        for r in self._cached_rects:
            if r.contains(point):
                area = r.width() * r.height()
                if area < min_area and area > 100:
                    min_area = area
                    best_rect = r

        return best_rect
