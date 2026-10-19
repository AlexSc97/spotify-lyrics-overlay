import asyncio
import time
from datetime import datetime, timezone
from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal
try:
    import winrt.windows.media.control as wmc
except ImportError:
    import winsdk.windows.media.control as wmc

class SpotifyMonitor(QThread):
    # Señales Qt
    song_changed = pyqtSignal(str, str, float)            # title, artist, duration_seconds
    sync_updated = pyqtSignal(float, bool, float)         # base_position, is_playing, sync_timestamp
    session_active = pyqtSignal(bool)                     # whether a media session exists

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = True
        self.current_title: str = ""
        self.current_artist: str = ""
        self.current_duration: float = 0.0
        self.is_playing: bool = False
        self.base_pos: float = 0.0
        self.sync_timestamp: float = time.time()

    def stop(self):
        self._running = False
        self.wait()

    def run(self):
        # Bucle de eventos asyncio para este hilo
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._monitor_loop())
        finally:
            loop.close()

    async def _find_spotify_session(self, manager):
        """Busca específicamente la sesión de Spotify o la sesión activa actual."""
        try:
            sessions = manager.get_sessions()
            for s in sessions:
                app_id = (s.source_app_user_model_id or "").lower()
                if "spotify" in app_id:
                    return s
            return manager.get_current_session()
        except Exception:
            return None

    async def _monitor_loop(self):
        manager = None
        while self._running:
            try:
                if manager is None:
                    manager = await wmc.GlobalSystemMediaTransportControlsSessionManager.request_async()

                session = await self._find_spotify_session(manager)

                if session is None:
                    self.session_active.emit(False)
                    await asyncio.sleep(1.0)
                    continue

                self.session_active.emit(True)

                # Obtener propiedades de la pista
                media_props = await session.try_get_media_properties_async()
                title = media_props.title or ""
                artist = media_props.artist or ""

                # Obtener info de reproducción (4 = Playing, 5 = Paused)
                playback_info = session.get_playback_info()
                status = playback_info.playback_status if playback_info else None
                is_playing_now = (status == 4)

                # Obtener línea de tiempo
                timeline = session.get_timeline_properties()
                duration = 0.0
                reported_pos = 0.0

                now_mono = time.time()
                now_utc = datetime.now(timezone.utc).timestamp()

                if timeline:
                    if timeline.end_time:
                        duration = timeline.end_time.total_seconds()
                    if timeline.position:
                        reported_pos = timeline.position.total_seconds()

                    # CORRECCIÓN DE LATENCIA DE WINDOWS GSMTC:
                    # Windows actualiza 'timeline.last_updated_time' periódicamente (a veces con 1-2s de retraso).
                    # Sumamos el tiempo transcurrido desde esa captura si la canción está reproduciéndose.
                    if timeline.last_updated_time:
                        up_utc = timeline.last_updated_time.timestamp()
                        delta_since_gsm_update = max(0.0, now_utc - up_utc)
                        if is_playing_now and delta_since_gsm_update < 30.0:
                            reported_pos += delta_since_gsm_update

                self.is_playing = is_playing_now
                self.base_pos = reported_pos
                self.sync_timestamp = now_mono

                # Detectar cambio de pista
                if title != self.current_title or artist != self.current_artist:
                    self.current_title = title
                    self.current_artist = artist
                    self.current_duration = duration
                    self.song_changed.emit(title, artist, duration)

                # Emitir estado de sincronización de alta precisión
                self.sync_updated.emit(self.base_pos, self.is_playing, self.sync_timestamp)

            except Exception:
                manager = None
                await asyncio.sleep(1.0)
                continue

            # Sondeo cada 250ms para capturar pausas, seeks y cambios rápidamente
            await asyncio.sleep(0.25)
