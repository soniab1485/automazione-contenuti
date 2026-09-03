#!/usr/bin/env bash
# ============================================================
#  INSTALLAZIONE — sistema contenuti La Rocca del Pavone v2
#
#  Uso:  bash installa.sh
#  Da lanciare dalla cartella dove hai scompattato l'archivio.
#  Si puo' rilanciare quante volte vuoi: non distrugge niente.
# ============================================================

set -euo pipefail

BASE="$HOME/Rocca"
SORGENTE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "════════════════════════════════════════════"
echo "  La Rocca del Pavone — sistema contenuti"
echo "════════════════════════════════════════════"
echo

# ---------- 1. dipendenze ----------
echo "→ Controllo i programmi necessari..."
MANCANTI=""
for c in ffmpeg ffprobe python3; do
  command -v "$c" >/dev/null 2>&1 || MANCANTI="$MANCANTI $c"
done
command -v magick >/dev/null 2>&1 || command -v convert >/dev/null 2>&1 \
  || MANCANTI="$MANCANTI imagemagick"
python3 -c "import yaml" 2>/dev/null || MANCANTI="$MANCANTI python3-yaml"

if [ -n "$MANCANTI" ]; then
  echo "  ✗ Mancano:$MANCANTI"
  echo
  echo "  Installali con:"
  echo "    sudo apt install ffmpeg imagemagick python3-yaml"
  echo
  echo "  Poi rilancia questo script."
  exit 2
fi
echo "  ✓ ci sono tutti"

# ---------- 2. cartelle ----------
echo "→ Preparo le cartelle in $BASE"
mkdir -p "$BASE"/{clip,ritratto,carosello,assets,montati,archivio}
for d in clip ritratto carosello assets montati archivio; do
  printf "  %-12s %s\n" "$d/" "$([ -d "$BASE/$d" ] && echo "✓")"
done

# ---------- 3. salvataggio della configurazione esistente ----------
CONFIG="$BASE/rocca.yaml"
TOKEN=""; CHATID=""
if [ -f "$CONFIG" ]; then
  echo "→ Trovata una configurazione: ne salvo una copia"
  cp "$CONFIG" "$BASE/rocca.yaml.precedente"
  TOKEN=$(grep -E '^\s*token:' "$CONFIG" | head -1 | sed 's/.*token:[[:space:]]*"\?\([^"#]*\)"\?.*/\1/' | xargs || true)
  CHATID=$(grep -E '^\s*chat_id:' "$CONFIG" | head -1 | sed 's/.*chat_id:[[:space:]]*"\?\([^"#]*\)"\?.*/\1/' | xargs || true)
  [ -n "$TOKEN" ] && echo "  ✓ token recuperato"
  [ -n "$CHATID" ] && echo "  ✓ chat id recuperato"
fi

# ---------- 3b. token dal vecchio script bash ----------
VECCHIO="$BASE/recap-settimanale.sh"
if [ -z "$TOKEN" ] && [ -f "$VECCHIO" ]; then
  echo "→ Recupero il token dal vecchio recap-settimanale.sh"
  TOKEN=$(grep '^TG_BOT_TOKEN=' "$VECCHIO" | head -1 | cut -d'"' -f2 || true)
  CHATID=$(grep '^TG_CHAT_ID=' "$VECCHIO" | head -1 | cut -d'"' -f2 || true)
  [ -n "$TOKEN" ] && echo "  ✓ token recuperato"
fi

# ---------- 4. copia dei file ----------
echo "→ Installo i file"
cp -r "$SORGENTE/rocca" "$BASE/"
cp "$SORGENTE/monta.py" "$SORGENTE/rocca-bot.py" "$BASE/"
chmod +x "$BASE/monta.py" "$BASE/rocca-bot.py"
rm -rf "$BASE/rocca/__pycache__"

if [ -f "$CONFIG" ]; then
  echo "  ! rocca.yaml esiste già: il nuovo è in rocca.yaml.nuovo"
  echo "    (confronta con: diff rocca.yaml rocca.yaml.nuovo)"
  cp "$SORGENTE/rocca.yaml" "$BASE/rocca.yaml.nuovo"
else
  cp "$SORGENTE/rocca.yaml" "$CONFIG"
  # reinserisco le credenziali recuperate
  if [ -n "$TOKEN" ]; then
    sed -i "s|^  token: \"\"|  token: \"$TOKEN\"|" "$CONFIG"
  fi
  if [ -n "$CHATID" ]; then
    sed -i "s|^  chat_id: \"\"|  chat_id: \"$CHATID\"|" "$CONFIG"
  fi
fi
echo "  ✓ file copiati"

# ---------- 5. servizio ----------
echo "→ Configuro il servizio del bot"
mkdir -p "$HOME/.config/systemd/user"
cp "$SORGENTE/rocca-bot.service" "$HOME/.config/systemd/user/"

if ! systemctl --user daemon-reload 2>/dev/null; then
  echo "  ! systemd utente non raggiungibile: salto questa parte."
  echo "    Poi lancia a mano:"
  echo "      systemctl --user daemon-reload"
  echo "      systemctl --user enable --now rocca-bot.service"
elif grep -qE '^\s*token:\s*""' "$CONFIG" 2>/dev/null; then
  echo "  ! token vuoto in rocca.yaml: il bot non parte finché non lo metti"
  echo "    nano ~/Rocca/rocca.yaml"
else
  systemctl --user enable rocca-bot.service >/dev/null 2>&1 || true
  systemctl --user restart rocca-bot.service 2>/dev/null || true
  sleep 2
  if systemctl --user is-active --quiet rocca-bot.service 2>/dev/null; then
    echo "  ✓ bot attivo"
  else
    echo "  ! il bot non è partito. Controlla con:"
    echo "    journalctl --user -u rocca-bot.service -n 20 --no-pager"
  fi
fi

# il servizio resta vivo anche a sessione chiusa
loginctl enable-linger "$(id -un)" >/dev/null 2>&1 || true

# ---------- 6. riepilogo ----------
echo
echo "════════════════════════════════════════════"
python3 "$BASE/monta.py" 2>/dev/null || true
echo "════════════════════════════════════════════"
echo
echo "Prossimi passi:"
echo "  1. Metti intro.png e outro.png (1080x1920) in ~/Rocca/assets/"
if grep -qE '^\s*token:\s*""' "$CONFIG" 2>/dev/null; then
  echo "  2. Metti token e chat_id in ~/Rocca/rocca.yaml, poi:"
  echo "     systemctl --user enable --now rocca-bot.service"
fi
echo "  3. Prova:  python3 ~/Rocca/monta.py recap 3650 --no-invio"
echo
