import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

DEFAULT_CONFIG = {
    "window_x": 100,
    "window_y": 100,
    "window_width": 640,
    "window_height": 180,
    "opacity": 0.85,
    "font_size_original": 17,
    "font_size_translation": 14,
    "font_color_original": "#FFFFFF",
    "font_color_translation": "#70D6FF",
    "bg_color": "#121214",
    "display_mode": "3_lines",  # "1_line", "3_lines", "full"
    "click_through_on_start": False,
    "hotkey": "F8",
    "sync_offset_ms": 150
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                config = DEFAULT_CONFIG.copy()
                config.update(data)
                return config
        except Exception:
            return DEFAULT_CONFIG.copy()
    return DEFAULT_CONFIG.copy()

def save_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving config: {e}")
