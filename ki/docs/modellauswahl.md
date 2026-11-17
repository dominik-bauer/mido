# Modellauswahl für den Start

Status: Vorschlag · Stand: 17.11.2026

Gesucht ist ein offenes Modell, das

1. lokal auf Hobby-Hardware läuft (F-1, N-4),
2. gut Deutsch kann,
3. Tool-Calling beherrscht (F-11),
4. eine Lizenz hat, die Nutzung **und Weitertrainieren** erlaubt (N-8, F-20),
5. sich mit verbreiteten Werkzeugen feintunen lässt (z. B. LoRA/QLoRA mit Unsloth oder Hugging Face PEFT).

> Hinweis: Der Modellmarkt ändert sich alle paar Monate. Vor dem Start kurz prüfen,
> ob es von den genannten Familien neuere Versionen gibt. Die Auswahl dann mit den
> Testfragen in `../evaluierung/` treffen, nicht nur nach Benchmarks.

## Empfehlung

**Start mit Qwen3-8B für den Assistenten und Qwen3-1.7B bzw. Qwen3-4B für die ersten
eigenen Feintuning-Versuche.**

Begründung:

- Apache-2.0-Lizenz: keine Einschränkungen beim Weitertrainieren und Weitergeben.
- Eine Familie in vielen Größen (0.6B bis 32B und größer): Mit dem kleinen Modell lernt man
  das Feintuning schnell und billig. Dasselbe Rezept funktioniert danach auch für das 8B-Modell.
- Gutes Deutsch, Tool-Calling und ein umschaltbarer „Denkmodus“ (Reasoning) sind eingebaut.
- In Ollama, llama.cpp, Unsloth und Hugging Face direkt verfügbar.

## Kandidaten im Vergleich

| Modell | Größe | Lizenz | Deutsch | Tool-Calling | Weitertrainieren | Rolle bei uns |
|--------|-------|--------|---------|--------------|------------------|---------------|
| **Qwen3** | 0.6B–32B (+ MoE) | Apache 2.0 | gut | ja | sehr gut unterstützt | **Hauptkandidat** |
| **Mistral Small 3.x** | 24B | Apache 2.0 | sehr gut (europäisch) | ja | möglich, braucht viel VRAM | Qualitätsvergleich, wenn ≥ 16–24 GB VRAM |
| **OLMo 2** (AI2) | 1B, 7B, 13B, 32B | Apache 2.0 | mittel | eingeschränkt | sehr gut, **Trainingsdaten und -code offen** | Lernprojekt: verstehen, wie ein Modell entsteht |
| **SmolLM3** (Hugging Face) | 3B | Apache 2.0 | ordentlich | ja | sehr gut, Trainingsrezept offen | Kleines Modell für Pi/Laptop, Lernprojekt |
| **Llama 3.x** (Meta) | 1B–70B | Llama Community License | gut | ja | gut unterstützt | Alternative; Lizenz hat Auflagen (Namensnennung, Nutzungsrichtlinie) |
| **Gemma 3** (Google) | 1B–27B | Gemma Terms of Use | gut | ja | gut unterstützt | Alternative; eigene Nutzungsbedingungen beachten |
| **Phi-4-mini** (Microsoft) | 3.8B | MIT | mittel | ja | gut | Kleines Modell mit starkem Logik-/Mathe-Profil |

„Offenes Modell“ heißt meist nur: Die Gewichte sind offen. Nur OLMo und SmolLM legen auch
Trainingsdaten und Trainingscode vollständig offen. Für das Lernziel „verstehen, wie es
funktioniert“ ist das ein großer Vorteil.

## Welche Größe für welche Hardware

Richtwerte für 4-Bit-Quantisierung (Q4_K_M), Inferenz:

| Verfügbarer Speicher | Modell für den Assistenten |
|----------------------|----------------------------|
| GPU 6–8 GB VRAM | Qwen3-8B (knapp) oder Qwen3-4B |
| GPU 12–16 GB VRAM | Qwen3-14B |
| GPU 24 GB VRAM | Mistral Small 3.x oder Qwen3-32B |
| Nur CPU, 16 GB RAM | Qwen3-4B / SmolLM3-3B (langsam, aber nutzbar) |
| Raspberry Pi 5 (8 GB) | Qwen3-1.7B / Qwen3-0.6B |

Richtwerte für Feintuning mit QLoRA (Unsloth):

| GPU-VRAM | Machbar |
|----------|---------|
| 6–8 GB | Modelle bis ca. 4B |
| 12–16 GB | Modelle bis ca. 8B–14B |
| keine GPU | Kostenlose Cloud-Notebooks (z. B. Google Colab / Kaggle) nur mit unkritischen Trainingsdaten |

## Was heißt „weiter trainieren“ konkret?

Abgestuft nach Aufwand:

1. **Kein Training, nur Wissen dazugeben (RAG):** Dokumente in die Wissensbasis importieren.
   Für „die KI soll unsere Daten kennen“ ist das fast immer der richtige erste Schritt (M2).
2. **LoRA-/QLoRA-Feintuning:** Dabei werden kleine Zusatzgewichte (Adapter) trainiert, das
   Basismodell bleibt unverändert. Geeignet für Stil, Format, Tool-Aufrufe und Fachbegriffe.
   Dafür reichen einige hundert bis wenige tausend Beispiele. Der Adapter wird als GGUF
   exportiert und in Ollama geladen.
3. **Weiter-Vortraining (Continued Pretraining):** Das Modell lernt mit viel Rohtext weiter,
   z. B. für mehr Deutsch oder eine Fachdomäne. Das braucht deutlich mehr Rechenzeit und ist eher
   etwas für kleine Modelle (OLMo 2 1B, SmolLM3, Qwen3-0.6B).
4. **Kleines Modell selbst trainieren:** Das ist kein Sprachmodell, sondern z. B. ein Bildmodell
   zum Ablesen des Gaszählers oder für Nummernschilder (F-21). Es ist auf eigener Hardware gut
   machbar und dafür sehr lehrreich.

## Vorgeschlagener Ablauf

1. Ollama installieren, `qwen3:8b` (oder passend zur Hardware) starten → M1.
2. 20–30 Testfragen in `../evaluierung/` anlegen. Damit Qwen3-8B gegen ein oder zwei
   Alternativen vergleichen (z. B. Llama 3.1 8B, Gemma 3 12B, Mistral Small bei genug VRAM).
3. Ergebnis und Entscheidung in `../config/modelle.yaml` und hier festhalten.
4. Erster Feintuning-Versuch: Qwen3-1.7B mit LoRA auf einem kleinen eigenen Datensatz, z. B.
   Antworten im gewünschten Stil oder Tool-Aufrufe für die Wetterstation. Skripte nach
   `../training/skripte/`, Notiz zum Lauf nach `../training/ergebnisse/`.
5. Wenn das klappt: dasselbe Rezept für das 8B-Modell.

## Offen

- Konkrete Hardware klären (siehe Anforderungen, Abschnitt 10). Davon hängt die Größe ab.
- Lizenzen vor der endgültigen Wahl noch einmal auf der Modellseite prüfen.
