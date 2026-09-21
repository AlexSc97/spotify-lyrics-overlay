import os
import time
import ctypes
from ctypes import wintypes
from typing import List, Dict, Optional

from PyQt6.QtCore import Qt, QPoint, pyqtSlot, QTimer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QGraphicsDropShadowEffect, QFrame, QSizePolicy
)
from PyQt6.QtGui import QColor, QFont

import config

GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED = 0x00080000

class OverlayWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.cfg = config.load_config()
        self.click_through = False
        self.drag_position = QPoint()

        self.lyrics_data: List[Dict[str, any]] = []
        self.current_line_idx = -1
        self.current_title = ""
        self.current_artist = ""

        # Control de sincronización suave
        self.base_pos = 0.0
        self.is_playing = False
        self.sync_timestamp = time.time()
        self.sync_offset_ms = self.cfg.get("sync_offset_ms", 150)

        self._init_window_flags()
        self._init_ui()
        self._apply_styling()

        # Restaurar posición y tamaño
        self.setGeometry(
            self.cfg.get("window_x", 150),
            self.cfg.get("window_y", 150),
            self.cfg.get("window_width", 680),
            self.cfg.get("window_height", 185)
        )

        # Timer de alta frecuencia (30ms = ~33 FPS) para sincronización milimétrica continua
        self.render_timer = QTimer(self)
        self.render_timer.setInterval(30)
        self.render_timer.timeout.connect(self._on_render_tick)
        self.render_timer.start()

        if self.cfg.get("click_through_on_start", False):
            self.toggle_click_through(True)

    def _init_window_flags(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.SubWindow
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(4)

        # Contenedor con borde y fondo semitransparente
        self.container = QFrame(self)
        self.container.setObjectName("container")
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(14, 8, 14, 10)
        container_layout.setSpacing(4)

        # 1. Barra superior de control y título
        self.header_layout = QHBoxLayout()
        self.header_layout.setSpacing(6)

        self.lbl_title = QLabel("🎵 Esperando reproducción en Spotify...", self.container)
        self.lbl_title.setObjectName("trackInfo")
        self.lbl_title.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.header_layout.addWidget(self.lbl_title)

        # Ajuste fino de sincronización (+/- 100ms)
        self.btn_sync_minus = QPushButton("-0.1s", self.container)
        self.btn_sync_minus.setObjectName("btnSmall")
        self.btn_sync_minus.setToolTip("Retrasar letra 100ms")
        self.btn_sync_minus.clicked.connect(lambda: self._adjust_sync_offset(-100))
        self.header_layout.addWidget(self.btn_sync_minus)

        self.lbl_sync_info = QPushButton(f"Sync: {self.sync_offset_ms:+d}ms", self.container)
        self.lbl_sync_info.setObjectName("btnSmall")
        self.lbl_sync_info.setToolTip("Compensación de sincronización. Haz clic para reiniciar a 0ms.")
        self.lbl_sync_info.clicked.connect(self._reset_sync_offset)
        self.header_layout.addWidget(self.lbl_sync_info)

        self.btn_sync_plus = QPushButton("+0.1s", self.container)
        self.btn_sync_plus.setObjectName("btnSmall")
        self.btn_sync_plus.setToolTip("Adelantar letra 100ms")
        self.btn_sync_plus.clicked.connect(lambda: self._adjust_sync_offset(100))
        self.header_layout.addWidget(self.btn_sync_plus)

        # Indicador de modo juego / candado
        self.btn_lock = QPushButton("🔒 Modo Juego (F8)", self.container)
        self.btn_lock.setObjectName("btnLock")
        self.btn_lock.setToolTip("Activa el modo fantasma: los clics pasan directo al LoL / juego.\nPulsa F8 o Ctrl+Alt+L para desbloquear.")
        self.btn_lock.clicked.connect(lambda: self.toggle_click_through(True))
        self.header_layout.addWidget(self.btn_lock)

        # Botón para alternar modo de líneas (1 línea o 3 líneas)
        self.btn_mode = QPushButton("3L", self.container)
        self.btn_mode.setObjectName("btnSmall")
        self.btn_mode.setToolTip("Alternar entre 3 líneas o 1 línea compacta")
        self.btn_mode.clicked.connect(self._toggle_display_mode)
        self.header_layout.addWidget(self.btn_mode)

        # Botones de tamaño de letra
        self.btn_font_dec = QPushButton("A-", self.container)
        self.btn_font_dec.setObjectName("btnSmall")
        self.btn_font_dec.clicked.connect(lambda: self._adjust_font_size(-1))
        self.header_layout.addWidget(self.btn_font_dec)

        self.btn_font_inc = QPushButton("A+", self.container)
        self.btn_font_inc.setObjectName("btnSmall")
        self.btn_font_inc.clicked.connect(lambda: self._adjust_font_size(1))
        self.header_layout.addWidget(self.btn_font_inc)

        # Botón cerrar
        self.btn_close = QPushButton("✕", self.container)
        self.btn_close.setObjectName("btnClose")
        self.btn_close.clicked.connect(self.close)
        self.header_layout.addWidget(self.btn_close)

        container_layout.addLayout(self.header_layout)

        # 2. Área de Letras
        self.lyrics_layout = QVBoxLayout()
        self.lyrics_layout.setSpacing(2)

        # Línea previa (tenue)
        self.lbl_prev = QLabel("", self.container)
        self.lbl_prev.setObjectName("prevLyric")
        self.lbl_prev.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._add_shadow(self.lbl_prev)
        self.lyrics_layout.addWidget(self.lbl_prev)

        # Línea actual original (destacada en blanco)
        self.lbl_current_orig = QLabel("Abre Spotify y reproduce cualquier canción", self.container)
        self.lbl_current_orig.setObjectName("currentOrig")
        self.lbl_current_orig.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_current_orig.setWordWrap(True)
        self._add_shadow(self.lbl_current_orig, radius=12, opacity=0.95)
        self.lyrics_layout.addWidget(self.lbl_current_orig)

        # Línea actual traducida al español (justo abajo en cian suave)
        self.lbl_current_trans = QLabel("La traducción al español aparecerá aquí", self.container)
        self.lbl_current_trans.setObjectName("currentTrans")
        self.lbl_current_trans.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_current_trans.setWordWrap(True)
        self._add_shadow(self.lbl_current_trans, radius=10, opacity=0.9)
        self.lyrics_layout.addWidget(self.lbl_current_trans)

        # Línea siguiente (tenue)
        self.lbl_next = QLabel("", self.container)
        self.lbl_next.setObjectName("nextLyric")
        self.lbl_next.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._add_shadow(self.lbl_next)
        self.lyrics_layout.addWidget(self.lbl_next)

        container_layout.addLayout(self.lyrics_layout)

        # Indicador flotante sutil para cuando esté bloqueado en modo juego
        self.lbl_game_mode_indicator = QLabel("🔒 Modo Juego Activo (Presiona F8 para desbloquear/mover)", self.container)
        self.lbl_game_mode_indicator.setObjectName("gameModeIndicator")
        self.lbl_game_mode_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_game_mode_indicator.setVisible(False)
        container_layout.addWidget(self.lbl_game_mode_indicator)

        main_layout.addWidget(self.container)

    def _add_shadow(self, widget: QLabel, radius: int = 8, opacity: float = 0.85):
        shadow = QGraphicsDropShadowEffect(widget)
        shadow.setBlurRadius(radius)
        shadow.setColor(QColor(0, 0, 0, int(255 * opacity)))
        shadow.setOffset(0, 2)
        widget.setGraphicsEffect(shadow)

    def _apply_styling(self):
        f_orig = self.cfg.get("font_size_original", 17)
        f_trans = self.cfg.get("font_size_translation", 14)
        c_orig = self.cfg.get("font_color_original", "#FFFFFF")
        c_trans = self.cfg.get("font_color_translation", "#70D6FF")

        stylesheet = f"""
            QFrame#container {{
                background-color: rgba(14, 16, 22, {int(self.cfg.get("opacity", 0.85) * 255)});
                border-radius: 12px;
                border: 1px solid rgba(255, 255, 255, 0.12);
            }}
            QLabel#trackInfo {{
                color: #CBD5E0;
                font-size: 11px;
                font-weight: bold;
                font-family: 'Segoe UI', sans-serif;
            }}
            QLabel#gameModeIndicator {{
                color: #48BB78;
                font-size: 10px;
                font-weight: bold;
                padding-top: 2px;
            }}
            QLabel#prevLyric, QLabel#nextLyric {{
                color: rgba(210, 215, 225, 0.45);
                font-size: {max(10, f_orig - 4)}px;
                font-family: 'Segoe UI', sans-serif;
            }}
            QLabel#currentOrig {{
                color: {c_orig};
                font-size: {f_orig}px;
                font-weight: 700;
                font-family: 'Segoe UI', sans-serif;
                margin-top: 2px;
            }}
            QLabel#currentTrans {{
                color: {c_trans};
                font-size: {f_trans}px;
                font-weight: 600;
                font-family: 'Segoe UI', sans-serif;
                font-style: italic;
                margin-bottom: 2px;
            }}
            QPushButton {{
                background-color: rgba(255, 255, 255, 0.08);
                color: #E2E8F0;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                padding: 2px 7px;
                font-size: 10px;
                font-family: 'Segoe UI', sans-serif;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.20);
                color: #FFFFFF;
            }}
            QPushButton#btnLock {{
                background-color: rgba(49, 130, 206, 0.3);
                border: 1px solid rgba(99, 179, 237, 0.5);
                color: #BEE3F8;
                font-weight: bold;
            }}
            QPushButton#btnLock:hover {{
                background-color: rgba(49, 130, 206, 0.5);
            }}
            QPushButton#btnClose {{
                background-color: rgba(229, 62, 62, 0.2);
                border: 1px solid rgba(245, 101, 101, 0.4);
                color: #FEB2B2;
                font-weight: bold;
            }}
            QPushButton#btnClose:hover {{
                background-color: rgba(229, 62, 62, 0.5);
                color: #FFFFFF;
            }}
        """
        self.setStyleSheet(stylesheet)
        
        mode = self.cfg.get("display_mode", "3_lines")
        self.lbl_prev.setVisible(mode == "3_lines")
        self.lbl_next.setVisible(mode == "3_lines")
        self.btn_mode.setText("3L" if mode == "3_lines" else "1L")
        self.lbl_sync_info.setText(f"Sync: {self.sync_offset_ms:+d}ms")

    def _adjust_sync_offset(self, delta_ms: int):
        self.sync_offset_ms += delta_ms
        self.cfg["sync_offset_ms"] = self.sync_offset_ms
        config.save_config(self.cfg)
        self.lbl_sync_info.setText(f"Sync: {self.sync_offset_ms:+d}ms")

    def _reset_sync_offset(self):
        self.sync_offset_ms = 0
        self.cfg["sync_offset_ms"] = 0
        config.save_config(self.cfg)
        self.lbl_sync_info.setText("Sync: +0ms")

    def _toggle_display_mode(self):
        current = self.cfg.get("display_mode", "3_lines")
        new_mode = "1_line" if current == "3_lines" else "3_lines"
        self.cfg["display_mode"] = new_mode
        config.save_config(self.cfg)
        self._apply_styling()

    def _adjust_font_size(self, delta: int):
        self.cfg["font_size_original"] = max(12, min(32, self.cfg.get("font_size_original", 17) + delta))
        self.cfg["font_size_translation"] = max(10, min(28, self.cfg.get("font_size_translation", 14) + delta))
        config.save_config(self.cfg)
        self._apply_styling()

    def set_sync_state(self, base_pos: float, is_playing: bool, sync_timestamp: float):
        self.base_pos = base_pos
        self.is_playing = is_playing
        self.sync_timestamp = sync_timestamp

    def _on_render_tick(self):
        """Tick continuo a alta frecuencia (~33 FPS) para sincronizar suavemente."""
        if not self.lyrics_data:
            return

        if self.is_playing:
            elapsed = time.time() - self.sync_timestamp
            current_sec = self.base_pos + elapsed
        else:
            current_sec = self.base_pos

        # Aplicar compensación de sincronización
        effective_sec = current_sec + (self.sync_offset_ms / 1000.0)
        self.update_position(effective_sec)

    def toggle_click_through(self, state: Optional[bool] = None):
        """Alterna el modo fantasma (Click-Through) para no interferir con clicks en juegos."""
        if state is None:
            self.click_through = not self.click_through
        else:
            self.click_through = state

        user32 = ctypes.windll.user32
        hwnd = int(self.winId())
        ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)

        interactive_controls = [
            self.btn_lock, self.btn_mode, self.btn_font_dec, self.btn_font_inc,
            self.btn_close, self.btn_sync_minus, self.lbl_sync_info, self.btn_sync_plus
        ]

        if self.click_through:
            # Modo fantasma: clics del mouse traspasan directo a League of Legends
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style | WS_EX_TRANSPARENT | WS_EX_LAYERED)
            for c in interactive_controls:
                c.setVisible(False)
            self.lbl_game_mode_indicator.setVisible(True)
            self.container.setStyleSheet(f"QFrame#container {{ background-color: rgba(10, 12, 16, {int(self.cfg.get('opacity', 0.85) * 190)}); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 10px; }}")
        else:
            # Modo interactivo: se puede arrastrar y editar
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style & ~WS_EX_TRANSPARENT)
            for c in interactive_controls:
                c.setVisible(True)
            self.lbl_game_mode_indicator.setVisible(False)
            self._apply_styling()

    # Arrastre de ventana con el ratón
    def mousePressEvent(self, event):
        if not self.click_through and event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if not self.click_through and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        if not self.click_through:
            self.cfg["window_x"] = self.x()
            self.cfg["window_y"] = self.y()
            config.save_config(self.cfg)

    def set_track_info(self, title: str, artist: str):
        self.current_title = title
        self.current_artist = artist
        self.current_line_idx = -1
        if title:
            self.lbl_title.setText(f"🎵 {title}  —  {artist}")
            self.lbl_current_orig.setText("Buscando letra y traducción...")
            self.lbl_current_trans.setText("")
            self.lbl_prev.setText("")
            self.lbl_next.setText("")
        else:
            self.lbl_title.setText("🎵 Spotify en pausa o detenido")
            self.lbl_current_orig.setText("No hay reproducción activa")
            self.lbl_current_trans.setText("")
            self.lbl_prev.setText("")
            self.lbl_next.setText("")

    def set_lyrics(self, lyrics_with_translations: List[Dict[str, any]]):
        self.lyrics_data = lyrics_with_translations
        self.current_line_idx = -1
        if not self.lyrics_data:
            self.lbl_current_orig.setText("No se encontró letra sincronizada para esta canción")
            self.lbl_current_trans.setText("")
            self.lbl_prev.setText("")
            self.lbl_next.setText("")

    def update_position(self, current_seconds: float):
        if not self.lyrics_data:
            return

        # Encontrar el verso exacto para el segundo actual
        idx = -1
        for i, line in enumerate(self.lyrics_data):
            if current_seconds >= line["time"]:
                idx = i
            else:
                break

        if idx != self.current_line_idx:
            self.current_line_idx = idx
            self._render_lyrics(idx)

    def _render_lyrics(self, idx: int):
        if idx < 0:
            self.lbl_prev.setText("")
            self.lbl_current_orig.setText("♪ ♪ ♪ (Intro instrumental)")
            self.lbl_current_trans.setText("")
            if len(self.lyrics_data) > 0:
                self.lbl_next.setText(self.lyrics_data[0]["text"])
            else:
                self.lbl_next.setText("")
            return

        curr = self.lyrics_data[idx]
        orig_text = curr["text"]
        trans_text = curr.get("translation", "")

        if not orig_text.strip():
            self.lbl_current_orig.setText("♪ ♪ ♪")
            self.lbl_current_trans.setText("")
        else:
            self.lbl_current_orig.setText(orig_text)
            self.lbl_current_trans.setText(trans_text if trans_text and trans_text.lower() != orig_text.lower() else "")

        # Línea anterior
        if idx > 0:
            self.lbl_prev.setText(self.lyrics_data[idx - 1]["text"])
        else:
            self.lbl_prev.setText("")

        # Línea siguiente
        if idx + 1 < len(self.lyrics_data):
            self.lbl_next.setText(self.lyrics_data[idx + 1]["text"])
        else:
            self.lbl_next.setText("")
