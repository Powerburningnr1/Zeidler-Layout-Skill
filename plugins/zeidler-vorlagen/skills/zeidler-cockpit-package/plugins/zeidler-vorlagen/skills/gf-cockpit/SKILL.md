---
name: gf-cockpit
description: Installiert ein Live-Statuscockpit als Cowork-Artifact fuer die Geschaeftsfuehrung der ZEIDLER GLAS + FENSTER GmbH. Triggert bei Anfragen wie "GF-Cockpit", "Live-Statusseite", "Cockpit", "Statusuebersicht", "Geschaeftsfuehrungs-Dashboard", "was muss ich heute pruefen", "Live-Statusseite ueber alle Tools", "Live-Cockpit", "Statusseite fuer 2026". Das Artifact zieht alle 15 Minuten frische Daten aus dem ZeidlerSoft-MCP und zeigt offene Aufgaben, eskalierte Vorgaenge, Risiko-Projekte und die Tourplanung der naechsten 7 Tage - strikt gefiltert auf Projekte ab 2026 (Praefix P26-).
---

# GF-Cockpit (Live-Statusseite)

## Zweck

Dieser Skill installiert ein **Live-Cockpit als Cowork-Artifact**, das beim Oeffnen automatisch frische Daten aus ZeidlerSoft zieht und sich alle 15 Minuten selbst aktualisiert. Es zeigt der Geschaeftsfuehrung auf einen Blick, was heute Aufmerksamkeit braucht - ohne dass jemand etwas im System suchen muss.

## Voraussetzungen

- MCP-Server `zeidlersoft-web-prod` ist verbunden.
- Cowork-Mode ist aktiv (fuer `mcp__cowork__create_artifact` / `update_artifact`).
- Folgende ZeidlerSoft-Tools muessen verfuegbar sein:
  - `aufgabe_search`
  - `tourplanung_list`
  - `user_search`
  - `mcp_table_search` (fuer die P26-Projektliste)
- Die HTML-Datei liegt unter `assets/gf_cockpit.html` neben dieser SKILL.md.

## Workflow

1. **Existenz pruefen.** Rufe `mcp__cowork__list_artifacts` und pruefe, ob bereits ein Artifact mit `id = "gf-cockpit"` existiert.

2. **HTML in den Output-Ordner kopieren.** Lies `<SKILL_DIR>/assets/gf_cockpit.html` und schreibe sie nach `<outputs>/gf-cockpit.html`. Das ist noetig, weil `create_artifact` einen absoluten Pfad im aktuellen Cowork-Output-Ordner erwartet.

3. **Artifact installieren oder aktualisieren.**
   - Existiert noch keins: rufe `mcp__cowork__create_artifact` mit
     - `id: "gf-cockpit"`
     - `html_path: "<outputs>/gf-cockpit.html"`
     - `description: "Live-Geschaeftsfuehrungs-Cockpit fuer ZEIDLER GLAS + FENSTER GmbH. Zeigt offene Aufgaben, Eskalationen, Risiko-Projekte und Tourplanung - strikt gefiltert auf P26-Projekte. Auto-Refresh alle 15 Minuten."`
     - `mcp_tools: ["mcp__zeidlersoft-web-prod__aufgabe_search", "mcp__zeidlersoft-web-prod__tourplanung_list", "mcp__zeidlersoft-web-prod__user_search", "mcp__zeidlersoft-web-prod__mcp_table_search"]`
   - Existiert es schon: rufe stattdessen `mcp__cowork__update_artifact` mit gleicher `id`, neuem `html_path` und kurzem `update_summary`.

4. **Rueckmeldung.** Sage dem Benutzer kurz: "Cockpit ist installiert / aktualisiert. Reload-Button oben rechts laedt frische Daten." Gib keinen langen Funktionsbericht ab, das Cockpit ist selbsterklaerend.

## Inhalte des Cockpits

- **4 KPIs:** Offene Aufgaben (P26), davon ueberfaellig, Eskalationen (>14 Tage alt), Touren der naechsten 7 Tage.
- **Top 10 eskalierte Aufgaben** sortiert nach Alter, mit Projektnummer P26-XXXX, Verantwortlichem und Ersteller.
- **Top 10 Risiko-Projekte** aggregiert aus dem Aufgaben-Center, mit Anzahl offener Aufgaben, aeltester Aufgabe und Risiko-Ampel.
- **Tourplanung** fuer die naechsten 7 Tage, gruppiert nach Tag, mit "Heute"/"Morgen"-Labels und Zeitfenster.

## Filterregeln (im HTML verankert)

- Es werden ausschliesslich Datensaetze angezeigt, deren Projekt einen Praefix von **P26-** (oder hoeher, z. B. P27-) traegt. Alt-Projekte (P24-, P25-) werden komplett ausgeblendet.
- Die P26-Projektliste wird per `mcp_table_search` (table=projekt, q="P26-") paginiert geladen und im `localStorage` 1 h gecacht.
- Tourplanung ist client-seitig strikt auf das 7-Tage-Fenster ab heute beschraenkt.
- Aufgaben werden serverseitig in 100er-Pages geladen (der Server cappt `limit` bei 100), das HTML paginiert dann clientseitig durch.

## Was dieser Skill nicht macht

- Keine Aenderungen an Daten in ZeidlerSoft - reines Lesen.
- Keine Geraete-Synchronisation - jeder Rechner haelt seinen eigenen `localStorage`-Cache. Die Daten selbst kommen natuerlich aus dem zentralen ZeidlerSoft.
- Keine Monteur-pro-Tour-Sicht. Die zugehoerigen Backend-Endpunkte (`tourplanung_mitarbeiter_list`, `monteur_tagesuebersicht`, `monteur_auslastung`) liefern aktuell SQL-Fehler ("Unknown column 't.datum'"). Sobald die behoben sind, kann eine Monteur-Gruppierung ergaenzt werden.

## Updates

Wenn das HTML weiterentwickelt wird, einfach `assets/gf_cockpit.html` im Repo aktualisieren und das Plugin in Cowork neu laden. Beim naechsten Trigger ruft der Skill `update_artifact` und verteilt die neue Version automatisch.
