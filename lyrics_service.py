import sys
import json
import os
import re
import requests
from typing import List, Dict, Optional, Tuple

LRCLIB_BASE_URL = "https://lrclib.net/api"
NETEASE_SEARCH_URL = "https://music.163.com/api/search/get"
NETEASE_LYRIC_URL = "https://music.163.com/api/song/lyric"

USER_AGENT = "SpotifyLyricsOverlay/2.0 (Windows; Python)"
NETEASE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://music.163.com",
}

def _get_base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


CACHE_FILE = os.path.join(_get_base_dir(), "lyrics_cache.json")

# Patrones de metadatos/créditos frecuentes al inicio de letras de NetEase o LRC
METADATA_LINE_RE = re.compile(
    r"^\s*(作词|作曲|编曲|制作人|混音|母带|录音|吉他|贝斯|鼓|弦乐|和声|出品|发行|统筹|监制|词|曲|编|唱|原唱|翻唱|lyricist|composer|arranger|producer|mixed by|mastered by)\s*[:：]",
    re.IGNORECASE,
)


def _load_lyrics_cache() -> Dict[str, List[Dict[str, any]]]:
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
    return {}


def _save_lyrics_cache(cache: Dict[str, List[Dict[str, any]]]):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


_LYRICS_CACHE: Dict[str, List[Dict[str, any]]] = _load_lyrics_cache()


def clean_track_info(title: str, artist: str) -> Tuple[str, str]:
    """Limpia sufijos comunes como (Remastered...), (feat...), etc. para maximizar aciertos."""
    t = title
    # Quitar sufijos después de guiones como - Remastered, - Explicit, - Live, - Edit, etc.
    t = re.sub(
        r"-\s*.*?(remaster|explicit|clean|live|deluxe|bonus|anniversary|version|edit|mono|stereo|soundtrack|feat|with|remix).*",
        "",
        t,
        flags=re.I,
    )
    # Quitar paréntesis con anotaciones adicionales
    t = re.sub(
        r"\(.*?(feat\.|ft\.|with|remaster|version|deluxe|live|explicit|remix|bonus).*?\)",
        "",
        t,
        flags=re.I,
    )
    # Quitar corchetes
    t = re.sub(r"\[.*?\]", "", t)
    # Quitar guión final suelto
    t = re.sub(r"-\s*$", "", t).strip()

    # Artista principal (si vienen varios separados por comas o barras)
    a = re.split(r"[,/;&]", artist)[0].strip() if artist else ""
    a = re.sub(r"\(.*?\)", "", a).strip()
    return t or title.strip(), a or artist.strip()


def parse_lrc_lines(lrc_text: str) -> List[Dict[str, any]]:
    """Parsea formatos LRC ([mm:ss.xx], [mm:ss.xxx], [mm:ss:xx], [mm:ss]) y filtra metadatos."""
    lines = []
    timestamp_pattern = re.compile(r"\[(\d{1,3}):(\d{2})(?:[.:](\d{1,3}))?\]")

    for raw_line in lrc_text.splitlines():
        raw_line = raw_line.strip()
        if not raw_line:
            continue

        matches = list(timestamp_pattern.finditer(raw_line))
        if not matches:
            continue

        # El texto de la línea es lo que sigue a la última marca de tiempo
        text = raw_line[matches[-1].end():].strip()

        # Ignorar líneas de créditos/metadatos típicos de NetEase
        if METADATA_LINE_RE.match(text):
            continue

        for match in matches:
            minutes = int(match.group(1))
            seconds = int(match.group(2))
            millis_str = match.group(3)
            if millis_str:
                divisor = 10.0 ** len(millis_str)
                fraction = int(millis_str) / divisor
            else:
                fraction = 0.0

            total_seconds = round(minutes * 60 + seconds + fraction, 3)
            lines.append({
                "time": total_seconds,
                "text": text,
            })

    lines.sort(key=lambda x: x["time"])
    return lines


def _pick_best_lrclib_result(results: List[Dict], target_duration: Optional[float]) -> Optional[Dict]:
    """Elige el mejor resultado de LRCLIB priorizando los que tienen syncedLyrics y duración más cercana."""
    if not results or not isinstance(results, list):
        return None

    synced_items = [r for r in results if r.get("syncedLyrics")]
    if synced_items:
        if target_duration and target_duration > 0:
            synced_items.sort(key=lambda x: abs((x.get("duration") or 0) - target_duration))
        return synced_items[0]

    plain_items = [r for r in results if r.get("plainLyrics")]
    if plain_items:
        if target_duration and target_duration > 0:
            plain_items.sort(key=lambda x: abs((x.get("duration") or 0) - target_duration))
        return plain_items[0]

    return None


def _fetch_from_lrclib(
    title: str, artist: str, clean_title: str, clean_artist: str, duration_sec: Optional[float]
) -> Optional[Dict[str, any]]:
    """Intenta obtener letras desde LRCLIB, abortando rápido si el servidor devuelve 5xx o timeout."""
    headers = {"User-Agent": USER_AGENT}

    # Paso 1: Intento directo con los datos de Spotify
    try:
        params = {"track_name": title, "artist_name": artist}
        if duration_sec and duration_sec > 0:
            params["duration"] = int(duration_sec)
        resp = requests.get(f"{LRCLIB_BASE_URL}/get", params=params, headers=headers, timeout=2.5)
        if resp.status_code >= 500:
            return None  # Servidor LRCLIB caído (502/503/504), pasar directo al respaldo
        if resp.status_code == 200:
            data = resp.json()
            if data.get("syncedLyrics"):
                parsed = parse_lrc_lines(data["syncedLyrics"])
                if parsed:
                    return {"synced": True, "lines": parsed, "plain": data.get("plainLyrics", "")}
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
        return None
    except Exception:
        pass

    # Paso 2: Intento con datos limpios
    if clean_title != title or clean_artist != artist:
        try:
            params = {"track_name": clean_title, "artist_name": clean_artist}
            if duration_sec and duration_sec > 0:
                params["duration"] = int(duration_sec)
            resp = requests.get(f"{LRCLIB_BASE_URL}/get", params=params, headers=headers, timeout=2.5)
            if resp.status_code >= 500:
                return None
            if resp.status_code == 200:
                data = resp.json()
                if data.get("syncedLyrics"):
                    parsed = parse_lrc_lines(data["syncedLyrics"])
                    if parsed:
                        return {"synced": True, "lines": parsed, "plain": data.get("plainLyrics", "")}
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            return None
        except Exception:
            pass

    # Paso 3: Búsqueda general por query en LRCLIB
    try:
        search_query = f"{clean_title} {clean_artist}".strip()
        resp = requests.get(f"{LRCLIB_BASE_URL}/search", params={"q": search_query}, headers=headers, timeout=3.0)
        if resp.status_code >= 500:
            return None
        if resp.status_code == 200:
            best = _pick_best_lrclib_result(resp.json(), duration_sec)
            if best and best.get("syncedLyrics"):
                parsed = parse_lrc_lines(best["syncedLyrics"])
                if parsed:
                    return {"synced": True, "lines": parsed, "plain": best.get("plainLyrics", "")}
    except Exception:
        pass

    return None


def _score_netease_song(
    song: Dict, clean_title: str, clean_artist: str, duration_sec: Optional[float]
) -> float:
    """Puntúa qué tan bien coincide un resultado de NetEase con la pista de Spotify (mayor es mejor)."""
    score = 0.0
    s_name = (song.get("name") or "").lower().strip()
    t_low = clean_title.lower().strip()

    if s_name == t_low:
        score += 50.0
    elif t_low in s_name or s_name in t_low:
        score += 25.0

    s_artists = [a.get("name", "").lower().strip() for a in song.get("artists", []) if a.get("name")]
    a_low = clean_artist.lower().strip()
    if a_low:
        if any(a_low == sa for sa in s_artists):
            score += 40.0
        elif any(a_low in sa or sa in a_low for sa in s_artists):
            score += 20.0

    if duration_sec and duration_sec > 0 and song.get("duration"):
        song_dur = float(song["duration"]) / 1000.0
        diff = abs(song_dur - duration_sec)
        if diff <= 2.0:
            score += 30.0
        elif diff <= 5.0:
            score += 15.0
        elif diff <= 12.0:
            score += 5.0
        else:
            score -= min(30.0, diff)

    return score


def _fetch_from_netease(
    title: str, artist: str, clean_title: str, clean_artist: str, duration_sec: Optional[float]
) -> Optional[Dict[str, any]]:
    """Busca y descarga letras sincronizadas desde NetEase Cloud Music API."""
    queries = [f"{clean_title} {clean_artist}".strip()]
    raw_query = f"{title} {artist}".strip()
    if raw_query.lower() != queries[0].lower():
        queries.append(raw_query)

    for q in queries:
        try:
            resp = requests.post(
                NETEASE_SEARCH_URL,
                data={"s": q, "type": 1, "limit": 8, "offset": 0},
                headers=NETEASE_HEADERS,
                timeout=4.0,
            )
            if resp.status_code != 200:
                continue

            songs = resp.json().get("result", {}).get("songs", [])
            if not songs:
                continue

            # Ordenar candidatos por puntuación de coincidencia (título, artista y duración)
            ranked = sorted(
                songs,
                key=lambda s: _score_netease_song(s, clean_title, clean_artist, duration_sec),
                reverse=True,
            )

            # Probar los mejores candidatos hasta encontrar uno con letra sincronizada válida
            for candidate in ranked[:4]:
                song_id = candidate.get("id")
                if not song_id:
                    continue

                lyric_resp = requests.get(
                    NETEASE_LYRIC_URL,
                    params={"os": "pc", "id": song_id, "lv": -1, "kv": -1, "tv": -1},
                    headers=NETEASE_HEADERS,
                    timeout=3.5,
                )
                if lyric_resp.status_code != 200:
                    continue

                lyric_data = lyric_resp.json()
                lrc_text = (lyric_data.get("lrc") or {}).get("lyric") or ""
                if not lrc_text:
                    continue

                parsed = parse_lrc_lines(lrc_text)
                if len(parsed) >= 3:
                    return {"synced": True, "lines": parsed, "plain": lrc_text}
        except Exception:
            continue

    return None


def fetch_lyrics(title: str, artist: str, duration_sec: Optional[float] = None) -> Optional[Dict[str, any]]:
    """
    Busca letras sincronizadas con caché local y respaldo automático:
    1. Caché local en disco (lyrics_cache.json) -> Instantáneo (0ms)
    2. LRCLIB API (con detección rápida de servidor caído)
    3. NetEase Cloud Music API (Proveedor 2 de respaldo de alta disponibilidad)
    """
    if not title:
        return None

    cache_key = f"{artist.strip().lower()} - {title.strip().lower()}"
    if cache_key in _LYRICS_CACHE and _LYRICS_CACHE[cache_key]:
        return {"synced": True, "lines": _LYRICS_CACHE[cache_key], "plain": ""}

    clean_title, clean_artist = clean_track_info(title, artist)
    clean_cache_key = f"{clean_artist.lower()} - {clean_title.lower()}"
    if clean_cache_key in _LYRICS_CACHE and _LYRICS_CACHE[clean_cache_key]:
        return {"synced": True, "lines": _LYRICS_CACHE[clean_cache_key], "plain": ""}

    # Proveedor 1: LRCLIB
    res = _fetch_from_lrclib(title, artist, clean_title, clean_artist, duration_sec)

    # Proveedor 2: NetEase Cloud Music (si LRCLIB falló o no encontró letra sincronizada)
    if not res or not res.get("synced"):
        res = _fetch_from_netease(title, artist, clean_title, clean_artist, duration_sec)

    # Guardar en caché local si se obtuvo letra sincronizada
    if res and res.get("synced") and res.get("lines"):
        _LYRICS_CACHE[cache_key] = res["lines"]
        _LYRICS_CACHE[clean_cache_key] = res["lines"]
        _save_lyrics_cache(_LYRICS_CACHE)

    return res
