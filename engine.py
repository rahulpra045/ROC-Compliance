"""Fills the template with a company's form data and returns the finished .docx bytes."""
import copy
import io
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

import docx
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph

from docx_core import *
from schema import PARA_TOGGLES, INLINE_TOGGLES, UNITS
import texts

import os as _os
from paths import RES
TEMPLATE = _os.path.join(RES, "template", "notice_director_report_template.docx")
D0 = Decimal(0)


# ----------------------------------------------------------------------------- helpers
def num(s):
    """'1,23,456.50' -> Decimal; blank/'-' -> None"""
    if s is None:
        return None
    s = str(s).replace(",", "").replace("/-", "").strip()
    if s in ("", "-", "NIL", "Nil", "NA"):
        return None
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def inr(x, dec=2):
    x = Decimal(x)
    neg = x < 0
    x = abs(x).quantize(Decimal(1).scaleb(-dec), rounding=ROUND_HALF_UP) if dec else abs(x).quantize(Decimal(1), rounding=ROUND_HALF_UP)
    s = f"{x:.{dec}f}"
    ip, _, fp = s.partition(".")
    if len(ip) > 3:
        head, tail = ip[:-3], ip[-3:]
        head = re.sub(r"(\d)(?=(\d\d)+$)", r"\1,", head)
        ip = head + "," + tail
    return ("-" if neg else "") + ip + ("." + fp if dec else "")


def inr_or_dash(x, dec=2):
    return "-" if x is None else inr(x, dec)


def amt_slash(x):
    """Whole-rupee style '13,40,502/-' ('-' for none/zero)."""
    if x is None or x == 0:
        return "-"
    dec = 0 if x == x.to_integral_value() else 2
    return inr(x, dec) + "/-"


def pct(part, whole):
    if not whole:
        return D0
    return (Decimal(part) / Decimal(whole) * 100)


def ordinal(n):
    n = int(n)
    suf = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"


def ordinal_sup(n):
    n = int(n)
    suf = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}<sup>{suf}</sup>"


def pdate(s):
    if not s:
        return None
    if isinstance(s, date):
        return s
    for f in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(str(s), f).date()
        except ValueError:
            pass
    return None


def dmy(s, blank=""):
    d = pdate(s)
    return d.strftime("%d-%m-%Y") if d else blank


def time12(s):
    if not s:
        return ""
    try:
        h, m = [int(x) for x in str(s).split(":")[:2]]
    except ValueError:
        return str(s)
    ap = "A.M." if h < 12 else "P.M."
    h12 = h % 12 or 12
    return f"{h12:02d}:{m:02d} {ap}"


def render(text, vals):
    return re.sub(r"\{(\w+)\}", lambda m: str(vals.get(m.group(1), m.group(0))), text)


# ----------------------------------------------------------------------------- numbers
def compute_fin(col, unit_mult, total_shares):
    """col: dict of strings -> dict of Decimals/None for display"""
    g = lambda k: num(col.get(k))
    rev, exp, dep, exc, tax, dtax = g("rev"), g("exp"), g("dep"), g("exc"), g("tax"), g("dtax")
    z = lambda x: x if x is not None else D0
    pbdt = g("pbdt") if g("pbdt") is not None else (z(rev) - z(exp) if (rev is not None or exp is not None) else None)
    pbt = g("pbt") if g("pbt") is not None else (z(pbdt) - z(dep) + z(exc) if pbdt is not None else None)
    pat = g("pat") if g("pat") is not None else (z(pbt) - z(tax) - z(dtax) if pbt is not None else None)
    reserve = g("reserve") if g("reserve") is not None else pat
    eps = g("eps")
    if eps is None and pat is not None and total_shares:
        eps = pat * Decimal(unit_mult) / Decimal(total_shares)
    return dict(rev=rev, exp=exp, pbdt=pbdt, dep=dep, exc=exc, pbt=pbt, tax=tax, dtax=dtax, pat=pat,
                reserve=reserve, eps=eps)


def analyse(f):
    """Derived numbers used by several parts of the document."""
    sh = f.get("shareholders") or []
    for s in sh:
        s["_b"] = int(num(s.get("begin")) or 0)
        s["_e"] = int(num(s.get("end")) or 0)
    tb = sum(s["_b"] for s in sh)
    te = sum(s["_e"] for s in sh)
    return sh, tb, te


# ----------------------------------------------------------------------------- values
def build_values(f):
    v = {}
    unit = UNITS.get(f.get("unit") or "hundreds", UNITS["hundreds"])
    sh, tb, te = analyse(f)
    fy_end = int(f.get("fy_end_year") or date.today().year)
    v["fy_end_year"] = str(fy_end)
    v["fy"] = f"{fy_end-1}-{str(fy_end)[2:]}"
    v["fy_end_dmy"] = f"31-03-{fy_end}"
    v["fy_start_dmy"] = f"01-04-{fy_end-1}"
    v["fy_end_ord"] = f"31<sup>st</sup> March, {fy_end}"
    v["py_end_ord"] = f"31<sup>st</sup> March, {fy_end-1}"
    v["fy_end_plain"] = f"31 March, {fy_end}"

    v["company"] = f.get("company", "").strip()
    v["company_upper"] = v["company"].upper()
    v["cin"] = (f.get("cin") or "").strip().upper()
    v["address"] = (f.get("address") or "").strip()
    v["email"] = (f.get("email") or "").strip()
    ph1, ph2 = (f.get("phone1") or "").strip(), (f.get("phone2") or "").strip()
    v["phone1"] = ph1
    v["phones"] = ("+91 " + ph1 if ph1 else "") + (", " + ph2 if ph2 else "")
    v["category"] = f.get("category") or "Private Limited Company"
    rd = pdate(f.get("reg_date"))
    v["reg_date_long"] = f"{ordinal_sup(rd.day)} Day of {rd.strftime('%B, %Y')}" if rd else ""
    v["sign_place"] = f.get("sign_place") or ""
    v["sign_date"] = dmy(f.get("sign_date"))

    ad = pdate(f.get("agm_date"))
    v["agm_no"] = ordinal(f.get("agm_no") or 1)
    v["agm_weekday"] = ad.strftime("%A") if ad else ""
    v["agm_day"] = ordinal_sup(ad.day) if ad else ""
    v["agm_month"] = ad.strftime("%B") if ad else ""
    v["agm_year"] = str(ad.year) if ad else str(fy_end)
    v["agm_time"] = time12(f.get("agm_time")) or "11:00 A.M."
    if (f.get("venue_mode") or "registered") == "registered":
        v["agm_venue"] = "at the registered office of the Company at <b>" + v["address"] + "</b>"
    else:
        v["agm_venue"] = "at <b>" + (f.get("venue_text") or "").strip() + "</b>"

    v["unit_label"], v["unit_paren1"], v["unit_paren2"] = unit["label"], unit["p1"], unit["p2"]

    # financials
    fin = f.get("fin") or {}
    cur = compute_fin(fin.get("cur") or {}, unit["mult"], te)
    prv = compute_fin(fin.get("prev") or {}, unit["mult"], tb or te)
    f["_cur"], f["_prv"] = cur, prv
    for pre, col in (("cur_", cur), ("prv_", prv)):
        for k, x in col.items():
            v[pre + k] = inr_or_dash(x)
    v["cur_rev"] = inr_or_dash(cur["rev"])

    # share capital
    fv = num(f.get("face_value")) or Decimal(10)
    paid = Decimal(te) * fv
    f["_paid"] = paid
    changed = any(s["_b"] != s["_e"] for s in sh)
    cap = f.get("capital") or {}
    base = f"During the Financial Year {v['fy']}, there has been no change in subscribed,& Paid-up Equity share capital of Rs-{inr(paid, 0)}/-"
    v["_capital_default"] = base + (" However Shareholdings had been changed" if changed else "") + "."

    pat = cur["pat"]
    if pat is not None and pat < 0:
        v["_reserve_default"] = ("During the financial year company has incurred net loss of Rs. " + inr(abs(pat)) +
                                 "/-" + unit["p2"] + " and same has been carried to Reserve and Surplus.")
    else:
        v["_reserve_default"] = ("During the financial year company has earn net profit of Rs. " + inr_or_dash(pat) +
                                 "/-" + unit["p2"] + " and same has been transferred to Reserve and Surplus.")

    nm = len(f.get("meetings") or [])
    v["_boardcount_default"] = (f"During the Financial Year {v['fy']}, {nm} meeting{'s' if nm != 1 else ''} of the Board of Directors of the company "
                                f"{'were' if nm != 1 else 'was'} held.")
    web = f.get("website") or {}
    if web.get("has") == "Yes" and web.get("url"):
        v["_website_default"] = f"The Annual Return of the Company for the Financial Year {v['fy']} is available on the website of the Company at {web['url']}"
    else:
        v["_website_default"] = "The Company Does not have any website."

    aud = f.get("auditor") or {}
    ca = f.get("ca") or {}
    v["auditor_firm"] = ca.get("firm") or aud.get("firm") or "____ & CO."
    v["auditor_city"] = ca.get("city") or aud.get("city") or "____"
    v["auditor_frn"] = ca.get("frn") or aud.get("frn") or "____"
    v["_auditor_default"] = ("M/s {auditor_firm}, Chartered Accountants, {auditor_city}, with registration number {auditor_frn} be and are hereby Continuing as "
                             "Statutory Auditors of the company at a remuneration as may be mutually agreed between the Board of Directors and M/s {auditor_firm}, "
                             "plus applicable taxes, in connection with the work of audit to be carried out by them, to hold office of statutory auditor till the "
                             "conclusion of the Annual General Meeting of the company to be held in the year {agm_year}.\".")

    # forex
    fe = num(f.get("fx_earn"))
    fo = num(f.get("fx_out"))
    v["fx_earn"] = (inr(fe) + "/-") if fe else "NIL"
    v["fx_out"] = (inr(fo) + "/-") if fo else "NIL"

    # inline yes/no answers
    inl = f.get("inline") or {}
    for t in INLINE_TOGGLES:
        st = inl.get(t["key"]) or {}
        v[t["key"]] = (st.get("text") or "Yes").strip() if st.get("on") else "No"
    v["ta_year"] = (f.get("ta_year") or "----------").strip() or "----------"

    # paragraph tokens
    tg = f.get("toggles") or {}
    for t in PARA_TOGGLES:
        st = tg.get(t["key"]) or {}
        text = (st.get("text") or "").strip() if st.get("on") else ""
        v[t["token"]] = text or texts.dflt("notice", t["token"], t["default"], f)
    def ovr(key, token, default_key):
        st = (f.get(key) or {})
        text = (st.get("text") or "").strip() if st.get("on") else ""
        v[token] = text or v[default_key]
    ovr("capital", "P_capital", "_capital_default")
    v["P_reserve"] = v["_reserve_default"]
    v["P_boardcount"] = v["_boardcount_default"]
    v["P_website"] = v["_website_default"]
    ovr("auditor", "P_auditor", "_auditor_default")
    for k in list(v):
        if k.startswith("P_"):
            v[k] = render(v[k], v)
    v["P_auditor"] = render(v["P_auditor"], v)
    return v


# ----------------------------------------------------------------------------- document parts
def fill_tokens(doc, vals):
    for p in iter_paragraphs(doc):
        t = para_text(p)
        if "{{" not in t:
            continue
        for m in reversed(list(TOKEN_RE.finditer(t))):
            replace_span(p, m.start(), m.end(), str(vals.get(m.group(1), "")))


def directors_on(f, d):
    out = []
    for dr in f.get("directors") or []:
        a, c = pdate(dr.get("appointed")), pdate(dr.get("ceased"))
        if d and a and a > d:
            continue
        if d and c and c < d:
            continue
        out.append(dr)
    return out


def part_signatures(doc, f):
    from docx.shared import Pt, Twips
    from docx.enum.text import WD_ALIGN_PARAGRAPH as AL
    allr = f.get("directors") or []
    dirs = [d for d in allr if d.get("name") and not d.get("ceased")] or allr
    n = len(dirs)
    per = 1 if n <= 1 else (2 if n in (2, 4) else 3)
    rows_n = max(1, -(-n // per))
    for p in list(doc.paragraphs):
        if "{{sig_name_1}}" not in para_text(p):
            continue
        names_p = p
        desig_p = Paragraph_next(names_p)
        din_p = Paragraph_next(desig_p)
        rpr = names_p.runs[0]._r.rPr
        tbl = doc.add_table(rows=rows_n, cols=per)
        tbl.autofit = False
        W = 9800
        tblPr = tbl._tbl.tblPr
        for tag in ("w:tblW", "w:jc", "w:tblLayout"):
            for e in tblPr.findall(qn(tag)):
                tblPr.remove(e)
        from docx.oxml import OxmlElement
        tw = OxmlElement("w:tblW"); tw.set(qn("w:w"), str(W)); tw.set(qn("w:type"), "dxa"); tblPr.append(tw)
        jc = OxmlElement("w:jc"); jc.set(qn("w:val"), "center"); tblPr.append(jc)
        lay = OxmlElement("w:tblLayout"); lay.set(qn("w:type"), "fixed"); tblPr.append(lay)
        for gc in tbl._tbl.tblGrid.findall(qn("w:gridCol")):
            gc.set(qn("w:w"), str(W // per))
        for ri, row in enumerate(tbl.rows):
            for ci, cell in enumerate(row.cells):
                cell.width = Twips(W // per)
                k = ri * per + ci
                align = AL.LEFT if ci == 0 else (AL.RIGHT if ci == per - 1 else AL.CENTER)
                if per == 1:
                    align = AL.LEFT
                lines = []
                if k < n:
                    d = dirs[k]
                    lines = [d["name"], d.get("desig") or "Director", ("Din: " + d["din"]) if d.get("din") else ""]
                par = cell.paragraphs[0]
                for _ in range(3 if ri else 0):  # signing space for the following rows
                    par.alignment = align
                    par = cell.add_paragraph()
                first = True
                for ln in lines:
                    if not first:
                        par = cell.add_paragraph()
                    first = False
                    par.alignment = align
                    par.paragraph_format.space_after = Pt(2)
                    r = par.add_run(ln)
                    if rpr is not None:
                        r._r.insert(0, copy.deepcopy(rpr))
                    r.font.name = "Verdana"; r.bold = True; r.font.size = Pt(10)
        names_p._p.addprevious(tbl._tbl)
        for q in (names_p, desig_p, din_p):
            q._p.getparent().remove(q._p)
        # keep "For & On behalf…", the signatures and Place/Date together on one page
        prev, k = tbl._tbl.getprevious(), 0
        while prev is not None and k < 8 and prev.tag == qn("w:p"):
            Paragraph(prev, names_p._parent).paragraph_format.keep_with_next = True
            prev = prev.getprevious(); k += 1
        for row in tbl.rows:
            for cell in row.cells:
                for par in cell.paragraphs:
                    par.paragraph_format.keep_with_next = True
        nxt = tbl._tbl.getnext()
        if nxt is not None and nxt.tag == qn("w:p"):
            Paragraph(nxt, names_p._parent).paragraph_format.keep_with_next = True
    return {}


def Paragraph_next(p):
    el = p._p.getnext()
    while el is not None and el.tag != qn("w:p"):
        el = el.getnext()
    return Paragraph(el, p._parent)


def part_directors_table(doc, f):
    t = find_table(doc, "Name of Director", "Appointment")
    rows = []
    for i, d in enumerate(f.get("directors") or []):
        rows.append([f"{i+1}.", d.get("name", ""), d.get("din", ""), dmy(d.get("appointed")), dmy(d.get("ceased"), "N.A.")])
    rebuild_rows(t, 1, rows or [["", "", "", "", ""]])


def part_meetings(doc, f):
    t = find_table(doc, "Date of Board Meeting")
    dirs_all = f.get("directors") or []
    rows = []
    for i, m in enumerate(f.get("meetings") or []):
        d = pdate(m.get("date"))
        on = directors_on(f, d)
        absent_names = set(m.get("absent") or [])
        present = [x["name"] for x in on if x["name"] not in absent_names]
        absent = [x["name"] for x in on if x["name"] in absent_names]
        rows.append([f"{i+1}.", dmy(m.get("date")), [x["name"] for x in on] or ["-"], present or ["-"], absent or ["-"]])
    if rows:
        rebuild_rows(t, 1, rows)


def part_financials(doc, f):
    t = find_table(doc, "FINANCIAL RESULTS")
    cur, prv = f["_cur"], f["_prv"]
    fm = inr_or_dash
    rows = list(t.rows)[1:]
    proto = None
    for r in rows:
        cs = unique_cells(r)
        if "expenditure" in cs[0].text.lower():
            proto = copy.deepcopy(cs[1].paragraphs[0]._p)
    def put(cell, lines, bold):
        old = list(cell.paragraphs)
        for ln in lines:
            el = copy.deepcopy(proto)
            old[-1]._p.addnext(el)
            from docx.text.paragraph import Paragraph as P_
            para = P_(el, cell)
            for r_ in para.runs[1:]:
                r_._r.getparent().remove(r_._r)
            para.runs[0].text = ln
            para.runs[0].bold = True if bold else None
            old.append(para)
        for o in old[: len(old) - len(lines)]:
            o._p.getparent().remove(o._p)
    keymap = [("before depreciation", ["pbdt"], 0), ("less: depreciation", ["dep"], 0), ("exceptional", ["exc"], 0),
              ("before tax", ["pbt"], 1), ("income tax", ["", "tax", "dtax"], 0), ("after tax", ["pat"], 1),
              ("transfer to reserve", ["reserve"], 0), ("earning per share", ["", "eps", "eps"], 0),
              ("revenue", ["rev"], 1), ("expenditure", ["exp"], 0)]
    for r in rows:
        cells = unique_cells(r)
        label = cells[0].text.lower()
        if "income tax" in label:
            set_cell_lines(cells[0], ["Less: Income Tax", "Current Tax:", "Deferred Tax:"])
        elif "earning per share" in label:
            set_cell_lines(cells[0], ["Earning Per Share", "Basic", "Diluted"])
        for key, fields, bold in keymap:
            if key in label:
                for ci, col in ((1, cur), (2, prv)):
                    put(cells[ci], [fm(col[k]) if k else "" for k in fields], bold)
                break


def part_registration(doc, f):
    t = find_table(doc, "Registration Date")
    for r in t.rows:
        cells = unique_cells(r)
        if len(cells) < 3:
            continue
        label = cells[1].text.lower()
        if "whether listed" in label:
            set_cell_text(cells[2], f.get("listed") or "Not Applicable")
        elif "registrar" in label:
            set_cell_text(cells[2], f.get("rta") or "NA")


def part_nic(doc, f):
    t = find_table(doc, "NIC Code")
    rows = []
    for i, a in enumerate(f.get("nic") or []):
        p = (a.get("pct") or "").strip()
        rows.append([str(i + 1), a.get("desc", ""), a.get("code", ""), (p + ("%" if p and not p.endswith("%") else "")) or "-"])
    rebuild_rows(t, 1, rows or [["1", "", "", ""]])


def _p(x):  # percentage text with 2 decimals
    return f"{x:.2f}"


def part_shareholding(doc, f):
    sh, tb, te = analyse(f)
    holding = (f.get("holding_form") or "Physical")
    fv = num(f.get("face_value")) or Decimal(10)
    prom = [s for s in sh if s.get("promoter", True)]
    pub = [s for s in sh if not s.get("promoter", True)]

    # ---- category-wise (two tables)
    t9 = find_table(doc, "Category of Shareholders")
    t10 = None
    for t in iter_tables_recursive(doc):
        if any(unique_cells(r)[0].text.strip().startswith("Grand Total") for r in t.rows):
            t10 = t
    def cat(sel):
        return (sum(s["_b"] for s in sel), sum(s["_e"] for s in sel))
    def vals(b, e):
        """returns 9 cell values (demat/phys/total/% for begin & end, % change)"""
        def side(n, tot):
            if n == 0:
                return ["-", "-", "-", "-"]
            dem = inr(n, 0) if holding == "Demat" else "-"
            phy = inr(n, 0) if holding != "Demat" else "-"
            pc = pct(n, tot)
            return [dem, phy, inr(n, 0), (f"{pc:g}%" if pc == pc.to_integral_value() else f"{pc:.2f}%")]
        ch = pct(e, te) - pct(b, tb)
        return side(b, tb) + side(e, te) + ["-" if ch == 0 else f"{ch:.2f}"]
    def setrow(table, startswith, v9):
        for r in table.rows:
            cells = unique_cells(r)
            if cells[0].text.strip().replace("\n", " ").startswith(startswith) and len(cells) >= 10:
                for c, val in zip(cells[1:10], v9):
                    set_cell_text(c, val, proto_run=None)
                return True
        return False
    ind = cat([s for s in prom if s.get("type") != "Body Corporate"])
    bod = cat([s for s in prom if s.get("type") == "Body Corporate"])
    pb = cat(prom)
    setrow(t9, "a) Individual", vals(*ind))
    setrow(t9, "d) Bodies Corp", vals(*bod))
    setrow(t9, "Sub Total (A)(1)", vals(*pb))
    setrow(t9, "Total shareholding of", vals(*pb))
    # public (non promoter) holders
    pub_ind_small = cat([s for s in pub if s.get("type") != "Body Corporate" and Decimal(s["_e"] or s["_b"]) * fv <= 100000])
    pub_ind_big = cat([s for s in pub if s.get("type") != "Body Corporate" and Decimal(s["_e"] or s["_b"]) * fv > 100000])
    pub_body = cat([s for s in pub if s.get("type") == "Body Corporate"])
    pubt = cat(pub)
    if pub:
        setrow(t10, "a) Bodies Corp", vals(*pub_body))
        setrow(t10, "i) Indian", vals(*pub_body))
        setrow(t10, "i) Individual shareholders holding nominal share capital upto", vals(*pub_ind_small))
        setrow(t10, "ii) Individual shareholders holding nominal", vals(*pub_ind_big))
        setrow(t10, "b) Individuals", vals(pub_ind_small[0] + pub_ind_big[0], pub_ind_small[1] + pub_ind_big[1]))
        setrow(t10, "Sub-total (B)(2)", vals(*pubt))
        setrow(t10, "Total Public Shareholding", vals(*pubt))
    setrow(t10, "Grand Total", vals(tb, te))
    # the original had stray values in some "(B)(2)" cells – make Sub-total (B)(1) tidy
    # ---- promoter table (B)
    t11 = find_table(doc, "pledged")
    rows = []
    for i, s in enumerate(prom):
        b, e = s["_b"], s["_e"]
        bp, ep = pct(b, tb), pct(e, te)
        ch = ep - bp
        rows.append([f"{i+1}.", s.get("name", ""),
                     inr(b, 0) if b else "-", _p(bp) if b else "-", "-",
                     inr(e, 0) if e else "-", _p(ep) if e else "-", "-",
                     "-" if ch == 0 else f"{ch:.2f}%"])
    rebuild_rows(t11, 2, rows or [["", "", "-", "-", "-", "-", "-", "-", "-"]])

    # ---- (C) change in promoters' shareholding
    t12 = find_table(doc, "Particulars", "Cumulative Shareholding")
    pbn, pen = cat(prom)
    r = list(t12.rows)
    def put(row, v):
        cs = unique_cells(row)
        for c, val in zip(cs[2:6], v):
            if val is not None:
                set_cell_text(c, val)
    pct_txt = lambda n, tot: ("-" if not n else (f"{pct(n, tot):g}%" if pct(n, tot) == pct(n, tot).to_integral_value() else f"{pct(n, tot):.2f}%"))
    put(r[2], [inr(pbn, 0) if pbn else "-", pct_txt(pbn, tb), "-", "-"])
    note = (f.get("sh_change_note") or "").strip()
    cs = unique_cells(r[3])
    if note:
        base = cs[1].text.rstrip()
        set_cell_text(cs[1], base + " " + note)
    put(r[3], ["-", "-", "-", "-"])
    put(r[4], [inr(pbn, 0) if pbn else "-", pct_txt(pbn, tb), inr(pen, 0) if pen else "-", pct_txt(pen, te)])

    # ---- (D) top ten (non promoters) and (E) directors – blocks of 3 rows
    def blocks(table, persons):
        rws = list(table.rows)
        protos = rws[2:5]
        if not persons:
            return False
        last = protos[-1]
        copies = []
        for _ in persons[1:]:
            blk = []
            for pr in protos:
                last = clone_row_after(table, pr, last)
                blk.append(last)
            copies.append(blk)
        all_blocks = [protos] + copies
        for blk, (name, b, e) in zip(all_blocks, persons):
            def setr(row, v, label=None):
                cs = unique_cells(row)
                if label is not None:
                    set_cell_text(cs[1], label)
                for c, val in zip(cs[2:6], v):
                    set_cell_text(c, val)
            setr(blk[0], [inr(b, 0) if b else "-", pct_txt(b, tb), "-", "-"], f"{name} – At the beginning of the year")
            setr(blk[1], ["-", "-", "-", "-"])
            setr(blk[2], [inr(b, 0) if b else "-", pct_txt(b, tb), inr(e, 0) if e else "-", pct_txt(e, te)], f"{name} – At the end of the year")
        return True
    t13 = find_table(doc, "Top 10")
    persons = [(s["name"], s["_b"], s["_e"]) for s in pub[:10]]
    if not blocks(t13, persons):
        pass
    else:
        pass
    if not persons:
        for rr in list(t13.rows)[2:5]:
            for c in unique_cells(rr)[2:6]:
                set_cell_text(c, "-")
    t14 = find_table(doc, "Directors and each Key") or find_table(doc, "each Directors")
    dnames = {(d.get("name") or "").strip().lower() for d in f.get("directors") or []}
    dsh = [(s["name"], s["_b"], s["_e"]) for s in sh if s["name"].strip().lower() in dnames]
    if not blocks(t14, dsh):
        for rr in list(t14.rows)[2:5]:
            for c in unique_cells(rr)[2:6]:
                set_cell_text(c, "-")
    elif note:
        pass


def part_indebtedness(doc, f):
    t = find_table(doc, "Secured Loans", "Unsecured")
    d = f.get("debt") or {}
    g = lambda k: num(d.get(k)) or D0
    os_, ou = g("open_sec"), g("open_unsec")
    as_, au = g("add_sec"), g("add_unsec")
    rs, ru = g("red_sec"), g("red_unsec")
    ns, nu = as_ - rs, au - ru
    cs_, cu = os_ + ns, ou + nu
    rows = list(t.rows)
    def setrow(i, a, b, tot=None, dep="-"):
        cs = unique_cells(rows[i])
        for c, val in zip(cs[1:5], [amt_slash(a), amt_slash(b), dep, amt_slash(a + b) if tot is None else tot]):
            set_cell_text(c, val)
    setrow(2, os_, ou); setrow(5, os_, ou)
    setrow(7, as_, au); setrow(8, rs, ru); setrow(9, ns, nu)
    setrow(11, cs_, cu); setrow(14, cs_, cu)
    f["_debt_close"] = (cs_, cu)


def part_remuneration(doc, f):
    t = find_table(doc, "Name of Directors")
    dirs = f.get("directors") or []
    n = len(dirs)
    rows = list(t.rows)
    # widen the table for >3 directors
    if n > 3:
        extra = n - 3
        W = qn("w:gridSpan")
        hdr = unique_cells(rows[0])
        gs = hdr[2]._tc.tcPr.find(qn("w:gridSpan"))
        gs.set(qn("w:val"), str(3 + extra))
        grid = t._tbl.tblGrid
        cols = grid.findall(qn("w:gridCol"))
        for _ in range(extra):
            cols[4].addnext(copy.deepcopy(cols[4]))
        for r in rows[1:]:
            cs = unique_cells(r)
            if len(cs) == 6:
                for _ in range(extra):
                    cs[4]._tc.addnext(copy.deepcopy(cs[4]._tc))
        # equalise the director columns
        allcols = grid.findall(qn("w:gridCol"))
        tot = sum(int(c.get(qn("w:w")) or 0) for c in allcols[2:5 + extra - 0][:3 + extra])
        # keep original total of 3 director columns
        orig = sum(int(c.get(qn("w:w")) or 0) for c in cols[2:5])
        each = str(int(orig / n))
        for c in allcols[2:2 + n]:
            c.set(qn("w:w"), each)
        for r in rows[1:]:
            cs = unique_cells(r)
            if len(cs) == 6 + extra:
                for c in cs[2:2 + n]:
                    tcw = c._tc.tcPr.find(qn("w:tcW")) if c._tc.tcPr is not None else None
                    if tcw is not None:
                        tcw.set(qn("w:w"), each)
    ndir = max(3, n)
    amts = [num(d.get("remuneration")) for d in dirs]
    total = sum((a for a in amts if a), D0)
    section2 = False
    others_seen = 0
    for ri, r in enumerate(rows):
        cs = unique_cells(r)
        if ri == 0:
            continue
        if ri == 1:
            for k in range(ndir):
                set_cell_text(cs[2 + k], dirs[k]["name"] if k < n else "")
            continue
        label = cs[1].text.strip().lower()
        dcells = cs[2:2 + ndir]
        tcell = cs[-1]
        def put(vals, tot):
            for k, c in enumerate(dcells):
                set_cell_text(c, vals[k] if k < len(vals) else "")
            set_cell_text(tcell, tot)
        if label.startswith("independent directors"):
            continue
        if label.startswith("other non-executive"):
            section2 = True
            continue
        if label.startswith("others") and section2:
            put([amt_slash(a) for a in amts], amt_slash(total))
        elif label.startswith(("total (2)", "total (b)", "total managerial")):
            put([amt_slash(a) for a in amts], amt_slash(total))
        elif label.startswith("overall ceiling"):
            put(["NA"] * n, "NA")
        elif label:
            put(["-"] * n, "-")
    f["_remun"] = amts


def part_rpt(doc, f):
    t = find_table(doc, "related party")
    dirs = f.get("directors") or []
    rows = []
    for d in dirs:
        a = num(d.get("remuneration"))
        rows.append([d["name"] + " (Director)" if False else d["name"], "Director Remuneration", "Yearly", "NA", (inr(a) + "/-") if a else "NA"])
    for x in f.get("rpt") or []:
        rows.append([x.get("party", ""), x.get("nature", ""), x.get("duration", ""), dmy(x.get("br_date"), "NA"), x.get("amount") or "NA"])
    rebuild_rows(t, 1, rows or [["NA", "NA", "NA", "NA", "NA"]])


def part_s186(doc, f):
    specs = [
        (("Date of Loan",), "loans", ["date", "party", "amount", "purpose", "period", "br", "sr", "rate", "security"]),
        (("Date of Investment",), "investments", ["date", "party", "amount", "br", "sr", "rate"]),
        (("Date of guarantee",), "guarantees", ["date", "party", "amount", "purpose", "br", "sr"]),
    ]
    for needles, key, fields in specs:
        t = find_table(doc, *needles)
        items = [x for x in (f.get(key) or []) if any((x.get(k) or "").strip() for k in x)]
        if not t or not items:
            continue
        rows = []
        for i, x in enumerate(items):
            vals = []
            for k in fields:
                val = x.get(k) or ""
                if k in ("date", "br", "sr"):
                    val = dmy(val, "-")
                vals.append(val or "-")
            rows.append([f"{i+1}."] + vals)
        rebuild_rows(t, 1, rows)


def part_route_map(doc, f, route_bytes):
    """Replace the sample route-map picture (never leak another client's map)."""
    target = None
    for p in doc.paragraphs:
        if p._p.xpath(".//a:blip[@r:embed]"):
            target = p
            break
    if target is None:
        return
    blip = target._p.xpath(".//a:blip[@r:embed]")[0]
    rid = blip.get(qn("r:embed"))
    if route_bytes:
        from PIL import Image
        im = Image.open(io.BytesIO(route_bytes)).convert("RGB")
        buf = io.BytesIO()
        im.save(buf, "PNG")
        doc.part.related_parts[rid]._blob = buf.getvalue()
        w_emu = 7239000
        h_emu = int(w_emu * im.height / im.width)
        for ext in target._p.xpath(".//wp:extent") + target._p.xpath(".//a:ext[@cx]"):
            ext.set("cx", str(w_emu)); ext.set("cy", str(h_emu))
    else:
        for drw in target._p.xpath(".//w:drawing"):
            drw.getparent().getparent().remove(drw.getparent())
        r = target.add_run("[Route map to be attached]")
        r.italic = True


def align_place_date(doc):
    """Put the 'Place:' / 'Date:' lines flush with the left signature column (table is centred, 9800 tw wide)."""
    from docx.shared import Twips
    sec = doc.sections[0]
    text_w = int((sec.page_width - sec.left_margin - sec.right_margin) / 635)
    left = max(0, (text_w - 9800) // 2 + 108)
    sig_rpr = None
    for t in iter_tables_recursive(doc):
        if any(para_text(q).strip().startswith("Din") for c in t._cells for q in c.paragraphs):
            for c in t._cells:
                for q in c.paragraphs:
                    if q.runs and q.runs[0]._r.rPr is not None and para_text(q).strip():
                        sig_rpr = q.runs[0]._r.rPr; break
                if sig_rpr is not None: break
            break
    for p in doc.paragraphs:
        t = para_text(p)
        if re.match(r"^(Place|Date)\s*:", t) and len(t) < 60 and "\t" not in t:
            if sig_rpr is not None:  # same typeface/size as the director names above
                for r in p.runs:
                    rpr = r._r.get_or_add_rPr()
                    for tag in ("w:rFonts", "w:sz", "w:szCs"):
                        for x in rpr.findall(qn(tag)): rpr.remove(x)
                    for tag in ("w:rFonts", "w:sz", "w:szCs"):
                        x = sig_rpr.find(qn(tag))
                        if x is not None: rpr.insert(0, copy.deepcopy(x))
            pf = p.paragraph_format
            pf.left_indent = Twips(left); pf.first_line_indent = Twips(0)
            pf.alignment = None
            ppr = p._p.pPr
            for jc in ppr.findall(qn("w:jc")): ppr.remove(jc)


def finish_layout(doc, fonts=True):
    """Centre every table on the page and keep fonts consistent."""
    from docx.oxml import OxmlElement
    from docx.shared import Pt
    for t in iter_tables_recursive(doc):
        pr = t._tbl.tblPr
        for tag in ("w:tblInd", "w:jc"):
            for e in pr.findall(qn(tag)):
                pr.remove(e)
        jc = OxmlElement("w:jc"); jc.set(qn("w:val"), "center")
        # schema order: jc must come before tblLayout/tblCellMar/tblLook
        anchor = None
        for tag in ("w:tblLayout", "w:tblCellMar", "w:tblLook"):
            anchor = pr.find(qn(tag))
            if anchor is not None:
                break
        (anchor.addprevious(jc) if anchor is not None else pr.append(jc))
    if not fonts:
        return
    # tidy fonts: one body family, headings keep their display face
    for p in iter_paragraphs(doc):
        for r in p.runs:
            if r.font.name in ("Arial", "Bookman Old Style", "Times New Roman"):
                r.font.name = "Verdana"
                rpr = r._r.rPr
                if rpr is not None and rpr.rFonts is not None:
                    for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
                        rpr.rFonts.set(qn(a), "Verdana")
    for p in doc.paragraphs:
        if para_text(p).strip() in ("Details of Loans", "Details of Investments", "Details of Guarantee / Security Provided"):
            for r in p.runs:
                r.font.size = Pt(10); r.bold = True


# ----------------------------------------------------------------------------- main
def generate(form, route_bytes=None):
    f = copy.deepcopy(form)
    doc = docx.Document(TEMPLATE)
    texts.apply(doc, "notice", f)
    vals = build_values(f)
    vals.update(part_signatures(doc, f))
    part_directors_table(doc, f)
    part_meetings(doc, f)
    part_financials(doc, f)
    part_registration(doc, f)
    part_nic(doc, f)
    part_shareholding(doc, f)
    part_indebtedness(doc, f)
    part_remuneration(doc, f)
    part_rpt(doc, f)
    part_s186(doc, f)
    part_route_map(doc, f, route_bytes)
    fill_tokens(doc, vals)
    align_place_date(doc)
    finish_layout(doc)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue(), f


def closing_values(f):
    """Numbers carried into next year (computed again so the db stays consistent)."""
    return f
