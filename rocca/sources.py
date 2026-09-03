"""Raccolta dei file sorgente, date di scatto e ordinamento."""

import os
import random
import re
import shutil
import subprocess
import time
from datetime import datetime

EST_FOTO = (".jpg", ".jpeg", ".png", ".heic")
EST_VIDEO = (".mp4", ".mov", ".m4v")
EST_TUTTE = EST_FOTO + EST_VIDEO


def e_foto(percorso):
    return percorso.lower().endswith(EST_FOTO)


def _identify():
    """ImageMagick 7 usa 'magick identify', la 6 usa 'identify'."""
    if shutil.which("magick"):
        return ["magick", "identify"]
    if shutil.which("identify"):
        return ["identify"]
    return None


def e_fantasma(nome):
    """File nascosti, cestinati Android, copie di conflitto Syncthing."""
    b = os.path.basename(nome).lower()
    return (b.startswith(".")
            or "sync-conflict" in b
            or ".trashed" in b
            or b.startswith("trashed-"))


def data_scatto(percorso):
    """Epoch del momento di scatto. Ripiega sulla data del file."""
    if e_foto(percorso):
        ident = _identify()
        if ident:
            for tag in ("%[EXIF:DateTimeOriginal]", "%[EXIF:DateTime]"):
                try:
                    out = subprocess.run(ident + ["-format", tag, percorso],
                                         capture_output=True, text=True,
                                         timeout=15).stdout.strip()
                except (OSError, subprocess.SubprocessError):
                    break
                if out:
                    # "2026:08:26 07:31:12"
                    m = re.match(r"(\d{4}):(\d{2}):(\d{2})[ T](\d{2}):(\d{2}):(\d{2})", out)
                    if m:
                        try:
                            dt = datetime(*(int(x) for x in m.groups()))
                            return dt.timestamp()
                        except ValueError:
                            pass
    else:
        try:
            out = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries",
                 "format_tags=creation_time", "-of", "default=nw=1:nk=1", percorso],
                capture_output=True, text=True, timeout=15).stdout.strip().split("\n")[0]
        except (OSError, subprocess.SubprocessError):
            out = ""
        if out:
            try:
                return datetime.fromisoformat(out.replace("Z", "+00:00")).timestamp()
            except ValueError:
                pass
    return os.path.getmtime(percorso)


def raccogli(cartella, giorni, max_elementi, data_da="scatto",
             selezione="recenti"):
    """Restituisce (file_scelti, fantasmi, quanti_esclusi_dal_limite).

    selezione:
      "recenti"    tiene gli ultimi N (buono per il recap settimanale)
      "distribuita" prende N file spalmati su tutta la finestra temporale
                    (buono per raccontare un'evoluzione)
    """
    if not os.path.isdir(cartella):
        return None, [], 0

    limite = time.time() - giorni * 86400
    buoni, fantasmi = [], []

    for nome in os.listdir(cartella):
        p = os.path.join(cartella, nome)
        if not os.path.isfile(p):
            continue
        if not nome.lower().endswith(EST_TUTTE):
            continue
        if e_fantasma(nome):
            fantasmi.append(nome)
            continue
        if os.path.getmtime(p) < limite:
            continue
        buoni.append(p)

    chiave = data_scatto if data_da == "scatto" else os.path.getmtime
    buoni.sort(key=chiave)

    esclusi = 0
    if len(buoni) > max_elementi:
        esclusi = len(buoni) - max_elementi
        if selezione == "distribuita" and max_elementi > 1:
            n = len(buoni)
            indici = sorted({round(k * (n - 1) / (max_elementi - 1))
                             for k in range(max_elementi)})
            buoni = [buoni[i] for i in indici]
        else:
            buoni = buoni[-max_elementi:]      # tiene i piu' recenti

    return buoni, fantasmi, esclusi


def ordina(file_list, modo):
    """cronologico | alternato | casuale. La lista arriva gia' cronologica."""
    if modo == "casuale":
        out = list(file_list)
        random.shuffle(out)
        return out

    if modo != "alternato":
        return list(file_list)

    foto = [f for f in file_list if e_foto(f)]
    video = [f for f in file_list if not e_foto(f)]
    if not foto or not video:
        return list(file_list)

    tot = len(foto) + len(video)
    # posizioni dei video, distribuite a intervalli regolari
    posizioni = {int((k + 0.5) * tot / len(video)) for k in range(len(video))}

    out, iv, if_ = [], 0, 0
    for j in range(tot):
        if j in posizioni and iv < len(video):
            out.append(video[iv]); iv += 1
        elif if_ < len(foto):
            out.append(foto[if_]); if_ += 1
        elif iv < len(video):
            out.append(video[iv]); iv += 1
    return out
