# Zeidler Cowork Marketplace

Privates Plugin-Marketplace der **ZEIDLER GLAS + FENSTER GmbH** für Cowork (Claude Desktop).
Enthält die Hausvorlagen, mit denen Claude wiederkehrende Dokumente automatisch im Hauslayout erstellt.

## Aktueller Inhalt

- **Plugin `zeidler-vorlagen`** mit folgenden Skills:
  - `projektbriefing` – erzeugt aus den Daten in ZeidlerSoft (P25-…, AN25-… usw.) ein einseitiges bis mehrseitiges Projektbriefing als **PDF im Hauslayout**.

Weitere Skills (Angebotsanschreiben, Aufmaßprotokoll, Tour-Tagesplan, …) lassen sich später als zusätzliche Ordner unter `plugins/zeidler-vorlagen/skills/` ergänzen.

---

## Schnellstart

### 1. Repository in ein eigenes Git übernehmen

Empfohlen: ein **privates** Repository (GitHub, GitLab, Codeberg oder eigener Git-Server). Die Daten in `plugins/zeidler-vorlagen/skills/projektbriefing/assets/corporate_design.json` enthalten Firmen- und Bankdaten – das sollte nicht öffentlich liegen.

```bash
# Beispiel: lokales Repo initial anlegen und auf ein privates GitHub-Repo pushen
cd zeidler-cowork-marketplace
git init
git add .
git commit -m "Initial: zeidler-vorlagen mit projektbriefing-Skill"
git branch -M main
git remote add origin git@github.com:<deine-org>/zeidler-cowork-marketplace.git
git push -u origin main
```

### 2. Branding einsetzen (einmalig)

Im Ordner `plugins/zeidler-vorlagen/skills/projektbriefing/assets/` liegen die Markenelemente:

| Datei                  | Was anpassen?                                                              |
|------------------------|----------------------------------------------------------------------------|
| `logo.png`             | Echtes Firmenlogo als PNG (transparent) ablegen, gleicher Dateiname        |
| `corporate_design.json`| Felder mit `PLATZHALTER` durch echte Firmen-, Bank- und Registerdaten ersetzen, Hausfarben prüfen |
| `briefbogen.pdf`       | Optional: einseitiges Briefbogen-PDF einlegen, dann wird es als Hintergrund jeder Seite verwendet |

Änderungen committen und pushen:

```bash
git add plugins/zeidler-vorlagen/skills/projektbriefing/assets/
git commit -m "Branding: Logo + Hausfarben + Footer-Daten gesetzt"
git push
```

Eine ausführliche Anleitung steht zusätzlich in
`plugins/zeidler-vorlagen/skills/projektbriefing/assets/README_BRANDING.md`.

### 3. Marketplace in Cowork hinzufügen (je Rechner einmalig)

In Cowork:

1. Plugin-Verwaltung öffnen.
2. **Neues Marketplace hinzufügen** wählen.
3. Als Quelle die Git-URL des Repos angeben, z. B. `git@github.com:<deine-org>/zeidler-cowork-marketplace.git` (oder `https://…`).
4. Anschließend im Marketplace `zeidler-cowork-marketplace` das Plugin **`zeidler-vorlagen`** installieren.

Auf einem zweiten Rechner sind nur Schritte 3+4 nötig – das Branding kommt automatisch aus dem Repo mit.

### 4. Updates verteilen

Wenn Du das Logo, die Farben oder einen Skill änderst, einfach committen und pushen. Auf den anderen Rechnern in Cowork das Plugin neu laden / aktualisieren – Cowork zieht die neue Version aus dem Repo.

```bash
git add .
git commit -m "Update: <was hat sich geändert>"
git push
```

---

## Verzeichnisstruktur

```
zeidler-cowork-marketplace/
├── .claude-plugin/
│   └── marketplace.json                # Marketplace-Manifest
├── plugins/
│   └── zeidler-vorlagen/
│       ├── .claude-plugin/
│       │   └── plugin.json             # Plugin-Manifest
│       └── skills/
│           └── projektbriefing/
│               ├── SKILL.md            # Anleitung für Claude (Trigger + Workflow)
│               ├── assets/
│               │   ├── logo.png            # Firmenlogo (Platzhalter)
│               │   ├── corporate_design.json  # Hausfarben + Footer-Daten
│               │   ├── README_BRANDING.md     # Anleitung zur Anpassung
│               │   └── (briefbogen.pdf)       # optional
│               └── scripts/
│                   └── build_briefing_pdf.py  # PDF-Generator (Python)
├── README.md                             # diese Datei
└── .gitignore
```

## Was Claude konkret tut, wenn der Skill triggert

1. Erkennt Anfragen wie *"Briefing für Projekt P25-3655"* und holt die Projektdaten via MCP `zeidlersoft-web-prod` (`projekt_briefing_section`, sektionsweise: Stammdaten, Aufgaben, Logs, Finanzen, Positionen, Tourplanung).
2. Baut daraus ein strukturiertes Markdown-Briefing mit fester Reihenfolge der Abschnitte.
3. Ruft `build_briefing_pdf.py` auf, das daraus ein PDF im Hauslayout erzeugt (Logo, Hausfarben, Footer mit Firmendaten und Seitenzahl).
4. Speichert das PDF in den vom Anwender gewählten Arbeitsordner (Desktop o. ä.) und liefert einen klickbaren Link zurück.

## Hinweise

- Das PDF-Skript installiert beim ersten Lauf benötigte Python-Pakete (`reportlab`, `markdown`, `Pillow`, `pypdf`) automatisch.
- Wenn ein `briefbogen.pdf` vorhanden ist, wird die eigene Kopfzeile (Logo + Titel) unterdrückt und stattdessen der Briefbogen als Hintergrund jeder Seite verwendet.
- Der Skill ändert nichts in ZeidlerSoft, er liest nur.

## Lizenz / Nutzung

Internes Werkzeug der ZEIDLER GLAS + FENSTER GmbH. Nicht zur Weitergabe an Dritte.
