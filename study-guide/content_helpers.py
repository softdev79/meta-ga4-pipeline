"""Tiny DSL used by the content modules. Each helper returns one block tuple."""

from xml.sax.saxutils import escape


def c(text: str) -> str:
    """Inline code span."""
    return f'<font face="Mono" size="8.6" color="#9a3412">{escape(text)}</font>'


def ch(title, lede=""):
    return ("chapter", title, lede)


def h2(text):
    return ("h2", text)


def h3(text):
    return ("h3", text)


def p(text):
    return ("p", text)


def ul(*items):
    return ("ul", list(items))


def ol(*items):
    return ("ol", list(items))


def code(lang, src, title=None):
    return ("code", lang, src, title)


def co(kind, text, title=None):
    return ("callout", kind, text, title)


def tbl(rows, widths=None):
    return ("table", rows, widths)


def cards(deck, items):
    return ("cards", deck, items)


def flow(steps, under=None):
    return ("flow", steps, under)


def space(n=8):
    return ("space", n)
