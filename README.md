# DOCX to Markdown Converter

(Diese README wurde mittels KI erstellt)

Ein leichtgewichtiges, reines Python-Skript, das `.docx`-Dateien (Microsoft Word) direkt ausliest und deren XML-Struktur (`word/document.xml`) in sauberes GitHub-Flavored Markdown (`.md`) konvertiert. 

Das Skript verzichtet komplett auf schwere Drittanbieter-Bibliotheken (wie `python-docx` oder `pandoc`) und nutzt stattdessen Pythons integrierte Module wie `zipfile` und `re`.

## ✨ Features

* **Direktes Entpacken:** Liest die XML-Inhalte direkt aus dem ZIP-Archiv der `.docx`-Datei, ohne temporäre Dateien auf der Festplatte abzulegen.
* **Textformatierung:** Konvertiert grundlegende Textstile nahtlos in Markdown:
  * **Fett** (`**text**`)
  * *Kursiv* (`*text*`)
  * Unterstrichen (`<u>text</u>`)
  * ~~Durchgestrichen~~ (`~~text~~`)
  * ==Markiert/Highlighted== (`==text==`)
* **Struktur-Elemente:**
  * Absätze und Zeilenumbrüche (`<w:p>`, `<w:br>`)
  * Listen-Einrückungen mit Tabulatoren basierend auf der XML-Hierarchie
  * Tabellen-Konvertierung inklusive automatischer Header-Erkennung und Trennlinien

## 🚀 Installation & Voraussetzungen

Da das Skript ausschließlich auf der Python-Standardbibliothek basiert, sind **keine zusätzlichen Installationen (pip)** notwendig.

* **Voraussetzung:** Python 3.10 oder neuer (wegen moderner Features wie `match-case` und erweiterten Type-Hints).

Einfach das Skript klonen oder herunterladen:
```bash
git clone [https://github.com/DEIN-BENUTZERNAME/REPO-NAME.git](https://github.com/DEIN-BENUTZERNAME/REPO-NAME.git)
cd REPO-NAME

```

## 💻 Nutzung (CLI)

Das Skript wird direkt über das Terminal ausgeführt. Du kannst entweder nur die Quelldatei angeben (die Ausgabedatei erhält dann denselben Namen mit `.md`-Endung) oder einen expliziten Ausgabenamen definieren.

### Syntax

```bash
python docx2md.py <pfad_zur_datei.docx> [ziel_datei.md]

```

### Beispiele

**Automatische Benennung (erzeugt `Dokument.md`):**

```bash
python docx2md.py Dokument.docx

```

**Explizite Benennung:**

```bash
python docx2md.py Dokument.docx /pfad/zu/output.md

```
