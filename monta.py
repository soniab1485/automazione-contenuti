#!/usr/bin/env python3
"""
Sistema contenuti — La Rocca del Pavone

  ./monta.py                    elenca i preset disponibili
  ./monta.py recap              monta il recap settimanale
  ./monta.py recap 30           come sopra, ma su 30 giorni
  ./monta.py ritratto           monta un ritratto di razza
  ./monta.py recap --no-invio   monta senza mandare su Telegram
"""

import os
import shutil
import sys
from datetime import date

from rocca.assembly import Montaggio
from rocca.config import Config
from rocca import delivery, sources

DIPENDENZE = ["ffmpeg", "ffprobe"]


def controlla_dipendenze():
    mancanti = [c for c in DIPENDENZE if not shutil.which(c)]
    if not (shutil.which("magick") or shutil.which("convert")):
        mancanti.append("imagemagick")
    if mancanti:
        print("✗ Mancano questi programmi: " + " ".join(mancanti))
        print("  sudo apt install ffmpeg imagemagick")
        sys.exit(2)


def elenca(cfg):
    print("Preset disponibili:\n")
    for nome in cfg.nomi_preset():
        p = cfg.preset(nome)
        cartella = os.path.basename(cfg.cartella_sorgente(p))
        print(f"  {nome:<12} {p.get('descrizione', '')}")
        print(f"  {'':<12} sorgente: {cartella}/ · {p['formato'][0]}×{p['formato'][1]}"
              f" · {p['giorni']} giorni · max {p['max_elementi']}\n")
    print(f"Configurazione: {cfg.percorso}")


def main():
    controlla_dipendenze()
    argomenti = [a for a in sys.argv[1:] if not a.startswith("--")]
    opzioni = {a for a in sys.argv[1:] if a.startswith("--")}

    cfg = Config()

    if not argomenti:
        elenca(cfg)
        return 0

    nome = argomenti[0]
    try:
        preset = cfg.preset(nome)
    except (KeyError, ValueError) as e:
        print(f"✗ {e}")
        return 2

    if len(argomenti) > 1 and argomenti[1].isdigit():
        preset["giorni"] = int(argomenti[1])

    cartella = cfg.cartella_sorgente(preset)
    print(f"→ [{nome}] cerco in {cartella} — ultimi {preset['giorni']} giorni")

    file_list, fantasmi, esclusi = sources.raccogli(
        cartella, preset["giorni"], preset["max_elementi"],
        preset["data_da"], preset["selezione"])

    tg = delivery.Telegram(cfg.token, cfg.chat_id)

    if file_list is None:
        print(f"✗ La cartella non esiste: {cartella}")
        tg.scrivi(f"✗ Cartella mancante per <b>{nome}</b>:\n<code>{cartella}</code>")
        return 1

    if not file_list:
        print("✗ Nessun contenuto trovato.")
        if fantasmi:
            print(f"  👻 {len(fantasmi)} file fantasma ignorati")
        tg.scrivi(f"📭 <b>{nome}</b>: niente da montare in questa finestra.")
        return 1

    print(f"→ Trovati {len(file_list) + esclusi} elementi.")
    if fantasmi:
        print(f"  👻 Ignorati {len(fantasmi)} file nascosti o di conflitto:")
        for g in fantasmi:
            print(f"     {g}")
    if esclusi:
        print(f"  ⚠️  Limite {preset['max_elementi']}: ne lascio fuori {esclusi} "
              f"(tengo i più recenti).")

    file_list = sources.ordina(file_list, preset["ordine"])
    print(f"  ordine: {preset['ordine']} · selezione: {preset['selezione']}"
          f" · colore: {preset['colore']['gradazione']}")

    destinazione = os.path.join(
        cfg.dir_uscita, f"{nome}_{date.today().isoformat()}.mp4")

    m = Montaggio(cfg, preset)
    try:
        esito = m.costruisci(file_list, destinazione)
    finally:
        m.pulisci()

    if not esito:
        print("✗ Il montaggio è fallito.")
        tg.scrivi(f"✗ <b>{nome}</b>: montaggio fallito.")
        return 1

    print(f"\n✓ Fatto: {destinazione} ({esito['durata']:.1f}s, "
          f"{esito['peso_mb']:.1f} MB)")
    print(f"  {esito['foto']} foto · {esito['video']} video")
    print("  Guardalo prima di pubblicarlo. Sempre.")

    if "--no-invio" not in opzioni:
        testo = delivery.riepilogo(preset.get("descrizione", nome), esito,
                                   fantasmi, esclusi, destinazione)
        tg.video(destinazione, testo, preset["formato"][0],
                 preset["formato"][1], esito["durata"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
