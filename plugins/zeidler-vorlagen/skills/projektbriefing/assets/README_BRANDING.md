# Branding-Anpassung

Dieser Ordner enthaelt alle Markenelemente, die das Briefing-PDF im Hauslayout erzeugen. **Aenderungen hier wirken automatisch**, ohne dass der Skill oder das Skript angefasst werden muss.

## Dateien in diesem Ordner

| Datei                  | Zweck                                                                  | Pflicht? |
|------------------------|------------------------------------------------------------------------|----------|
| `logo.png`             | Firmenlogo, wird in der Kopfzeile links eingebunden                    | ja (Platzhalter ersetzen) |
| `corporate_design.json`| Hausfarben, Schrift, Footer-Daten, Seitenraender                       | ja       |
| `briefbogen.pdf`       | Optionaler Briefbogen-Hintergrund (z. B. mit Logo, Wasserzeichen, Adressblock); wenn vorhanden, wird er als Hintergrund jeder Seite verwendet, und die in `corporate_design.json` definierte Kopfzeile wird automatisch unterdrueckt | nein     |

## So tauschst Du das Logo aus

1. Lege Dein Logo als `logo.png` in diesen Ordner (transparenter Hintergrund empfohlen).
2. Die Breite in der Kopfzeile wird ueber `corporate_design.json -> kopfzeile.logo_breite_mm` gesteuert (Standard 35 mm). Hoehe skaliert proportional.

## So passt Du Farben/Footer an

Oeffne `corporate_design.json` und ueberschreibe die Werte. Beispiel: Primaerfarbe aendern auf Dein Hausgruen:

```json
"farben": {
  "primaer": "#3A7D44"
}
```

Felder mit `PLATZHALTER` muessen vor produktiver Nutzung durch echte Daten ersetzt werden (Adresse, Telefon, USt-IdNr., HRB, Bankverbindung).

## So nutzt Du einen vorhandenen Briefbogen

Lege Deinen vorhandenen Briefbogen als einseitiges PDF unter dem Namen `briefbogen.pdf` in diesem Ordner ab. Das Skript erkennt ihn automatisch und legt jeden Briefing-Inhalt darueber. Achte darauf, dass im Briefbogen genug Freiraum fuer den Inhaltsbereich (innerhalb der in `corporate_design.json` definierten Seitenraender) bleibt.
