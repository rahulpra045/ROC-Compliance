"""Low-level helpers for editing .docx text without losing run formatting."""
import copy
import re
from docx.text.run import Run
from docx.text.paragraph import Paragraph
from docx.table import Table
from docx.oxml.ns import qn

TOKEN_RE = re.compile(r"\{\{(\w+)\}\}")
SUP_RE = re.compile(r"<(sup|b)>(.*?)</\1>")


def parse_markup(value):
    """'30<sup>th</sup> Day' -> [('30', False), ('th', True), (' Day', False)]"""
    out, pos = [], 0
    for m in SUP_RE.finditer(value):
        if m.start() > pos:
            out.append((value[pos:m.start()], False))
        out.append((m.group(2), True if m.group(1) == "sup" else "b"))
        pos = m.end()
    if pos < len(value):
        out.append((value[pos:], False))
    return out or [("", False)]


def iter_tables_recursive(container):
    for t in container.tables:
        yield t
        for row in t.rows:
            seen = set()
            for c in row.cells:
                if id(c._tc) in seen:
                    continue
                seen.add(id(c._tc))
                yield from iter_tables_recursive(c)


def iter_paragraphs(doc):
    """All paragraphs in the body, including those inside tables."""
    for p in doc.paragraphs:
        yield p
    for t in iter_tables_recursive(doc):
        for row in t.rows:
            seen = set()
            for c in row.cells:
                if id(c._tc) in seen:
                    continue
                seen.add(id(c._tc))
                for p in c.paragraphs:
                    yield p


def para_text(p):
    return "".join(r.text for r in p.runs)


def _clone_run_after(run, text, sup=None):
    new_r = copy.deepcopy(run._r)
    for ch in list(new_r):
        if ch.tag != qn("w:rPr"):
            new_r.remove(ch)
    run._r.addnext(new_r)
    nr = Run(new_r, run._parent)
    nr.text = text
    if sup == "b":
        nr.font.bold = True
        for va in new_r.get_or_add_rPr().findall(qn("w:vertAlign")):
            new_r.rPr.remove(va)
    elif sup is not None:
        nr.font.superscript = True if sup else None
        if not sup:
            # explicit reset so a superscript source run does not leak
            rpr = new_r.get_or_add_rPr()
            for va in rpr.findall(qn("w:vertAlign")):
                rpr.remove(va)
    return nr


def replace_span(p, start, end, value):
    """Replace characters [start,end) of the paragraph's run text with value (supports <sup>)."""
    runs = p.runs
    pos = 0
    spans = []
    for r in runs:
        t = r.text
        spans.append((r, pos, pos + len(t)))
        pos += len(t)
    s_i = e_i = None
    for i, (r, rs, re_) in enumerate(spans):
        if s_i is None and rs <= start < re_:
            s_i = i
        if rs < end <= re_:
            e_i = i
    if s_i is None or e_i is None:
        return False
    s_run, s_rs, _ = spans[s_i]
    e_run, e_rs, e_re = spans[e_i]
    before = s_run.text[: start - s_rs]
    after = e_run.text[end - e_rs:]
    for i in range(s_i + 1, e_i):
        spans[i][0].text = ""
    if s_i != e_i:
        e_run.text = after
    pieces = parse_markup(value)
    # first piece goes in the start run when it's plain text
    if not pieces[0][1]:
        s_run.text = before + pieces[0][0]
        rest = pieces[1:]
    else:
        s_run.text = before
        rest = pieces
    cur = s_run
    for txt, sup in rest:
        cur = _clone_run_after(cur, txt, sup)
    if s_i == e_i and after:
        _clone_run_after(cur, after, False if any(s for _, s in pieces) else None)
    return True


def sub_in_paragraph(p, pattern, repl):
    """regex-substitute inside a paragraph across run boundaries. repl: str or callable(match)->str"""
    text = para_text(p)
    rx = pattern if hasattr(pattern, "finditer") else re.compile(pattern)
    ms = list(rx.finditer(text))
    n = 0
    for m in reversed(ms):
        val = repl(m) if callable(repl) else m.expand(repl)
        if replace_span(p, m.start(), m.end(), val):
            n += 1
    return n


def set_paragraph_text(p, value):
    """Replace the entire text of a paragraph, keeping the first run's formatting."""
    text = para_text(p)
    if not p.runs:
        r = p.add_run("")
    if text == "":
        p.runs[0].text = ""
        text = ""
        replace_span_empty(p, value)
        return
    replace_span(p, 0, len(text), value)


def replace_span_empty(p, value):
    r = p.runs[0]
    pieces = parse_markup(value)
    r.text = pieces[0][0] if not pieces[0][1] else ""
    cur = r
    for txt, sup in (pieces[1:] if not pieces[0][1] else pieces):
        cur = _clone_run_after(cur, txt, sup)


def set_cell_text(cell, value, proto_run=None):
    """Set the text of a cell. Leading empty paragraphs (spacing) are kept; the first paragraph that holds
    text receives the value and anything after it is removed. value may contain <sup>/<b>."""
    paras = cell.paragraphs
    idx = next((i for i, q in enumerate(paras) if q.runs and para_text(q).strip()), 0)
    for extra in paras[idx + 1:]:
        extra._p.getparent().remove(extra._p)
    p = paras[idx]
    if not p.runs:
        r = p.add_run("")
        src = proto_run._r.rPr if (proto_run is not None and proto_run._r.rPr is not None) else None
        if src is None:  # empty cell: inherit the paragraph-mark formatting (e.g. bold totals)
            ppr = p._p.pPr
            src = ppr.find(qn("w:rPr")) if ppr is not None else None
        if src is not None:
            new = copy.deepcopy(src); new.tag = qn("w:rPr")
            r._r.insert(0, new)
    # drop all but first run
    for r in p.runs[1:]:
        r._r.getparent().remove(r._r)
    replace_span_empty(p, value)


def set_cell_lines(cell, lines):
    """Set a cell to several paragraphs (one per line), cloning the first paragraph's format."""
    lines = list(lines) or [""]
    set_cell_text(cell, lines[0])
    first = cell.paragraphs[0]
    prev = first
    for ln in lines[1:]:
        newp = copy.deepcopy(first._p)
        prev._p.addnext(newp)
        np_ = Paragraph(newp, first._parent)
        for r in np_.runs[1:]:
            r._r.getparent().remove(r._r)
        replace_span_empty(np_, ln)
        prev = np_


def find_table(doc, *needles, nth=0):
    """Find a table whose first rows' text contains all needles (case-insensitive)."""
    hits = []
    for t in iter_tables_recursive(doc):
        head = " ".join(c.text for r in t.rows[:2] for c in r.cells).lower()
        if all(n.lower() in head for n in needles):
            hits.append(t)
    return hits[nth] if len(hits) > nth else None


def unique_cells(row):
    seen, out = set(), []
    for c in row.cells:
        if id(c._tc) in seen:
            continue
        seen.add(id(c._tc))
        out.append(c)
    return out


def clone_row_after(table, src_row, after_row=None):
    new_tr = copy.deepcopy(src_row._tr)
    (after_row or src_row)._tr.addnext(new_tr)
    from docx.table import _Row
    return _Row(new_tr, table)


def delete_row(row):
    row._tr.getparent().remove(row._tr)


def fill_row(row, values):
    """values: list aligned to unique cells; str or list(lines) per cell; None = leave."""
    cells = unique_cells(row)
    for c, v in zip(cells, values):
        if v is None:
            continue
        if isinstance(v, (list, tuple)):
            set_cell_lines(c, v)
        else:
            set_cell_text(c, v)


def rebuild_rows(table, proto_idx, rows_values, drop_after=None):
    """Use row[proto_idx] as prototype; produce len(rows_values) rows; delete the prototype's following rows up to drop_after (exclusive end idx)."""
    rows = list(table.rows)
    proto = rows[proto_idx]
    stop = drop_after if drop_after is not None else len(rows)
    for r in rows[proto_idx + 1: stop]:
        delete_row(r)
    if not rows_values:
        return
    last = proto
    created = []
    for _ in rows_values[1:]:
        last = clone_row_after(table, proto, last)
        created.append(last)
    for row, vals in zip([proto] + created, rows_values):
        fill_row(row, vals)
