# PDF a audio

Convierte el texto de un PDF en un archivo de audio (MP3 o WAV).

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r pdf-a-audio/requirements.txt
```

Solo para el motor offline en Linux también hace falta: `sudo apt install espeak-ng`
(en Windows y macOS se usan las voces que ya trae el sistema).

## Uso

```bash
python pdf-a-audio/pdf_a_audio.py libro.pdf                     # libro.mp3, voz de Google (requiere internet)
python pdf-a-audio/pdf_a_audio.py libro.pdf --motor offline     # libro.wav, sin internet
python pdf-a-audio/pdf_a_audio.py libro.pdf --paginas 1-10 -o capitulo1.mp3
python pdf-a-audio/pdf_a_audio.py libro.pdf --idioma en
```

| Librería | Para qué |
|---|---|
| `pypdf` | Extraer el texto del PDF |
| `gTTS` | Voz natural de Google Translate (MP3, necesita internet) |
| `pyttsx3` | Voz del sistema, sin internet (WAV) |

Si el PDF es escaneado (imágenes, sin texto seleccionable) primero hay que aplicarle OCR.
