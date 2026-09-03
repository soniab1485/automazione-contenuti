"""Caricamento e risoluzione della configurazione."""

import copy
import os
import sys

import yaml

NOME_FILE = "rocca.yaml"


def _fondi(base, sopra):
    """Unisce due dizionari in profondita': 'sopra' vince."""
    out = copy.deepcopy(base)
    for k, v in sopra.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _fondi(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def trova_config(percorso=None):
    """Cerca rocca.yaml accanto al progetto, poi in ~/Rocca."""
    candidati = []
    if percorso:
        candidati.append(percorso)
    qui = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidati.append(os.path.join(qui, NOME_FILE))
    candidati.append(os.path.expanduser(f"~/Rocca/{NOME_FILE}"))

    for c in candidati:
        if c and os.path.isfile(c):
            return c
    return None


class Config:
    def __init__(self, percorso=None):
        self.percorso = trova_config(percorso)
        if not self.percorso:
            print(f"✗ Non trovo {NOME_FILE}.", file=sys.stderr)
            sys.exit(2)
        with open(self.percorso, "r", encoding="utf-8") as f:
            self.dati = yaml.safe_load(f) or {}

        base = self.dati.get("generale", {}).get("base", "~/Rocca")
        self.base = os.path.expanduser(base)
        self.dir_uscita = os.path.join(
            self.base, self.dati.get("generale", {}).get("uscita", "montati"))
        self.dir_assets = os.path.join(
            self.base, self.dati.get("generale", {}).get("assets", "assets"))

    # ---------- telegram ----------
    @property
    def token(self):
        return (self.dati.get("telegram") or {}).get("token", "") or ""

    @property
    def chat_id(self):
        return str((self.dati.get("telegram") or {}).get("chat_id", "") or "")

    # ---------- preset ----------
    def nomi_preset(self):
        return list((self.dati.get("preset") or {}).keys())

    def preset(self, nome):
        tutti = self.dati.get("preset") or {}
        if nome not in tutti:
            disponibili = ", ".join(tutti.keys()) or "nessuno"
            raise KeyError(f"preset '{nome}' inesistente. Disponibili: {disponibili}")

        p = copy.deepcopy(tutti[nome])
        # eredita da un altro preset, in catena
        visti = {nome}
        while "eredita" in p:
            padre = p.pop("eredita")
            if padre in visti:
                raise ValueError(f"eredita circolare su '{padre}'")
            visti.add(padre)
            if padre not in tutti:
                raise KeyError(f"preset padre '{padre}' inesistente")
            p = _fondi(copy.deepcopy(tutti[padre]), p)

        p["_nome"] = nome
        p.setdefault("fps", 30)
        p.setdefault("formato", [1080, 1920])
        p.setdefault("ordine", "cronologico")
        p.setdefault("data_da", "scatto")
        p.setdefault("max_elementi", 20)
        p.setdefault("giorni", 7)
        p.setdefault("selezione", "recenti")
        p.setdefault("foto", {})
        p["foto"].setdefault("durata", 1.8)
        p["foto"].setdefault("zoom", 0.0033)
        p["foto"].setdefault("verso", "alterna")
        p.setdefault("video", {})
        p["video"].setdefault("durata", 2.5)
        p["video"].setdefault("salta_inizio", 0.5)
        p.setdefault("card", {})
        p["card"].setdefault("durata", 1.8)
        p.setdefault("transizione", {})
        p["transizione"].setdefault("tipo", "taglio")
        p["transizione"].setdefault("durata_luce", 0.45)
        p["transizione"].setdefault("fusione", 0.18)
        p.setdefault("colore", {})
        p["colore"].setdefault("gradazione", "nessuno")
        p["colore"].setdefault("vignetta", 0.0)
        return p

    def cartella_sorgente(self, preset):
        return os.path.join(self.base, preset.get("sorgente", "clip"))

    def gradazione(self, nome):
        g = (self.dati.get("gradazioni") or {}).get(nome, "")
        # il YAML puo' spezzare su piu' righe: ricompatto
        return " ".join(g.split()).replace(", ", ",") if g else ""

    def colore_rgb(self, nome):
        """Da '#4A5D23' a (74, 93, 35)."""
        h = (self.dati.get("palette") or {}).get(nome, "#000000").lstrip("#")
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

    def asset(self, nome):
        if not nome:
            return None
        p = os.path.join(self.dir_assets, nome)
        return p if os.path.isfile(p) else None
