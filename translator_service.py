import json
import os
import time
from typing import List, Dict
from deep_translator import MyMemoryTranslator, GoogleTranslator

CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "translations_cache.json")

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

    def translate_lines(self, track_id: str, original_lines: List[str]) -> List[str]:
        """
        Traduce líneas al español en segundo plano de manera segura y sin bloqueos.
        """
        track_key = track_id.lower().strip()
        if track_key in self.cache and len(self.cache[track_key]) == len(original_lines):
            return self.cache[track_key]

        if not original_lines:
            return []

        translations = ["" for _ in original_lines]

        # Agrupar en pequeños bloques de 6 a 8 líneas para no saturar APIs
        batch_size = 7
        batches = []
        current_indices = []
        current_texts = []

        for idx, line in enumerate(original_lines):
            text = line.strip()
            if not text or text in ["♪", "♫", "Instrumental", "[Instrumental]"]:
                translations[idx] = text
                continue

            current_indices.append(idx)
            current_texts.append(text)

            if len(current_texts) >= batch_size:
                batches.append((current_indices, current_texts))
                current_indices = []
                current_texts = []

        if current_texts:
            batches.append((current_indices, current_texts))

        # Intentar con MyMemory primero (más tolerante con bloques multilínea)
        for batch_indices, batch_texts in batches:
            joined = "\n".join(batch_texts)
            translated_lines = None

            # Intento 1: MyMemory
            try:
                res = MyMemoryTranslator(source="auto", target="es-ES").translate(joined)
                lines = res.splitlines() if res else []
                if len(lines) == len(batch_texts):
                    translated_lines = [l.strip() for l in lines]
            except Exception:
                pass

            # Intento 2: GoogleTranslator si MyMemory no cuadró el conteo
            if not translated_lines:
                try:
                    res = GoogleTranslator(source="auto", target="es").translate(joined)
                    lines = res.splitlines() if res else []
                    if len(lines) == len(batch_texts):
                        translated_lines = [l.strip() for l in lines]
                except Exception:
                    pass

            # Asignar resultados
            if translated_lines:
                for b_idx, trans in zip(batch_indices, translated_lines):
                    translations[b_idx] = trans
            else:
                # Si falló la traducción del bloque, dejar el texto original sin bloquear
                for b_idx, orig in zip(batch_indices, batch_texts):
                    translations[b_idx] = ""

            # Breve pausa de cortesía para no saturar límites de red
            time.sleep(0.08)

        # Guardar en caché solo si se obtuvo al menos alguna traducción
        if any(translations):
            self.cache[track_key] = translations
            self._save_cache()

        return translations
