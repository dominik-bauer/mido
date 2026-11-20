#!/usr/bin/env bash
# Richtet die KI auf einem Raspberry Pi 3 ein: Ollama, Modell, Assistent-Dienst.
# Läuft AUF DEM PI, mit sudo:   sudo bash ki/deploy/pi3/install.sh
# Mehrfach ausführbar (z. B. nach einem Update des Repos).
#
# Einstellbar über Umgebungsvariablen:
#   KI_MODELL  Eintrag aus config/modelle.yaml  (Standard: qwen3-0.6b)
#   KI_PORT    Port des Dashboards              (Standard: 8080)
set -euo pipefail

KI_MODELL="${KI_MODELL:-qwen3-0.6b}"
KI_PORT="${KI_PORT:-8080}"
KI_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
NUTZER="${SUDO_USER:-}"

schritt() { printf '\n== %s\n' "$*"; }
abbruch() { printf 'FEHLER: %s\n' "$*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || abbruch "Bitte mit sudo starten."
[ -n "$NUTZER" ] && [ "$NUTZER" != "root" ] ||
  abbruch "Bitte als normaler Nutzer mit sudo starten (nicht direkt als root), der Dienst läuft unter diesem Nutzer."
[ -f "$KI_DIR/assistent/server.py" ] || abbruch "$KI_DIR sieht nicht nach dem ki/-Ordner aus."

# Ollama gibt es nur für 64-Bit. Der Pi 3 kann 64 Bit, aber nur mit dem
# 64-Bit-Image von Raspberry Pi OS (im Imager "Raspberry Pi OS Lite (64-bit)").
[ "$(uname -m)" = "aarch64" ] ||
  abbruch "Dieses System ist $(uname -m). Benötigt wird ein 64-Bit-System (aarch64), z. B. Raspberry Pi OS Lite (64-bit)."

schritt "Pakete"
if ! command -v curl >/dev/null || ! python3 -c 'import yaml' 2>/dev/null; then
  apt-get update
  apt-get install -y --no-install-recommends python3 python3-yaml curl ca-certificates
fi

# Mit 1 GB RAM lädt Ollama das Modell nur, wenn genug Auslagerungsspeicher da ist.
schritt "Auslagerungsspeicher"
speicher_mb() { awk '/^MemTotal:|^SwapTotal:/ {s += $2} END {print int(s / 1024)}' /proc/meminfo; }
if [ "$(speicher_mb)" -lt 1800 ]; then
  if [ -f /etc/dphys-swapfile ] && command -v dphys-swapfile >/dev/null; then
    echo "Vergrößere die Auslagerungsdatei auf 1024 MB."
    dphys-swapfile swapoff || true
    if grep -q '^#\?CONF_SWAPSIZE=' /etc/dphys-swapfile; then
      sed -i 's/^#\?CONF_SWAPSIZE=.*/CONF_SWAPSIZE=1024/' /etc/dphys-swapfile
    else
      echo 'CONF_SWAPSIZE=1024' >>/etc/dphys-swapfile
    fi
    dphys-swapfile setup
    dphys-swapfile swapon
  else
    echo "WARNUNG: RAM + Swap sind nur $(speicher_mb) MB. Bitte ca. 1 GB Swap einrichten,"
    echo "         sonst kann Ollama das Modell evtl. nicht laden."
  fi
else
  echo "RAM + Swap: $(speicher_mb) MB, ausreichend."
fi

schritt "Ollama"
if ! command -v ollama >/dev/null; then
  curl -fsSL https://ollama.com/install.sh | sh
fi
# Sparsame Einstellungen: ein Modell, eine Anfrage gleichzeitig. Das Modell
# bleibt 15 Minuten geladen (Laden von der SD-Karte dauert) und wird danach
# entladen (N-5). Ollama lauscht nur auf 127.0.0.1, also nicht im Heimnetz.
mkdir -p /etc/systemd/system/ollama.service.d
cat >/etc/systemd/system/ollama.service.d/pi3.conf <<'EOF'
[Service]
Environment=OLLAMA_NUM_PARALLEL=1
Environment=OLLAMA_MAX_LOADED_MODELS=1
Environment=OLLAMA_KEEP_ALIVE=15m
EOF
systemctl daemon-reload
systemctl enable ollama
systemctl restart ollama

schritt "Modell"
OLLAMA_TAG="$(python3 - "$KI_DIR/config/modelle.yaml" "$KI_MODELL" <<'EOF'
import sys, yaml
modelle = yaml.safe_load(open(sys.argv[1], encoding="utf-8"))["modelle"]
if sys.argv[2] not in modelle:
    sys.exit(f"Modell '{sys.argv[2]}' steht nicht in modelle.yaml")
print(modelle[sys.argv[2]]["ollama"])
EOF
)"
for _ in $(seq 30); do
  curl -fs http://127.0.0.1:11434/api/version >/dev/null && break
  sleep 1
done
echo "Lade $OLLAMA_TAG (einmalig, braucht Internet) ..."
ollama pull "$OLLAMA_TAG"

schritt "Assistent-Dienst"
install -d -o "$NUTZER" -g "$(id -gn "$NUTZER")" "$KI_DIR/daten" "$KI_DIR/daten/artefakte"
cat >/etc/systemd/system/ki-assistent.service <<EOF
[Unit]
Description=Eigene KI: Assistent-Dienst und Dashboard
After=network-online.target ollama.service
Wants=network-online.target ollama.service

[Service]
User=$NUTZER
WorkingDirectory=$KI_DIR
Environment=KI_MODELL=$KI_MODELL
Environment=KI_PORT=$KI_PORT
Environment=PYTHONUNBUFFERED=1
# Optionale lokale Überschreibungen, nicht eingecheckt
EnvironmentFile=-$KI_DIR/.env
ExecStart=/usr/bin/python3 $KI_DIR/assistent/server.py
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=$KI_DIR/daten

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable ki-assistent
systemctl restart ki-assistent

for _ in $(seq 20); do
  curl -fs "http://127.0.0.1:$KI_PORT/api/status" >/dev/null && break
  sleep 1
done
curl -fs "http://127.0.0.1:$KI_PORT/api/status" >/dev/null ||
  abbruch "Der Dienst antwortet nicht. Log: journalctl -u ki-assistent -n 50"

schritt "Fertig"
echo "Dashboard:  http://$(hostname -I | awk '{print $1}'):$KI_PORT/   (oder http://$(hostname).local:$KI_PORT/)"
echo "Logs:       journalctl -u ki-assistent -f"
echo "Artefakte:  $KI_DIR/daten/artefakte/"
