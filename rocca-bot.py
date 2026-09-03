#!/usr/bin/env python3
"""
ROCCA BOT — La Rocca del Pavone

Ascolta Telegram e lancia il montaggio dei preset definiti in rocca.yaml.
Ogni preset diventa automaticamente un comando: /recap, /ritratto, /carosello…

Comandi fissi:
  /preset          elenca i preset disponibili
  /stato [preset]  cosa c'e' in attesa nelle cartelle
  /svuota <preset> pulisce la cartella di quel preset
  /aiuto           la lista
"""

import os
import re
import subprocess
import sys
import time

QUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, QUI)

from rocca import delivery, sources          # noqa: E402
from rocca.config import Config              # noqa: E402

MONTA = os.path.join(QUI, "monta.py")


class Bot:
    def __init__(self, cfg):
        self.cfg = cfg
        self.tg = delivery.Telegram(cfg.token, cfg.chat_id)
        self.offset = None

    def leggi(self):
        dati = {"timeout": 50}
        if self.offset is not None:
            dati["offset"] = self.offset
        r = self.tg._post("getUpdates", dati)
        if not r or not r.get("ok"):
            return []

        fuori = []
        for upd in r.get("result", []):
            self.offset = upd["update_id"] + 1
            msg = upd.get("message") or {}
            testo = (msg.get("text") or "").strip()
            mittente = str((msg.get("chat") or {}).get("id", ""))
            if mittente != self.tg.chat_id:
                print(f"  ! ignoro messaggio da {mittente}", file=sys.stderr)
                continue
            if testo:
                fuori.append(testo)
        return fuori


def elenco_file(cfg, preset):
    cartella = cfg.cartella_sorgente(preset)
    if not os.path.isdir(cartella):
        return None, None
    validi, fantasmi = [], []
    for n in os.listdir(cartella):
        if not os.path.isfile(os.path.join(cartella, n)):
            continue
        if not n.lower().endswith(sources.EST_TUTTE):
            continue
        (fantasmi if sources.e_fantasma(n) else validi).append(n)
    return sorted(validi), fantasmi


def cmd_monta(bot, nome, giorni):
    cfg = bot.cfg
    try:
        preset = cfg.preset(nome)
    except (KeyError, ValueError) as e:
        bot.tg.scrivi(f"✗ {e}")
        return

    validi, fantasmi = elenco_file(cfg, preset)
    if validi is None:
        bot.tg.scrivi(f"✗ Cartella mancante:\n<code>{cfg.cartella_sorgente(preset)}</code>")
        return
    if not validi:
        bot.tg.scrivi(f"📭 <b>{nome}</b>: la cartella è vuota.")
        return

    g = giorni or str(preset["giorni"])
    bot.tg.scrivi(f"🎬 Monto <b>{nome}</b> ({len(validi)} file, ultimi {g} giorni)…")

    try:
        p = subprocess.run([sys.executable, MONTA, nome, g],
                           capture_output=True, text=True, timeout=1800)
    except subprocess.TimeoutExpired:
        bot.tg.scrivi("✗ Più di 30 minuti. Qualcosa non va.")
        return
    except OSError as e:
        bot.tg.scrivi(f"✗ Non riesco a lanciare il montaggio:\n<code>{e}</code>")
        return

    # monta.py manda gia' lui il video: qui riporto solo i fallimenti
    if p.returncode != 0:
        coda = (p.stdout + p.stderr).strip()[-500:] or "nessun dettaglio"
        bot.tg.scrivi(f"✗ <b>{nome}</b> fallito:\n<code>{coda}</code>")


def cmd_stato(bot, nome=None):
    cfg = bot.cfg
    nomi = [nome] if nome else cfg.nomi_preset()
    righe = []
    for n in nomi:
        try:
            preset = cfg.preset(n)
        except (KeyError, ValueError):
            righe.append(f"✗ preset <b>{n}</b> inesistente")
            continue
        validi, fantasmi = elenco_file(cfg, preset)
        if validi is None:
            righe.append(f"<b>{n}</b> — cartella mancante")
            continue
        foto = sum(1 for f in validi if sources.e_foto(f))
        video = len(validi) - foto
        r = f"<b>{n}</b> — 📷 {foto} · 🎬 {video}"
        if fantasmi:
            r += f" · 👻 {len(fantasmi)}"
        righe.append(r)
        if nome and validi:
            righe += [f"   • {f}" for f in validi[:15]]
            if len(validi) > 15:
                righe.append(f"   … e altri {len(validi) - 15}")
    bot.tg.scrivi("📦 <b>In attesa</b>\n\n" + "\n".join(righe))


def cmd_svuota(bot, nome):
    cfg = bot.cfg
    if not nome:
        bot.tg.scrivi("Serve il preset: <code>/svuota recap</code>")
        return
    try:
        preset = cfg.preset(nome)
    except (KeyError, ValueError) as e:
        bot.tg.scrivi(f"✗ {e}")
        return

    cartella = cfg.cartella_sorgente(preset)
    validi, fantasmi = elenco_file(cfg, preset)
    if not validi and not fantasmi:
        bot.tg.scrivi("📭 Era già vuota.")
        return
    n = 0
    for f in (validi or []) + (fantasmi or []):
        try:
            os.remove(os.path.join(cartella, f))
            n += 1
        except OSError:
            pass
    bot.tg.scrivi(f"🧹 <b>{nome}</b>: {n} file rimossi.\n"
                  "⚠️ Se la cartella è sincronizzata in Send Only, "
                  "il telefono li rimetterà. Cancella dall'album.")


def cmd_preset(bot):
    cfg = bot.cfg
    righe = []
    for n in cfg.nomi_preset():
        p = cfg.preset(n)
        righe.append(f"/{n} — {p.get('descrizione', '')}")
        righe.append(f"   {p['formato'][0]}×{p['formato'][1]} · "
                     f"{p['giorni']}g · max {p['max_elementi']}")
    bot.tg.scrivi("🪶 <b>Preset</b>\n\n" + "\n".join(righe))


def aiuto(cfg):
    comandi = "\n".join(f"/{n}" for n in cfg.nomi_preset())
    return (f"🪶 <b>Rocca Bot</b>\n\n<b>Montaggi</b>\n{comandi}\n\n"
            "Con un numero attaccato o staccato cambi la finestra:\n"
            "<code>/recap30</code> · <code>/recap 30</code>\n\n"
            "<b>Altro</b>\n/preset — dettagli dei preset\n"
            "/stato [preset] — cosa c'è in attesa\n"
            "/svuota &lt;preset&gt; — pulisce la cartella\n/aiuto")


def main():
    cfg = Config()
    if not (cfg.token and cfg.chat_id):
        print("✗ token o chat_id vuoti in rocca.yaml", file=sys.stderr)
        sys.exit(2)

    bot = Bot(cfg)
    print(f"→ Bot avviato. Config: {cfg.percorso}")
    print(f"  preset: {', '.join(cfg.nomi_preset())}")

    bot.leggi()                      # scarta l'arretrato
    bot.tg.scrivi("🪶 Bot acceso. /aiuto per i comandi.")

    while True:
        try:
            for testo in bot.leggi():
                parti = testo.split()
                comando = parti[0].lower().split("@")[0]
                arg = parti[1] if len(parti) > 1 else None
                print(f"  ← {testo}")

                if comando in ("/aiuto", "/help", "/start"):
                    bot.tg.scrivi(aiuto(cfg))
                    continue
                if comando == "/preset":
                    cmd_preset(bot)
                    continue
                if comando in ("/stato", "/status"):
                    cmd_stato(bot, arg)
                    continue
                if comando == "/svuota":
                    cmd_svuota(bot, arg)
                    continue

                # /<preset> oppure /<preset><giorni>, es. /recap30
                m = re.match(r"^/([a-z_]+)(\d*)$", comando)
                if m and m.group(1) in cfg.nomi_preset():
                    giorni = m.group(2) or (arg if arg and arg.isdigit() else None)
                    cmd_monta(bot, m.group(1), giorni)
                elif comando.startswith("/"):
                    bot.tg.scrivi("Non conosco questo comando. /aiuto per la lista.")
        except KeyboardInterrupt:
            print("\n→ Chiudo.")
            break
        except Exception as e:                       # noqa: BLE001
            print(f"  ! errore: {e}", file=sys.stderr)
            time.sleep(5)


if __name__ == "__main__":
    main()
