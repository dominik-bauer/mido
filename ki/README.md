# Eigene KI

Lokal betriebener KI-Assistent ohne Cloud: offenes Sprachmodell, eigenes Wissen,
Anbindung an unsere anderen Projekte und eigenes Feintuning als Lernprojekt.

- Anforderungen: [docs/anforderungen.md](docs/anforderungen.md)
- Modellauswahl: [docs/modellauswahl.md](docs/modellauswahl.md)

## Ordnerstruktur

```
ki/
├── docs/            Anforderungen, Modellauswahl, Entscheidungen
├── config/          Modellwahl (modelle.yaml), System-Prompt
├── assistent/       Assistent-Dienst: API, Chat-Logik, RAG, Tool-Calling
├── wissensbasis/    Import, Embeddings, Index
│   └── dokumente/   eigene Dokumente (nicht eingecheckt)
├── werkzeuge/       Anbindung Wetterstation, Gaszähler, Bewässerung, Kalender
├── modelle/         Modellgewichte und LoRA-Adapter (nicht eingecheckt)
├── training/        Feintuning / eigenes Training
│   ├── daten/
│   ├── skripte/
│   └── ergebnisse/
├── evaluierung/     Testfragen zum Vergleich von Modellen und Trainingsläufen
├── clients/
│   ├── web/         Weboberfläche
│   ├── cli-rust/    Kommandozeilen-Client in Rust
│   └── esp32/       ESP32-Geräte (z. B. eInk-Kalenderstation)
└── deploy/          Docker Compose für alle Dienste
```

## Meilensteine

1. **M1 – Lokaler Chat:** Ollama + Modell aus `config/modelle.yaml`, Weboberfläche
2. **M2 – Eigenes Wissen:** Dokumente importieren, Antworten mit Quellen
3. **M3 – Anbindung:** Wetterstation und Gaszähler lesen
4. **M4 – Aktionen:** Bewässerung mit Bestätigung
5. **M5 – Extras:** Sprache, Rust-CLI, eigenes Training
