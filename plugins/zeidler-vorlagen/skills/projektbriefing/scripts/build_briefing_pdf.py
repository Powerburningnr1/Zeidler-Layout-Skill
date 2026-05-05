#!/usr/bin/env python3
"""
build_briefing_pdf.py

Erzeugt aus einer Markdown-Datei ein Briefing-PDF im Hauslayout.

Aufruf:
    python3 build_briefing_pdf.py \
        --markdown <pfad/zur/briefing.md> \
        --output <pfad/zum/briefing.pdf> \
        --assets <pfad/zu/assets-ordner>

Erwartet im Assets-Ordner:
    - logo.png                (Pflicht, Platzhalter ist OK)
    - corporate_design.json   (Pflicht)
    - briefbogen.pdf          (optional; wenn vorhanden, wird er als
                               Hintergrund jeder Seite verwendet)

Abhaengigkeiten: reportlab, markdown, Pillow
Wenn fehlend, werden sie via pip --break-system-packages installiert.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def ensure_dependencies() -> None:
    needed = []
    try:
        import reportlab  # noqa: F401
    except ImportError:
        needed.append("reportlab")
    try:
        import markdown  # noqa: F401
    except ImportError:
        needed.append("markdown")
    try:
        import PIL  # noqa: F401
    except ImportError:
        needed.append("Pillow")
    try:
        import pypdf  # noqa: F401
    except ImportError:
        needed.append("pypdf")
    if needed:
        print(f"[build_briefing_pdf] installiere fehlende Pakete: {needed}", file=sys.stderr)
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--quiet", "--break-system-packages", *needed]
        )


ensure_dependencies()

from reportlab.lib import colors  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # noqa: E402
from reportlab.lib.units import mm  # noqa: E402
from reportlab.pdfgen import canvas  # noqa: E402
from reportlab.platypus import (  # noqa: E402
    BaseDocTemplate,
    Frame,
    Image,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib.enums import TA_LEFT  # noqa: E402


class NumberedCanvas(canvas.Canvas):
    """Canvas, der auf jeder Seite die Gesamtseitenzahl korrekt einsetzt.

    Reportlab kennt waehrend des onPage-Callbacks die Gesamtseitenzahl
    noch nicht. Wir sammeln deshalb die Seiten-States und setzen den
    Platzhalter erst beim finalen save() ein.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._saved_states: list[dict[str, Any]] = []

    def showPage(self) -> None:  # noqa: N802 (reportlab API)
        self._saved_states.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        total = len(self._saved_states)
        for state in self._saved_states:
            self.__dict__.update(state)
            self._draw_page_number(total)
            super().showPage()
        super().save()

    def _draw_page_number(self, total: int) -> None:
        # Wird vom HeaderFooter via setattr injiziert
        renderer = getattr(self, "_zeidler_footer_renderer", None)
        if renderer is not None:
            renderer(self, total)


# ------------------------------------------------------------------ helpers ---


def load_design(assets_dir: Path) -> dict[str, Any]:
    cd_path = assets_dir / "corporate_design.json"
    if not cd_path.exists():
        sys.exit(f"corporate_design.json fehlt in {assets_dir}")
    with cd_path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def fmt(template: str, ctx: dict[str, Any]) -> str:
    """Sehr schlanker {firma.name}-Resolver, kein full jinja."""

    def lookup(match: re.Match[str]) -> str:
        path = match.group(1).split(".")
        node: Any = ctx
        for part in path:
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                return match.group(0)
        return str(node)

    return re.sub(r"\{([a-zA-Z0-9_.]+)\}", lookup, template)


def hex_to_color(value: str) -> colors.Color:
    return colors.HexColor(value)


# ------------------------------------------------------------ markdown parsing ---


HEADING_RE = re.compile(r"^(#{1,4})\s+(.*)$")
TABLE_SEP_RE = re.compile(r"^\s*\|?\s*[:\- ]+\s*(\|\s*[:\- ]+\s*)+\|?\s*$")


def split_blocks(md_text: str) -> list[dict[str, Any]]:
    """Sehr leichtgewichtiger Markdown-Parser, bewusst nur das, was Briefings brauchen."""
    lines = md_text.splitlines()
    blocks: list[dict[str, Any]] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        # Heading
        m = HEADING_RE.match(stripped)
        if m:
            blocks.append({"type": "heading", "level": len(m.group(1)), "text": m.group(2).strip()})
            i += 1
            continue

        # Table: header line + separator line + body lines
        if "|" in line and i + 1 < len(lines) and TABLE_SEP_RE.match(lines[i + 1]):
            header_cells = [c.strip() for c in stripped.strip("|").split("|")]
            i += 2
            rows: list[list[str]] = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                row = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                # pad/truncate to header length
                if len(row) < len(header_cells):
                    row += [""] * (len(header_cells) - len(row))
                else:
                    row = row[: len(header_cells)]
                rows.append(row)
                i += 1
            blocks.append({"type": "table", "header": header_cells, "rows": rows})
            continue

        # List
        if stripped.startswith(("- ", "* ")):
            items: list[str] = []
            while i < len(lines) and lines[i].strip().startswith(("- ", "* ")):
                items.append(lines[i].strip()[2:])
                i += 1
            blocks.append({"type": "list", "items": items})
            continue

        # Blockquote
        if stripped.startswith(">"):
            quote_lines: list[str] = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote_lines.append(lines[i].strip().lstrip(">").strip())
                i += 1
            blocks.append({"type": "quote", "text": " ".join(quote_lines)})
            continue

        # Paragraph (alles bis zur naechsten Leerzeile)
        para_lines: list[str] = []
        while i < len(lines) and lines[i].strip() and not HEADING_RE.match(lines[i].strip()):
            para_lines.append(lines[i].strip())
            i += 1
        blocks.append({"type": "paragraph", "text": " ".join(para_lines)})
    return blocks


def md_inline_to_html(text: str) -> str:
    # **bold** -> <b>...</b>
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    # *italic*
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", text)
    # `code`
    text = re.sub(r"`([^`]+)`", r"<font face='Courier'>\1</font>", text)
    return text


# -------------------------------------------------------------- pdf builder ---


def build_styles(design: dict[str, Any]) -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()["BodyText"]
    schrift = design.get("schrift", {})
    farben = design.get("farben", {})
    family = schrift.get("familie", "Helvetica")
    text_color = hex_to_color(farben.get("text", "#1A1A1A"))
    text_leise = hex_to_color(farben.get("text_leise", "#666666"))
    primary = hex_to_color(farben.get("primaer", "#0F7037"))
    primary_dark = hex_to_color(farben.get("primaer_dunkel", "#0A4F26"))

    body = ParagraphStyle(
        "Body",
        parent=base,
        fontName=family,
        fontSize=schrift.get("groesse_fliesstext", 10),
        leading=schrift.get("groesse_fliesstext", 10) * 1.4,
        textColor=text_color,
        alignment=TA_LEFT,
        spaceAfter=5,
    )
    body_table = ParagraphStyle(
        "BodyTable",
        parent=body,
        leading=schrift.get("groesse_fliesstext", 10) * 1.25,
        spaceAfter=0,
    )
    body_table_white = ParagraphStyle(
        "BodyTableWhite",
        parent=body_table,
        textColor=hex_to_color(farben.get("tabellenkopf_text", "#FFFFFF")),
        fontName=family + "-Bold",
    )
    title_label = ParagraphStyle(
        "TitleLabel",
        parent=body,
        fontName=family + "-Bold",
        fontSize=schrift.get("groesse_h1_label", 8),
        leading=schrift.get("groesse_h1_label", 8) * 1.25,
        textColor=primary,
        spaceBefore=0,
        spaceAfter=2,
    )
    h1 = ParagraphStyle(
        "H1",
        parent=body,
        fontName=family + "-Bold",
        fontSize=schrift.get("groesse_h1", 20),
        leading=schrift.get("groesse_h1", 20) * 1.15,
        textColor=primary_dark,
        spaceBefore=0,
        spaceAfter=8,
    )
    h2_title = ParagraphStyle(
        "H2Title",
        parent=body,
        fontName=family + "-Bold",
        fontSize=schrift.get("groesse_h2", 13),
        leading=schrift.get("groesse_h2", 13) * 1.2,
        textColor=primary_dark,
        spaceBefore=0,
        spaceAfter=0,
    )
    h2_num = ParagraphStyle(
        "H2Num",
        parent=h2_title,
        textColor=hex_to_color(farben.get("tabellenkopf_text", "#FFFFFF")),
        alignment=1,  # center
    )
    h3 = ParagraphStyle(
        "H3",
        parent=body,
        fontName=family + "-Bold",
        fontSize=schrift.get("groesse_h3", 11),
        textColor=primary_dark,
        spaceBefore=8,
        spaceAfter=3,
    )
    meta_label = ParagraphStyle(
        "MetaLabel",
        parent=body,
        fontName=family + "-Bold",
        fontSize=schrift.get("groesse_meta", 9),
        textColor=primary,
        spaceAfter=0,
    )
    meta_value = ParagraphStyle(
        "MetaValue",
        parent=body,
        fontName=family,
        fontSize=schrift.get("groesse_meta", 9),
        textColor=text_color,
        spaceAfter=0,
    )
    callout_title = ParagraphStyle(
        "CalloutTitle",
        parent=body,
        fontName=family + "-Bold",
        fontSize=schrift.get("groesse_callout_titel", 9),
        textColor=hex_to_color(farben.get("callout_titel", "#8C5800")),
        spaceAfter=2,
    )
    callout_text = ParagraphStyle(
        "CalloutText",
        parent=body,
        fontName=family,
        fontSize=schrift.get("groesse_callout_text", 9),
        textColor=text_color,
        spaceAfter=0,
        leading=schrift.get("groesse_callout_text", 9) * 1.35,
    )
    return {
        "body": body,
        "body_table": body_table,
        "body_table_white": body_table_white,
        "title_label": title_label,
        "h1": h1,
        "h2_title": h2_title,
        "h2_num": h2_num,
        "h3": h3,
        "meta_label": meta_label,
        "meta_value": meta_value,
        "callout_title": callout_title,
        "callout_text": callout_text,
    }


def make_table(block: dict[str, Any], design: dict[str, Any], styles: dict[str, ParagraphStyle], usable_width: float) -> Table:
    farben = design.get("farben", {})
    head_bg = hex_to_color(farben.get("tabellenkopf_hintergrund", "#0F7037"))
    alt_bg = hex_to_color(farben.get("tabellenzeile_alternativ", "#F1F7F2"))
    grid = colors.HexColor("#D9E5DC")
    line_strong = hex_to_color(farben.get("primaer", "#0F7037"))

    header_para = [Paragraph(md_inline_to_html(c), styles["body_table_white"]) for c in block["header"]]
    rows = [header_para]
    for row in block["rows"]:
        rows.append([Paragraph(md_inline_to_html(c), styles["body_table"]) for c in row])

    n_cols = len(block["header"])
    col_widths = [usable_width / n_cols] * n_cols

    tbl = Table(rows, colWidths=col_widths, repeatRows=1)
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), head_bg),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, 0), 1.0, line_strong),
        ("LINEABOVE", (0, 0), (-1, 0), 1.0, line_strong),
        ("INNERGRID", (0, 1), (-1, -1), 0.25, grid),
        ("LINEBELOW", (0, -1), (-1, -1), 0.5, line_strong),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("TOPPADDING", (0, 1), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
    ]
    for r in range(2, len(rows), 2):
        style_cmds.append(("BACKGROUND", (0, r), (-1, r), alt_bg))
    tbl.setStyle(TableStyle(style_cmds))
    return tbl


SECTION_RE = re.compile(r"^(\d+)\.\s+(.+)$")
META_BOLD_RE = re.compile(r"\*\*([^*:]+)[:\s]*\*\*\s*([^*]+?)(?=\s*\*\*|$)")
WARNING_KEYS = ("DRINGEND", "ACHTUNG", "WICHTIG", "WARNUNG")


def make_section_heading(num: str, title: str, design: dict[str, Any], styles: dict[str, ParagraphStyle], usable_width: float) -> Table:
    """H2 mit gruener Quadrat-Marke vor dem Titel."""
    farben = design.get("farben", {})
    badge_bg = hex_to_color(farben.get("primaer", "#0F7037"))
    badge_w = 9 * mm

    # Badge-Zelle als Tabelle mit zentrierter Ziffer
    badge_para = Paragraph(f"<b>{num}</b>", styles["h2_num"])
    title_para = Paragraph(md_inline_to_html(title), styles["h2_title"])

    tbl = Table(
        [[badge_para, title_para]],
        colWidths=[badge_w, usable_width - badge_w - 2 * mm],
    )
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), badge_bg),
                ("TEXTCOLOR", (0, 0), (0, 0), hex_to_color(farben.get("tabellenkopf_text", "#FFFFFF"))),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (0, 0), "CENTER"),
                ("ALIGN", (1, 0), (1, 0), "LEFT"),
                ("LEFTPADDING", (0, 0), (0, 0), 0),
                ("RIGHTPADDING", (0, 0), (0, 0), 0),
                ("TOPPADDING", (0, 0), (0, 0), 4),
                ("BOTTOMPADDING", (0, 0), (0, 0), 4),
                ("LEFTPADDING", (1, 0), (1, 0), 8),
                ("RIGHTPADDING", (1, 0), (1, 0), 0),
                ("TOPPADDING", (1, 0), (1, 0), 4),
                ("BOTTOMPADDING", (1, 0), (1, 0), 4),
            ]
        )
    )
    tbl.keepWithNext = True  # Sektionsueberschrift nicht alleine am Seitenende
    return tbl


def make_title_block(title: str, design: dict[str, Any], styles: dict[str, ParagraphStyle]) -> list[Any]:
    farben = design.get("farben", {})
    primary = hex_to_color(farben.get("primaer", "#0F7037"))
    return [
        Paragraph("PROJEKT-BRIEFING", styles["title_label"]),
        Paragraph(md_inline_to_html(title), styles["h1"]),
        # Akzentlinie unter dem Titel
        _Rule(width_pt=2.0, color=primary, length_mm=20, spacer_below=4),
    ]


def make_metadata_strip(pairs: list[tuple[str, str]], design: dict[str, Any], styles: dict[str, ParagraphStyle], usable_width: float) -> Table:
    farben = design.get("farben", {})
    bg = hex_to_color(farben.get("metadata_hintergrund", "#F1F7F2"))
    border = hex_to_color(farben.get("primaer", "#0F7037"))

    # Pro Paar zwei Zeilen: Label oben (klein, primaer), Wert unten
    cells = []
    for k, v in pairs:
        cell = [
            Paragraph(k.upper(), styles["meta_label"]),
            Paragraph(md_inline_to_html(v), styles["meta_value"]),
        ]
        cells.append(cell)

    n = len(cells) or 1
    col_widths = [usable_width / n] * n

    # Wir bauen 2 Zeilen: Labels-Zeile, Werte-Zeile
    label_row = [Paragraph(k.upper(), styles["meta_label"]) for k, _ in pairs]
    value_row = [Paragraph(md_inline_to_html(v), styles["meta_value"]) for _, v in pairs]
    tbl = Table([label_row, value_row], colWidths=col_widths)
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), bg),
                ("LINEBEFORE", (0, 0), (0, -1), 2, border),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, 0), 6),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 1),
                ("TOPPADDING", (0, 1), (-1, 1), 0),
                ("BOTTOMPADDING", (0, 1), (-1, 1), 6),
            ]
        )
    )
    return tbl


def make_callout(text: str, design: dict[str, Any], styles: dict[str, ParagraphStyle], usable_width: float) -> Table:
    farben = design.get("farben", {})
    is_warning = any(k in text.upper() for k in WARNING_KEYS)
    if is_warning:
        bg = hex_to_color(farben.get("callout_hintergrund", "#FFF8E1"))
        border = hex_to_color(farben.get("callout_rand", "#E6A300"))
        title_color = hex_to_color(farben.get("callout_titel", "#8C5800"))
        title_text = "ACHTUNG"
    else:
        bg = hex_to_color(farben.get("metadata_hintergrund", "#F1F7F2"))
        border = hex_to_color(farben.get("primaer", "#0F7037"))
        title_color = hex_to_color(farben.get("primaer", "#0F7037"))
        title_text = "HINWEIS"

    title_para = Paragraph(f'<font color="{title_color.hexval()}"><b>{title_text}</b></font>', styles["callout_title"])
    body_para = Paragraph(md_inline_to_html(text), styles["callout_text"])

    tbl = Table(
        [[title_para], [body_para]],
        colWidths=[usable_width],
    )
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), bg),
                ("LINEBEFORE", (0, 0), (0, -1), 3, border),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (0, 0), 6),
                ("BOTTOMPADDING", (0, 0), (0, 0), 0),
                ("TOPPADDING", (0, 1), (0, 1), 0),
                ("BOTTOMPADDING", (0, 1), (0, 1), 6),
            ]
        )
    )
    return tbl


class _Rule(Spacer):
    """Schmale, kurze Akzentlinie als Flowable - Marker unter dem Titel."""

    def __init__(self, width_pt: float, color: colors.Color, length_mm: float, spacer_below: float = 4):
        super().__init__(1, width_pt + spacer_below + 1)
        self._w_pt = width_pt
        self._color = color
        self._len = length_mm * mm
        self._spacer = spacer_below

    def draw(self) -> None:
        self.canv.setStrokeColor(self._color)
        self.canv.setLineWidth(self._w_pt)
        self.canv.line(0, self._spacer + self._w_pt / 2, self._len, self._spacer + self._w_pt / 2)


def parse_metadata_paragraph(text: str) -> list[tuple[str, str]] | None:
    """Erkennt eine Zeile vom Typ '**Stand:** 05.05.2026 **Status:** Angebot ...'.
    Gibt eine Liste von (Label, Wert)-Paaren zurueck oder None.
    """
    pairs = re.findall(r"\*\*([^*:]+):\*\*\s*(.+?)(?=\s*\*\*[^*]+:\*\*|$)", text)
    cleaned = [(k.strip(), v.strip()) for k, v in pairs if v.strip()]
    if len(cleaned) >= 2:
        return cleaned
    return None


def blocks_to_flowables(blocks: list[dict[str, Any]], design: dict[str, Any], styles: dict[str, ParagraphStyle], usable_width: float) -> list[Any]:
    flow: list[Any] = []
    seen_first_h1 = False
    i = 0
    while i < len(blocks):
        b = blocks[i]
        t = b["type"]

        if t == "heading":
            level = b["level"]
            text = b["text"]

            if level == 1 and not seen_first_h1:
                # Premium-Titelblock fuer das erste H1
                seen_first_h1 = True
                flow.extend(make_title_block(text, design, styles))
                # Pruefe, ob naechster Block ein Metadaten-Absatz ist
                if i + 1 < len(blocks) and blocks[i + 1]["type"] == "paragraph":
                    pairs = parse_metadata_paragraph(blocks[i + 1]["text"])
                    if pairs:
                        flow.append(make_metadata_strip(pairs, design, styles, usable_width))
                        flow.append(Spacer(1, 8))
                        i += 2  # Heading + Metadata-Absatz konsumiert
                        continue
                flow.append(Spacer(1, 6))
            elif level == 2:
                m = SECTION_RE.match(text)
                if m:
                    flow.append(Spacer(1, 6))
                    flow.append(make_section_heading(m.group(1), m.group(2), design, styles, usable_width))
                    flow.append(Spacer(1, 4))
                else:
                    para = Paragraph(md_inline_to_html(text), styles["h2_title"])
                    para.keepWithNext = True
                    flow.append(Spacer(1, 6))
                    flow.append(para)
                    flow.append(Spacer(1, 4))
            else:
                flow.append(Paragraph(md_inline_to_html(text), styles["h3"]))

        elif t == "paragraph":
            text = b["text"]
            # Reine Trennstriche '---' aus Markdown nicht ausgeben
            if text.strip() == "---":
                pass
            else:
                flow.append(Paragraph(md_inline_to_html(text), styles["body"]))

        elif t == "list":
            for item in b["items"]:
                flow.append(Paragraph("&bull;&nbsp;&nbsp;" + md_inline_to_html(item), styles["body"]))
            flow.append(Spacer(1, 4))

        elif t == "quote":
            flow.append(make_callout(b["text"], design, styles, usable_width))
            flow.append(Spacer(1, 6))

        elif t == "table":
            flow.append(make_table(b, design, styles, usable_width))
            flow.append(Spacer(1, 6))

        i += 1
    return flow


# ----------------------------------------------------------- header / footer ---


class HeaderFooter:
    def __init__(self, design: dict[str, Any], assets_dir: Path, doc_title: str):
        self.design = design
        self.assets_dir = assets_dir
        self.doc_title = doc_title
        self.logo_path = assets_dir / "logo.png"
        self.signet_path = assets_dir / "jubilaeum_signet.png"
        self.briefbogen_path = assets_dir / "briefbogen.pdf"
        self.use_briefbogen = self.briefbogen_path.exists()

    def __call__(self, c: canvas.Canvas, doc: BaseDocTemplate) -> None:
        # Kopfzeile sofort, Fusszeile spaeter (wegen "Seite X von Y").
        self._draw_header(c)
        # Fusszeilen-Renderer in den NumberedCanvas einklinken
        if not hasattr(c, "_zeidler_footer_renderer"):
            c._zeidler_footer_renderer = self._draw_footer  # type: ignore[attr-defined]

    # ---- Header ----------------------------------------------------------
    def _draw_image(self, c: canvas.Canvas, path: Path, x_mm: float, top_y: float, target_w_mm: float, anchor: str = "left") -> float:
        """Zeichnet ein Bild und gibt die effektive Hoehe in Punkt zurueck."""
        from PIL import Image as PILImage
        with PILImage.open(path) as im:
            iw, ih = im.size
        if iw == 0 or ih == 0:
            return 0
        aspect = ih / iw
        target_w = target_w_mm * mm
        target_h = target_w * aspect
        if anchor == "right":
            x = x_mm * mm - target_w
        else:
            x = x_mm * mm
        c.drawImage(
            str(path),
            x,
            top_y - target_h,
            width=target_w,
            height=target_h,
            mask="auto",
            preserveAspectRatio=True,
        )
        return target_h

    def _draw_header(self, c: canvas.Canvas) -> None:
        if self.use_briefbogen:
            return

        page_w, page_h = A4
        farben = self.design.get("farben", {})
        kopfzeile = self.design.get("kopfzeile", {})
        seite = self.design.get("seite", {})
        primary = hex_to_color(farben.get("trennlinie", farben.get("primaer", "#2D7A3E")))

        # Header-Position: top_anchor = Oberkante des Logo-Bildes (von der Blattoberkante).
        top_anchor = page_h - float(kopfzeile.get("abstand_oben_mm", 12)) * mm

        # Logo links
        logo_h = 0.0
        if self.logo_path.exists():
            try:
                logo_h = self._draw_image(
                    c,
                    self.logo_path,
                    x_mm=float(seite.get("rand_links_mm", 20)),
                    top_y=top_anchor,
                    target_w_mm=float(kopfzeile.get("logo_breite_mm", 55)),
                    anchor="left",
                )
            except Exception as exc:  # pragma: no cover
                print(f"[build_briefing_pdf] Logo konnte nicht eingebettet werden: {exc}", file=sys.stderr)

        # Jubilaeums-Signet rechts. Wir richten das Signet an der Logo-Hoehe aus,
        # damit es nicht ueber den Header-Bereich hinausragt.
        signet_h = 0.0
        if self.signet_path.exists():
            try:
                from PIL import Image as PILImage
                with PILImage.open(self.signet_path) as im:
                    siw, sih = im.size
                # Wenn Logo-Hoehe bekannt, signet auf gleiche Hoehe bringen
                if logo_h > 0 and siw > 0:
                    target_w_mm = (logo_h / mm) * (siw / sih)
                    # aber nicht breiter als jubilaeum_signet_breite_mm
                    max_w = float(kopfzeile.get("jubilaeum_signet_breite_mm", 18))
                    target_w_mm = min(target_w_mm, max_w)
                else:
                    target_w_mm = float(kopfzeile.get("jubilaeum_signet_breite_mm", 18))
                signet_h = self._draw_image(
                    c,
                    self.signet_path,
                    x_mm=(page_w / mm) - float(seite.get("rand_rechts_mm", 20)),
                    top_y=top_anchor,
                    target_w_mm=target_w_mm,
                    anchor="right",
                )
            except Exception as exc:  # pragma: no cover
                print(f"[build_briefing_pdf] Signet konnte nicht eingebettet werden: {exc}", file=sys.stderr)

        # Trennlinie. Liegt sicher OBERHALB des Inhaltsbereichs:
        # max(unterer Headerkante, frame_top + 2mm).
        margin_top_mm = float(seite.get("rand_oben_mm", 38))
        frame_top = page_h - margin_top_mm * mm
        gap = float(kopfzeile.get("abstand_strich_mm", 4)) * mm
        line_y = top_anchor - max(logo_h, signet_h) - gap
        # Falls die Berechnung noch in den Inhaltsbereich rutschen wuerde,
        # ziehen wir die Linie 2mm ueber den Frame-Top.
        if line_y <= frame_top:
            line_y = frame_top + 2 * mm

        c.setStrokeColor(primary)
        c.setLineWidth(float(kopfzeile.get("strich_staerke_pt", 1.5)))
        margin_left = float(seite.get("rand_links_mm", 20)) * mm
        margin_right = float(seite.get("rand_rechts_mm", 20)) * mm
        c.line(margin_left, line_y, page_w - margin_right, line_y)

        # ---- Premium-Akzentstreifen oben am Blattrand --------------------
        if kopfzeile.get("akzent_streifen_anzeigen"):
            akzent_h = float(kopfzeile.get("akzent_streifen_hoehe_mm", 2)) * mm
            akzent_top = page_h - float(kopfzeile.get("akzent_streifen_oben_mm", 3)) * mm
            primary_dark = hex_to_color(self.design.get("farben", {}).get("primaer_dunkel", "#0A4F26"))
            akzent_color = hex_to_color(self.design.get("farben", {}).get("akzent", "#C7A04C"))
            # Zwei Bloecke: linker Hauptblock in Hausgruen-dunkel, kurzer Goldakzent rechts
            block_w = (page_w - margin_left - margin_right) * 0.85
            c.setFillColor(primary_dark)
            c.rect(margin_left, akzent_top - akzent_h, block_w, akzent_h, stroke=0, fill=1)
            c.setFillColor(akzent_color)
            c.rect(margin_left + block_w + 2 * mm, akzent_top - akzent_h, page_w - margin_right - margin_left - block_w - 2 * mm, akzent_h, stroke=0, fill=1)

        # ---- Kontakt- / Web-Streifen unter dem Trennstrich ---------------
        kontakt = kopfzeile.get("kontaktstreifen") or {}
        if kontakt.get("anzeigen"):
            firma = self.design.get("firma", {})
            text_leise = hex_to_color(self.design.get("farben", {}).get("text_leise", "#666666"))
            ctx_meta = {"firma": firma}
            elemente = [fmt(e, ctx_meta) for e in kontakt.get("elemente", [])]
            elemente = [e.strip() for e in elemente if e and e.strip()]
            if elemente:
                trenner = kontakt.get("trennzeichen", "  ·  ")
                font_size = float(kontakt.get("schriftgroesse_pt", 7.5))
                contact_y = line_y - float(kontakt.get("abstand_unter_strich_mm", 3)) * mm

                hervorheben = bool(kontakt.get("letztes_element_hervorgehoben", True))
                if hervorheben and len(elemente) >= 1:
                    front = trenner.join(elemente[:-1])
                    if front:
                        front = front + trenner
                    highlight = elemente[-1]
                else:
                    front = trenner.join(elemente)
                    highlight = ""

                # Breiten ausmessen, gesamt rechtsbuendig setzen
                front_w = c.stringWidth(front, "Helvetica", font_size)
                hl_w = c.stringWidth(highlight, "Helvetica-Bold", font_size) if highlight else 0
                total_w = front_w + hl_w
                x_start = page_w - margin_right - total_w

                if front:
                    c.setFont("Helvetica", font_size)
                    c.setFillColor(text_leise)
                    c.drawString(x_start, contact_y, front)
                if highlight:
                    c.setFont("Helvetica-Bold", font_size)
                    c.setFillColor(primary)
                    c.drawString(x_start + front_w, contact_y, highlight)

    # ---- Footer ----------------------------------------------------------
    def _draw_footer(self, c: canvas.Canvas, total_pages: int) -> None:
        page_w, _ = A4
        farben = self.design.get("farben", {})
        schrift = self.design.get("schrift", {})
        firma = self.design.get("firma", {})
        fz = self.design.get("fusszeile", {})

        text_color = hex_to_color(farben.get("text", "#1A1A1A"))
        line_color = hex_to_color(farben.get("trennlinie", farben.get("primaer", "#2D7A3E")))
        font_size = schrift.get("groesse_fusszeile", 7)
        leading = font_size + 1.5

        ctx = {"firma": firma, "seite": c.getPageNumber(), "seiten_gesamt": total_pages}

        spalten = fz.get("spalten")
        # Fallback fuer altes 2-Zeilen-Schema
        if not spalten:
            spalten = [
                {"breite_anteil": 1.0, "zeilen": [fz.get("links_zeile_1", "{firma.name}"), fz.get("links_zeile_2", "")]},
                {"breite_anteil": 1.0, "zeilen": [fz.get("rechts", "Seite {seite} / {seiten_gesamt}")]},
            ]

        margin = 20 * mm
        usable_w = page_w - 2 * margin
        gesamt_anteil = sum(float(s.get("breite_anteil", 1.0)) for s in spalten) or 1.0

        # Platzbedarf bestimmen (max. Zeilenzahl)
        max_zeilen = max(len([z for z in s.get("zeilen", []) if z is not None]) for s in spalten)
        block_h = max_zeilen * leading
        bottom_y = 12 * mm  # untere Innenkante

        # Trennlinie ueber Footer
        c.setStrokeColor(line_color)
        c.setLineWidth(0.4)
        c.line(margin, bottom_y + block_h + 2 * mm, page_w - margin, bottom_y + block_h + 2 * mm)

        # Spalten zeichnen
        x = margin
        c.setFillColor(text_color)
        for s in spalten:
            spalte_w = usable_w * float(s.get("breite_anteil", 1.0)) / gesamt_anteil
            zeilen = [z for z in s.get("zeilen", []) if z is not None]
            for i, raw in enumerate(zeilen):
                if not raw:
                    continue
                txt = fmt(raw, ctx)
                if i == 0 and s.get("fett_zeile_1"):
                    c.setFont("Helvetica-Bold", font_size)
                else:
                    c.setFont("Helvetica", font_size)
                y = bottom_y + block_h - (i + 1) * leading + (leading - font_size) / 2
                c.drawString(x, y, txt)
            x += spalte_w

        # Seitenzahl rechts oberhalb der Trennlinie (separater kleiner Streifen)
        seiten_template = fz.get("seitenzahl_rechts")
        if seiten_template:
            c.setFont("Helvetica", font_size)
            c.setFillColor(text_color)
            seiten_y = bottom_y + block_h + 4 * mm
            c.drawRightString(page_w - margin, seiten_y, fmt(seiten_template, ctx))


# ------------------------------------------------------------------- main ---


def derive_doc_title(md_text: str, fallback: str) -> str:
    for line in md_text.splitlines():
        s = line.strip()
        if s.startswith("# "):
            return s[2:].strip()
    return fallback


def stamp_with_briefbogen(content_pdf: Path, briefbogen_pdf: Path, output_pdf: Path) -> None:
    """Legt content_pdf ueber briefbogen_pdf (erste Seite) auf jede Seite."""
    from pypdf import PdfReader, PdfWriter

    bb_reader = PdfReader(str(briefbogen_pdf))
    bb_page = bb_reader.pages[0]

    content_reader = PdfReader(str(content_pdf))
    writer = PdfWriter()

    for page in content_reader.pages:
        # Klone Briefbogen-Seite, lege Content darueber
        from copy import deepcopy
        new_page = deepcopy(bb_page)
        new_page.merge_page(page)
        writer.add_page(new_page)

    with output_pdf.open("wb") as fh:
        writer.write(fh)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--markdown", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--assets", required=True, type=Path)
    parser.add_argument("--title", default=None, help="Optionaler Dokumenttitel; Default ist die erste H1 im Markdown.")
    args = parser.parse_args()

    if not args.markdown.exists():
        sys.exit(f"Markdown-Datei nicht gefunden: {args.markdown}")
    if not args.assets.exists():
        sys.exit(f"Assets-Ordner nicht gefunden: {args.assets}")

    design = load_design(args.assets)
    md_text = args.markdown.read_text(encoding="utf-8")
    doc_title = args.title or derive_doc_title(md_text, args.markdown.stem)

    seite = design.get("seite", {})
    margin_top = seite.get("rand_oben_mm", 25) * mm
    margin_bottom = seite.get("rand_unten_mm", 25) * mm
    margin_left = seite.get("rand_links_mm", 20) * mm
    margin_right = seite.get("rand_rechts_mm", 20) * mm
    page_w, page_h = A4
    usable_width = page_w - margin_left - margin_right

    # Wenn Briefbogen vorhanden, generieren wir zuerst ein Content-PDF
    # ohne eigene Kopfzeile, und stempeln es danach auf den Briefbogen.
    briefbogen = args.assets / "briefbogen.pdf"
    use_briefbogen = briefbogen.exists()

    if use_briefbogen:
        tmp_content = args.output.with_suffix(".content.pdf")
        target_path = tmp_content
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        target_path = args.output

    doc = BaseDocTemplate(
        str(target_path),
        pagesize=A4,
        leftMargin=margin_left,
        rightMargin=margin_right,
        topMargin=margin_top,
        bottomMargin=margin_bottom,
        title=doc_title,
        author=design.get("firma", {}).get("name", ""),
    )

    frame = Frame(margin_left, margin_bottom, usable_width, page_h - margin_top - margin_bottom, id="content")
    hf = HeaderFooter(design, args.assets, doc_title)
    template = PageTemplate(id="main", frames=[frame], onPage=hf)
    doc.addPageTemplates([template])

    styles = build_styles(design)
    blocks = split_blocks(md_text)
    flow = blocks_to_flowables(blocks, design, styles, usable_width)

    doc.build(flow, canvasmaker=NumberedCanvas)

    if use_briefbogen:
        stamp_with_briefbogen(target_path, briefbogen, args.output)
        target_path.unlink(missing_ok=True)

    print(f"[build_briefing_pdf] PDF geschrieben: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
