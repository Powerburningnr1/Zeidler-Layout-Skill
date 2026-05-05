---
name: projektbriefing
description: Erstellt ein Projektbriefing fuer ein Projekt aus dem ZeidlerSoft-System (z. B. P25-3655) als PDF im Hauslayout der ZEIDLER GLAS + FENSTER GmbH. Triggert immer wenn der Benutzer nach einem "Projektbriefing", "Projekt-Briefing", "Briefing fuer Projekt", "Projektakte", "Projektzusammenfassung" oder "Projektreport" fragt, ein Projekt mit ZeidlerSoft-Praefix wie P25-, LB25-, AN25- nennt, oder eine Uebersicht zu einem laufenden Projekt anfordert. Der Skill holt die Daten ueber die ZeidlerSoft-MCP-Tools, baut ein strukturiertes Briefing und gibt am Ende immer ein PDF im definierten Hauslayout aus - auch wenn der Benutzer das Format nicht ausdruecklich nennt. Markdown ist nur Zwischenformat. Bei mehreren genannten Projekten wird je Projekt ein eigenes PDF erzeugt.
---

# Projektbriefing (Hauslayout)

## Zweck

Dieser Skill erzeugt ein einheitliches **Projektbriefing als PDF** aus den Stamm-, Vorgangs- und Aktivitaetsdaten eines ZeidlerSoft-Projekts. Das PDF folgt dem Hauslayout (Logo, Hausfarben, Kopf- und Fusszeile) und ist als Arbeitsgrundlage fuer Geschaeftsfuehrung, Projektleitung und Mitarbeitende gedacht.

Das **Standardausgabeformat ist PDF**. Eine Markdown-Variante wird nur als Zwischenschritt erzeugt und nicht ausgeliefert, ausser der Benutzer fordert sie ausdruecklich an.

## Voraussetzungen

- MCP-Server `zeidlersoft-web-prod` ist verbunden und folgende Tools sind verfuegbar:
  - `projekt_briefing_section` (bevorzugt, weil sektionsweise und gut groessenkontrollierbar)
  - `projekt_briefing` (Fallback)
  - optional `email_get`, `dokument_get` fuer Detailnachladungen
- Python 3 mit `reportlab` und `markdown` ist vorhanden (das Skript installiert beides bei Bedarf via `pip install --break-system-packages`).
- Im Skill-Verzeichnis liegen unter `assets/`:
  - `logo.png` (Firmenlogo, transparent)
  - `corporate_design.json` (Farben, Schriften, Footer-Daten)
  - optional `briefbogen.pdf` (Briefbogenhintergrund, wird wenn vorhanden als Hintergrund aller Seiten verwendet)

## Workflow

Befolge diese Schritte in dieser Reihenfolge:

1. **Projekt identifizieren.** Extrahiere aus der Anfrage die Projektkennung (z. B. `P25-3655`). Wenn der Benutzer mehrere Projekte nennt, fuehre die Schritte 2-5 je Projekt einzeln aus.

2. **Daten holen (sektionsweise, parallel).** Rufe in einem Aufruf parallel mit `projekt_briefing_section` die folgenden Sektionen ab:
   - `stammdaten` (Identitaet, Kunde, Adresse, Summen)
   - `aufgaben` (limit 50)
   - `logs` (limit 30)
   - `finanzen` (Angebote, AB, Rechnungen, Lieferantenanfragen, Bestellungen)
   - `positionen` (limit 50)
   - bei Bedarf zusaetzlich `tourplanung`

   Falls eine Sektion das Token-Limit reisst, reduziere zuerst `limit`, statt Sektionen wegzulassen. Wenn auch das nicht reicht, lies die im Tool-Ergebnis genannte Datei chunkweise und arbeite mit jq.

3. **Briefing inhaltlich aufbauen.** Erzeuge ein Markdown-Dokument mit dieser Struktur (deutsche Ueberschriften, Reihenfolge fix, Abschnitte ohne Inhalt weglassen):

   ```
   # Projekt-Briefing <PRAEFIX-NUMMER> - <Bezeichnung>
   **Stand:** <heutiges Datum dd.mm.yyyy>
   **Status:** <Status>
   **Projektleitung:** <falls bekannt, sonst weglassen>

   ## 1. Stammdaten
   ## 2. Aktuelle Lage / dringende Aufgaben
   ## 3. Finanzielle Uebersicht
   ## 4. Beschaffung
   ## 5. Positionen
   ## 6. Termine / Tourplanung
   ## 7. Aktivitaet & Kommunikation
   ## 8. Empfohlene naechste Schritte
   ```

   Hinweise zum Inhalt:
   - In Abschnitt 2 immer offene Aufgaben mit hoher Dringlichkeit (z. B. "DRINGEND", "SEHR DRINGEND") namentlich nennen, mit Faelligkeit und Ersteller.
   - In Abschnitt 3 die aktuellste Angebotssumme (netto, USt, brutto) hervorheben und die Angebotshistorie tabellarisch zeigen.
   - In Abschnitt 4 Lieferantenanfragen, Bestellungen und deren Status auffuehren; offene Themen (z. B. "Angebot fehlt", Lieferverzug) explizit benennen.
   - In Abschnitt 5 Tabelle mit Pos./Menge/Beschreibung/EP netto/GP netto. HTML in Beschreibungen (z. B. `<p>`, `<font>`) bereinigen.
   - In Abschnitt 8 konkrete, umsetzbare Naechste-Schritte ableiten, kein generisches "Lieferung pruefen", sondern z. B. "Bei Imholz Sperre wegen offener Rechnung klaeren, danach Liefertermin mit Kunde abstimmen".

4. **PDF erzeugen.** Schreibe das Markdown nach `<outputs>/projektbriefing_<PRAEFIX-NUMMER>.md` und rufe dann das gebuendelte Skript auf:

   ```bash
   python3 "<SKILL_DIR>/scripts/build_briefing_pdf.py" \
     --markdown "<outputs>/projektbriefing_<PRAEFIX-NUMMER>.md" \
     --output "<workspace>/Projekt-Briefing_<PRAEFIX-NUMMER>.pdf" \
     --assets "<SKILL_DIR>/assets"
   ```

   `<SKILL_DIR>` ist das Verzeichnis dieser SKILL.md, `<workspace>` ist der vom Benutzer ausgewaehlte Arbeitsordner (Desktop o. ae.). Das Skript laedt automatisch `logo.png` und `corporate_design.json` aus `--assets` und nutzt `briefbogen.pdf` als Hintergrund, wenn vorhanden.

5. **Ergebnis liefern.** Gib dem Benutzer einen `computer://`-Link auf das fertige PDF und liefere drei bis fuenf Saetze Kurzfazit (Status, kritische Punkte, naechster sinnvoller Schritt). Die Markdown-Zwischendatei bleibt im Output-Ordner liegen, wird aber nicht aktiv beworben.

## Layout-Regeln (im Skript verankert)

- Kopfzeile: Firmenlogo links, Dokumenttitel ("Projekt-Briefing P25-3655 - Innentueren") mittig, Datum rechts
- Fusszeile: Firmierung + Adresse links, Seitenzahl rechts, alle Felder aus `corporate_design.json`
- Hausfarben: Primaerfarbe fuer Ueberschriften H1/H2, Sekundaerfarbe fuer Tabellenkopf
- Schrift: Arial/Helvetica 10 pt fuer Fliesstext, 14 pt H1, 12 pt H2
- Seitenraender: 25 mm oben/unten, 20 mm links/rechts
- DIN A4 hoch

Diese Werte koennen ueber `corporate_design.json` ueberschrieben werden, das Skript liest sie zur Laufzeit.

## Edge Cases

- **Projekt nicht gefunden:** Wenn `projekt_briefing` mit dem Praefix-Nummer-Format scheitert (z. B. weil der Server die Form `P253655` erwartet), versuche den Aufruf erneut mit `projekt: "<praefix>-<nummer>"` als Gesamtwert.
- **Sehr grosse Datenmenge:** Reduziere `limit` der einzelnen Sektionen, bevor du Sektionen weglaesst. Lass den Benutzer wissen, wenn relevante Sektionen gekuerzt wurden.
- **Fehlendes Logo:** Wenn `logo.png` 1x1 Pixel oder leer ist (Default-Platzhalter), erzeuge das PDF trotzdem - das Skript behandelt das gracioes.
- **Mehrere Projekte in einer Anfrage:** Pro Projekt eigener Workflow, eigenes PDF, am Ende eine zusammenfassende Antwort mit allen Links.

## Was dieser Skill nicht macht

- Keine Aenderungen an den Projektdaten in ZeidlerSoft (nur Lesen).
- Kein Versand des PDFs per E-Mail an Kunden oder Lieferanten ohne ausdrueckliche, separate Aufforderung mit klarem Empfaengerkreis.
- Keine Finanzentscheidungen (z. B. Freigabe von Bestellungen) - solche Punkte werden nur im Abschnitt "Naechste Schritte" empfohlen.
