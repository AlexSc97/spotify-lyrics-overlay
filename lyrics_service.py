import re
import requests
from typing import List, Dict, Optional, Tuple

LRCLIB_BASE_URL = "https://lrclib.net/api"
USER_AGENT = "SpotifyLyricsOverlay/1.0 (Windows; Python)"

def clean_track_info(title: str, artist: str) -> Tuple[str, str]:
    """Limpia sufijos comunes como (Remastered...), (feat...), etc. para mejorar la búsqueda."""
    clean_title = re.sub(r"-\s*.*remaster.*", "", title, flags=re.IGNORECASE)
    clean_title = re.sub(r"\(.*?remaster.*?\)", "", clean_title, flags=re.IGNORECASE)
    clean_title = re.sub(r"\(feat\..*?\)", "", clean_title, flags=re.IGNORECASE)
    clean_title = re.sub(r"\[.*?\]", "", clean_title)
    clean_title = clean_title.strip()

    clean_artist = artist.split(",")[0].strip() if "," in artist else artist.strip()
    return clean_title, clean_artist

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
            # Normalizar milisegundos a decimal de segundo
            if len(millis_str) == 2:
                fraction = int(millis_str) / 100.0
            else:
                fraction = int(millis_str) / 1000.0
                
            total_seconds = minutes * 60 + seconds + fraction
            text = match.group(4).strip()
            lines.append({
                "time": total_seconds,
                "text": text
            })
            
    # Ordenar por tiempo
    lines.sort(key=lambda x: x["time"])
    return lines

def fetch_lyrics(title: str, artist: str, duration_sec: Optional[float] = None) -> Optional[Dict[str, any]]:
    """
    Busca letras sincronizadas en LRCLIB.
    Devuelve un diccionario con:
    {
        'synced': bool,
        'lines': [{'time': float, 'text': str}],
        'plain': str
    }
    """
    headers = {"User-Agent": USER_AGENT}
    
    # 1. Intento exacto
    params = {
        "track_name": title,
        "artist_name": artist
    }
    if duration_sec and duration_sec > 0:
        params["duration"] = int(duration_sec)
        
    try:
        resp = requests.get(f"{LRCLIB_BASE_URL}/get", params=params, headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            synced = data.get("syncedLyrics")
            plain = data.get("plainLyrics", "")
            if synced:
                parsed = parse_lrc_lines(synced)
                if parsed:
                    return {"synced": True, "lines": parsed, "plain": plain}
            elif plain:
                return {"synced": False, "lines": [], "plain": plain}
    except Exception as e:
        print(f"[LyricsService] Error en búsqueda exacta: {e}")

    # 2. Intento con nombres limpios o búsqueda libre
    clean_title, clean_artist = clean_track_info(title, artist)
    try:
        search_query = f"{clean_title} {clean_artist}"
        resp = requests.get(f"{LRCLIB_BASE_URL}/search", params={"q": search_query}, headers=headers, timeout=6)
        if resp.status_code == 200:
            results = resp.json()
            if results and isinstance(results, list):
                # Priorizar resultado con syncedLyrics
                for item in results:
                    synced = item.get("syncedLyrics")
                    if synced:
                        parsed = parse_lrc_lines(synced)
                        if parsed:
                            return {"synced": True, "lines": parsed, "plain": item.get("plainLyrics", "")}
                # Si ninguno tiene sincronizada, tomar la primera con plainLyrics
                for item in results:
                    plain = item.get("plainLyrics")
                    if plain:
                        return {"synced": False, "lines": [], "plain": plain}
    except Exception as e:
        print(f"[LyricsService] Error en búsqueda por texto: {e}")

    return None
