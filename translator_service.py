import json
import os
import sys
import time
from typing import List, Dict, Callable, Optional
try:
    import translators as ts
except Exception:
    ts = None

def _get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

CACHE_FILE = os.path.join(_get_base_dir(), "translations_cache.json")

class TranslatorService:
    def __init__(self):
        self.cache: Dict[str, List[str]] = self._load_cache()

    def _load_cache(self) -> Dict[str, List[str]]:
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_cache(self):
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def translate_batch_with_fallback(self, text_list: List[str]) -> List[str]:
        """Traduce una lista de líneas utilizando múltiples motores de respaldo."""
        if not text_list:
            return []

        joined = "\n".join(text_list)
        # Motores ordenados por fiabilidad y sin límites de cuota diarios
        engines = ["bing", "sogou", "alibaba", "caiyun", "baidu"]

        for engine in engines:
            try:
                res = ts.translate_text(
                    joined,
                    from_language="auto",
                    to_language="es",
                    translator=engine,
                    timeout=5
                )
                if res:
                    lines = [l.strip() for l in res.splitlines()]
                    if len(lines) == len(text_list):
                        return lines
                    elif len(lines) > 0:
                        # Si devolvió líneas pero hubo saltos de línea combinados, ajustar longitud
                        adjusted = []
                        for i in range(len(text_list)):
                            if i < len(lines):
                                adjusted.append(lines[i])
                            else:
                                adjusted.append("")
                        return adjusted
            except Exception:
                continue

        # Si todos los motores en lote fallaron, intentar traducción línea por línea
        fallback_res = []
        for single in text_list:
            try:
                t = ts.translate_text(single, from_language="auto", to_language="es", translator="bing", timeout=3)
                fallback_res.append(t.strip() if t else "")
            except Exception:
                fallback_res.append("")
        return fallback_res

    def translate_lines(
        self,
        track_id: str,
        original_lines: List[str],
        on_batch_done: Optional[Callable[[List[str]], None]] = None,
        is_cancelled: Optional[Callable[[], bool]] = None
    ) -> List[str]:
        """
        Traduce líneas al español con actualización progresiva en tiempo real.
        """
        track_key = track_id.lower().strip()
        if track_key in self.cache and len(self.cache[track_key]) == len(original_lines):
            cached = self.cache[track_key]
            if on_batch_done:
                on_batch_done(cached)
            return cached

        if not original_lines:
            return []

        translations = ["" for _ in original_lines]

        # Agrupar en lotes pequeños (7-8 líneas) para máxima velocidad de respuesta
        batch_size = 8
        batches = []
        curr_indices = []
        curr_texts = []

        for idx, line in enumerate(original_lines):
            t = line.strip()
            if not t or t in ["♪", "♫", "Instrumental", "[Instrumental]"]:
                translations[idx] = t
                continue
            curr_indices.append(idx)
            curr_texts.append(t)
            if len(curr_texts) >= batch_size:
                batches.append((curr_indices, curr_texts))
                curr_indices = []
                curr_texts = []

        if curr_texts:
            batches.append((curr_indices, curr_texts))

        for batch_indices, batch_texts in batches:
            if is_cancelled and is_cancelled():
                return translations

            translated_batch = self.translate_batch_with_fallback(batch_texts)
            for b_idx, tr_text in zip(batch_indices, translated_batch):
                translations[b_idx] = tr_text

            # Enviar actualización inmediata a la interfaz para que el usuario no espere al final
            if on_batch_done:
                on_batch_done(list(translations))

            time.sleep(0.04)

        if any(translations):
            self.cache[track_key] = translations
            self._save_cache()

        return translations
