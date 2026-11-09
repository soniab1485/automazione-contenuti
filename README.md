# Rocca — montaggio automatico di reel da foto e video

Sistema di produzione contenuti social per una piccola azienda agricola.
Prende foto e video da una cartella sincronizzata dal telefono e restituisce
un video verticale montato, consegnato su Telegram.

Scritto in Python, appoggiato a `ffmpeg` e `ImageMagick`. Configurazione in un
solo file YAML.

---

## ⚠️ Leggi prima

**Questo non è un prodotto e non è mantenuto.**

È un sistema costruito su misura per una specifica azienda agricola
([La Rocca del Pavone](https://laroccadelpavone.it/), Garfagnana), pubblicato
come esempio di come si può automatizzare la produzione di contenuti social
con strumenti liberi. Chi l'ha scritto e perché:
[soniabastiani.it](https://soniabastiani.it/).

- Nessun supporto
- Nessuna richiesta di funzionalità
- Nessuna versione Windows o macOS
- Le segnalazioni non verranno lavorate

Se ti è utile, prendilo e adattalo. Licenza MIT.

---

## Cosa fa

1. Legge foto e video da una cartella, entro una finestra temporale
2. Li ordina per **data reale di scatto** (EXIF per le foto, `creation_time`
   per i video), non per data del file
3. Applica un movimento lento di zoom alle foto, taglia i video
4. Normalizza tutto al formato di uscita
5. Aggiunge card di apertura e chiusura, transizioni, gradazione colore
6. Consegna il risultato su Telegram

Un bot Telegram permette di lanciare il montaggio dal telefono, da qualsiasi
rete.

## Preset

Ogni tipo di contenuto è una voce in `rocca.yaml`, e diventa automaticamente un
comando del bot.

| Preset | Finestra | Formato | Caratteristica |
|---|---|---|---|
| `recap` | 7 giorni | 9:16 | Video distribuiti fra le foto |
| `mensile` | 30 giorni | 9:16 | Eredita da `recap` |
| `trimestrale` | 90 giorni | 9:16 | Campionamento distribuito nel tempo |
| `ritratto` | — | 9:16 | Lento, zoom sempre in avvicinamento |
| `carosello` | — | 4:5 | Immagini ferme, stacchi netti |

## Requisiti

- Linux (testato su Ubuntu 24.04)
- `ffmpeg`, `ImageMagick`, Python 3 con PyYAML

```bash
sudo apt install ffmpeg imagemagick python3-yaml
```

Per la sincronizzazione dal telefono: [Syncthing](https://syncthing.net/).
Per il bot: un token da [@BotFather](https://t.me/BotFather).

## Installazione

```bash
git clone <questo-repo> rocca
cd rocca
bash installa.sh
```

Lo script crea le cartelle, copia i file e configura il servizio systemd.
Poi metti token e chat id in `~/Rocca/rocca.yaml`.

```bash
python3 ~/Rocca/monta.py                     # elenca i preset
python3 ~/Rocca/monta.py recap --no-invio    # monta senza inviare
```

## Struttura

```
monta.py            comando da terminale
rocca-bot.py        bot Telegram
rocca.yaml          configurazione e preset
rocca/
  config.py         caricamento preset, ereditarietà
  sources.py        raccolta file, date EXIF, ordinamento
  effects.py        Ken Burns, gradazioni, transizioni
  assembly.py       orchestrazione ffmpeg
  delivery.py       consegna Telegram
```

Documentazione completa in [GUIDA.md](GUIDA.md).

## Scelte tecniche che vale la pena conoscere

Alcune sono correzioni a problemi che non sono ovvi finché non ci sbatti
contro.

**`yuv420p` forzato in uscita.** Il filtro `xfade` promuove il formato colore
a `yuv444p`, che i decoder hardware Android non leggono. Il video parte sul PC
e non sul telefono.

**`+faststart`.** Senza, l'indice del file finisce in coda e i lettori mobili
faticano a riprodurlo.

**Ordinamento per data EXIF.** Android riscrive la data di modifica quando
sposti i file fra album, nell'ordine in cui li selezioni. Siccome la galleria
mostra i più recenti in cima, il risultato è la sequenza rovesciata.

**Filtro dei file fantasma.** Android non cancella: rinomina in `.trashed-…`
e conserva 30 giorni. Syncthing crea copie `sync-conflict`. Entrambi sono
invisibili a `ls` ma non a `find`.

**Zoom espresso come escursione totale.** Non per fotogramma: così cambiando la
durata di una foto il movimento resta identico invece di troncarsi a metà.

**Pre-ingrandimento 2× prima di `zoompan`.** Elimina lo scatto a gradini tipico
di quel filtro.

**Campionamento distribuito.** Su una finestra lunga, tenere gli ultimi N file
mostrerebbe solo la fine del periodo. Per raccontare un'evoluzione serve un
campione lungo tutto l'arco, primo e ultimo compresi.

## Autore

**Sonia Bastiani** — consulente SEO e Google Ads, sviluppo WordPress e
automazioni, docente di digital marketing e AI generativa. Lavora a Lucca e da
remoto, e conduce l'azienda agricola per cui questo sistema è nato.

- Sito e servizi: <https://soniabastiani.it/>
- LinkedIn: <https://www.linkedin.com/in/sonia-bastiani/>
- L'azienda agricola: <https://laroccadelpavone.it/>

## Licenza

MIT
