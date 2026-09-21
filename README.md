# Spotify Lyrics Overlay para Gaming (LoL)

Overlay flotante transparente con letras sincronizadas de Spotify y traducción al español en tiempo real, diseñado para situarse sobre videojuegos (como League of Legends) sin interferir en los clics ni la jugabilidad.

---

## 🚀 Características

- **Sincronización Automática con Spotify**:
  - Lee directamente el reproductor de Windows (GSMTC).
  - No requiere cuentas de desarrollador de Spotify ni iniciar sesión con tokens.
- **Letras Sincronizadas (LRCLIB)**:
  - Resalta verso a verso al ritmo exacto de la música.
- **Traducción al Español Instantánea**:
  - Cada línea muestra el texto original arriba y la traducción al español justo debajo.
  - Caché local automática para que las canciones ya traducidas no consuman internet.
- **Modo Juego / Fantasma (Click-Through)**:
  - Al activar el modo juego, la ventana se vuelve **transparente a los clics del ratón** (`WS_EX_TRANSPARENT`).
  - Puedes seguir clickeando en el LoL, moviendo a tu campeón o peleando sin interactuar accidentalmente con las letras.
- **Atajos Globales**:
  - **`F8`** o **`Ctrl + Alt + L`**: Alterna entre el **Modo Juego** (bloqueado/clics traspasan) y el **Modo Edición** (desbloqueado para mover la ventana o cambiar tamaño de letra).
- **Ajustes Rápidos en Pantalla**:
  - `A-` / `A+`: Ajustar tamaño de fuente al vuelo.
  - `3L` / `1L`: Alternar entre visualización de 3 líneas (previa + actual + siguiente) o 1 sola línea tipo subtítulo.
  - Arrastre libre con el ratón cuando está desbloqueado.

---

## 🎮 Recomendación para League of Legends

Para que cualquier overlay de Windows (como este visor de letras, Discord o Porofessor) se muestre encima de League of Legends:
1. Abre los **Ajustes de Video de LoL** (tecla Esc dentro de partida).
2. Asegúrate de que el **Modo de Ventana** esté configurado en:
   - **"Sin bordes" (Borderless)** o **"En ventana" (Windowed)**.
   *(El modo "Pantalla completa exclusiva" de DirectX bloquea las ventanas flotantes de Windows).*

---

## 📦 Ejecución

Puedes iniciar la aplicación ejecutando:
- Doble clic en `run_overlay.bat`
- O desde la terminal:
  ```powershell
  cd "C:\Users\Asjer\.gemini\antigravity\scratch\spotify-lyrics-overlay"
  python main.py
  ```
