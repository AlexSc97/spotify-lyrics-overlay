# Spotify Lyrics Overlay para Gaming (LoL)

Overlay flotante transparente con letras sincronizadas de Spotify en tiempo real y traducción al español, diseñado específicamente para situarse sobre videojuegos (como League of Legends) sin interferir en los clics ni el rendimiento.

---

## 🚀 Características Principales

- **Sincronización Inmediata y de Alta Precisión**:
  - Lee directamente el reproductor de Windows (GSMTC) con compensación de latencia milimétrica.
  - La letra original en blanco aparece de inmediato (< 0.4s) y empieza a sincronizarse al compás exacto de la música.
- **Traducción al Español en Tiempo Real**:
  - Cada verso muestra su traducción al español justo debajo sin demoras ni bloqueos en la interfaz.
  - Almacenamiento en caché local (`translations_cache.json`) para consumo cero en canciones ya escuchadas.
- **Transparencia de Fondo Totalmente Configurable**:
  - Botón **`[🌓 %]`** en la barra superior: haz clic para alternar entre niveles de opacidad (`100%` -> `80%` -> `60%` -> `40%` -> `20%` -> `0% Solo Texto`).
  - También puedes usar la **rueda del ratón** sobre el botón de opacidad para un ajuste fino de ±5%.
  - En el modo `0% (Solo Texto)`, el fondo desaparece completamente, dejando únicamente las letras flotando con sombra de alto contraste sobre el juego.
- **Modo Juego / Fantasma (Click-Through para LoL)**:
  - Pulsa **`F8`** (o `Ctrl + Alt + L`) para activar el **Modo Juego**.
  - La ventana se vuelve completamente transparente a los clics (`WS_EX_TRANSPARENT`), permitiéndote mover el ratón y farmear/pelear en LoL a través de las letras sin hacer missclick.
  - Pulsa **`F8`** de nuevo para desbloquear y mover la ventana.
- **Ajustes Rápidos**:
  - `Sync: +/-0.1s`: Ajuste de compensación de latencia de audio.
  - `3L` / `1L`: Alternar entre 3 versos (anterior + actual + siguiente) o 1 solo verso estilo subtítulo de cine.
  - `A-` / `A+`: Tamaño de tipografía al vuelo.

---

## 🎮 Recomendación para League of Legends

Para que los overlays flotantes se muestren por encima de LoL:
1. Pulsa `Esc` dentro de una partida en LoL > ve a **Video**.
2. Configura el **Modo de Ventana** en **"Sin bordes" (Borderless)** o **"En ventana"**.

---

## 📦 Ejecución

Inicia la aplicación con un solo clic:
- Doble clic en `run_overlay.bat`
- O desde la terminal:
  ```powershell
  python main.py
  ```
