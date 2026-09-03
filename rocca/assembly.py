"""Orchestrazione ffmpeg: normalizzazione dei segmenti e montaggio finale."""

import os
import shutil
import subprocess
import tempfile

from . import effects, sources

SILENZIO = ["-f", "lavfi", "-i",
            "anullsrc=channel_layout=stereo:sample_rate=44100"]


def _ff(args, timeout=600):
    return subprocess.run(["ffmpeg", "-y", "-loglevel", "error"] + args,
                          capture_output=True, text=True, timeout=timeout)


def durata_di(percorso):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", percorso],
        capture_output=True, text=True, timeout=30).stdout.strip()
    try:
        return float(out)
    except ValueError:
        return 0.0


def _magick():
    return "magick" if shutil.which("magick") else "convert"


class Montaggio:
    def __init__(self, cfg, preset, log=print):
        self.cfg = cfg
        self.p = preset
        self.log = log
        self.w, self.h = preset["formato"]
        self.fps = preset["fps"]
        self.tmp = tempfile.mkdtemp(prefix="rocca_")
        self.grad = cfg.gradazione(preset["colore"]["gradazione"])
        self.vign = float(preset["colore"].get("vignetta", 0.0))

    def pulisci(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ---------- segmenti ----------
    def _card(self, nome_file, indice):
        percorso = self.cfg.asset(nome_file)
        if not percorso:
            return None
        dur = self.p["card"]["durata"]
        out = os.path.join(self.tmp, f"{indice:03d}_card.mp4")
        r = _ff(["-loop", "1", "-t", str(dur), "-i", percorso] + SILENZIO
                + ["-t", str(dur),
                   "-vf", effects.catena_card(self.w, self.h, self.fps),
                   "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                   "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", out])
        return out if r.returncode == 0 else None

    def _sting(self):
        dur = self.p["transizione"].get("durata_luce", 0.45)
        out = os.path.join(self.tmp, "sting.mp4")
        filtro = effects.sting(self.w, self.h, self.fps, dur,
                               self.cfg.colore_rgb("salvia"),
                               self.cfg.colore_rgb("formenton"))
        r = _ff(["-f", "lavfi", "-i",
                 f"color=c=black:s={self.w}x{self.h}:d={dur}:r={self.fps}"]
                + SILENZIO + ["-t", str(dur), "-vf", filtro,
                              "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                              "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", out])
        return out if r.returncode == 0 else None

    def _foto(self, src, indice):
        dur = self.p["foto"]["durata"]
        dritta = os.path.join(self.tmp, f"src_{indice:03d}.png")
        r = subprocess.run([_magick(), src, "-auto-orient", dritta],
                           capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            return None

        out = os.path.join(self.tmp, f"{indice:03d}_seg.mp4")
        filtro = effects.catena_foto(self.w, self.h, self.fps, dur,
                                     self.p["foto"]["zoom"],
                                     self.p["foto"]["verso"], indice,
                                     self.grad, self.vign)
        r = _ff(["-loop", "1", "-t", str(dur), "-i", dritta] + SILENZIO
                + ["-t", str(dur), "-map", "0:v:0", "-map", "1:a:0",
                   "-vf", filtro,
                   "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                   "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", out])
        return out if r.returncode == 0 else None

    def _video(self, src, indice):
        dur = self.p["video"]["durata"]
        salta = self.p["video"]["salta_inizio"]
        out = os.path.join(self.tmp, f"{indice:03d}_seg.mp4")
        filtro = effects.catena_video(self.w, self.h, self.fps,
                                      self.grad, self.vign)
        r = _ff(["-ss", str(salta), "-t", str(dur), "-i", src] + SILENZIO
                + ["-t", str(dur), "-map", "0:v:0", "-map", "1:a:0",
                   "-vf", filtro,
                   "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                   "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", out])
        return out if r.returncode == 0 else None

    # ---------- montaggio ----------
    def costruisci(self, file_list, destinazione):
        segmenti, n_foto, n_video, saltati = [], 0, 0, []

        intro = self._card(self.p["card"].get("intro"), 0)
        if intro:
            segmenti.append(intro)

        for i, f in enumerate(file_list, start=1):
            if sources.e_foto(f):
                seg = self._foto(f, i)
                if seg:
                    n_foto += 1
                    self.log(f"  📷 {os.path.basename(f)}")
            else:
                seg = self._video(f, i)
                if seg:
                    n_video += 1
                    self.log(f"  🎬 {os.path.basename(f)}")
            if seg:
                segmenti.append(seg)
            else:
                saltati.append(os.path.basename(f))
                self.log(f"  ! salto {os.path.basename(f)}")

        if not segmenti:
            return None

        outro = self._card(self.p["card"].get("outro"), 999)
        if outro:
            segmenti.append(outro)

        finali = self._inserisci_transizioni(segmenti, bool(intro), bool(outro))
        muto = self._unisci(finali)
        if not muto:
            return None

        # indice all'inizio del file: senza, Android non lo riproduce
        os.makedirs(os.path.dirname(destinazione), exist_ok=True)
        r = _ff(["-i", muto, "-c", "copy", "-movflags", "+faststart", destinazione])
        if r.returncode != 0:
            return None

        return {"foto": n_foto, "video": n_video, "saltati": saltati,
                "segmenti": len(finali), "durata": durata_di(destinazione),
                "peso_mb": os.path.getsize(destinazione) / 1048576}

    def _inserisci_transizioni(self, segmenti, ha_intro, ha_outro):
        tipo = self.p["transizione"]["tipo"]
        if tipo not in ("rocca", "rocca-tutto") or len(segmenti) < 2:
            return segmenti

        s = self._sting()
        if not s:
            return segmenti

        n, out = len(segmenti), []
        for k, seg in enumerate(segmenti):
            out.append(seg)
            if k == n - 1:
                break
            if tipo == "rocca-tutto":
                out.append(s)
            elif (k == 0 and ha_intro) or (k == n - 2 and ha_outro):
                out.append(s)
        return out

    def _unisci(self, segmenti):
        muto = os.path.join(self.tmp, "muto.mp4")
        tipo = self.p["transizione"]["tipo"]

        if tipo == "taglio" or len(segmenti) < 2:
            lista = os.path.join(self.tmp, "lista.txt")
            with open(lista, "w", encoding="utf-8") as f:
                for s in segmenti:
                    f.write(f"file '{s}'\n")
            self.log(f"→ Concateno {len(segmenti)} segmenti...")
            r = _ff(["-f", "concat", "-safe", "0", "-i", lista, "-c", "copy", muto])
            return muto if r.returncode == 0 else None

        fusione = self.p["transizione"]["fusione"]
        xf = effects.TRANSIZIONI_XFADE.get(tipo, "fade")
        durate = [durata_di(s) for s in segmenti]
        filtro, _ = effects.catena_xfade(durate, fusione, xf)

        ingressi = []
        for s in segmenti:
            ingressi += ["-i", s]

        self.log(f"→ Monto {len(segmenti)} segmenti con transizione...")
        r = _ff(ingressi + SILENZIO + [
            "-filter_complex", filtro,
            "-map", "[vout]", "-map", f"{len(segmenti)}:a", "-shortest",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.0",
            "-c:a", "aac", muto])
        if r.returncode != 0:
            self.log(f"  ! ffmpeg: {r.stderr.strip()[:300]}")
            return None
        return muto
