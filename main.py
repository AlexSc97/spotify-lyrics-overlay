import sys
import os

# Si se ejecuta con pythonw (sin consola), redirigir stdout y stderr para evitar cierres silenciosos
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

from typing import List, Dict

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QThread, pyqtSignal, pyqtSlot, QObject

from overlay_window import OverlayWindow
from spotify_monitor import SpotifyMonitor
from hotkey_manager import HotkeyListener
from lyrics_service import fetch_lyrics
from translator_service import TranslatorService

class LyricsFetchWorker(QThread):
    # 1. Letras listas de inmediato (no bloqueante)
    lyrics_ready = pyqtSignal(str, str, list)
    # 2. Traducciones listas en segundo plano
    translations_ready = pyqtSignal(str, str, list)

    def __init__(self, title: str, artist: str, duration: float, translator: TranslatorService):
        super().__init__()
        self.title = title
        self.artist = artist
        self.duration = duration
        self.translator = translator
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        track_key = f"{self.artist} - {self.title}"
        lyrics_result = fetch_lyrics(self.title, self.artist, self.duration)

        if self._is_cancelled:
            return

        if not lyrics_result or not lyrics_result.get("synced"):
            self.lyrics_ready.emit(self.title, self.artist, [])
            return

        raw_lines = lyrics_result.get("lines", [])
        original_texts = [line["text"] for line in raw_lines]

        # PASO 1: Emitir inmediatamente las letras originales para visualización instantánea (< 0.4s)
        initial_lines = [
            {"time": line["time"], "text": line["text"], "translation": ""}
            for line in raw_lines
        ]
        self.lyrics_ready.emit(self.title, self.artist, initial_lines)

        if self._is_cancelled:
            return

        # PASO 2: Traducir en segundo plano con transmisión progresiva lote a lote
        def on_batch(partial_translations: List[str]):
            if not self._is_cancelled:
                self.translations_ready.emit(self.title, self.artist, partial_translations)

        self.translator.translate_lines(
            track_key,
            original_texts,
            on_batch_done=on_batch,
            is_cancelled=lambda: self._is_cancelled
        )

class AppController(QObject):
    def __init__(self):
        super().__init__()
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        self.overlay = OverlayWindow()
        self.translator = TranslatorService()
        self.current_worker: LyricsFetchWorker = None

        # 1. Monitor de Spotify de alta precisión
        self.spotify_monitor = SpotifyMonitor()
        self.spotify_monitor.song_changed.connect(self.on_song_changed)
        self.spotify_monitor.sync_updated.connect(self.overlay.set_sync_state)
        self.spotify_monitor.session_active.connect(self.on_session_active)

        # 2. Listener de Atajos de Teclado (F8 / Ctrl+Alt+L)
        self.hotkey_listener = HotkeyListener()
        self.hotkey_listener.hotkey_triggered.connect(self.on_hotkey)

        # Iniciar hilos
        self.spotify_monitor.start()
        self.hotkey_listener.start()

        self.overlay.show()

    def on_hotkey(self):
        self.overlay.toggle_click_through()

    def on_session_active(self, active: bool):
        if not active and not self.spotify_monitor.current_title:
            self.overlay.set_track_info("", "")

    def on_song_changed(self, title: str, artist: str, duration: float):
        if not title:
            self.overlay.set_track_info("", "")
            return

        self.overlay.set_track_info(title, artist)

        # Cancelar worker anterior si aún procesaba
        if self.current_worker and self.current_worker.isRunning():
            self.current_worker.cancel()

        # Iniciar nuevo worker de letras no bloqueante
        self.current_worker = LyricsFetchWorker(title, artist, duration, self.translator)
        self.current_worker.lyrics_ready.connect(self.on_lyrics_loaded)
        self.current_worker.translations_ready.connect(self.on_translations_loaded)
        self.current_worker.start()

    def on_lyrics_loaded(self, title: str, artist: str, lyrics_list: List[Dict[str, any]]):
        if title == self.spotify_monitor.current_title and artist == self.spotify_monitor.current_artist:
            self.overlay.set_lyrics(lyrics_list)

    def on_translations_loaded(self, title: str, artist: str, translations_list: List[str]):
        if title == self.spotify_monitor.current_title and artist == self.spotify_monitor.current_artist:
            self.overlay.update_translations(translations_list)

    def run(self):
        exit_code = self.app.exec()
        self.spotify_monitor.stop()
        self.hotkey_listener.stop()
        if self.current_worker and self.current_worker.isRunning():
            self.current_worker.cancel()
            self.current_worker.wait()
        sys.exit(exit_code)

if __name__ == "__main__":
    controller = AppController()
    controller.run()
