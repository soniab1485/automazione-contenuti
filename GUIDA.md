# Sistema contenuti — La Rocca del Pavone

Versione 2 · testato su Ubuntu 24.04

---

## In due righe

Metti i contenuti nella cartella giusta sul telefono. Arrivano sul PC da soli.
Scrivi al bot il nome di quello che vuoi montare. Ti torna il video pronto.

---

## Installazione

Scompatta l'archivio e lancia lo script:

```bash
cd ~/Downloads
tar xzf rocca-v2.tar.gz
cd rocca
bash installa.sh
```

Lo script crea le cartelle, copia i file, **recupera il token dal vecchio
`recap-settimanale.sh`** e accende il servizio. Si può rilanciare quante volte
vuoi: se `rocca.yaml` esiste già non lo sovrascrive, mette il nuovo accanto
come `rocca.yaml.nuovo`.

Se mancano dei programmi te lo dice e si ferma:

```bash
sudo apt install ffmpeg imagemagick python3-yaml
```

**Dopo l'installazione servono due cose:**

1. `intro.png` e `outro.png` (1080×1920) in `~/Rocca/assets/`
2. Token e chat id in `~/Rocca/rocca.yaml`, se non sono stati recuperati

Prova che tutto giri:

```bash
python3 ~/Rocca/monta.py                      # elenca i preset
python3 ~/Rocca/monta.py recap 3650 --no-invio  # monta senza inviare
```

---

## I cinque preset

| Comando | Cosa racconta | Cartella | Formato |
|---|---|---|---|
| `/recap` | La settimana | `clip/` | 9:16 |
| `/mensile` | Il mese | `clip/` | 9:16 |
| `/trimestrale` | **L'evoluzione su 90 giorni** | `clip/` | 9:16 |
| `/ritratto` | Una razza, lento e contemplativo | `ritratto/` | 9:16 |
| `/carosello` | Post informativo | `carosello/` | 4:5 |

I primi tre pescano dalla stessa cartella: cambia solo la finestra temporale
e il modo di scegliere.

### Perché il trimestrale è diverso

Sugli altri, quando ci sono più file del limite, il sistema **tiene i più
recenti**. Su 90 giorni sarebbe sbagliato: ti monterebbe solo l'ultimo mese e
il "prima" — che è tutto il punto — sparirebbe.

Il trimestrale usa `selezione: "distribuita"`: campiona lungo tutto il
periodo, primo e ultimo compresi. Con 60 file su 90 giorni e un tetto di 20,
prende uno ogni cinque giorni circa.

Ed è **cronologico**, non alternato: su un video di evoluzione la sequenza
temporale *è* il contenuto.

---

## La procedura

1. **Domenica 12:30** — notifica dal calendario
2. Dalla galleria, sposta i contenuti nell'album giusto:
   - `RoccaRecap` → diario quotidiano
   - `RoccaRitratto` → materiale per un ritratto di razza
   - `RoccaCarosello` → immagini per un post informativo
3. Aspetta che Syncthing li porti sul PC
4. Su Telegram scrivi il comando: `/recap`, `/ritratto`, `/carosello`…
5. Ti arriva il video montato
6. Lo salvi nella galleria
7. Lo carichi su Instagram → **scegli l'audio dalla libreria interna** → pubblichi
8. **Svuota l'album dal telefono**

> **Il passo 7 non è negoziabile.** La musica va aggiunta dentro Instagram o
> TikTok, mai incorporata nel file. Le licenze delle piattaforme coprono solo
> le tracce della loro libreria: un mp3 importato viene riconosciuto dal
> content ID e il reel può essere silenziato o limitato nella distribuzione.
> In più, l'audio scelto dalla libreria è un canale di scoperta: chi tocca il
> nome della traccia trova il tuo video.

### La pulizia si fa dal telefono

La cartella Syncthing è **Send Only**: il telefono comanda. Se cancelli dal PC,
Syncthing rimette tutto. È la garanzia che nessuna cancellazione sul PC possa
toccarti la galleria.

**E svuota anche il cestino della galleria** (*Foto → Raccolta → Cestino*).
Android non cancella subito: rinomina in `.trashed-…` e tiene 30 giorni.

---

## I comandi del bot

| Comando | Cosa fa |
|---|---|
| `/recap` | Monta con la finestra predefinita del preset |
| `/recap30` · `/recap 30` | Cambia la finestra a 30 giorni |
| `/preset` | Dettagli di tutti i preset |
| `/stato` | Cosa c'è in attesa in tutte le cartelle |
| `/stato recap` | Elenco dei file di quella cartella |
| `/svuota recap` | Pulisce quella cartella sul PC |
| `/aiuto` | La lista |

Ogni preset definito in `rocca.yaml` diventa **automaticamente** un comando.
Ne aggiungi uno nel file, `/nomepreset` esiste. Non serve toccare codice.

Il bot risponde solo a te. Funziona ovunque, anche a PC bloccato.

Per il menu di Telegram: **@BotFather** → `/setcommands` →

```
recap - La settimana
mensile - Il mese
trimestrale - L'evoluzione su 90 giorni
ritratto - Ritratto di razza
carosello - Post informativo 4:5
stato - Cosa c'è in attesa
preset - Dettagli dei preset
aiuto - Lista comandi
```

---

## Da terminale

```bash
python3 ~/Rocca/monta.py                  # elenca i preset
python3 ~/Rocca/monta.py recap            # monta e invia
python3 ~/Rocca/monta.py recap 30         # finestra diversa
python3 ~/Rocca/monta.py ritratto --no-invio   # monta senza inviare
```

---

## Struttura

```
~/Rocca/
├── rocca.yaml          ← tutto quello che si tocca sta qui
├── monta.py            ← comando da terminale
├── rocca-bot.py        ← il bot
├── rocca/              ← il codice
│   ├── config.py       preset ed ereditarietà
│   ├── sources.py      raccolta file, date EXIF, ordinamento
│   ├── effects.py      Ken Burns, gradazioni, transizioni
│   ├── assembly.py     orchestrazione ffmpeg
│   └── delivery.py     Telegram
├── clip/               ← recap, mensile, trimestrale
├── ritratto/
├── carosello/
├── assets/             ← intro.png, outro.png
└── montati/            ← i video finiti
```

Dentro le cartelle sincronizzate c'è `.stfolder`: serve a Syncthing,
**non cancellarla**.

---

## Modificare i preset

Tutto sta in `rocca.yaml`. Si apre con `nano ~/Rocca/rocca.yaml`, si salva con
`Ctrl+O` → `Invio` → `Ctrl+X`.

```yaml
recap:
  descrizione: "Recap settimanale"
  sorgente: "clip"           # cartella dentro ~/Rocca
  giorni: 7                  # finestra temporale
  max_elementi: 20           # tetto
  selezione: "recenti"       # recenti | distribuita
  formato: [1080, 1920]      # 9:16. Per il 4:5 usa [1080, 1350]
  ordine: "alternato"        # cronologico | alternato | casuale
  data_da: "scatto"          # scatto | file
  foto:
    durata: 1.8
    zoom: 0.0033
    verso: "alterna"         # dentro | fuori | alterna | fermo
  video:
    durata: 2.5
    salta_inizio: 0.5
  card:
    intro: "intro.png"       # null per non metterla
    outro: "outro.png"
    durata: 1.8
  transizione:
    tipo: "rocca"            # taglio | dissolvenza | rocca | rocca-tutto
    durata_luce: 0.45
    fusione: 0.18
  colore:
    gradazione: "salvia_leggero"
    vignetta: 0.0            # da 0 a 1
```

### Ereditarietà

Un preset può partire da un altro e cambiare solo quello che serve:

```yaml
mensile:
  eredita: "recap"
  giorni: 30
  foto:
    durata: 1.6
```

Tutto il resto arriva da `recap`.

### Le opzioni, spiegate

**`selezione`** — cosa fare quando ci sono più file del limite.
`recenti` tiene la coda, `distribuita` campiona su tutto il periodo. La prima
per i diari, la seconda per le evoluzioni.

**`ordine`** — `cronologico` è l'ordine di scatto. `alternato` distribuisce i
video fra le foto per dare movimento, tenendo le foto in ordine. `casuale`
mescola davvero (e può rimettere due video attaccati, quindi serve a poco).

**`data_da`** — **usa sempre `scatto`.** Quando sposti le foto nell'album,
Android riscrive la data di modifica nell'ordine in cui le hai selezionate, e
la galleria mostra le più recenti in cima: risultato, sequenza rovesciata. La
data EXIF non la tocca nessuno. Se una foto non ha EXIF, ripiega da sola.

**`verso`** — la direzione dello zoom sulle foto. `dentro` dà solennità (il
ritratto lo usa sempre), `alterna` dà varietà (il recap), `fermo` toglie il
movimento quando c'è del testo da leggere (il carosello).

**`zoom`** — l'escursione totale sull'intera durata, **non per fotogramma**.
Vuol dire che puoi cambiare `durata` senza ricalcolare niente: il movimento
resta identico.

---

## Le gradazioni colore

Costruite sui colori del brand: verdi tirati verso il salvia, alte luci verso
il formenton. Servono a far sembrare venti foto scattate in momenti diversi un
unico corpo di lavoro. È la differenza più visibile fra dilettante e
professionale, e non c'entra con gli effetti appariscenti.

| Nome | Quando |
|---|---|
| `nessuno` | Caroselli informativi, dove il colore deve restare fedele |
| `salvia_leggero` | Uso quotidiano |
| `salvia_forte` | Ritratti di razza, dove l'immagine deve pesare |
| `caldo` | Materiale di golden hour |
| `smorzato` | Fondo per contenuti con testo sopra |

Si definiscono in fondo a `rocca.yaml` come catene di filtri ffmpeg. Se ne
vuoi una nuova, la aggiungi lì.

**La vignetta** va da 0 a 1. Scurisce i bordi e porta l'occhio al centro.
Sopra 0.4 si vede troppo.

---

## Quanto viene lungo

A 1,8 secondi per foto, card comprese:

| Elementi | Durata |
|---|---|
| 8 | ~18s |
| 10 | ~22s |
| 15 | ~30s |
| 20 | ~39s |
| **28** | **~55s — limite pratico** |

**Instagram consente 60 secondi per singola Storia.** Oltre, il video viene
diviso in segmenti automatici con tagli in punti a caso.

Tutti i preset "recap" sono a **max 20**: oltre diventa lungo e noioso, e la
percentuale di visualizzazione completa crolla. Meglio otto contenuti buoni
che venti così così.

---

## Se qualcosa non va

| Sintomo | Causa | Cosa fare |
|---|---|---|
| **Un file cancellato torna** | Cartella Send Only: comanda il telefono | Cancella dall'album, non dal PC |
| **Foto doppia o vecchia nel montato** | File fantasma (`.trashed-`, `sync-conflict`) | Svuota il cestino della galleria. Il sistema li ignora e li conta come 👻 |
| **Ordine rovesciato** | `data_da: "file"` con date riscritte | Metti `data_da: "scatto"` |
| **Mancano dei file** | Il tetto `max_elementi` | Leggi l'avviso ⚠️ nel messaggio Telegram |
| **Il trimestrale mostra solo l'ultimo mese** | `selezione: "recenti"` | Metti `selezione: "distribuita"` |
| Il bot non risponde | Servizio fermo | `systemctl --user restart rocca-bot.service` |
| `/stato` non vede file appena spostati | Syncthing non ha sincronizzato | Nell'app: cartella → **Rescan** |
| Le foto non arrivano | Telefono sotto dati mobili | Vai in WiFi e riapri Syncthing-Fork |
| Niente luce di transizione | Mancano `intro.png` o `outro.png` | Mettile in `~/Rocca/assets/` |
| Foto saltate | Formato HEIC | Fotocamera su **JPEG** |
| "Can't play video" sul telefono | Formato colore o indice | Già risolto (`yuv420p` + `faststart`). Se torna, prova `tipo: "taglio"` |
| Video muto | È voluto | La musica si aggiunge su Instagram |

### Diagnosi

```bash
systemctl --user status rocca-bot.service --no-pager | head -5
systemctl --user status syncthing.service --no-pager | head -5
journalctl --user -u rocca-bot.service -n 30 --no-pager
python3 ~/Rocca/monta.py recap --no-invio     # errori per esteso
ls -la ~/Rocca/clip/                          # anche i file nascosti
```

Pannello Syncthing: `xdg-open http://127.0.0.1:8384`

---

## Aggiornare

```bash
cd ~/Downloads && tar xzf rocca-v2.tar.gz && cd rocca && bash installa.sh
```

Lo script preserva `rocca.yaml` e salva una copia in `rocca.yaml.precedente`.
Il nuovo finisce in `rocca.yaml.nuovo`: per vedere cosa è cambiato,

```bash
diff ~/Rocca/rocca.yaml ~/Rocca/rocca.yaml.nuovo
```

Dopo aver toccato `rocca-bot.py` o `rocca/`, riavvia:

```bash
systemctl --user restart rocca-bot.service
```

`monta.py` invece viene rilanciato ogni volta, quindi non serve riavviare
niente per le modifiche al montaggio o a `rocca.yaml`.

---

## Due promemoria

**La pulizia si fa dal telefono.** Album svuotato, più il cestino della
galleria ogni tanto.

**Il recap va in Storia, non in Reel.** Parla a chi già ti segue: non occupa la
griglia, non conta come post della settimana, e lo archivi in un Highlight
*Diario*. Il trimestrale invece regge come Reel — un'evoluzione visibile
funziona anche su chi non ti conosce.

**Per il trimestrale, comincia adesso.** Lascia in `clip/` una foto a settimana
degli stessi soggetti: lo stesso angolo dell'orto, lo stesso recinto. Fra tre
mesi hai il confronto. Se aspetti novembre per pensarci, a novembre non ce
l'hai.
