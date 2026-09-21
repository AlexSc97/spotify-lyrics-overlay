import json
import os
from typing import List, Dict
from deep_translator import GoogleTranslator

CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "translations_cache.json")

class TranslatorService:
    def __init__(self):
        self.cache: Dict[str, List[str]] = self._load_cache()
        self.translator = GoogleTranslator(source="auto", target="es")

    def _load_cache(self) -> Dict[str, List[str]]:
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[TranslatorService] Error cargando caché: {e}")
        return {}

    def _save_cache(self):
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[TranslatorService] Error guardando caché: {e}")

    def translate_lines(self, track_id: str, original_lines: List[str]) -> List[str]:
        """
        Traduce una lista de líneas de letra al español.
        Usa caché si ya fue traducida previamente.
        """
        track_key = track_id.lower().strip()
        if track_key in self.cache and len(self.cache[track_key]) == len(original_lines):
            return self.cache[track_key]

        if not original_lines:
            return []

        translations = ["" for _ in original_lines]
        
        # Agrupar líneas no vacías para traducir por lotes eficientemente
        batch_indices = []
        batch_texts = []
        char_count = 0
        MAX_BATCH_CHARS = 2500

        batches = []
        current_batch_indices = []
        current_batch_texts = []

        for idx, line in enumerate(original_lines):
            text = line.strip()
            # Ignorar líneas instrumentales, vacías o notas musicales
            if not text or text in ["♪", "♫", "Instrumental", "[Instrumental]"]:
                translations[idx] = text
                continue

            line_len = len(text)
            if char_count + line_len > MAX_BATCH_CHARS and current_batch_texts:
                batches.append((current_batch_indices, current_batch_texts))
                current_batch_indices = []
                current_batch_texts = []
                char_count = 0

            current_batch_indices.append(idx)
            current_batch_texts.append(text)
            char_count += line_len + 1

        if current_batch_texts:
            batches.append((current_batch_indices, current_batch_texts))

        for batch_indices, batch_texts in batches:
            try:
                # Usar un delimitador seguro para mantener correspondencia de líneas exacta
                # Por ejemplo salto de línea doble o estándar
                combined_text = "\n".join(batch_texts)
                translated_combined = self.translator.translate(combined_text)
                translated_lines = translated_combined.splitlines()

                if len(translated_lines) == len(batch_texts):
                    for b_idx, trans_text in zip(batch_indices, translated_lines):
                        translations[b_idx] = trans_text.strip()
                else:
                    # Si el número de líneas traducidas difiere (a veces la API une líneas),
                    # traducir individualmente ese lote
                    for b_idx, orig_text in zip(batch_indices, batch_texts):
                        try:
                            translations[b_idx] = self.translator.translate(orig_text).strip()
                        except Exception:
                            translations[b_idx] = orig_text
            except Exception as e:
                print(f"[TranslatorService] Error en lote: {e}")
                for b_idx, orig_text in zip(batch_indices, batch_texts):
                    try:
                        translations[b_idx] = self.translator.translate(orig_text).strip()
                    except Exception:
                        translations[b_idx] = orig_text

        # Guardar en caché
        self.cache[track_key] = translations
        self._save_cache()
        return translations
