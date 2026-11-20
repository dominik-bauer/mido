"use strict";

// Dashboard für den Assistent-Dienst. Bewusst ohne Framework und ohne externe
// Dateien, damit es offline und auf schwacher Hardware funktioniert.
// Modell-Ausgaben werden ausschließlich über textContent eingefügt (kein innerHTML).

const $ = (id) => document.getElementById(id);

const ENDUNGEN = {
  python: "py", py: "py", rust: "rs", rs: "rs", javascript: "js", js: "js",
  typescript: "ts", ts: "ts", bash: "sh", sh: "sh", shell: "sh", json: "json",
  yaml: "yaml", yml: "yaml", toml: "toml", html: "html", css: "css", c: "c",
  cpp: "cpp", sql: "sql", markdown: "md", md: "md",
};

let nachrichten = []; // {role, content} – der Gesprächsverlauf dieser Sitzung
let abbruch = null; // AbortController der laufenden Anfrage

function el(tag, klasse, text) {
  const e = document.createElement(tag);
  if (klasse) e.className = klasse;
  if (text !== undefined) e.textContent = text;
  return e;
}

async function api(pfad, optionen) {
  const antwort = await fetch(pfad, optionen);
  if (!antwort.ok) {
    let meldung = `Fehler ${antwort.status}`;
    try {
      meldung = (await antwort.json()).fehler || meldung;
    } catch { /* keine JSON-Antwort */ }
    const fehler = new Error(meldung);
    fehler.status = antwort.status;
    throw fehler;
  }
  return antwort;
}

function zeitstempel() {
  const d = new Date();
  const z = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}${z(d.getMonth() + 1)}${z(d.getDate())}-${z(d.getHours())}${z(d.getMinutes())}${z(d.getSeconds())}`;
}

// --- Status ----------------------------------------------------------------

function setze(id, text, klasse) {
  const e = $(id);
  e.textContent = text;
  e.className = klasse || "";
}

async function ladeStatus() {
  if (document.hidden) return;
  try {
    const s = await (await api("/api/status")).json();
    setze("st-modell", `${s.modell} (${s.ollama_tag})`);
    if (!s.ollama.erreichbar) setze("st-ollama", "nicht erreichbar", "schlecht");
    else if (!s.ollama.modell_vorhanden) setze("st-ollama", "Modell fehlt", "schlecht");
    else setze("st-ollama", "bereit", "gut");
    const sys = s.system;
    setze("st-ram", sys.ram_frei_mb !== undefined ? `${sys.ram_frei_mb} / ${sys.ram_gesamt_mb} MB` : "–");
    const cpu = [];
    if (sys.last !== undefined) cpu.push(`Last ${sys.last.toFixed(2)}`);
    if (sys.cpu_temp_c !== undefined) cpu.push(`${sys.cpu_temp_c.toFixed(1)} °C`);
    setze("st-cpu", cpu.join(" · ") || "–", sys.cpu_temp_c >= 80 ? "schlecht" : "");
  } catch {
    setze("st-ollama", "Dienst nicht erreichbar", "schlecht");
  }
}

// --- Darstellung von Antworten ---------------------------------------------

// Zerlegt Text in normale Absätze und ```-Code-Blöcke.
function zerlege(text) {
  const teile = [];
  let puffer = [];
  let code = null;
  const abschluss = () => {
    const t = puffer.join("\n").trim();
    if (t) teile.push({ art: "text", text: t });
    puffer = [];
  };
  for (const zeile of text.split("\n")) {
    const zaun = zeile.match(/^\s*```\s*([\w+#-]*)\s*$/);
    if (code === null && zaun) {
      abschluss();
      code = { art: "code", sprache: zaun[1].toLowerCase(), zeilen: [] };
    } else if (code !== null && zaun) {
      teile.push({ art: "code", sprache: code.sprache, text: code.zeilen.join("\n") });
      code = null;
    } else if (code !== null) {
      code.zeilen.push(zeile);
    } else {
      puffer.push(zeile);
    }
  }
  if (code !== null) teile.push({ art: "code", sprache: code.sprache, text: code.zeilen.join("\n") });
  abschluss();
  return teile;
}

function zeichne(ziel, text, fertig) {
  ziel.replaceChildren();
  for (const teil of zerlege(text)) {
    if (teil.art === "text") {
      ziel.append(el("p", "", teil.text));
      continue;
    }
    const block = el("div", "codeblock");
    const kopf = el("div", "codeblock-kopf");
    kopf.append(el("span", "", teil.sprache || "Code"));
    if (fertig) {
      const knopf = el("button", "leise klein", "Speichern");
      knopf.type = "button";
      const endung = ENDUNGEN[teil.sprache] || "txt";
      knopf.addEventListener("click", () => oeffneSpeichern(`code-${zeitstempel()}.${endung}`, teil.text));
      kopf.append(knopf);
    }
    block.append(kopf, el("pre", "", teil.text));
    ziel.append(block);
  }
}

function haengeAn(knoten) {
  const verlauf = $("verlauf");
  const unten = verlauf.scrollHeight - verlauf.scrollTop - verlauf.clientHeight < 80;
  $("leer").hidden = true;
  verlauf.append(knoten);
  if (unten) rolleNachUnten();
}

function rolleNachUnten() {
  const verlauf = $("verlauf");
  verlauf.scrollTop = verlauf.scrollHeight;
  if (getComputedStyle(verlauf).overflowY === "visible") {
    verlauf.lastElementChild?.scrollIntoView({ block: "end" });
  }
}

// --- Chat ------------------------------------------------------------------

function setzeLaeuft(laeuft) {
  $("senden").disabled = laeuft;
  $("stopp").hidden = !laeuft;
  $("neu").disabled = laeuft;
  $("gespraech-speichern").disabled = laeuft || nachrichten.length === 0;
}

async function sende(frage) {
  nachrichten.push({ role: "user", content: frage });
  haengeAn(el("div", "nachricht nutzer", frage));

  const kasten = el("div", "nachricht");
  const inhalt = el("div");
  const fuss = el("div", "fuss");
  kasten.append(inhalt, fuss);
  haengeAn(kasten);
  rolleNachUnten();

  // Auf dem Pi dauert das Laden des Modells – deshalb eine laufende Uhr zeigen.
  const start = Date.now();
  const uhr = setInterval(() => {
    fuss.textContent = `Modell arbeitet … ${Math.round((Date.now() - start) / 1000)} s`;
  }, 1000);
  fuss.textContent = "Modell arbeitet …";

  abbruch = new AbortController();
  setzeLaeuft(true);
  let text = "";
  let ende = null;
  let fehler = null;
  let geplant = false;
  const neuZeichnen = () => {
    if (geplant) return;
    geplant = true;
    requestAnimationFrame(() => {
      geplant = false;
      const verlauf = $("verlauf");
      const unten = verlauf.scrollHeight - verlauf.scrollTop - verlauf.clientHeight < 80;
      zeichne(inhalt, text, false);
      if (unten) verlauf.scrollTop = verlauf.scrollHeight;
    });
  };

  try {
    const antwort = await api("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nachrichten }),
      signal: abbruch.signal,
    });
    const leser = antwort.body.getReader();
    const dekoder = new TextDecoder();
    let rest = "";
    for (;;) {
      const { done, value } = await leser.read();
      if (done) break;
      rest += dekoder.decode(value, { stream: true });
      const zeilen = rest.split("\n");
      rest = zeilen.pop();
      for (const zeile of zeilen) {
        if (!zeile.trim()) continue;
        const ereignis = JSON.parse(zeile);
        if (ereignis.typ === "text") {
          text += ereignis.text;
          neuZeichnen();
        } else if (ereignis.typ === "ende") {
          ende = ereignis;
        } else if (ereignis.typ === "fehler") {
          fehler = ereignis.meldung;
        }
      }
    }
  } catch (e) {
    if (e.name !== "AbortError") fehler = e.message;
  }

  clearInterval(uhr);
  const gestoppt = abbruch.signal.aborted;
  abbruch = null;
  text = text.trim();

  if (text) {
    nachrichten.push({ role: "assistant", content: text });
    zeichne(inhalt, text, true);
    const angaben = [];
    if (ende) {
      angaben.push(`${ende.modell} (${ende.ollama_tag})`, `${ende.token} Token`);
      if (ende.token_pro_s) angaben.push(`${ende.token_pro_s} Token/s`);
      angaben.push(`${ende.dauer_s} s`);
    }
    if (gestoppt) angaben.push("gestoppt");
    fuss.replaceChildren(el("span", "", angaben.join(" · ")));
    const knopf = el("button", "leise klein", "Als Artefakt speichern");
    knopf.type = "button";
    knopf.addEventListener("click", () => oeffneSpeichern(`antwort-${zeitstempel()}.md`, text));
    fuss.append(knopf);
  } else {
    // Ohne Antwort die Frage wieder aus dem Verlauf nehmen, sonst folgen zwei
    // Nutzer-Nachrichten aufeinander.
    nachrichten.pop();
    kasten.remove();
    if (!fehler && !gestoppt) fehler = "Das Modell hat keine Antwort geliefert.";
  }
  if (fehler) haengeAn(el("div", "nachricht fehler", fehler));
  setzeLaeuft(false);
  ladeStatus();
}

$("eingabe").addEventListener("submit", (e) => {
  e.preventDefault();
  const frage = $("prompt").value.trim();
  if (!frage || abbruch) return;
  $("prompt").value = "";
  sende(frage);
});

$("prompt").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
    e.preventDefault();
    $("eingabe").requestSubmit();
  }
});

$("stopp").addEventListener("click", () => abbruch?.abort());

$("neu").addEventListener("click", () => {
  nachrichten = [];
  $("verlauf").replaceChildren($("leer"));
  $("leer").hidden = false;
  setzeLaeuft(false);
  $("prompt").focus();
});

$("gespraech-speichern").addEventListener("click", () => {
  const text = nachrichten
    .map((n) => `## ${n.role === "user" ? "Frage" : "Antwort"}\n\n${n.content}`)
    .join("\n\n");
  oeffneSpeichern(`gespraech-${zeitstempel()}.md`, text + "\n");
});

// --- Artefakte -------------------------------------------------------------

function groesse(bytes) {
  return bytes < 1024 ? `${bytes} B` : `${(bytes / 1024).toFixed(1)} kB`;
}

async function ladeArtefakte() {
  let liste;
  try {
    liste = (await (await api("/api/artefakte")).json()).artefakte;
  } catch {
    return;
  }
  const ul = $("artefakt-liste");
  ul.replaceChildren();
  for (const a of liste) {
    const knopf = el("button");
    knopf.type = "button";
    const datum = new Date(a.geaendert * 1000).toLocaleString("de-DE", { dateStyle: "short", timeStyle: "short" });
    knopf.append(el("span", "name", a.name), el("span", "info", `${groesse(a.groesse)} · ${datum}`));
    knopf.addEventListener("click", () => oeffneAnsicht(a.name));
    const li = el("li");
    li.append(knopf);
    ul.append(li);
  }
  $("artefakte-leer").hidden = liste.length > 0;
}

const pfadZu = (name) => `/api/artefakte/${encodeURIComponent(name)}`;

// Speichern-Dialog. "darfErsetzen" ist der Name, der ohne Rückfrage
// überschrieben werden darf (beim Bearbeiten bzw. nach der Rückfrage).
let darfErsetzen = null;

function oeffneSpeichern(name, inhalt, ersetzen) {
  $("sp-name").value = name;
  $("sp-inhalt").value = inhalt;
  $("sp-meldung").textContent = "";
  $("sp-ok").textContent = "Speichern";
  darfErsetzen = ersetzen ? name : null;
  $("dlg-speichern").showModal();
  $("sp-name").focus();
  const punkt = name.lastIndexOf(".");
  $("sp-name").setSelectionRange(0, punkt > 0 ? punkt : name.length);
}

$("sp-name").addEventListener("input", () => {
  $("sp-ok").textContent = "Speichern";
  $("sp-meldung").textContent = "";
});

$("sp-abbrechen").addEventListener("click", () => $("dlg-speichern").close());

$("form-speichern").addEventListener("submit", async (e) => {
  e.preventDefault();
  const name = $("sp-name").value.trim();
  try {
    await api("/api/artefakte", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, inhalt: $("sp-inhalt").value, ueberschreiben: name === darfErsetzen }),
    });
    $("dlg-speichern").close();
    ladeArtefakte();
  } catch (fehler) {
    if (fehler.status === 409) {
      darfErsetzen = name;
      $("sp-ok").textContent = "Überschreiben";
      $("sp-meldung").textContent = `${fehler.message} Noch einmal bestätigen, um zu überschreiben.`;
    } else {
      $("sp-meldung").textContent = fehler.message;
    }
  }
});

$("artefakt-neu").addEventListener("click", () => oeffneSpeichern(`notiz-${zeitstempel()}.md`, ""));

// Ansicht-Dialog
let offen = null; // {name, inhalt}

async function oeffneAnsicht(name) {
  let inhalt;
  try {
    inhalt = await (await api(pfadZu(name))).text();
  } catch {
    ladeArtefakte(); // vermutlich inzwischen gelöscht
    return;
  }
  offen = { name, inhalt };
  $("an-name").textContent = name;
  $("an-inhalt").textContent = inhalt;
  $("an-meldung").textContent = "";
  $("an-download").href = `${pfadZu(name)}?download=1`;
  $("an-loeschen").textContent = "Löschen";
  $("an-loeschen").dataset.sicher = "";
  $("dlg-ansicht").showModal();
}

$("an-schliessen").addEventListener("click", () => $("dlg-ansicht").close());

$("an-loeschen").addEventListener("click", async () => {
  const knopf = $("an-loeschen");
  if (!knopf.dataset.sicher) {
    knopf.dataset.sicher = "1";
    knopf.textContent = "Wirklich löschen?";
    return;
  }
  try {
    await api(pfadZu(offen.name), { method: "DELETE" });
    $("dlg-ansicht").close();
    ladeArtefakte();
  } catch (fehler) {
    $("an-meldung").textContent = fehler.message;
  }
});

$("an-prompt").addEventListener("click", () => {
  const feld = $("prompt");
  feld.value = (feld.value ? feld.value.trimEnd() + "\n\n" : "") + offen.inhalt;
  $("dlg-ansicht").close();
  feld.focus();
});

$("an-bearbeiten").addEventListener("click", () => {
  $("dlg-ansicht").close();
  oeffneSpeichern(offen.name, offen.inhalt, true);
});

// --- Start -----------------------------------------------------------------

ladeStatus();
ladeArtefakte();
setInterval(ladeStatus, 10000);
document.addEventListener("visibilitychange", ladeStatus);
