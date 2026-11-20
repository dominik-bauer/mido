#!/usr/bin/env bash
# Kopiert den ki/-Ordner auf den Raspberry Pi und startet dort install.sh.
# Läuft AUF DEM PC:   ki/deploy/pi3/deploy.sh nutzer@raspberrypi.local [zielordner]
#
# KI_MODELL und KI_PORT werden an install.sh durchgereicht, z. B.:
#   KI_PORT=8000 ki/deploy/pi3/deploy.sh pi@192.168.1.50
set -euo pipefail

[ $# -ge 1 ] || { echo "Aufruf: $0 nutzer@host [zielordner, Standard: ki]" >&2; exit 1; }
ZIEL_HOST="$1"
ZIEL_DIR="${2:-ki}"
KI_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "== Kopiere $KI_DIR nach $ZIEL_HOST:$ZIEL_DIR"
# Modelle, private Dokumente und Laufzeitdaten bleiben, wo sie sind.
rsync -az --info=stats1 \
  --exclude '/modelle/*' \
  --exclude '/daten/' \
  --exclude '/wissensbasis/dokumente/*' \
  --exclude '/training/' \
  --exclude '/.env' \
  --exclude '__pycache__/' \
  "$KI_DIR/" "$ZIEL_HOST:$ZIEL_DIR/"

echo "== Starte Installation auf $ZIEL_HOST (fragt ggf. nach dem sudo-Passwort)"
# shellcheck disable=SC2029  # Variablen sollen hier lokal aufgelöst werden
ssh -t "$ZIEL_HOST" "sudo KI_MODELL='${KI_MODELL:-qwen3-0.6b}' KI_PORT='${KI_PORT:-8080}' bash '$ZIEL_DIR/deploy/pi3/install.sh'"
