#!/usr/bin/env python3
"""Convierte el texto de un PDF en un archivo de audio.

Uso:
    python pdf_a_audio.py documento.pdf                 # -> documento.mp3 (gTTS, español)
    python pdf_a_audio.py documento.pdf -o salida.mp3
    python pdf_a_audio.py documento.pdf --motor offline # -> documento.wav (espeak-ng, sin internet)
    python pdf_a_audio.py documento.pdf --paginas 1-5 --idioma en
"""
import argparse
import re
import sys
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
    partes = []
    for i in rango_paginas(paginas, len(lector.pages)):
        partes.append(lector.pages[i].extract_text() or "")
    texto = "\n".join(partes)
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


def con_offline(texto, salida, idioma, velocidad):
    import pyttsx3
    motor = pyttsx3.init()
    for voz in motor.getProperty("voices"):
        idiomas = [str(l).lower().replace("_", "-") for l in (voz.languages or [])]
        nombre = f"{voz.id} {voz.name}".lower()
        if any(l == idioma or l.startswith(idioma + "-") for l in idiomas) or \
                (not idiomas and ("spanish" in nombre or "español" in nombre) and idioma == "es"):
            motor.setProperty("voice", voz.id)
            break
    motor.setProperty("rate", velocidad)
    motor.save_to_file(texto, str(salida))
    motor.runAndWait()


def main():
    p = argparse.ArgumentParser(description="Convierte un PDF de texto en audio.")
    p.add_argument("pdf", type=Path)
    p.add_argument("-o", "--salida", type=Path)
    p.add_argument("--motor", choices=["gtts", "offline"], default="gtts",
                   help="gtts: voz natural, requiere internet (mp3). offline: espeak-ng (wav).")
    p.add_argument("--idioma", default="es")
    p.add_argument("--paginas", help="Ej.: 3 o 1-10")
    p.add_argument("--velocidad", type=int, default=160, help="Palabras/min (solo offline)")
    a = p.parse_args()

    texto = extraer_texto(a.pdf, a.paginas)
    if not texto:
        sys.exit("No se encontró texto. ¿Es un PDF escaneado? Necesitaría OCR.")

    salida = a.salida or a.pdf.with_suffix(".mp3" if a.motor == "gtts" else ".wav")
    print(f"{len(texto)} caracteres extraídos. Generando audio con {a.motor}...")
    if a.motor == "gtts":
        con_gtts(texto, salida, a.idioma)
    else:
        con_offline(texto, salida, a.idioma, a.velocidad)
    print(f"Listo: {salida}")


if __name__ == "__main__":
    main()
