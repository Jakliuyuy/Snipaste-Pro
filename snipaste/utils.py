import sys
import colorsys
from pathlib import Path
from PyQt6.QtCore import QUrl, QRect, QPoint, QSize, Qt
from PyQt6.QtGui import QColor, QImage, QPixmap, QPainter, QBrush, QPen

# Try importing QSoundEffect if available
try:
    from PyQt6.QtMultimedia import QSoundEffect
    HAS_QT_AUDIO = True
except ImportError:
    HAS_QT_AUDIO = False

_SOUND_CACHE = {}

def get_asset_path(filename: str) -> Path:
    assets_dir = Path(__file__).parent / "assets"
    return assets_dir / filename

def play_sound(name: str):
    """Plays snip or bubble sound if available and enabled."""
    from snipaste.config import get_config
    if not get_config().get_bool("General", "play_sound", True):
        return

    wav_file = get_asset_path(f"{name}.wav")
    if not wav_file.exists():
        return

    # 1. Try Windows winsound if on Windows
    if sys.platform == "win32":
        try:
            import winsound
            winsound.PlaySound(str(wav_file), winsound.SND_FILENAME | winsound.SND_ASYNC)
            return
        except Exception:
            pass

    # 2. Try QtMultimedia
    if HAS_QT_AUDIO:
        try:
            if name not in _SOUND_CACHE:
                effect = QSoundEffect()
                effect.setSource(QUrl.fromLocalFile(str(wav_file)))
                _SOUND_CACHE[name] = effect
            _SOUND_CACHE[name].play()
            return
        except Exception:
            pass

def rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02X}{g:02X}{b:02X}"

def hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    hex_str = hex_str.lstrip("#")
    if len(hex_str) == 6:
        return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))
    return (0, 0, 0)

def rgb_to_hsl(r: int, g: int, b: int) -> tuple[int, int, int]:
    h, l, s = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)
    return (int(h * 360), int(s * 100), int(l * 100))

def format_color_string(r: int, g: int, b: int, mode="HEX") -> str:
    mode = mode.upper()
    if mode == "HEX":
        return rgb_to_hex(r, g, b)
    elif mode == "RGB":
        return f"RGB({r}, {g}, {b})"
    elif mode == "HSL":
        h, s, l = rgb_to_hsl(r, g, b)
        return f"HSL({h}, {s}%, {l}%)"
    return rgb_to_hex(r, g, b)

def apply_mosaic_to_image(img: QImage, rect: QRect, block_size: int = 12) -> QImage:
    """Applies pixelated mosaic effect to a specified rect within QImage."""
    res_img = img.copy()
    x1 = max(0, rect.left())
    y1 = max(0, rect.top())
    x2 = min(img.width(), rect.right() + 1)
    y2 = min(img.height(), rect.bottom() + 1)

    for by in range(y1, y2, block_size):
        for bx in range(x1, x2, block_size):
            bw = min(block_size, x2 - bx)
            bh = min(block_size, y2 - by)
            # Sample center pixel of block
            sample_x = min(bx + bw // 2, x2 - 1)
            sample_y = min(by + bh // 2, y2 - 1)
            sample_color = img.pixelColor(sample_x, sample_y)

            for dy in range(bh):
                for dx in range(bw):
                    res_img.setPixelColor(bx + dx, by + dy, sample_color)
    return res_img

def apply_blur_to_image(img: QImage, rect: QRect, radius: int = 8) -> QImage:
    """Applies box/gaussian-like blur to a rect in QImage using multi-pass downsampling."""
    target_rect = rect.intersected(img.rect())
    if target_rect.isEmpty():
        return img

    sub = img.copy(target_rect)
    # Downscale and upscale for high-performance smooth blur
    scaled = sub.scaled(
        max(1, sub.width() // radius),
        max(1, sub.height() // radius),
        Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.SmoothTransformation
    )
    blurred = scaled.scaled(
        sub.width(),
        sub.height(),
        Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.SmoothTransformation
    )

    res_img = img.copy()
    painter = QPainter(res_img)
    painter.drawImage(target_rect.topLeft(), blurred)
    painter.end()
    return res_img

def calculate_magnetic_snap(source_rect: QRect, target_rects: list[QRect], threshold: int = 12) -> tuple[int, int]:
    """
    Computes delta (dx, dy) to snap source_rect edges to target_rects (e.g. screen boundaries or other windows).
    """
    dx, dy = 0, 0
    min_dist_x = threshold + 1
    min_dist_y = threshold + 1

    s_left, s_right = source_rect.left(), source_rect.right()
    s_top, s_bottom = source_rect.top(), source_rect.bottom()

    for target in target_rects:
        t_left, t_right = target.left(), target.right()
        t_top, t_bottom = target.top(), target.bottom()

        # Check vertical overlap to qualify for horizontal snap
        if not (s_bottom < t_top or s_top > t_bottom):
            # Left to Target Left
            if abs(s_left - t_left) < min_dist_x:
                min_dist_x = abs(s_left - t_left)
                dx = t_left - s_left
            # Left to Target Right
            if abs(s_left - t_right) < min_dist_x:
                min_dist_x = abs(s_left - t_right)
                dx = t_right - s_left
            # Right to Target Left
            if abs(s_right - t_left) < min_dist_x:
                min_dist_x = abs(s_right - t_left)
                dx = t_left - s_right
            # Right to Target Right
            if abs(s_right - t_right) < min_dist_x:
                min_dist_x = abs(s_right - t_right)
                dx = t_right - s_right

        # Check horizontal overlap to qualify for vertical snap
        if not (s_right < t_left or s_left > t_right):
            # Top to Target Top
            if abs(s_top - t_top) < min_dist_y:
                min_dist_y = abs(s_top - t_top)
                dy = t_top - s_top
            # Top to Target Bottom
            if abs(s_top - t_bottom) < min_dist_y:
                min_dist_y = abs(s_top - t_bottom)
                dy = t_bottom - s_top
            # Bottom to Target Top
            if abs(s_bottom - t_top) < min_dist_y:
                min_dist_y = abs(s_bottom - t_top)
                dy = t_top - s_bottom
            # Bottom to Target Bottom
            if abs(s_bottom - t_bottom) < min_dist_y:
                min_dist_y = abs(s_bottom - t_bottom)
                dy = t_bottom - s_bottom

    return (dx, dy)
