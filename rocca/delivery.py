"""Consegna su Telegram."""

import json
import os
import urllib.error
import urllib.parse
import urllib.request

API_BASE = os.environ.get("TG_API_BASE", "https://api.telegram.org")
LIMITE_UPLOAD = 50_000_000


class Telegram:
    def __init__(self, token, chat_id):
        self.token = token or ""
        self.chat_id = str(chat_id or "")
        self.attivo = bool(self.token and self.chat_id)
        self.api = f"{API_BASE}/bot{self.token}"

    def _post(self, metodo, dati=None, timeout=70):
        try:
            req = urllib.request.Request(
                f"{self.api}/{metodo}",
                data=urllib.parse.urlencode(dati or {}).encode())
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode())
        except (urllib.error.URLError, OSError, json.JSONDecodeError):
            return None

    def scrivi(self, testo):
        if not self.attivo:
            return False
        r = self._post("sendMessage", {"chat_id": self.chat_id, "text": testo,
                                       "parse_mode": "HTML"}, timeout=30)
        return bool(r and r.get("ok"))

    def video(self, percorso, didascalia, w, h, durata):
        """Manda il video. Se troppo grande o se fallisce, ripiega sul testo."""
        if not self.attivo:
            return False
        if os.path.isfile(percorso) and os.path.getsize(percorso) < LIMITE_UPLOAD:
            if self._multipart(percorso, didascalia, w, h, durata):
                return True
        return self.scrivi(didascalia)

    def _multipart(self, percorso, didascalia, w, h, durata):
        campi = {"chat_id": self.chat_id, "caption": didascalia,
                 "parse_mode": "HTML", "supports_streaming": "true",
                 "width": str(w), "height": str(h), "duration": str(int(durata))}
        confine = "----RoccaBoundary7d91f2"
        corpo = b""
        for k, v in campi.items():
            corpo += (f"--{confine}\r\nContent-Disposition: form-data; "
                      f'name="{k}"\r\n\r\n{v}\r\n').encode()
        with open(percorso, "rb") as f:
            dati = f.read()
        corpo += (f"--{confine}\r\nContent-Disposition: form-data; name=\"video\"; "
                  f'filename="{os.path.basename(percorso)}"\r\n'
                  f"Content-Type: video/mp4\r\n\r\n").encode()
        corpo += dati + f"\r\n--{confine}--\r\n".encode()

        try:
            req = urllib.request.Request(
                f"{self.api}/sendVideo", data=corpo,
                headers={"Content-Type": f"multipart/form-data; boundary={confine}"})
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.loads(r.read().decode()).get("ok", False)
        except (urllib.error.URLError, OSError, json.JSONDecodeError):
            return False


def riepilogo(nome_preset, esito, fantasmi, esclusi, percorso):
    m = [f"🪶 <b>{nome_preset}</b> pronto",
         f"📷 {esito['foto']} foto · 🎬 {esito['video']} video"]
    if esito["saltati"]:
        m[-1] += f" · ⚠️ {len(esito['saltati'])} illeggibili"
    if esclusi:
        m.append(f"⚠️ <b>{esclusi} file esclusi</b> dal limite (tenuti i più recenti)")
    if fantasmi:
        m.append(f"👻 <b>{len(fantasmi)} file fantasma ignorati</b> — svuota il cestino della galleria")
    m.append(f"{esito['durata']:.0f}s · {esito['peso_mb']:.1f} MB")
    m.append(f"\n<code>{percorso}</code>\nGuardalo prima di pubblicarlo.")
    return "\n".join(m)
