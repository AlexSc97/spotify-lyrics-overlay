import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

DEFAULT_CONFIG = {
    "window_x": 150,
    "window_y": 150,
    "window_width": 680,
    "window_height": 185,
    "opacity": 0.80,  # Opacidad de fondo: 0.0 (transparente total) a 1.0 (opaco)
    "font_size_original": 17,
    "font_size_translation": 14,
    "font_color_original": "#FFFFFF",
    "font_color_translation": "#70D6FF",
    "bg_color": "#0E1016",
    "display_mode": "3_lines",  # "1_line", "3_lines"
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
