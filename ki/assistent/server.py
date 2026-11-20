#!/usr/bin/env python3
"""Assistent-Dienst: HTTP-API, Dashboard und Artefakt-Ablage.

Schlank gehalten, damit er auf einem Raspberry Pi 3 (1 GB RAM) neben Ollama
läuft: nur Python-Standardbibliothek plus PyYAML, kein Framework.

Start:  python3 server.py            (Einstellungen über Umgebungsvariablen)

  KI_PORT       Port des Dashboards            (Standard 8080)
  KI_BIND       Adresse, auf der gelauscht wird (Standard 0.0.0.0)
  KI_MODELL     überschreibt "aktiv" aus config/modelle.yaml
  KI_DATEN      Datenverzeichnis                (Standard ki/daten)
  OLLAMA_HOST   Inferenz-Server                 (Standard 127.0.0.1:11434)
"""

import http.client
import json
import os
import re
import socket
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlsplit

import yaml

KI = Path(__file__).resolve().parent.parent
CONFIG = KI / "config"
WEB = KI / "clients" / "web"
DATEN = Path(os.environ.get("KI_DATEN", KI / "daten")).resolve()
ARTEFAKTE = DATEN / "artefakte"

MAX_ANFRAGE = 2 * 1024 * 1024  # größter akzeptierter Request-Body
MAX_ARTEFAKT = 1024 * 1024  # größtes einzelnes Artefakt
OLLAMA_TIMEOUT = 600  # Modell laden + erstes Token dauert auf dem Pi lange

NAME_RE = re.compile(r"^[\wäöüÄÖÜß][\wäöüÄÖÜß .\-]{0,99}$")
MIME = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".svg": "image/svg+xml",
}


class Fehler(Exception):
    """Fehler, der als JSON mit HTTP-Status an den Client geht."""

    def __init__(self, status, meldung):
        super().__init__(meldung)
        self.status = status
        self.meldung = meldung


# --- Konfiguration ---------------------------------------------------------


def lade_modell():
    """Liest das aktive Modell bei jeder Anfrage neu (Wechsel ohne Neustart)."""
    cfg = yaml.safe_load((CONFIG / "modelle.yaml").read_text(encoding="utf-8"))
    name = os.environ.get("KI_MODELL") or cfg["aktiv"]
    modelle = cfg.get("modelle") or {}
    if name not in modelle:
        raise Fehler(500, f"Modell '{name}' steht nicht in config/modelle.yaml")
    eintrag = dict(modelle[name])
    eintrag["name"] = name
    return eintrag


def lade_system_prompt():
    return (CONFIG / "system-prompt.md").read_text(encoding="utf-8").strip()


def ollama_adresse():
    host = os.environ.get("OLLAMA_HOST", "127.0.0.1:11434")
    teile = urlsplit(host if "//" in host else "//" + host)
    return teile.hostname or "127.0.0.1", teile.port or 11434


def ollama_verbindung(timeout):
    host, port = ollama_adresse()
    return http.client.HTTPConnection(host, port, timeout=timeout)


# --- Status ----------------------------------------------------------------


def system_status():
    info = {"host": socket.gethostname()}
    try:
        werte = {}
        for zeile in Path("/proc/meminfo").read_text().splitlines():
            schluessel, _, rest = zeile.partition(":")
            werte[schluessel] = int(rest.split()[0]) // 1024  # kB -> MB
        info["ram_gesamt_mb"] = werte["MemTotal"]
        info["ram_frei_mb"] = werte["MemAvailable"]
        info["swap_gesamt_mb"] = werte.get("SwapTotal", 0)
        info["swap_frei_mb"] = werte.get("SwapFree", 0)
    except (OSError, KeyError, ValueError):
        pass
    try:
        roh = Path("/sys/class/thermal/thermal_zone0/temp").read_text()
        info["cpu_temp_c"] = round(int(roh) / 1000, 1)
    except (OSError, ValueError):
        pass
    try:
        info["last"] = round(os.getloadavg()[0], 2)
        info["kerne"] = os.cpu_count()
    except OSError:
        pass
    return info


def ollama_status(tag):
    """Prüft, ob Ollama läuft und das Modell heruntergeladen ist."""
    status = {"erreichbar": False, "modell_vorhanden": False}
    verbindung = ollama_verbindung(timeout=3)
    try:
        verbindung.request("GET", "/api/tags")
        daten = json.loads(verbindung.getresponse().read())
        status["erreichbar"] = True
        vorhanden = {m.get("name") for m in daten.get("models", [])}
        gesucht = tag if ":" in tag else tag + ":latest"
        status["modell_vorhanden"] = gesucht in vorhanden
    except (OSError, ValueError, http.client.HTTPException):
        pass
    finally:
        verbindung.close()
    return status


# --- Artefakte -------------------------------------------------------------


def artefakt_pfad(name):
    if not NAME_RE.match(name) or name.endswith((".", " ")) or ".." in name:
        raise Fehler(
            400,
            "Ungültiger Name. Erlaubt sind Buchstaben, Ziffern, Leerzeichen, "
            "Punkt, Bindestrich und Unterstrich (max. 100 Zeichen).",
        )
    pfad = (ARTEFAKTE / name).resolve()
    if pfad.parent != ARTEFAKTE:
        raise Fehler(400, "Ungültiger Name.")
    return pfad


def artefakte_liste():
    eintraege = []
    for pfad in ARTEFAKTE.iterdir():
        if pfad.is_file() and not pfad.name.startswith("."):
            stat = pfad.stat()
            eintraege.append(
                {"name": pfad.name, "groesse": stat.st_size, "geaendert": int(stat.st_mtime)}
            )
    eintraege.sort(key=lambda e: e["geaendert"], reverse=True)
    return eintraege


def artefakt_speichern(daten):
    name = daten.get("name")
    inhalt = daten.get("inhalt")
    if not isinstance(name, str) or not isinstance(inhalt, str):
        raise Fehler(400, "Erwartet werden 'name' und 'inhalt' als Text.")
    roh = inhalt.encode("utf-8")
    if len(roh) > MAX_ARTEFAKT:
        raise Fehler(413, "Artefakt ist zu groß (max. 1 MB).")
    pfad = artefakt_pfad(name.strip())
    if pfad.exists() and not daten.get("ueberschreiben"):
        raise Fehler(409, f"'{pfad.name}' existiert bereits.")
    # Erst in eine Temp-Datei schreiben, damit bei Stromausfall nichts halb bleibt.
    temp = pfad.with_name("." + pfad.name + ".tmp")
    temp.write_bytes(roh)
    temp.replace(pfad)
    return {"name": pfad.name, "groesse": len(roh)}


# --- HTTP ------------------------------------------------------------------


def pruefe_nachrichten(nachrichten):
    if not isinstance(nachrichten, list) or not nachrichten:
        raise Fehler(400, "'nachrichten' muss eine nicht-leere Liste sein.")
    sauber = []
    for n in nachrichten:
        if (
            not isinstance(n, dict)
            or n.get("role") not in ("user", "assistant")
            or not isinstance(n.get("content"), str)
        ):
            raise Fehler(400, "Jede Nachricht braucht 'role' (user/assistant) und 'content'.")
        sauber.append({"role": n["role"], "content": n["content"]})
    if sauber[-1]["role"] != "user":
        raise Fehler(400, "Die letzte Nachricht muss vom Nutzer stammen.")
    return sauber


class Handler(BaseHTTPRequestHandler):
    server_version = "ki-assistent"

    def log_message(self, fmt, *args):
        sys.stderr.write("%s %s\n" % (self.address_string(), fmt % args))

    # -- Hilfen --

    def sende_json(self, daten, status=200):
        roh = json.dumps(daten, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(roh)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(roh)

    def lies_json(self):
        try:
            laenge = int(self.headers.get("Content-Length", ""))
        except ValueError:
            raise Fehler(411, "Content-Length fehlt.")
        if laenge > MAX_ANFRAGE:
            raise Fehler(413, "Anfrage ist zu groß.")
        try:
            daten = json.loads(self.rfile.read(laenge))
        except ValueError:
            raise Fehler(400, "Ungültiges JSON.")
        if not isinstance(daten, dict):
            raise Fehler(400, "Erwartet wird ein JSON-Objekt.")
        return daten

    def pruefe_herkunft(self):
        """Verhindert, dass fremde Webseiten im Browser schreibend zugreifen."""
        origin = self.headers.get("Origin")
        if origin and urlsplit(origin).netloc != self.headers.get("Host"):
            raise Fehler(403, "Anfrage von fremder Herkunft abgelehnt.")

    def verteile(self, methode):
        try:
            url = urlsplit(self.path)
            pfad = unquote(url.path)
            if methode != "GET":
                self.pruefe_herkunft()
            if pfad.startswith("/api/"):
                self.api(methode, pfad, parse_qs(url.query))
            elif methode == "GET":
                self.statisch(pfad)
            else:
                raise Fehler(405, "Methode nicht erlaubt.")
        except Fehler as f:
            self.sende_json({"fehler": f.meldung}, f.status)
        except (BrokenPipeError, ConnectionResetError):
            pass  # Browser hat die Verbindung geschlossen

    def do_GET(self):
        self.verteile("GET")

    def do_POST(self):
        self.verteile("POST")

    def do_DELETE(self):
        self.verteile("DELETE")

    # -- Routen --

    def api(self, methode, pfad, query):
        if pfad == "/api/status" and methode == "GET":
            modell = lade_modell()
            self.sende_json(
                {
                    "modell": modell["name"],
                    "ollama_tag": modell["ollama"],
                    "ollama": ollama_status(modell["ollama"]),
                    "system": system_status(),
                }
            )
        elif pfad == "/api/chat" and methode == "POST":
            self.chat(self.lies_json())
        elif pfad == "/api/artefakte" and methode == "GET":
            self.sende_json({"artefakte": artefakte_liste()})
        elif pfad == "/api/artefakte" and methode == "POST":
            self.sende_json(artefakt_speichern(self.lies_json()), 201)
        elif pfad.startswith("/api/artefakte/"):
            datei = artefakt_pfad(pfad[len("/api/artefakte/"):])
            if not datei.is_file():
                raise Fehler(404, "Artefakt nicht gefunden.")
            if methode == "GET":
                self.sende_artefakt(datei, download="download" in query)
            elif methode == "DELETE":
                datei.unlink()
                self.sende_json({"geloescht": datei.name})
            else:
                raise Fehler(405, "Methode nicht erlaubt.")
        else:
            raise Fehler(404, "Unbekannter API-Pfad.")

    def statisch(self, pfad):
        datei = (WEB / (pfad.lstrip("/") or "index.html")).resolve()
        if WEB not in datei.parents or not datei.is_file() or datei.suffix not in MIME:
            raise Fehler(404, "Nicht gefunden.")
        roh = datei.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", MIME[datei.suffix])
        self.send_header("Content-Length", str(len(roh)))
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(roh)

    def sende_artefakt(self, datei, download):
        roh = datei.read_bytes()
        self.send_response(200)
        # Immer als reiner Text: gespeichertes HTML/JS darf nie im Browser laufen.
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(roh)))
        self.send_header("Cache-Control", "no-store")
        if download:
            ascii_name = datei.name.encode("ascii", "replace").decode().replace('"', "_")
            self.send_header(
                "Content-Disposition",
                f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(datei.name)}",
            )
        self.end_headers()
        self.wfile.write(roh)

    # -- Chat --

    def chat(self, daten):
        nachrichten = pruefe_nachrichten(daten.get("nachrichten"))
        modell = lade_modell()
        anfrage = {
            "model": modell["ollama"],
            "messages": [{"role": "system", "content": lade_system_prompt()}] + nachrichten,
            "stream": True,
        }
        if "denken" in modell:
            anfrage["think"] = bool(modell["denken"])
        if modell.get("optionen"):
            anfrage["options"] = modell["optionen"]

        verbindung = ollama_verbindung(timeout=OLLAMA_TIMEOUT)
        try:
            try:
                verbindung.request(
                    "POST",
                    "/api/chat",
                    body=json.dumps(anfrage),
                    headers={"Content-Type": "application/json"},
                )
                antwort = verbindung.getresponse()
            except (OSError, http.client.HTTPException) as e:
                raise Fehler(502, f"Ollama ist nicht erreichbar ({e}).")
            if antwort.status != 200:
                try:
                    grund = json.loads(antwort.read()).get("error", "")
                except ValueError:
                    grund = ""
                raise Fehler(502, f"Ollama meldet Fehler {antwort.status}: {grund}")

            # Ab hier wird gestreamt (F-3): eine JSON-Zeile pro Ereignis.
            self.send_response(200)
            self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Accel-Buffering", "no")
            self.end_headers()
            beginn = time.monotonic()
            for zeile in antwort:
                if not zeile.strip():
                    continue
                teil = json.loads(zeile)
                if teil.get("error"):
                    self.sende_ereignis({"typ": "fehler", "meldung": teil["error"]})
                    break
                text = (teil.get("message") or {}).get("content")
                if text:
                    self.sende_ereignis({"typ": "text", "text": text})
                if teil.get("done"):
                    anzahl = teil.get("eval_count") or 0
                    dauer = (teil.get("eval_duration") or 0) / 1e9
                    ende = {
                        "typ": "ende",
                        "modell": modell["name"],
                        "ollama_tag": modell["ollama"],
                        "token": anzahl,
                        "token_pro_s": round(anzahl / dauer, 1) if dauer else None,
                        "dauer_s": round(time.monotonic() - beginn, 1),
                    }
                    self.sende_ereignis(ende)
                    # N-7: Modell und Leistung im Log
                    self.log_message(
                        "chat modell=%s token=%s tok/s=%s dauer=%ss",
                        modell["ollama"], anzahl, ende["token_pro_s"], ende["dauer_s"],
                    )
        except (OSError, ValueError, http.client.HTTPException) as e:
            # Kopfzeilen sind evtl. schon gesendet, also Fehler als Ereignis melden.
            # Schlägt auch das fehl, ist der Browser weg (z. B. "Stopp" gedrückt).
            try:
                self.sende_ereignis({"typ": "fehler", "meldung": f"Abbruch: {e}"})
            except OSError:
                pass
        finally:
            # Schließen bricht die Generierung in Ollama ab und gibt die CPU frei.
            verbindung.close()

    def sende_ereignis(self, ereignis):
        self.wfile.write(json.dumps(ereignis, ensure_ascii=False).encode("utf-8") + b"\n")
        self.wfile.flush()


def main():
    ARTEFAKTE.mkdir(parents=True, exist_ok=True)
    bind = os.environ.get("KI_BIND", "0.0.0.0")
    port = int(os.environ.get("KI_PORT", "8080"))
    modell = lade_modell()
    server = ThreadingHTTPServer((bind, port), Handler)
    server.daemon_threads = True
    print(
        f"ki-assistent: http://{bind}:{port}  modell={modell['name']} "
        f"({modell['ollama']})  daten={DATEN}",
        file=sys.stderr,
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
