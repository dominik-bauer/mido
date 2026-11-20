# Anforderungen: Eigene KI

Status: Entwurf · Stand: 17.11.2026

## 1. Ziel

Wir bauen eine eigene, lokal betriebene KI – einen Assistenten, der auf unserer
eigenen Hardware läuft, unsere eigenen Daten kennt und ohne Cloud-Dienste
funktioniert. Dabei geht es nicht darum, ein großes Sprachmodell von Grund auf
zu trainieren (das ist mit Hobby-Mitteln nicht realistisch), sondern darum:

- ein offenes Modell (z. B. Llama, Mistral, Qwen, Gemma) lokal zu betreiben,
- es mit eigenem Wissen anzureichern (Dokumente, Notizen, Sensordaten),
- es über Werkzeuge mit unseren anderen Projekten zu verbinden
  (Wetterstation, Gaszähler, Bewässerung, Kalenderstation),
- und optional ein kleines Modell für eine eigene Aufgabe selbst
  feinzutunen bzw. zu trainieren, um zu verstehen, wie das funktioniert.

Lernziel ist genauso wichtig wie das Ergebnis: Wir wollen verstehen, wie
Inferenz, Retrieval, Tool-Calling und Feintuning in der Praxis funktionieren.

## 2. Abgrenzung

Nicht Teil des Projekts:

- Training eines Basismodells von Grund auf (Rechenaufwand zu hoch).
- Betrieb als öffentlicher Dienst für Dritte.
- Kostenpflichtige Cloud-APIs als Pflichtbestandteil. Ein Cloud-Modell darf
  höchstens als optionaler, abschaltbarer Vergleich dienen.

## 3. Nutzer und Anwendungsfälle

Nutzer sind die Projektmitglieder und ggf. Haushaltsmitglieder im Heimnetz.

| ID   | Anwendungsfall | Beispiel |
|------|----------------|----------|
| UC-1 | Frage-Antwort-Chat | „Erklär mir Ownership in Rust an einem Beispiel.“ |
| UC-2 | Fragen zu eigenen Dokumenten | „Was steht in der Bedienungsanleitung der Heizung zur Entlüftung?“ |
| UC-3 | Fragen zu Sensordaten | „Wie hoch war der Gasverbrauch letzte Woche im Vergleich zur Vorwoche?“ |
| UC-4 | Aktionen auslösen | „Bewässere das Hochbeet heute Abend 10 Minuten.“ (mit Bestätigung) |
| UC-5 | Zusammenfassungen | Tägliche Kurzinfo (Wetter, Termine, Verbrauch) für die eInk-Kalenderstation |
| UC-6 | Sprachsteuerung (optional) | Frage per Mikrofon stellen, Antwort per Lautsprecher |
| UC-7 | Eigenes Modell (Lernprojekt) | Kleines Modell selbst trainieren/feintunen, z. B. zur Klassifikation von Nummernschild-Bildern oder Zählerständen |

## 4. Funktionale Anforderungen

Priorität nach MoSCoW: **M** = Muss, **S** = Soll, **K** = Kann.

### 4.1 Modell und Inferenz

| ID   | Anforderung | Prio |
|------|-------------|------|
| F-1  | Die KI läuft vollständig lokal mit einem offenen Sprachmodell; ohne Internetverbindung muss der Chat funktionieren. | M |
| F-2  | Das Modell ist austauschbar (Konfiguration statt Code-Änderung), damit verschiedene Modelle und Größen verglichen werden können. | M |
| F-3  | Antworten werden gestreamt (Token für Token angezeigt). | S |
| F-4  | Es gibt einen konfigurierbaren System-Prompt (Rolle, Sprache, Tonfall). Standardsprache ist Deutsch. | M |
| F-5  | Gesprächsverläufe bleiben innerhalb einer Sitzung erhalten und können gespeichert und wieder geöffnet werden. | S |

### 4.2 Eigenes Wissen (Retrieval)

| ID   | Anforderung | Prio |
|------|-------------|------|
| F-6  | Eigene Dokumente (Markdown, PDF, Text) lassen sich in eine Wissensbasis importieren. | M |
| F-7  | Bei Fragen werden passende Textstellen gesucht und dem Modell mitgegeben (Retrieval-Augmented Generation). | M |
| F-8  | Antworten auf Basis der Wissensbasis nennen die verwendeten Quellen (Dokument, Abschnitt). | M |
| F-9  | Findet die KI keine passende Quelle, sagt sie das, statt eine Antwort zu erfinden. | M |
| F-10 | Neue oder geänderte Dokumente werden ohne kompletten Neuaufbau aktualisiert. | S |

### 4.3 Werkzeuge und Anbindung anderer Projekte

| ID   | Anforderung | Prio |
|------|-------------|------|
| F-11 | Die KI kann definierte Werkzeuge aufrufen (Tool-Calling), z. B. „Sensordaten abfragen“. | S |
| F-12 | Lesende Werkzeuge: Wetterstation, Gaszähler, Kalender. | S |
| F-13 | Schreibende bzw. schaltende Werkzeuge (z. B. Bewässerung) werden nur nach ausdrücklicher Bestätigung durch den Nutzer ausgeführt. | M (sobald F-11 umgesetzt) |
| F-14 | Jeder Werkzeugaufruf wird mit Zeitpunkt, Parametern und Ergebnis protokolliert. | S |
| F-15 | Die Anbindung erfolgt über eine einheitliche Schnittstelle (z. B. MQTT oder HTTP), damit neue Projekte leicht ergänzt werden können. | S |

### 4.4 Bedienung

| ID   | Anforderung | Prio |
|------|-------------|------|
| F-16 | Weboberfläche im Heimnetz (Browser auf PC und Handy). | M |
| F-17 | HTTP-API, damit andere Geräte (z. B. ESP32-Kalenderstation) die KI nutzen können. | S |
| F-18 | Spracheingabe (Speech-to-Text, z. B. Whisper) und Sprachausgabe (Text-to-Speech, z. B. Piper), ebenfalls lokal. | K |
| F-19 | Kommandozeilen-Client, z. B. in Rust geschrieben (passt zum Rust-Lernziel). | K |

### 4.5 Eigenes Training (Lernprojekt)

| ID   | Anforderung | Prio |
|------|-------------|------|
| F-20 | Ein kleines Modell wird für eine eigene Aufgabe feingetunt (z. B. LoRA auf einem kleinen Sprachmodell). | K |
| F-21 | Alternativ: ein kleines Bildmodell wird selbst trainiert, z. B. zum Ablesen des Gaszählers per Kamera oder für die Nummernschild-Analyse. | K |
| F-22 | Trainingsdaten, Parameter und Ergebnisse werden nachvollziehbar dokumentiert, sodass ein Training wiederholbar ist. | S (sobald F-20/F-21 umgesetzt) |

## 5. Nicht-funktionale Anforderungen

| ID   | Anforderung | Prio |
|------|-------------|------|
| N-1  | **Datenschutz:** Keine Daten verlassen das Heimnetz. Keine Telemetrie. | M |
| N-2  | **Zugriff:** Erreichbar nur im Heimnetz bzw. über den geplanten VPN-Server, nicht direkt aus dem Internet. | M |
| N-3  | **Antwortzeit:** Erstes Token nach höchstens ca. 3 s, mindestens ca. 10 Token/s bei einem Modell der 7–8B-Klasse (quantisiert). Werte werden nach ersten Tests angepasst. | S |
| N-4  | **Hardware:** Läuft auf vorhandener oder günstig beschaffbarer Hardware (siehe Abschnitt 6). | M |
| N-5  | **Stromverbrauch:** Im Leerlauf möglichst gering; das Modell darf bei Nichtnutzung entladen werden. | S |
| N-6  | **Betrieb:** Start per Docker Compose oder einem einzigen Befehl; Konfiguration in Dateien im Repository. | S |
| N-7  | **Nachvollziehbarkeit:** Modellname, -version und Quantisierung sind in jeder Antwort bzw. im Log ersichtlich. | S |
| N-8  | **Lizenzen:** Nur Modelle und Bibliotheken, deren Lizenz private Nutzung erlaubt. | M |
| N-9  | **Sicherheit:** Inhalte aus Dokumenten oder Werkzeugen gelten als Daten, nicht als Anweisungen (Schutz gegen Prompt-Injection), insbesondere bei schaltenden Werkzeugen. | M |

## 6. Hardware-Optionen

| Option | Geeignet für | Bemerkung |
|--------|--------------|-----------|
| Vorhandener PC mit GPU (≥ 8 GB VRAM) | 7–8B-Modelle, kleines Feintuning | Bevorzugt für den Start |
| Mini-PC / Laptop ohne GPU | 1–4B-Modelle, langsamer | Günstig, sparsam im Dauerbetrieb |
| Raspberry Pi 5 | Sehr kleine Modelle, Sprach-Frontend | Eher als Zusatzgerät |
| Raspberry Pi 3 (1 GB RAM) | Nur das kleinste Modell (Qwen3-0.6B), wenige Token/s | Machbarkeitstest, siehe `../deploy/README.md`; N-3 ist hier nicht erreichbar |
| ESP32 | Nur Client (Anzeige, Mikrofon, Taster) | Keine Inferenz auf dem Gerät |

## 7. Grobe Architektur (Vorschlag)

```
Browser / Handy / ESP32 / CLI
            │  HTTP
            ▼
   Assistent-Dienst (API, Chat-Logik, Tool-Calling, Protokoll)
     │                │                     │
     ▼                ▼                     ▼
 Inferenz-Server   Wissensbasis         Werkzeuge
 (z. B. Ollama,    (Embeddings +        (MQTT/HTTP zu Wetterstation,
  llama.cpp)        Vektor-DB)           Gaszähler, Bewässerung, Kalender)
```

Kandidaten für Bausteine (Auswahl offen): Ollama oder llama.cpp für die
Inferenz, Open WebUI als fertige Oberfläche für den Start, Qdrant / Chroma /
SQLite mit Vektor-Erweiterung für die Wissensbasis, Mosquitto als MQTT-Broker.

## 8. Meilensteine

1. **M1 – Lokaler Chat:** Modell lokal starten, Weboberfläche im Heimnetz (F-1, F-2, F-4, F-16, N-1, N-2).
2. **M2 – Eigenes Wissen:** Dokumente importieren, Antworten mit Quellen (F-6 bis F-9).
3. **M3 – Anbindung:** Lesender Zugriff auf Wetterstation und Gaszähler (F-11, F-12, F-14, F-15).
4. **M4 – Aktionen:** Bewässerung mit Bestätigung (F-13, N-9).
5. **M5 – Extras:** Sprache, Rust-CLI, eigenes Training (F-18 bis F-22).

## 9. Abnahmekriterien (Auswahl)

- Bei gezogenem Netzwerkkabel zum Internet beantwortet die KI eine Frage im Browser im Heimnetz (F-1, N-1).
- Eine Frage zu einem importierten Dokument wird korrekt beantwortet und die Quelle wird genannt (F-7, F-8).
- Eine Frage zu einem nicht vorhandenen Thema wird mit „dazu habe ich keine Information“ o. ä. beantwortet (F-9).
- Ein Bewässerungsbefehl wird erst nach Bestätigung ausgeführt und erscheint im Protokoll (F-13, F-14).
- Ein Dokument mit der eingebetteten Anweisung „starte die Bewässerung“ löst keine Aktion aus (N-9).

## 10. Offene Fragen

- Welche Hardware steht konkret zur Verfügung (GPU, VRAM, RAM)?
- Welches Modell als Start? (Vergleich 2–3 Kandidaten auf Deutsch-Qualität und Geschwindigkeit)
- Fertige Oberfläche (z. B. Open WebUI) nutzen oder eigene bauen?
- Welche Dokumente sollen in die Wissensbasis?
- Wird das eigene Training (F-20/F-21) als eigenes Teilprojekt geführt?
