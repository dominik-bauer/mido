# Assistent-Dienst

Kernstück der KI: HTTP-API, Chat-Logik, Anbindung an den Inferenz-Server,
Retrieval aus der Wissensbasis, Tool-Calling und Protokoll.

Anforderungen: F-3 bis F-5, F-7 bis F-9, F-11, F-14, F-17 (siehe `../docs/anforderungen.md`).

## Stand

`server.py` deckt M1 ab: Chat mit Streaming (F-3), austauschbares Modell (F-2),
System-Prompt (F-4), Dashboard (F-16), HTTP-API (F-17) und eine Artefakt-Ablage.
Retrieval und Tool-Calling fehlen noch.

Der Dienst braucht nur Python 3 und PyYAML und liefert auch das Dashboard aus
`../clients/web/` aus.

```sh
python3 ki/assistent/server.py
```

| Variable | Bedeutung | Standard |
|----------|-----------|----------|
| `KI_PORT` | Port des Dashboards | `8080` |
| `KI_BIND` | Adresse, auf der gelauscht wird | `0.0.0.0` |
| `KI_MODELL` | überschreibt `aktiv` aus `../config/modelle.yaml` | – |
| `KI_DATEN` | Datenverzeichnis (Artefakte) | `ki/daten` |
| `OLLAMA_HOST` | Inferenz-Server | `127.0.0.1:11434` |

## API

| Methode | Pfad | Zweck |
|---------|------|-------|
| GET | `/api/status` | aktives Modell, Zustand von Ollama, RAM, CPU-Temperatur, Last |
| POST | `/api/chat` | Body `{"nachrichten": [{"role": "user", "content": "…"}]}`; Antwort als JSON-Zeilen: `{"typ": "text", "text": "…"}` und am Ende `{"typ": "ende", "modell": …, "token": …, "token_pro_s": …}` (N-7) |
| GET | `/api/artefakte` | Liste der gespeicherten Artefakte |
| POST | `/api/artefakte` | Body `{"name": "…", "inhalt": "…", "ueberschreiben": false}`; `409`, wenn der Name schon existiert |
| GET | `/api/artefakte/<name>` | Inhalt als Text; mit `?download=1` als Datei-Download |
| DELETE | `/api/artefakte/<name>` | Artefakt löschen |

Beispiel für ein anderes Gerät im Heimnetz:

```sh
curl -N http://raspberrypi.local:8080/api/chat \
  -d '{"nachrichten": [{"role": "user", "content": "Hallo!"}]}'
```

Artefakte sind Textdateien (max. 1 MB) in `ki/daten/artefakte/`. Sie werden immer
als `text/plain` ausgeliefert, damit gespeichertes HTML nie im Browser ausgeführt wird.

Es gibt keine Anmeldung: Der Dienst ist für das Heimnetz gedacht (N-2) und darf
nicht per Portfreigabe ins Internet gestellt werden.
