"""Render the Data Engineer study guide (content.py) to a PDF with ReportLab.

Usage:
    pip install reportlab pygments
    python study-guide/build_pdf.py

Content is kept as plain data in ``content.py``; this file only knows how to
draw it: headings, prose, syntax-highlighted code, callouts, tables and
two-sided flashcards (question on the left, answer on the right -- fold the
page down the middle or cover the right column to self-test).
"""

from __future__ import annotations

import sys
from pathlib import Path
from xml.sax.saxutils import escape

from pygments import lex
from pygments.lexers import get_lexer_by_name
from pygments.token import Comment, Keyword, Name, Number, Operator, String, Token
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    CondPageBreak,
    Frame,
    KeepTogether,
    NextPageTemplate,
    PageBreak,
    PageBreakIfNotEmpty,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    XPreformatted,
)
from reportlab.platypus.tableofcontents import TableOfContents

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import content  # noqa: E402

OUT = HERE / "Data_Engineer_Study_Guide.pdf"

# --------------------------------------------------------------------------- fonts
FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
for name, file in {
    "Sans": "DejaVuSans.ttf",
    "Sans-Bold": "DejaVuSans-Bold.ttf",
    "Serif": "DejaVuSerif.ttf",
    "Serif-Bold": "DejaVuSerif-Bold.ttf",
    "Mono": "DejaVuSansMono.ttf",
    "Mono-Bold": "DejaVuSansMono-Bold.ttf",
    "Mono-Oblique": "DejaVuSansMono-Oblique.ttf",
    "Mono-BoldOblique": "DejaVuSansMono-BoldOblique.ttf",
}.items():
    pdfmetrics.registerFont(TTFont(name, str(FONT_DIR / file)))
pdfmetrics.registerFontFamily("Sans", normal="Sans", bold="Sans-Bold",
                              italic="Sans", boldItalic="Sans-Bold")
pdfmetrics.registerFontFamily("Mono", normal="Mono", bold="Mono-Bold",
                              italic="Mono-Oblique", boldItalic="Mono-BoldOblique")

# --------------------------------------------------------------------------- palette
INK = colors.HexColor("#1f2933")
MUTED = colors.HexColor("#52606d")
ACCENT = colors.HexColor("#0b6e99")
ACCENT_DARK = colors.HexColor("#08415c")
RULE = colors.HexColor("#d9e2ec")
CODE_BG = colors.HexColor("#f6f8fa")
CODE_BORDER = colors.HexColor("#d0d7de")
CARD_FRONT = colors.HexColor("#e6f2f8")
CARD_BACK = colors.HexColor("#ffffff")
CARD_EDGE = colors.HexColor("#7fb3cc")

CALLOUTS = {
    # kind: (label, fill, bar)
    "bridge": ("CONTROL-M BRIDGE", colors.HexColor("#fff6e0"), colors.HexColor("#d69e00")),
    "tip": ("INTERVIEW TIP", colors.HexColor("#e8f6ec"), colors.HexColor("#2f9e57")),
    "warn": ("COMMON PITFALL", colors.HexColor("#fdecec"), colors.HexColor("#c73a3a")),
    "note": ("KEY IDEA", colors.HexColor("#eef2ff"), colors.HexColor("#4c5fd5")),
    "practice": ("PRACTICE", colors.HexColor("#f3ecfb"), colors.HexColor("#7a4cc2")),
}

TOKEN_COLORS = [
    (Comment, "#6e7781", True),
    (String, "#0a3069", False),
    (Number, "#0550ae", False),
    (Keyword, "#cf222e", False),
    (Name.Builtin, "#953800", False),
    (Name.Function, "#8250df", False),
    (Name.Class, "#8250df", False),
    (Name.Decorator, "#8250df", False),
    (Name.Tag, "#116329", False),
    (Name.Attribute, "#0550ae", False),
    (Operator.Word, "#cf222e", False),
]

# --------------------------------------------------------------------------- styles
PAGE_W, PAGE_H = A4
MARGIN = 18 * mm
CONTENT_W = PAGE_W - 2 * MARGIN

S = {
    "body": ParagraphStyle("body", fontName="Sans", fontSize=9.6, leading=14.2,
                           textColor=INK, spaceAfter=6),
    "small": ParagraphStyle("small", fontName="Sans", fontSize=8.4, leading=11.6,
                            textColor=INK),
    "bullet": ParagraphStyle("bullet", fontName="Sans", fontSize=9.6, leading=13.6,
                             textColor=INK, leftIndent=14, bulletIndent=3, spaceAfter=2.5),
    "h1": ParagraphStyle("h1", fontName="Serif-Bold", fontSize=22, leading=27,
                         textColor=ACCENT_DARK, spaceBefore=0, spaceAfter=4),
    "h1num": ParagraphStyle("h1num", fontName="Sans-Bold", fontSize=10, leading=13,
                            textColor=ACCENT, spaceAfter=2),
    "h2": ParagraphStyle("h2", fontName="Sans-Bold", fontSize=13.2, leading=17,
                         textColor=ACCENT_DARK, spaceBefore=12, spaceAfter=5),
    "h3": ParagraphStyle("h3", fontName="Sans-Bold", fontSize=10.6, leading=14,
                         textColor=INK, spaceBefore=8, spaceAfter=3),
    "lede": ParagraphStyle("lede", fontName="Serif", fontSize=11, leading=16,
                           textColor=MUTED, spaceAfter=10),
    "code": ParagraphStyle("code", fontName="Mono", fontSize=7.7, leading=10.4,
                           textColor=INK),
    "codelabel": ParagraphStyle("codelabel", fontName="Sans-Bold", fontSize=6.8,
                                leading=8, textColor=MUTED),
    "cell": ParagraphStyle("cell", fontName="Sans", fontSize=8.4, leading=11.2,
                           textColor=INK),
    "cellhead": ParagraphStyle("cellhead", fontName="Sans-Bold", fontSize=8.4,
                               leading=11.2, textColor=colors.white),
    "cardq": ParagraphStyle("cardq", fontName="Sans-Bold", fontSize=8.8, leading=12,
                            textColor=ACCENT_DARK),
    "carda": ParagraphStyle("carda", fontName="Sans", fontSize=8.6, leading=11.8,
                            textColor=INK),
    "cardtag": ParagraphStyle("cardtag", fontName="Sans-Bold", fontSize=6.5, leading=8,
                              textColor=ACCENT),
    "callouttitle": ParagraphStyle("callouttitle", fontName="Sans-Bold", fontSize=7.2,
                                   leading=9, spaceAfter=3),
    "callout": ParagraphStyle("callout", fontName="Sans", fontSize=9, leading=13,
                              textColor=INK, spaceAfter=2),
    "toc1": ParagraphStyle("toc1", fontName="Sans-Bold", fontSize=10.5, leading=15,
                           leftIndent=0, textColor=INK),
    "toc2": ParagraphStyle("toc2", fontName="Sans", fontSize=8.8, leading=12,
                           leftIndent=16, textColor=MUTED),
}


# --------------------------------------------------------------------------- doc
class GuideDoc(BaseDocTemplate):
    def __init__(self, path: str):
        super().__init__(path, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN,
                         topMargin=MARGIN + 4 * mm, bottomMargin=MARGIN,
                         title=content.TITLE, author=content.AUTHOR,
                         subject=content.SUBTITLE)
        frame = Frame(MARGIN, MARGIN, CONTENT_W, PAGE_H - 2 * MARGIN - 4 * mm, id="f",
                      leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates([
            PageTemplate("cover", frames=[frame], onPage=draw_cover),
            PageTemplate("body", frames=[frame], onPageEnd=draw_chrome),
        ])
        self.chapter = ""

    def beforeDocument(self):
        self.chapter = ""

    def afterFlowable(self, flowable):
        key = getattr(flowable, "_toc", None)
        if key:
            level, text = key
            if level == 0:
                self.chapter = text
            anchor = f"a{id(flowable)}"
            self.canv.bookmarkPage(anchor)
            self.canv.addOutlineEntry(text, anchor, level=level, closed=level > 0)
            self.notify("TOCEntry", (level, text, self.page, anchor))


def draw_cover(canv, doc):
    canv.saveState()
    canv.setFillColor(ACCENT_DARK)
    canv.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)
    canv.setFillColor(ACCENT)
    canv.rect(0, PAGE_H * 0.36, PAGE_W, 5, stroke=0, fill=1)
    # faint pipeline motif
    canv.setStrokeColor(colors.HexColor("#1d6f94"))
    canv.setLineWidth(1.2)
    y = PAGE_H * 0.085
    xs = [MARGIN + i * (CONTENT_W / 5) for i in range(6)]
    for i, x in enumerate(xs):
        canv.circle(x, y, 9, stroke=1, fill=0)
        if i < len(xs) - 1:
            canv.line(x + 9, y, xs[i + 1] - 9, y)
    canv.setFillColor(colors.HexColor("#9cc9dd"))
    canv.setFont("Sans", 7.5)
    for x, label in zip(xs, ["SOURCE", "INGEST", "LAKE", "TRANSFORM", "WAREHOUSE", "SERVE"]):
        canv.drawCentredString(x, y - 22, label)
    canv.restoreState()


def draw_chrome(canv, doc):
    canv.saveState()
    canv.setStrokeColor(RULE)
    canv.setLineWidth(0.6)
    top = PAGE_H - MARGIN + 2 * mm
    canv.line(MARGIN, top, PAGE_W - MARGIN, top)
    canv.setFont("Sans", 7.2)
    canv.setFillColor(MUTED)
    canv.drawString(MARGIN, top + 4, "Control-M Admin → Data Engineer  ·  Study Guide")
    canv.drawRightString(PAGE_W - MARGIN, top + 4, doc.chapter[:70])
    canv.line(MARGIN, MARGIN - 6 * mm, PAGE_W - MARGIN, MARGIN - 6 * mm)
    canv.drawCentredString(PAGE_W / 2, MARGIN - 10.5 * mm, str(doc.page))
    canv.restoreState()


# --------------------------------------------------------------------------- blocks
def toc_para(text, style, level):
    p = Paragraph(text, style)
    p._toc = (level, p.getPlainText())
    return p


def highlight(code: str, lang: str) -> list[str]:
    """Return one ReportLab-markup string per source line."""
    try:
        lexer = get_lexer_by_name(lang, stripnl=False)
    except Exception:
        lexer = get_lexer_by_name("text")
    lines, cur = [], []
    for ttype, value in lex(code, lexer):
        color, italic = None, False
        for base, hexcol, it in TOKEN_COLORS:
            if ttype in base:
                color, italic = hexcol, it
                break
        for i, piece in enumerate(value.split("\n")):
            if i:
                lines.append("".join(cur))
                cur = []
            text = escape(piece)
            if color and piece.strip():
                if italic:
                    text = f"<i>{text}</i>"
                text = f'<font color="{color}">{text}</font>'
            cur.append(text)
    lines.append("".join(cur))
    while lines and not lines[-1].strip():
        lines.pop()
    return lines


def code_block(lang: str, code: str, title: str | None = None):
    code = code.strip("\n")
    for ln in code.splitlines():
        if len(ln) > 96:
            print(f"warning: long code line ({len(ln)}): {ln[:60]}...", file=sys.stderr)
    label = (title + "  \u00b7  " if title else "") + lang.upper()
    rows = [[Paragraph(label, S["codelabel"])]]
    for ln in highlight(code, lang):
        rows.append([XPreformatted(ln if ln.strip() else "\u00a0", S["code"])])
    last = len(rows) - 1
    t = Table(rows, colWidths=[CONTENT_W], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CODE_BG),
        ("BOX", (0, 0), (-1, -1), 0.6, CODE_BORDER),
        ("LINEBEFORE", (0, 0), (0, -1), 3, ACCENT),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, 0), 5),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 3),
        ("BOTTOMPADDING", (0, last), (-1, last), 6),
    ]))
    return [CondPageBreak(min(110, 16 + 10.4 * (len(rows) - 1))), t, Spacer(1, 8)]


def callout(kind: str, text, title: str | None = None):
    label, fill, bar = CALLOUTS[kind]
    head = label + (f"  ·  {title}" if title else "")
    ts = ParagraphStyle("ct", parent=S["callouttitle"], textColor=bar)
    paras = [Paragraph(head, ts)]
    items = text if isinstance(text, list) else [text]
    for item in items:
        if item.startswith("- "):
            paras.append(Paragraph(item[2:], S["callout"], bulletText="•"))
        else:
            paras.append(Paragraph(item, S["callout"]))
    t = Table([[paras]], colWidths=[CONTENT_W])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), fill),
        ("LINEBEFORE", (0, 0), (0, -1), 3.5, bar),
        ("LEFTPADDING", (0, 0), (-1, -1), 11),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return [t, Spacer(1, 9)]


def table(rows, widths=None, head=True):
    n = len(rows[0])
    widths = widths or [1] * n
    total = sum(widths)
    col_w = [CONTENT_W * w / total for w in widths]
    data = []
    for r, row in enumerate(rows):
        style = S["cellhead"] if head and r == 0 else S["cell"]
        data.append([Paragraph(str(c), style) for c in row])
    t = Table(data, colWidths=col_w, repeatRows=1 if head else 0)
    cmds = [
        ("GRID", (0, 0), (-1, -1), 0.4, RULE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if head:
        cmds.append(("BACKGROUND", (0, 0), (-1, 0), ACCENT_DARK))
    for r in range(1 if head else 0, len(rows)):
        if r % 2 == 0:
            cmds.append(("BACKGROUND", (0, r), (-1, r), colors.HexColor("#f5f8fa")))
    t.setStyle(TableStyle(cmds))
    return [t, Spacer(1, 9)]


class CardCounter:
    n = 0


def flashcards(deck: str, cards):
    out = [Spacer(1, 2)]
    banner = Table([[Paragraph(
        f"✦  FLASHCARDS · {deck}  "
        f"<font color='#9cc9dd' size='7'>cover the right column, answer aloud, then reveal</font>",
        ParagraphStyle("fb", parent=S["cellhead"], fontSize=8.6))]],
        colWidths=[CONTENT_W])
    banner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), ACCENT),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 4.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
    ]))
    first = True
    for q, a in cards:
        CardCounter.n += 1
        front = [Paragraph(f"CARD {CardCounter.n:03d} · FRONT", S["cardtag"]),
                 Spacer(1, 2), Paragraph(q, S["cardq"])]
        back = [Paragraph("BACK", S["cardtag"]), Spacer(1, 2)]
        for part in (a if isinstance(a, list) else [a]):
            if part.startswith("- "):
                back.append(Paragraph(part[2:], S["carda"], bulletText="•"))
            else:
                back.append(Paragraph(part, S["carda"]))
        t = Table([[front, back]], colWidths=[CONTENT_W * 0.40, CONTENT_W * 0.60])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), CARD_FRONT),
            ("BACKGROUND", (1, 0), (1, 0), CARD_BACK),
            ("BOX", (0, 0), (-1, -1), 0.8, CARD_EDGE),
            ("LINEAFTER", (0, 0), (0, 0), 0.8, CARD_EDGE, None, (3, 2)),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]))
        if first:
            out.append(KeepTogether([banner, Spacer(1, 4), t]))
            first = False
        else:
            out.append(t)
        out.append(Spacer(1, 4))
    out.append(Spacer(1, 8))
    return out


def flow_diagram(steps, under=None):
    """A left-to-right box diagram, e.g. sources -> ingest -> lake ..."""
    n = len(steps)
    gap = 12
    box_w = (CONTENT_W - gap * (n - 1)) / n
    cells, widths = [], []
    for i, (title, sub) in enumerate(steps):
        cells.append([Paragraph(f"<b>{title}</b>", ParagraphStyle(
            "fd", parent=S["cell"], alignment=TA_CENTER, textColor=colors.white, fontSize=8.2)),
            Paragraph(sub, ParagraphStyle("fds", parent=S["cell"], alignment=TA_CENTER,
                                          textColor=colors.HexColor("#d7ebf4"), fontSize=6.9,
                                          leading=8.8))])
        widths.append(box_w)
        if i < n - 1:
            cells.append(Paragraph("▶", ParagraphStyle(
                "arr", parent=S["cell"], alignment=TA_CENTER, textColor=ACCENT)))
            widths.append(gap)
    t = Table([cells], colWidths=widths)
    cmds = [("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]
    for i in range(0, len(cells), 2):
        cmds.append(("BACKGROUND", (i, 0), (i, 0), ACCENT_DARK))
    for i in range(1, len(cells), 2):
        cmds += [("LEFTPADDING", (i, 0), (i, 0), 0), ("RIGHTPADDING", (i, 0), (i, 0), 0)]
    t.setStyle(TableStyle(cmds))
    out = [t]
    if under:
        bar = Table([[Paragraph(under, ParagraphStyle(
            "under", parent=S["cell"], alignment=TA_CENTER, textColor=INK, fontSize=7.6))]],
            colWidths=[CONTENT_W])
        bar.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fff6e0")),
                                 ("LINEABOVE", (0, 0), (-1, 0), 2, colors.HexColor("#d69e00")),
                                 ("TOPPADDING", (0, 0), (-1, -1), 4),
                                 ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
        out += [Spacer(1, 4), bar]
    return [KeepTogether(out), Spacer(1, 10)]


# --------------------------------------------------------------------------- assemble
def cover():
    white = ParagraphStyle("cw", fontName="Serif-Bold", fontSize=34, leading=40,
                           textColor=colors.white, alignment=TA_LEFT)
    sub = ParagraphStyle("cs", fontName="Sans", fontSize=13, leading=19,
                         textColor=colors.HexColor("#cfe6f1"))
    small = ParagraphStyle("csm", fontName="Sans", fontSize=9.5, leading=14,
                           textColor=colors.HexColor("#9cc9dd"))
    tag = ParagraphStyle("ctag", fontName="Sans-Bold", fontSize=9, leading=12,
                         textColor=colors.HexColor("#ffcf5c"))
    return [
        Spacer(1, 62 * mm),
        Paragraph("CAREER TRANSITION STUDY GUIDE", tag),
        Spacer(1, 6),
        Paragraph(content.TITLE, white),
        Spacer(1, 10),
        Paragraph(content.SUBTITLE, sub),
        Spacer(1, 70 * mm),
        Paragraph(content.COVER_BLURB, small),
        NextPageTemplate("body"),
        PageBreak(),
    ]


def render(blocks):
    story = []
    chapter_no = 0
    for b in blocks:
        kind = b[0]
        if kind == "chapter":
            chapter_no += 1
            _, title, lede = b
            while story and isinstance(story[-1], Spacer):
                story.pop()                     # a stray spacer must not spill onto a blank page
            story += [PageBreakIfNotEmpty()] if chapter_no > 1 else []
            label = "APPENDIX" if title.startswith("Appendix") else f"CHAPTER {chapter_no}"
            story.append(Paragraph(label, S["h1num"]))
            story.append(toc_para(title, S["h1"], 0))
            story.append(Table([[""]], colWidths=[40], rowHeights=[3],
                               style=[("BACKGROUND", (0, 0), (-1, -1), ACCENT)], hAlign="LEFT"))
            story.append(Spacer(1, 8))
            if lede:
                story.append(Paragraph(lede, S["lede"]))
        elif kind == "h2":
            story.append(CondPageBreak(90))
            story.append(toc_para(b[1], S["h2"], 1))
        elif kind == "h3":
            story.append(CondPageBreak(45))
            story.append(Paragraph(b[1], S["h3"]))
        elif kind == "p":
            story.append(Paragraph(b[1], S["body"]))
        elif kind == "ul":
            for item in b[1]:
                story.append(Paragraph(item, S["bullet"], bulletText="•"))
            story.append(Spacer(1, 5))
        elif kind == "ol":
            for i, item in enumerate(b[1], 1):
                story.append(Paragraph(item, S["bullet"], bulletText=f"{i}."))
            story.append(Spacer(1, 5))
        elif kind == "code":
            story += code_block(*b[1:])
        elif kind == "callout":
            story += callout(*b[1:])
        elif kind == "table":
            story += table(*b[1:])
        elif kind == "cards":
            story += flashcards(b[1], b[2])
        elif kind == "flow":
            story += flow_diagram(*b[1:])
        elif kind == "space":
            story.append(Spacer(1, b[1]))
        elif kind == "pagebreak":
            story.append(PageBreak())
        else:
            raise ValueError(f"unknown block {kind}")
    return story


def build():
    toc = TableOfContents()
    toc.levelStyles = [S["toc1"], S["toc2"]]
    toc.dotsMinLevel = 0
    story = cover()
    story += [Paragraph("Contents", S["h1"]), Spacer(1, 8), toc, PageBreak()]
    story += render(content.BLOCKS)
    doc = GuideDoc(str(OUT))
    doc.multiBuild(story)
    print(f"wrote {OUT} ({doc.page} pages, {CardCounter.n} flashcards)")


if __name__ == "__main__":
    build()
