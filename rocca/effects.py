"""Costruzione delle catene di filtri ffmpeg."""


def riquadra(w, h, fps):
    """Porta qualsiasi sorgente al formato di uscita, riempiendo il quadro."""
    return (f"scale={w}:{h}:force_original_aspect_ratio=increase,"
            f"crop={w}:{h},fps={fps}")


def ken_burns(w, h, fps, durata, escursione, verso, indice):
    """Movimento lento sulle foto.

    'escursione' e' lo zoom totale sull'intera durata (non per fotogramma):
    cambiando la durata il movimento resta uguale.
    """
    if verso == "fermo" or escursione <= 0:
        return riquadra(w, h, fps)

    frame = max(1, int(round(durata * fps)))
    passo = escursione * fps      # incremento per fotogramma
    massimo = 1.0 + escursione * durata

    if verso == "alterna":
        verso = "dentro" if indice % 2 == 0 else "fuori"

    if verso == "fuori":
        z = f"max({massimo:.4f}-{passo / fps:.6f}*on,1.0)"
    else:
        z = f"min(1.0+{passo / fps:.6f}*on,{massimo:.4f})"

    # pre-ingrandimento 2x: elimina lo scatto a gradini di zoompan
    return (f"scale={w * 2}:{h * 2}:force_original_aspect_ratio=increase,"
            f"crop={w * 2}:{h * 2},"
            f"zoompan=z='{z}':d={frame}:"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={fps}")


def colore(gradazione="", vignetta=0.0):
    """Gradazione cromatica e vignettatura, entrambe opzionali."""
    parti = []
    if gradazione:
        parti.append(gradazione)
    if vignetta and vignetta > 0:
        # 0 = niente, 1 = molto marcata
        angolo = 1.5708 - min(max(vignetta, 0.0), 1.0) * 0.9
        parti.append(f"vignette=angle={angolo:.4f}")
    return ",".join(parti)


def catena_foto(w, h, fps, durata, escursione, verso, indice, grad="", vign=0.0):
    parti = [ken_burns(w, h, fps, durata, escursione, verso, indice)]
    c = colore(grad, vign)
    if c:
        parti.append(c)
    parti.append("format=yuv420p")
    return ",".join(parti)


def catena_video(w, h, fps, grad="", vign=0.0):
    parti = [riquadra(w, h, fps)]
    c = colore(grad, vign)
    if c:
        parti.append(c)
    parti.append("format=yuv420p")
    return ",".join(parti)


def catena_card(w, h, fps):
    """Le card NON vengono gradate: sono gia' nei colori giusti."""
    return f"{riquadra(w, h, fps)},format=yuv420p"


def sting(w, h, fps, durata, rgb_fondo, rgb_luce):
    """La spazzata di luce brandizzata, come espressione geq."""
    fr, fg, fb = rgb_fondo
    lr, lg, lb = rgb_luce
    d = "(X/W+0.35*(1-Y/H))/1.35"
    cond = f"lt(abs({d}-T/{durata}),0.10)"
    return (f"geq="
            f"r='if({cond},{lr},{fr})':"
            f"g='if({cond},{lg},{fg})':"
            f"b='if({cond},{lb},{fb})',format=yuv420p")


TRANSIZIONI_XFADE = {
    "dissolvenza": "fade",
    "rocca": "fade",
    "rocca-tutto": "fade",
}


def catena_xfade(durate, fusione, tipo="fade"):
    """Catena di dissolvenze fra N segmenti, in un solo passaggio.

    Restituisce (stringa_filtro, durata_totale).
    """
    n = len(durate)
    if n < 2:
        return "", durate[0] if durate else 0.0

    pezzi, prec = [], "[0:v]"
    cum = durate[0]
    for k in range(1, n):
        off = cum - fusione
        uscita = "[vout]" if k == n - 1 else f"[v{k}]"
        pezzi.append(f"{prec}[{k}:v]xfade=transition={tipo}:"
                     f"duration={fusione}:offset={off:.3f}{uscita}")
        prec = uscita
        cum = cum + durate[k] - fusione
    return ";".join(pezzi), cum
