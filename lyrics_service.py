import re
import requests
from typing import List, Dict, Optional, Tuple

LRCLIB_BASE_URL = "https://lrclib.net/api"
USER_AGENT = "SpotifyLyricsOverlay/2.0 (Windows; Python)"

def clean_track_info(title: str, artist: str) -> Tuple[str, str]:
    """Limpia sufijos comunes como (Remastered...), (feat...), etc. para maximizar aciertos."""
    t = title
    # Quitar sufijos después de guiones como - Remastered, - Explicit, - Live, - Edit, etc.
    t = re.sub(r'-\s*.*?(remaster|explicit|clean|live|deluxe|bonus|anniversary|version|edit|mono|stereo|soundtrack|feat|with|remix).*', '', t, flags=re.I)
    # Quitar paréntesis con anotaciones adicionales
    t = re.sub(r'\(.*?(feat\.|ft\.|with|remaster|version|deluxe|live|explicit|remix|bonus).*?\)', '', t, flags=re.I)
    # Quitar corchetes
    t = re.sub(r'\[.*?\]', '', t)
    # Quitar guión final suelto
    t = re.sub(r'-\s*$', '', t).strip()

    # Artista principal (si vienen varios separados por comas)
    a = artist.split(",")[0].strip() if "," in artist else artist.strip()
    a = re.sub(r'\(.*?\)', '', a).strip()
    return t, a

def parse_lrc_lines(lrc_text: str) -> List[Dict[str, any]]:
    """Parsea el formato LRC de marcas de tiempo [mm:ss.xx] o [mm:ss.xxx] a segundos."""
    lines = []
    pattern = re.compile(r"\[(\d{2}):(\d{2})\.(\d{2,3})\](.*)")
    
    for raw_line in lrc_text.splitlines():
        match = pattern.match(raw_line.strip())
        if match:
            minutes = int(match.group(1))
            seconds = int(match.group(2))
            millis_str = match.group(3)
            fraction = int(millis_str) / (100.0 if len(millis_str) == 2 else 1000.0)
            total_seconds = minutes * 60 + seconds + fraction
            text = match.group(4).strip()
            lines.append({
                "time": total_seconds,
                "text": text
            })
            
    lines.sort(key=lambda x: x["time"])
    return lines

def _pick_best_result(results: List[Dict], target_duration: Optional[float]) -> Optional[Dict]:
    """Elige el mejor resultado priorizando los que tienen syncedLyrics y duración más cercana."""
    if not results:
        return None

    synced_items = [r for r in results if r.get("syncedLyrics")]
    if synced_items:
        if target_duration and target_duration > 0:
            # Ordenar por cercanía a la duración reportada por Spotify
            synced_items.sort(key=lambda x: abs((x.get("duration") or 0) - target_duration))
        return synced_items[0]

    # Respaldo: si no hay sincronizada, tomar con plainLyrics
    plain_items = [r for r in results if r.get("plainLyrics")]
    if plain_items:
        if target_duration and target_duration > 0:
            plain_items.sort(key=lambda x: abs((x.get("duration") or 0) - target_duration))
        return plain_items[0]

    return None

def fetch_lyrics(title: str, artist: str, duration_sec: Optional[float] = None) -> Optional[Dict[str, any]]:
    """
    Busca letras sincronizadas en LRCLIB con estrategia multinivel.
    Devuelve diccionario con:
    {
        'synced': bool,
        'lines': [{'time': float, 'text': str}],
        'plain': str
    }
    """
    headers = {"User-Agent": USER_AGENT}
    clean_title, clean_artist = clean_track_info(title, artist)

    # Paso 1: Intento directo exacto con los datos de Spotify
    try:
        params = {"track_name": title, "artist_name": artist}
        if duration_sec and duration_sec > 0:
            params["duration"] = int(duration_sec)
        resp = requests.get(f"{LRCLIB_BASE_URL}/get", params=params, headers=headers, timeout=3.5)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("syncedLyrics"):
                parsed = parse_lrc_lines(data["syncedLyrics"])
                if parsed:
                    return {"synced": True, "lines": parsed, "plain": data.get("plainLyrics", "")}
    except Exception:
        pass

    # Paso 2: Intento con datos limpios
    if clean_title != title or clean_artist != artist:
        try:
            params = {"track_name": clean_title, "artist_name": clean_artist}
            if duration_sec and duration_sec > 0:
                params["duration"] = int(duration_sec)
            resp = requests.get(f"{LRCLIB_BASE_URL}/get", params=params, headers=headers, timeout=3.5)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("syncedLyrics"):
                    parsed = parse_lrc_lines(data["syncedLyrics"])
                    if parsed:
                        return {"synced": True, "lines": parsed, "plain": data.get("plainLyrics", "")}
        except Exception:
            pass

    # Paso 3: Búsqueda avanzada por parámetros track_name y artist_name en LRCLIB
    try:
        search_params = {"track_name": clean_title, "artist_name": clean_artist}
        resp = requests.get(f"{LRCLIB_BASE_URL}/search", params=search_params, headers=headers, timeout=4)
        if resp.status_code == 200:
            best = _pick_best_result(resp.json(), duration_sec)
            if best:
                if best.get("syncedLyrics"):
                    parsed = parse_lrc_lines(best["syncedLyrics"])
                    if parsed:
                        return {"synced": True, "lines": parsed, "plain": best.get("plainLyrics", "")}
                elif best.get("plainLyrics"):
                    return {"synced": False, "lines": [], "plain": best["plainLyrics"]}
    except Exception:
        pass

    # Paso 4: Búsqueda libre general por query "q"
    try:
        search_query = f"{clean_title} {clean_artist}"
        resp = requests.get(f"{LRCLIB_BASE_URL}/search", params={"q": search_query}, headers=headers, timeout=4)
        if resp.status_code == 200:
            best = _pick_best_result(resp.json(), duration_sec)
            if best:
                if best.get("syncedLyrics"):
                    parsed = parse_lrc_lines(best["syncedLyrics"])
                    if parsed:
                        return {"synced": True, "lines": parsed, "plain": best.get("plainLyrics", "")}
                elif best.get("plainLyrics"):
                    return {"synced": False, "lines": [], "plain": best["plainLyrics"]}
    except Exception:
        pass

    return None
