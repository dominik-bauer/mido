# Deployment

Nur im Heimnetz bzw. über VPN erreichbar (N-2). Der Dienst hat keine Anmeldung,
also keine Portfreigabe im Router einrichten.

## Lokal auf dem PC

```sh
ollama pull qwen3:8b               # Modell aus ../config/modelle.yaml
python3 ki/assistent/server.py     # Dashboard: http://localhost:8080/
```

Ein anderes Modell zum Ausprobieren: `KI_MODELL=qwen3-0.6b python3 ki/assistent/server.py`.

Docker Compose (N-6) für die späteren Dienste (Vektor-Datenbank, MQTT-Broker)
steht noch aus. Für M1 reicht der eine Befehl oben.

## Raspberry Pi 3

Der Pi 3 hat 1 GB RAM und vier langsame Kerne. Deshalb läuft dort bewusst eine
abgespeckte Variante: kein Docker, kein Open WebUI, sondern Ollama und der
Assistent-Dienst direkt als systemd-Dienste, mit dem kleinsten Modell `qwen3-0.6b`.

Voraussetzungen:

- **Raspberry Pi OS Lite (64-bit)**. Ollama gibt es nicht für 32 Bit, und die
  Desktop-Variante braucht zu viel RAM.
- SSH-Zugang und ein Nutzer mit sudo.
- Für die Installation einmalig Internet (Ollama und Modell, ca. 0,5 GB), danach nicht mehr (F-1).
- Mindestens 4 GB frei auf der SD-Karte.

Vom PC aus:

```sh
ki/deploy/pi3/deploy.sh nutzer@raspberrypi.local
```

Das Skript kopiert den `ki/`-Ordner per rsync auf den Pi und startet dort
`pi3/install.sh`. Dieses

1. installiert `python3-yaml` und `curl`,
2. vergrößert bei Bedarf die Auslagerungsdatei auf 1 GB (ohne Swap lädt Ollama das Modell nicht),
3. installiert Ollama und stellt es sparsam ein (ein Modell, eine Anfrage, Entladen nach 15 Minuten, N-5),
4. lädt das Modell,
5. richtet den Dienst `ki-assistent` ein und startet ihn.

Danach ist das Dashboard unter `http://raspberrypi.local:8080/` erreichbar.
Für ein Update dasselbe Kommando noch einmal ausführen. Gespeicherte Artefakte
in `ki/daten/` auf dem Pi bleiben dabei erhalten.

Anderes Modell oder anderer Port: `KI_MODELL=… KI_PORT=… ki/deploy/pi3/deploy.sh …`.

Betrieb auf dem Pi:

```sh
journalctl -u ki-assistent -f      # Log, inkl. Modell und Token/s je Antwort (N-7)
sudo systemctl restart ki-assistent
ollama ps                          # ist das Modell geladen?
```

### Was man erwarten kann

- Die erste Antwort nach einer Pause dauert, weil das Modell erst von der
  SD-Karte geladen wird. Das Dashboard zeigt so lange eine laufende Uhr.
- Geschwindigkeit: voraussichtlich wenige Token pro Sekunde. N-3 (10 Token/s) ist
  auf dem Pi 3 nicht erreichbar. Den gemessenen Wert zeigt das Dashboard unter jeder Antwort.
- Qualität: Ein 0,6B-Modell macht Fehler, auch im Deutschen, und hält sich nicht
  immer an den System-Prompt. Für einfache Fragen und als Machbarkeitstest reicht es.
- Wenn der Speicher knapp wird: in `../config/modelle.yaml` `num_ctx` verkleinern
  (z. B. 1024). Mehr Tempo und Qualität gibt es nur mit anderer Hardware. Dann
  läuft der Assistent-Dienst weiter auf dem Pi und `OLLAMA_HOST` zeigt auf den PC.

Stand: Dienst und Dashboard sind auf dem PC mit `qwen3-0.6b` getestet. Die
Installation auf einem echten Pi 3 ist noch nicht erprobt.
