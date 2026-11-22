# PDF a audio

Convierte el texto de un PDF en un archivo de audio MP3.

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r pdf-a-audio/requirements.txt
```

También hace falta **ffmpeg** para guardar en MP3 (Linux: `sudo apt install ffmpeg`).

## Uso

```bash
python pdf-a-audio/pdf_a_audio.py libro.pdf                          # voz neuronal natural (Kokoro), mujer
python pdf-a-audio/pdf_a_audio.py libro.pdf --voz em_alex            # voz neuronal, hombre
python pdf-a-audio/pdf_a_audio.py libro.pdf --velocidad 1.1          # un poco más rápido
python pdf-a-audio/pdf_a_audio.py libro.pdf --paginas 1-40 -o informe.mp3
python pdf-a-audio/pdf_a_audio.py libro.pdf --motor gtts             # voz de Google (requiere internet)
python pdf-a-audio/pdf_a_audio.py libro.pdf --motor offline          # espeak-ng: ligera pero robótica
```

## Motores de voz

| Motor | Calidad | Internet | Notas |
|---|---|---|---|
| `kokoro` (por defecto) | Natural | Solo la 1.ª vez | Descarga un modelo de ~350 MB en `pdf-a-audio/modelos/`. Voces: `ef_dora`, `em_alex`, `em_santa` |
| `gtts` | Buena | Siempre | Voz de Google Translate |
| `offline` | Robótica | Nunca | `espeak-ng` en Linux (`sudo apt install espeak-ng`); voces del sistema en Windows/macOS |

El script quita encabezados y pies de página repetidos, números de página y las cifras sueltas
de gráficos y tablas. Si el PDF es escaneado (imágenes, sin texto seleccionable) primero hay que
aplicarle OCR.
