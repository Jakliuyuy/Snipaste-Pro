import os
import sys
import configparser
from pathlib import Path

DEFAULT_CONFIG = {
    "General": {
        "theme_color": "#1E90FF",
        "play_sound": "true",
        "auto_save": "false",
        "save_dir": str(Path.home() / "Pictures" / "Snipaste"),
        "language": "zh_CN",
        "gpu_acceleration": "true"
    },
    "Snip": {
        "auto_detect_windows": "true",
        "show_magnifier": "true",
        "magnifier_zoom": "6",
        "color_format": "HEX",  # HEX, RGB, HSL
        "border_color": "#1E90FF",
        "border_width": "2",
        "dim_opacity": "140",   # 0 - 255
        "quick_copy": "false"
    },
    "Paste": {
        "magnetic_snap": "true",
        "magnetic_distance": "12",
        "default_opacity": "1.0",
        "opacity_step": "0.1",
        "max_history": "20",
        "zoom_factor": "1.15",
        "shadow_enabled": "true"
    },
    "Hotkey": {
        "snip": "F1",
        "paste": "F3",
        "click_through_toggle": "F4",
        "snip_and_copy": "Ctrl+F1",
        "translate": "T"
    },
    "Translation": {
        "engine": "google_free",     # google_free, bing_free, openai_compatible, deepseek
        "source_lang": "auto",       # auto, en, zh-CN, ja, ko, fr, de, ru
        "target_lang": "zh-CN",      # zh-CN, en, ja, ko, fr, de, ru
        "display_mode": "both",      # both, inplace, floating
        "api_key": "",
        "api_base": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "ocr_engine": "rapidocr",    # rapidocr, win_ocr, tesseract
        "auto_translate_on_snip": "false",
        "font_size_scale": "1.0"
    }
}

class ConfigManager:
    def __init__(self, config_path=None):
        if config_path:
            self.config_file = Path(config_path)
        else:
            # Portable mode check: look for config.ini in current directory or app directory
            local_config = Path(__file__).parent.parent / "config.ini"
            if local_config.exists():
                self.config_file = local_config
            else:
                app_dir = Path.home() / ".config" / "snipaste" if sys.platform != "win32" else Path(os.environ.get("APPDATA", str(Path.home()))) / "Snipaste"
                app_dir.mkdir(parents=True, exist_ok=True)
                self.config_file = app_dir / "config.ini"

        self.parser = configparser.ConfigParser()
        self.load()

    def load(self):
        # Initialize defaults
        for section, values in DEFAULT_CONFIG.items():
            if not self.parser.has_section(section):
                self.parser.add_section(section)
            for k, v in values.items():
                self.parser.set(section, k, str(v))

        if self.config_file.exists():
            try:
                self.parser.read(str(self.config_file), encoding="utf-8")
            except Exception as e:
                print(f"[Config] Error reading config: {e}")

    def save(self):
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, "w", encoding="utf-8") as f:
                self.parser.write(f)
        except Exception as e:
            print(f"[Config] Error writing config: {e}")

    def get(self, section, key, fallback=None):
        if fallback is None and section in DEFAULT_CONFIG and key in DEFAULT_CONFIG[section]:
            fallback = DEFAULT_CONFIG[section][key]
        return self.parser.get(section, key, fallback=fallback)

    def get_bool(self, section, key, fallback=False):
        val = self.get(section, key, str(fallback)).lower()
        return val in ("true", "1", "yes", "on")

    def get_int(self, section, key, fallback=0):
        try:
            return self.parser.getint(section, key, fallback=fallback)
        except ValueError:
            return fallback

    def get_float(self, section, key, fallback=0.0):
        try:
            return self.parser.getfloat(section, key, fallback=fallback)
        except ValueError:
            return fallback

    def set(self, section, key, value):
        if not self.parser.has_section(section):
            self.parser.add_section(section)
        self.parser.set(section, key, str(value))
        self.save()

# Global singleton
_config_instance = None

def get_config():
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigManager()
    return _config_instance
