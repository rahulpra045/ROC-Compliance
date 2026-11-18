"""The seven document modules. Each takes the shared form (common details + module extras) and returns .docx bytes."""
import copy, io, os, re
from datetime import date
from decimal import Decimal

import docx
from docx.shared import Pt
from docx.oxml.ns import qn

import engine
import texts
from engine import align_place_date
from engine import num, inr, inr_or_dash, dmy, pdate, render, directors_on, fill_tokens, finish_layout, part_signatures
from docx_core import *
from paths import RES
from schema import MODULES, UNITS, MRL_TOGGLES, INDEX_ATTACHMENTS


def load_tpl(mid, f):
    """open a template and apply the user's saved text edits"""
    doc = docx.Document(tpl(mid))
    texts.apply(doc, mid, f)
    return doc


def tpl(mid):
    return os.path.join(RES, "template", f"{mid}.docx")


def migrate(f):
    """Bring an older saved form up to the current structure."""
    f.setdefault("ca", {})
    aud = f.get("auditor") or {}
    for k_new, k_old in (("firm", "firm"), ("city", "city"), ("frn", "frn")):
        if not f["ca"].get(k_new) and aud.get(k_old):
            f["ca"][k_new] = aud[k_old]
    f.setdefault("mods", {})
    for m in ("index", "mrl", "dsc", "policies"):
        f["mods"].setdefault(m, {})
    for k in ("business_desc", "revenue_desc", "books_address", "letter_date", "share_class", "fx_earn_prev", "fx_out_prev"):
        f.setdefault(k, "")
    for d in f.get("directors", []):
        d.setdefault("address", "")
    return f


def common_values(f):
    migrate(f)
    v = engine.build_values(f)
    fy = int(f.get("fy_end_year"))
    ca = f.get("ca") or {}
    v["ca_firm"] = ca.get("firm") or "____ & CO."
    v["ca_address"] = ca.get("address") or "____"
    v["ca_pin"] = ca.get("pincode") or "____"
    v["ca_state"] = ca.get("state") or "____"
    v["letter_date"] = dmy(f.get("letter_date")) or dmy(f.get("sign_date"))
    v["fy_end_upper"] = f"31<sup>ST</sup> MARCH, {fy}"
    v["fy_end_ord_nc"] = f"31<sup>st</sup> March {fy}"
    v["fy_end_slash"] = f"31/03/{fy}"
    v["m31_of"] = f"March 31<sup>st</sup> of {fy}"
    unit = UNITS.get(f.get("unit") or "hundreds", UNITS["hundreds"])
    v["unit_rs"] = unit["rs"]
    return v


def _finish(doc, f, v, signatures=True):
    if signatures:
        v.update(part_signatures(doc, f))
    fill_tokens(doc, v)
    align_place_date(doc)
    finish_layout(doc, fonts=False)  # keep each reference document's own fonts (page count stays as in the original)
    buf = io.BytesIO(); doc.save(buf)
    return buf.getvalue()


# ----------------------------------------------------------------------------- modules
def gen_directors(f):
    v = common_values(f)
    doc = load_tpl("directors", f)
    t = find_table(doc, "Name of Director")
    on = directors_on(f, date(int(f["fy_end_year"]), 3, 31))
    rows = [[str(i + 1), d.get("name", ""), d.get("address", ""), d.get("din", "")] for i, d in enumerate(on)]
    rebuild_rows(t, 1, rows or [["", "", "", ""]])
    return _finish(doc, f, v)


def gen_shareholders(f):
    v = common_values(f)
    doc = load_tpl("shareholders", f)
    t = find_table(doc, "Name of Shareholders")
    sh, tb, te = engine.analyse(f)
    cls = f.get("share_class") or "Equity"
    rows = [[str(i + 1), s.get("name", ""), cls, inr(s["_e"], 0) + "/-"] for i, s in enumerate([x for x in sh if x["_e"] > 0])]
    rebuild_rows(t, 1, rows or [["", "", "", ""]])
    return _finish(doc, f, v)


def gen_dsc(f):
    v = common_values(f)
    return _finish(load_tpl("dsc", f), f, v)


def gen_index(f):
    v = common_values(f)
    doc = load_tpl("index", f)
    mi = (f.get("mods") or {}).get("index") or {}
    att = mi.get("att") or {}
    norm = lambda s: re.sub(r"\s+", " ", s).strip()
    start = None
    paras = list(doc.paragraphs)
    for i, p in enumerate(paras):
        if norm(para_text(p)) == "Attachments":
            start = i
    last_kept = None
    if start is not None:
        for label, prefix in INDEX_ATTACHMENTS:
            for p in paras[start + 1:]:
                if norm(para_text(p)).startswith(prefix) and p._p.getparent() is not None:
                    if att.get(label, True) is False or att.get(label) == "false":
                        p._p.getparent().remove(p._p)
                    else:
                        last_kept = p
                    break
        extras = [x.strip() for x in (mi.get("extra") or []) if x and x.strip()]
        anchor = last_kept
        for text in extras:
            if anchor is None:
                break
            el = copy.deepcopy(anchor._p)
            anchor._p.addnext(el)
            from docx.text.paragraph import Paragraph
            np_ = Paragraph(el, anchor._parent)
            set_paragraph_text(np_, text)
            anchor = np_
    return _finish(doc, f, v, signatures=False)


def _fx(x):
    n = num(x)
    return (inr(n) + "/-") if n else "NIL"


def gen_policies(f):
    v = common_values(f)
    f["_cur"]  # computed by build_values
    mp = (f.get("mods") or {}).get("policies") or {}
    unit = UNITS.get(f.get("unit") or "hundreds", UNITS["hundreds"])
    v["business_desc"] = (f.get("business_desc") or "____").strip()
    v["revenue_desc"] = (f.get("revenue_desc") or f.get("business_desc") or "____").strip()
    v["books_address"] = (f.get("books_address") or f.get("address") or "").strip()
    dt = f["_cur"].get("dtax")
    if dt is None or dt == 0:
        v["dt_sentence"] = "deferred tax for the year of <b>Rs.NIL/-</b>"
    else:
        v["dt_sentence"] = f"deferred tax {'Liability' if dt > 0 else 'Asset'} for the year of <b>Rs.{inr(abs(dt))}/-{unit['p2']}</b>"
    doc = load_tpl("policies", f)
    t = doc.tables[0]
    rows = list(t.rows)
    fill_row(rows[0], [None, None, _fx(f.get("fx_out")), _fx(f.get("fx_out_prev"))])
    fill_row(rows[1], [None, None, _fx(f.get("fx_earn")), _fx(f.get("fx_earn_prev"))])
    # heading lines ("Current Year / Previous Year / Value (Rs.in ..)") were tab-aligned text and wrapped;
    # make them two proper header rows of the same table so they line up with the figures.
    for p in list(doc.paragraphs):
        tx = para_text(p)
        if tx.strip().startswith("2.7"):
            p.paragraph_format.space_after = Pt(8)
        if tx.strip().replace("\t", " ").split() == ["Current", "Year", "Previous", "Year"] or tx.strip().startswith("Value (Rs.in") or tx.strip().startswith("Value (") and "{{unit_rs}}" in tx:
            p._p.getparent().remove(p._p)
    h2 = clone_row_after(t, rows[0], after_row=None); t._tbl.remove(h2._tr); rows[0]._tr.addprevious(h2._tr)
    h1 = clone_row_after(t, rows[0], after_row=None); t._tbl.remove(h1._tr); h2._tr.addprevious(h1._tr)
    val = "Value (" + unit["rs"] + ")"
    fill_row(h1, [" ", " ", "Current Year", "Previous Year"]); fill_row(h2, [" ", " ", val, val])
    for r in (h1, h2):
        for c in unique_cells(r)[2:]:
            for run in c.paragraphs[0].runs: run.bold = True
    # light dotted frame around the whole block (header + 2.8 + 2.9)
    from docx.oxml import OxmlElement
    pr = t._tbl.tblPr; tb = pr.find(qn("w:tblBorders"))
    if tb is not None: pr.remove(tb)
    tb = OxmlElement("w:tblBorders")
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        b = OxmlElement("w:" + side)
        for k, v_ in (("val", "dotted"), ("sz", "6"), ("space", "0"), ("color", "404040")): b.set(qn("w:" + k), v_)
        tb.append(b)
    pr.find(qn("w:tblW")).addnext(tb)
    return _finish(doc, f, v, signatures=False)


def gen_mrl(f):
    v = common_values(f)
    mm = (f.get("mods") or {}).get("mrl") or {}
    money = lambda k: inr(num(mm.get(k)) or Decimal(0), 0)
    v["cash"], v["stock"], v["debtors"], v["creditors"] = money("cash"), money("stock"), money("debtors"), money("creditors")
    unit = UNITS.get(f.get("unit") or "hundreds", UNITS["hundreds"])
    rev = num(mm.get("revenue"))
    if rev is None:
        r0 = f["_cur"].get("rev")
        rev = (r0 * Decimal(unit["mult"])) if r0 is not None else Decimal(0)
    v["revenue_abs"] = inr(rev, 0)
    tg = mm.get("toggles") or {}
    for t in MRL_TOGGLES:
        st = tg.get(t["key"]) or {}
        text = (st.get("text") or "").strip() if st.get("on") else ""
        v[t["token"]] = text or texts.dflt("mrl", t["token"], t["default"], f)
    for t in MRL_TOGGLES:
        v[t["token"]] = render(v[t["token"]], v)
    return _finish(load_tpl("mrl", f), f, v)


def gen_notice(f, route_bytes=None):
    migrate(f)
    data, _ = engine.generate(f, route_bytes)
    return data


GENERATORS = {"directors": gen_directors, "shareholders": gen_shareholders, "dsc": gen_dsc,
              "index": gen_index, "policies": gen_policies, "mrl": gen_mrl}


def generate_module(mid, form, route_bytes=None):
    f = copy.deepcopy(form)
    if mid == "notice":
        return gen_notice(f, route_bytes)
    return GENERATORS[mid](f)
