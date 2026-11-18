"""Editable default text.

Overrides are kept in <db folder>/_text_overrides.json:
    {"version": 1,
     "global":  {doc_id: {pid: text}},
     "company": {company_id: {doc_id: {pid: text}}}}
pid  = "p<index>:<hash>"  -> a body paragraph of the template (hash of the original text guards against template changes)
       "tok:P_xxx"        -> the standard sentence behind a whole-paragraph token (Yes/No statements)
Company overrides win over global ones, global over the built-in text.
"""
import difflib, hashlib, json, os, re

import docx

from docx_core import para_text, replace_span, set_paragraph_text
from paths import RES

DB_GETTER = lambda: None          # set by app.py: returns the current db folder
FILE = "_text_overrides.json"

DOC_FILES = {"notice": "notice_director_report_template.docx", "directors": "directors.docx", "shareholders": "shareholders.docx",
             "dsc": "dsc.docx", "index": "index.docx", "policies": "policies.docx", "mrl": "mrl.docx"}
COMMON_TOKENS = ["company", "company_upper", "cin", "address", "email", "phones", "sign_place", "sign_date"]
PLACEHOLDERS = ["fy", "fy_end_ord", "fy_end_dmy", "company", "company_upper", "agm_year"]
TOKEN_RE = re.compile(r"\{\{(\w+)\}\}")
SINGLE_RE = re.compile(r"(?<!\{)\{(\w+)\}(?!\})")


def slug(s):
    return re.sub(r"[^A-Za-z0-9]+", "_", (s or "").strip()).strip("_") or "company"


def path():
    d = DB_GETTER()
    return os.path.join(d, FILE) if d else None


def load_all():
    p = path()
    try:
        return json.load(open(p, encoding="utf-8")) if p and os.path.exists(p) else {}
    except Exception:
        return {}


def template_path(mid):
    return os.path.join(RES, "template", DOC_FILES[mid])


def pid_for(i, text):
    return f"p{i}:{hashlib.md5(text.encode('utf-8')).hexdigest()[:6]}"


def effective(mid, cid=None, data=None):
    """pid -> (text, source)"""
    data = data if data is not None else load_all()
    out = {}
    for pid, t in ((data.get("global") or {}).get(mid) or {}).items():
        out[pid] = (t, "global")
    if cid:
        for pid, t in (((data.get("company") or {}).get(cid) or {}).get(mid) or {}).items():
            out[pid] = (t, "company")
    return out


# ---------------------------------------------------------------- locked paragraphs (found by the code by their text)
def _norm(s):
    return re.sub(r"\s+", " ", s).strip()


def locked_reason(mid, text):
    t = _norm(text)
    if "{{sig_" in text:
        return "Signature block – built from your directors"
    if mid == "index":
        from schema import INDEX_ATTACHMENTS
        if t == "Attachments" or any(t.startswith(pref) for _, pref in INDEX_ATTACHMENTS):
            return "Attachment list – use the tick-list on the Financials Index tab"
    if mid == "policies" and (t.replace(" ", "").startswith("CurrentYear") or t.startswith("Value (")):
        return "Table heading – built automatically"
    if t in ("Details of Loans", "Details of Investments", "Details of Guarantee / Security Provided"):
        return "Table title"
    return None


# ---------------------------------------------------------------- applying
def _toks(s):
    return re.findall(r"\s+|\w+|[^\w\s]", s)


def apply_text(p, new):
    old = para_text(p)
    if new == old:
        return
    if "<b>" in new or "<sup>" in new or not p.runs or not old:
        set_paragraph_text(p, new)
        return
    a, b = _toks(old), _toks(new)
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    offs_a = [0]
    for x in a: offs_a.append(offs_a[-1] + len(x))
    offs_b = [0]
    for x in b: offs_b.append(offs_b[-1] + len(x))
    ops = [(offs_a[i1], offs_a[i2], new[offs_b[j1]:offs_b[j2]]) for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag != "equal"]
    for s, e, rep in reversed(ops):
        if s == e:                                   # pure insertion: attach to a neighbouring character
            ok = replace_span(p, s - 1, s, old[s - 1] + rep) if s > 0 else replace_span(p, 0, 1, rep + old[0])
        else:
            ok = replace_span(p, s, e, rep)
        if not ok:
            set_paragraph_text(p, new)
            return


def apply(doc, mid, form):
    """Apply saved paragraph edits to a freshly loaded template (before values are filled in)."""
    cid = slug((form or {}).get("company"))
    eff = effective(mid, cid)
    if not eff:
        return
    for i, p in enumerate(doc.paragraphs):
        t = para_text(p)
        if not t.strip():
            continue
        hit = eff.get(pid_for(i, t))
        if hit is not None and not locked_reason(mid, t):
            apply_text(p, hit[0])


def dflt(mid, token, default, form):
    """Standard sentence behind a whole-paragraph token: saved edit or the built-in default."""
    hit = effective(mid, slug((form or {}).get("company"))).get("tok:" + token)
    return hit[0] if hit else default


# ---------------------------------------------------------------- outline for the editor
def _std_tables():
    from schema import PARA_TOGGLES, MRL_TOGGLES
    return {"notice": {t["token"]: t for t in PARA_TOGGLES}, "mrl": {t["token"]: t for t in MRL_TOGGLES}}


def template_tokens(mid):
    d = docx.Document(template_path(mid))
    found = set()
    from docx_core import iter_paragraphs
    for p in iter_paragraphs(d):
        found.update(TOKEN_RE.findall(para_text(p)))
    return found


def allowed_tokens(mid):
    return sorted({t for t in template_tokens(mid) if not t.startswith("P_") and not t.startswith("sig_")} | set(COMMON_TOKENS))


def outline(mid, cid=None):
    data = load_all()
    eff = effective(mid, cid, data)
    base = effective(mid, None, data)          # what the text would be without a company override
    d = docx.Document(template_path(mid))
    std = _std_tables().get(mid, {})
    items = []
    body = d.element.body
    pi = -1
    from docx.text.paragraph import Paragraph
    from docx.table import Table
    for child in body.iterchildren():
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            pi += 1
            p = Paragraph(child, d)
            t = para_text(p)
            if not t.strip():
                continue
            m = TOKEN_RE.fullmatch(t.strip())
            if m and m.group(1).startswith("P_"):
                tok = m.group(1)
                if tok in std:
                    s = std[tok]; key = "tok:" + tok
                    items.append(dict(pid=key, kind="std", label=s["label"], orig=s["default"], text=eff.get(key, (s["default"], "original"))[0],
                                      source=eff.get(key, (None, "original"))[1], base=base.get(key, (s["default"], "original"))[0]))
                else:
                    items.append(dict(pid="auto:" + tok, kind="computed", label="Automatic text", orig="", text="", source="original",
                                      note="This paragraph is built from the figures / details you enter, so it is not edited here."))
                continue
            pid = pid_for(pi, t)
            lock = locked_reason(mid, t)
            runs = [r for r in p.runs if r.text.strip()]
            bold = bool(runs) and all(bool(r.bold) for r in runs)
            if lock:
                items.append(dict(pid=pid, kind="locked", orig=t, text=t, source="original", note=lock, bold=bold))
            else:
                items.append(dict(pid=pid, kind="para", orig=t, text=eff.get(pid, (t, "original"))[0], source=eff.get(pid, (None, "original"))[1],
                                  base=base.get(pid, (t, "original"))[0], bold=bold))
        elif tag == "tbl":
            tb = Table(child, d)
            first = " | ".join(_norm(c.text) for c in tb.rows[0].cells if _norm(c.text))[:110] if tb.rows else ""
            items.append(dict(pid="tbl", kind="table", orig=first, text=first, source="original",
                              note="Table – layout and headings are built by the program"))
    return items


# ---------------------------------------------------------------- validation
def validate(mid, pid, text):
    """returns an error string or None"""
    if pid.startswith("tok:"):
        bad = [x for x in SINGLE_RE.findall(text) if x not in PLACEHOLDERS]
        if bad:
            return "Unknown field {" + bad[0] + "}. Allowed: " + ", ".join("{" + x + "}" for x in PLACEHOLDERS)
        if "{{" in text:
            return "Use single braces like {fy} in standard statements."
        return None
    if text.count("{{") != len(TOKEN_RE.findall(text)) or text.count("}}") != len(TOKEN_RE.findall(text)):
        return "A {{field}} is broken – every {{ must be closed with }}."
    ok = set(allowed_tokens(mid))
    for tok in TOKEN_RE.findall(text):
        if tok not in ok:
            return "Unknown field {{" + tok + "}} for this document."
    return None
