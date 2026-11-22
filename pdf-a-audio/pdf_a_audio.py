#!/usr/bin/env python3
"""Convierte el texto de un PDF en un archivo de audio.

Uso:
    python pdf_a_audio.py documento.pdf                 # -> documento.mp3 (voz neuronal Kokoro)
    python pdf_a_audio.py documento.pdf --voz em_alex   # voz masculina
    python pdf_a_audio.py documento.pdf --motor gtts    # voz de Google (requiere internet)
    python pdf_a_audio.py documento.pdf --motor offline # espeak-ng, ligera pero robótica
    python pdf_a_audio.py documento.pdf --paginas 1-5 --idioma en
"""
import argparse
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from collections import Counter
from pathlib import Path

from pypdf import PdfReader


def rango_paginas(texto, total):
    if not texto:
        return range(total)
    inicio, _, fin = texto.partition("-")
    inicio = max(int(inicio), 1)
    fin = min(int(fin) if fin else inicio, total)
    return range(inicio - 1, fin)


def extraer_texto(ruta_pdf, paginas=None):
    lector = PdfReader(ruta_pdf)
    total = len(lector.pages)
    todas = [(p.extract_text() or "").split("\n") for p in lector.pages]

    def norm(linea):
        return re.sub(r"\s+", " ", linea).strip()

    # Encabezados/pies que se repiten en muchas páginas (títulos corridos, etc.)
    # Se agrupan por los primeros 40 caracteres para atrapar variantes como
    # "Título del libro   Capítulo 1", "Título del libro   Capítulo 2"...
    def clave(linea):
        return norm(linea)[:40]

    frecuencia = Counter(c for lineas in todas
                         for c in {clave(x) for x in lineas if 15 < len(norm(x)) < 120})
    umbral = max(3, total // 5)
    repetidas = {c for c, n in frecuencia.items() if n >= umbral}

    def sirve(linea):
        l = norm(linea)
        if not l or (len(l) < 120 and clave(l) in repetidas):
            return False
        # números sueltos (páginas) y líneas de gráficos/tablas: casi todo números
        tokens = l.split()
        numericos = sum(bool(re.fullmatch(r"[\d.,%()+\-–]+", t)) for t in tokens)
        return numericos / len(tokens) <= 0.6

    partes = []
    for i in rango_paginas(paginas, total):
        lineas = [l for l in todas[i] if sirve(l)]
        partes.append("\n".join(lineas))
    texto = unicodedata.normalize("NFKC", "\n".join(partes))  # ligaduras ﬁ, ﬂ...
    texto = re.sub(r"(?<=\w)�(?=\w)", "ti", texto)       # ligadura "ti" mal codificada
    texto = re.sub(r"-\n(\w)", r"\1", texto)        # une palabras cortadas con guion
    texto = re.sub(r"(?<!\n)\n(?!\n)", " ", texto)  # saltos de línea dentro de un párrafo
    texto = re.sub(r"[ \t]+", " ", texto)
    return texto.strip()


def con_gtts(texto, salida, idioma):
    from gtts import gTTS, gTTSError
    try:
        gTTS(text=texto, lang=idioma).save(str(salida))
    except gTTSError as e:
        Path(salida).unlink(missing_ok=True)
        sys.exit(f"gTTS falló ({e}). ¿Hay conexión a internet? Prueba con --motor offline.")


def wav_con_espeak(texto, wav, idioma, velocidad):
    """Linux: espeak-ng directo (más fiable que pyttsx3 con textos largos)."""
    with tempfile.NamedTemporaryFile("w", suffix=".txt", encoding="utf-8", delete=False) as f:
        f.write(texto)
    try:
        subprocess.run(["espeak-ng", "-v", idioma, "-s", str(velocidad),
                        "-w", str(wav), "-f", f.name], check=True)
    finally:
        Path(f.name).unlink(missing_ok=True)


def wav_con_pyttsx3(texto, wav, idioma, velocidad):
    """Windows/macOS: voces del sistema."""
    import pyttsx3
    motor = pyttsx3.init()
    for voz in motor.getProperty("voices"):
        idiomas = [str(l).lower().replace("_", "-") for l in (voz.languages or [])]
        nombre = f"{voz.id} {voz.name}".lower()
        if any(l == idioma or l.startswith(idioma + "-") for l in idiomas) or \
                (not idiomas and idioma.startswith("es") and ("spanish" in nombre or "español" in nombre)):
            motor.setProperty("voice", voz.id)
            break
    motor.setProperty("rate", velocidad)
    motor.save_to_file(texto, str(wav))
    motor.runAndWait()


MODELOS = Path(__file__).parent / "modelos"
URL_KOKORO = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"


def a_mp3(wav, salida):
    if not shutil.which("ffmpeg"):
        sys.exit("Para guardar MP3 hace falta ffmpeg (o usa -o archivo.wav).")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav),
                    "-b:a", "64k", str(salida)], check=True)


def fragmentos(texto, maximo=400):
    """Divide en trozos de hasta `maximo` caracteres respetando las oraciones."""
    actual = ""
    for oracion in re.split(r"(?<=[.!?:;])\s+", texto):
        if actual and len(actual) + len(oracion) > maximo:
            yield actual
            actual = ""
        actual = f"{actual} {oracion}".strip()
    if actual:
        yield actual


def con_kokoro(texto, salida, voz, velocidad):
    """Voz neuronal, natural y sin internet (tras descargar el modelo, ~350 MB)."""
    import urllib.request
    import numpy as np
    import soundfile as sf
    from kokoro_onnx import Kokoro

    MODELOS.mkdir(exist_ok=True)
    for nombre in ("kokoro-v1.0.onnx", "voices-v1.0.bin"):
        if not (MODELOS / nombre).exists():
            print(f"Descargando {nombre} (solo la primera vez)...")
            urllib.request.urlretrieve(URL_KOKORO + nombre, MODELOS / nombre)
    k = Kokoro(str(MODELOS / "kokoro-v1.0.onnx"), str(MODELOS / "voices-v1.0.bin"))

    trozos = list(fragmentos(texto))
    pausa = None
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(salida) if Path(salida).suffix.lower() == ".wav" else Path(tmp) / "audio.wav"
        archivo = None
        for i, trozo in enumerate(trozos, 1):
            audio, sr = k.create(trozo, voice=voz, speed=velocidad, lang="es")
            if archivo is None:
                archivo = sf.SoundFile(str(wav), "w", samplerate=sr, channels=1)
                pausa = np.zeros(int(sr * 0.25), dtype=audio.dtype)
            archivo.write(audio)
            archivo.write(pausa)
            print(f"\r  {i}/{len(trozos)} fragmentos", end="", flush=True)
        print()
        archivo.close()
        if wav != Path(salida):
            a_mp3(wav, salida)


def con_offline(texto, salida, idioma, velocidad):
    generar = wav_con_espeak if shutil.which("espeak-ng") else wav_con_pyttsx3
    if Path(salida).suffix.lower() != ".mp3":
        generar(texto, salida, idioma, velocidad)
        return
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "audio.wav"
        generar(texto, wav, idioma, velocidad)
        if not wav.exists():
            sys.exit("El motor de voz no generó audio.")
        a_mp3(wav, salida)


def main():
    p = argparse.ArgumentParser(description="Convierte un PDF de texto en audio.")
    p.add_argument("pdf", type=Path)
    p.add_argument("-o", "--salida", type=Path)
    p.add_argument("--motor", choices=["kokoro", "gtts", "offline"], default="kokoro",
                   help="kokoro: voz neuronal natural, sin internet (descarga el modelo la 1.a vez). "
                        "gtts: voz de Google, requiere internet. offline: espeak-ng, robótica pero ligera.")
    p.add_argument("--voz", default="ef_dora",
                   help="Solo kokoro: ef_dora (mujer), em_alex (hombre), em_santa (hombre)")
    p.add_argument("--idioma", default="es", help="gtts/offline (ej.: es, es-419, en)")
    p.add_argument("--paginas", help="Ej.: 3 o 1-10")
    p.add_argument("--velocidad", type=float,
                   help="kokoro: factor (1.0 normal, 1.1 más rápido). offline: palabras/min (160)")
    a = p.parse_args()

    texto = extraer_texto(a.pdf, a.paginas)
    if not texto:
        sys.exit("No se encontró texto. ¿Es un PDF escaneado? Necesitaría OCR.")

    salida = a.salida or a.pdf.with_suffix(".mp3")
    print(f"{len(texto)} caracteres extraídos. Generando audio con {a.motor}...")
    if a.motor == "kokoro":
        con_kokoro(texto, salida, a.voz, a.velocidad or 1.0)
    elif a.motor == "gtts":
        con_gtts(texto, salida, a.idioma)
    else:
        con_offline(texto, salida, a.idioma, int(a.velocidad or 160))
    print(f"Listo: {salida}")


if __name__ == "__main__":
    main()
