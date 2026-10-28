"""table_helpers.py

Style and common utilities of the results tables of the manuscript (Tables 3 and 4):
three lines of the MDPI template, black type, no fill, Palatino Linotype, numbered
superscript footnotes. Used by 07_tab03_v1.py and 08_tab04_v1.py, so that both tables
come out identical in format to Tables 1 and 2.
"""
import hashlib, os, re, textwrap

import xlsxwriter

FONT = "Palatino Linotype"
EN = chr(8211)   # en dash of an interval; in the source it is written as an escape so as not to leave ASCII
DASH = chr(8212)  # em dash: cell without applicable datum
TAU2 = "*" + chr(964) + "*" + chr(178)   # tau squared: letter in italics, exponent in roman
I2 = "*I*" + chr(178)                    # I squared, with the I in italics

OUTCOME = {"NWT": "Non-wild-type by epidemiological cut-off value",
           "R": "Resistant by clinical breakpoint"}
CRITERION = {"ECV_CLSI": "CLSI ECV", "ECV_EUCAST": "EUCAST ECV",
             "CLSI_SS": "CLSI, species-specific", "CLSI_pre2012": "CLSI, pre-2012",
             "EUCAST": "EUCAST",
             "CLSI_SS+EUCAST": "CLSI species-specific or EUCAST"}
NOT_POOLED = {"not_pooled_boundary_AR18a": "6", "not_pooled_tau2_AR18b": "7",
              "not_pooled_no_profile_AR18c": "7", "below_minimum": "8"}


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def lines(text, width, chars=1.25):
    """Lines that a text takes in a column of that width; only for the row height."""
    return max(1, len(textwrap.wrap(text, max(4, int(width * chars)))))


def miss(v):
    """The datum is missing. R writes empty values as NA, so they come in as text."""
    if v is None or (isinstance(v, float) and v != v):
        return True
    return isinstance(v, str) and v.strip() in ("", "NA", "NaN", "NULL")


MARKUP = re.compile(r"\*([^*]+)\*")


def as_parts(x):
    """Pieces of a text. A string admits *italics* between asterisks; a list also admits
    the piece ("i", text). The variables of the manuscript always go in italics."""
    if not isinstance(x, str):
        return list(x)
    out, i = [], 0
    for m in MARKUP.finditer(x):
        if m.start() > i:
            out.append(x[i:m.start()])
        out.append(("i", m.group(1)))
        i = m.end()
    if i < len(x):
        out.append(x[i:])
    return out or [x]


def plain(x):
    """The same text without marks: for the CSV mirror and to compute the row height."""
    return "".join(p[1] if isinstance(p, tuple) else p for p in as_parts(x))


def pct(p, d=1):
    return DASH if miss(p) else f"{100 * float(p):.{d}f}"


def pct_ci(p, lo, hi, d=1):
    if miss(p):
        return DASH
    if miss(lo) or miss(hi):
        return pct(p, d)
    return f"{pct(p, d)} ({pct(lo, d)}{EN}{pct(hi, d)})"


def pct_range(lo, hi, d=1):
    return DASH if miss(lo) or miss(hi) else f"{pct(lo, d)}{EN}{pct(hi, d)}"


def tau_ci(t, lo, hi):
    if miss(t):
        return DASH
    s = f"{float(t):.2f}"
    if miss(lo) or miss(hi):
        return s
    return f"{s} ({float(lo):.2f}{EN}{float(hi):.2f})"


def write_table(path, sheet, number, caption, headers, widths, blocks, footnotes):
    """Writes a table in the MDPI style.

    caption, headers and footnotes: text with *italics* between asterisks, or a list of pieces
            where ("i", text) goes in italics: the species name and the variables.
    blocks: list of (group label or None, rows); each row is a list of cells, and a
            cell is a text or a tuple (text, footnote number).
    footnotes: list of (number, text).
    """
    wb = xlsxwriter.Workbook(path)
    ws = wb.add_worksheet(sheet)
    base = {"font_name": FONT, "font_color": "black", "text_wrap": True, "valign": "top"}

    def fmt(**k):
        return wb.add_format({**base, **k})

    cap, cap_b, cap_i = fmt(font_size=9), fmt(font_size=9, bold=True), fmt(font_size=9, italic=True)
    head = fmt(font_size=10, bold=True, top=2, bottom=1)
    head_i = fmt(font_size=10, bold=True, italic=True, top=2, bottom=1)
    grp = fmt(font_size=10, italic=True)
    txt, sup = fmt(font_size=10), fmt(font_size=10, font_script=1)
    last = fmt(font_size=10, bottom=2)
    last_sup = fmt(font_size=10, font_script=1, bottom=2)
    note, note_sup = fmt(font_size=9), fmt(font_size=9, font_script=1)
    note_i = fmt(font_size=9, italic=True)
    ncol = len(headers)
    for j, w in enumerate(widths):
        ws.set_column(j, j, w)
    total = sum(widths)

    def rich_of(x, f_plain, f_ital):
        out = []
        for part in as_parts(x):
            out += [f_ital, part[1]] if isinstance(part, tuple) else [f_plain, part]
        return out

    ws.merge_range(0, 0, 0, ncol - 1, "", cap)
    ws.write_rich_string(0, 0, cap_b, f"Table {number}. ", *rich_of(caption, cap, cap_i), cap)
    ws.set_row(0, 13 * lines(f"Table {number}. " + plain(caption), total, 1.4))
    for j, h in enumerate(headers):
        frags = rich_of(h, head, head_i)
        if len(frags) == 2:
            ws.write(1, j, frags[1], head)
        else:
            ws.write_rich_string(1, j, *frags, head)
    ws.set_row(1, 14 * max(lines(plain(h), w) for h, w in zip(headers, widths)) + 2)

    body = [(lab, r) for lab, rows in blocks for r in ([None] + rows if lab else rows)]
    n_body = len(body)
    row = 2
    for i, (lab, cells) in enumerate(body):
        is_last = i == n_body - 1
        cell_f, sup_f = (last, last_sup) if is_last else (txt, sup)
        if cells is None:
            ws.merge_range(row, 0, row, ncol - 1, "", grp)
            ws.write(row, 0, lab, grp)
            ws.set_row(row, 15)
        else:
            need = 1
            for j, c in enumerate(cells):
                text, n = c if isinstance(c, tuple) else (c, None)
                if n:
                    ws.write_rich_string(row, j, cell_f, text, sup_f, n, cell_f)
                else:
                    ws.write(row, j, text, cell_f)
                need = max(need, lines(text, widths[j]))
            ws.set_row(row, 14 * need + 2)
        row += 1
    for n, text in footnotes:
        ws.merge_range(row, 0, row, ncol - 1, "", note)
        frags = rich_of(text, note, note_i)
        frags[1] = " " + frags[1]
        ws.write_rich_string(row, 0, note_sup, n, *frags, note)
        ws.set_row(row, 13 * lines(plain(text), total, 1.4))
        row += 1
    ws.hide_gridlines(2)
    ws.set_landscape()
    ws.fit_to_pages(1, 0)
    wb.close()
    return row
