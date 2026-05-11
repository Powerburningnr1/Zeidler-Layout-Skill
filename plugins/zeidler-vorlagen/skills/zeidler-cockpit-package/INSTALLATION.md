# GF-Cockpit als Skill ins Zeidler-Marketplace einbauen

Dieses Paket fügt dem bestehenden Repo
`Powerburningnr1/Zeidler-Layout-Skill` einen neuen Skill **`gf-cockpit`** hinzu,
mit dem das Live-Statuscockpit auf jedem Rechner, der das Plugin installiert hat,
mit einem Satz ("zeig mir das Cockpit") aufgerufen werden kann.

## Was hier drin liegt

```
plugins/zeidler-vorlagen/skills/gf-cockpit/
├── SKILL.md                  # Trigger und Workflow für Claude
└── assets/
    └── gf_cockpit.html       # Die Cockpit-HTML (selbstaktualisierend, 15-min Refresh)
```

Pfad und Struktur entsprechen exakt dem bestehenden `projektbriefing`-Skill.

## Upload — drei Wege

### Variante A: GitHub-Web-Oberfläche (schnellster Weg, kein Git-Client nötig)

1. Im Browser zu https://github.com/Powerburningnr1/Zeidler-Layout-Skill gehen
   und in den Ordner `plugins/zeidler-vorlagen/skills/` navigieren.
2. Oben rechts auf **"Add file" → "Upload files"** klicken.
3. Den Ordner `gf-cockpit` aus diesem Paket per Drag-and-Drop ins Browser-Fenster
   ziehen. GitHub legt die Unterordner automatisch an.
4. Commit-Message z. B. `Add gf-cockpit skill` und auf **"Commit changes"** klicken.

### Variante B: Mit Git-Client (sauberer für Verlauf)

```bash
git clone git@github.com:Powerburningnr1/Zeidler-Layout-Skill.git
cd Zeidler-Layout-Skill
cp -r /pfad/zu/diesem/paket/plugins/zeidler-vorlagen/skills/gf-cockpit \
      plugins/zeidler-vorlagen/skills/
git add plugins/zeidler-vorlagen/skills/gf-cockpit
git commit -m "Add gf-cockpit skill: live status dashboard artifact for management"
git push
```

### Variante C: Optional — Plugin-Version bumpen

In `plugins/zeidler-vorlagen/.claude-plugin/plugin.json` die Version von
`0.1.1` auf `0.2.0` heben. Das ist nicht zwingend nötig, aber sauber, weil ein
neuer Skill dazugekommen ist.

## Nach dem Upload — auf einem zweiten Rechner

Auf jedem weiteren Rechner mit Cowork:

1. In Cowork unter Plugin-Verwaltung das Marketplace
   `Powerburningnr1/Zeidler-Layout-Skill` einmal hinzufügen
   (oder, wenn schon vorhanden, das Plugin `zeidler-vorlagen` neu laden).
2. Im Chat einfach schreiben: **"Zeig mir das GF-Cockpit"** oder
   **"Live-Statusseite"** — der Skill triggert dann automatisch und installiert
   das Artifact lokal auf diesem Rechner.

Die Daten selbst kommen weiterhin aus dem zentralen ZeidlerSoft-MCP — d. h.
inhaltlich sehen alle Rechner exakt dieselben Aufgaben, Touren und Risiken.

## Wichtige Hinweise zur Geräte-Sichtbarkeit

- **Artifact ist lokal.** Jeder Rechner installiert das Cockpit beim ersten
  Trigger in sein eigenes Cowork. Das ist Absicht — so können auf verschiedenen
  Rechnern unterschiedliche Filter/Caches gehalten werden.
- **Daten zentral.** Aufgaben, Touren und Projekte werden bei jedem Refresh
  frisch aus ZeidlerSoft gezogen.
- **localStorage-Cache je Browser.** Die P26-Projektliste wird 1 h pro Rechner
  gecacht. Beim ersten Aufruf auf einem neuen Gerät dauert der erste Refresh
  ein paar Sekunden länger, weil die Liste komplett geladen wird.

## Wenn etwas nicht klappt

- **Skill triggert nicht:** Plugin in Cowork neu laden, ggf. einmal Cowork
  schließen und wieder öffnen. Das Triggerwort steht in der `description` der
  SKILL.md.
- **Artifact zeigt Fehler:** Schauen Sie auf die kleine graue Debug-Zeile oben
  rechts im Cockpit. Sie zeigt, wieviele Aufgaben/Touren/Projekte geladen wurden
  und ob die Pipeline durchlief.
- **HTML weiterentwickelt:** Nur `assets/gf_cockpit.html` im Repo aktualisieren,
  committen, push. Auf den Clients das Plugin neu laden — der Skill nutzt beim
  nächsten Trigger automatisch `update_artifact`.
