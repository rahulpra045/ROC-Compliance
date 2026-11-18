"""One-time: builds the token templates for the six extra documents from template/originals/*.docx
Run:  python build_templates_new.py      (output: template/<module>.docx)"""
import re, docx
from docx_core import *

OUT = "template/%s.docx"

def run(mod, steps):
    d = docx.Document("template/originals/%s.docx" % mod)
    allp = lambda: list(iter_paragraphs(d))
    def sub(pattern, repl, flags=0, must=False):
        rx = re.compile(pattern, flags); n = 0
        for p in iter_paragraphs(d):
            n += sub_in_paragraph(p, rx, repl)
        if must and not n: raise SystemExit(f"[{mod}] NO MATCH {pattern}")
        return n
    def whole(prefix, token):
        hits = [p for p in iter_paragraphs(d) if para_text(p).strip().startswith(prefix)]
        if not hits: raise SystemExit(f"[{mod}] NOT FOUND {prefix!r}")
        set_paragraph_text(hits[0], "{{%s}}" % token)
    def sig():
        n = 0
        body = d.paragraphs
        for i, p in enumerate(body):
            if para_text(p).startswith("Director 1"):
                set_paragraph_text(p, "{{sig_name_1}}\t{{sig_name_2}}")
                set_paragraph_text(body[i + 1], "{{sig_desig_1}}\t{{sig_desig_2}}")
                set_paragraph_text(body[i + 2], "{{sig_din_1}}\t{{sig_din_2}}")
                n += 1
        if not n: raise SystemExit(f"[{mod}] no signature block")
    steps(sub, whole, sig)
    d.save(OUT % mod)
    left = [para_text(p)[:90] for p in iter_paragraphs(d) if re.search(r"XXX|Sign_|sign_Date|CA_|Director 1|Din 1|DKS|2026|2025|2024", para_text(p))]
    print(mod, "saved; leftover sample text:", left)

def common(sub):
    I = re.I
    sub(r"(?i)company\s+private\s+limited", lambda m: "{{company_upper}}" if "PRIVATE LIMITED" in m.group(0) else "{{company}}")
    sub(r"UXXXXXXXXXXXXXXXXXX27", "{{cin}}")
    sub(r"XXX, Sector-XX, City, State-Pincode, India", "{{address}}")
    sub(r"abc2?@gmail\.com", "{{email}}")
    sub(r"\+91 9810xxxxxx, 7428xxxxxx", "{{phones}}", I)
    sub(r"Sign_Place", "{{sign_place}}", I)
    sub(r"Sign_Date", "{{sign_date}}", I)

def ca(sub):
    sub(r"CA_Name\s*&\s*Co\.", "{{ca_firm}}")
    sub(r"CA_Address,", "{{ca_address}},")
    sub(r"Pincode, State\.", "{{ca_pin}}, {{ca_state}}.")

# ---- list of directors / shareholders
def lists(sub, whole, sig):
    common(sub); sub(r"31ST MARCH, 2026", "{{fy_end_upper}}"); sig()

# ---- DSC consent
def dsc(sub, whole, sig):
    common(sub); ca(sub)
    sub(r"Date:\s*02-07-2026", "Date: {{letter_date}}")
    sub(r"31/03/2026", "31/03/{{fy_end_year}}")
    sig()

# ---- index
def index(sub, whole, sig):
    sub(r"(?i)company\s+private\s+limited", "{{company_upper}}")
    sub(r"XXX, Sector-XX, City, State, India", "{{address}}")
    sub(r"CA_Name\s*&\s*Co\.", "{{ca_firm}}")
    sub(r"2024-25", "{{fy}}", must=True)

# ---- notes on accounts
def policies(sub, whole, sig):
    sub(r"(?i)company\s+private\s+limited", lambda m: "{{company_upper}}" if "PRIVATE LIMITED" in m.group(0) else "{{company}}")
    sub(r"manufacturing of desiccants and silica gel and related products", "{{business_desc}}", must=True)
    sub(r"XXX, Sector-XX, City, State(?= and address)", "{{address}}", must=True)
    sub(r"YY, Sector-YY, City, State\.", "{{books_address}}.", must=True)
    sub(r"manufacturing of desiccant and silica gel", "{{revenue_desc}}", must=True)
    sub(r"31\s*st\s*March\s*2026", "{{fy_end_ord_nc}}", must=True)
    sub(r"deferred tax Liability for the year of Rs\.1,12,4\.33/-\(hundreds\)", "{{dt_sentence}}", must=True)
    sub(r"Rs\.in\s*“00", "{{unit_rs}}", must=True)

# ---- management representation letter
MRL_WHOLE = [
    ("There have been no communications from regulatory agencies", "P_comm"),
    ("There are no material transactions that have not been properly recorded", "P_unrec"),
    ("Fraud involving management or employees", "P_fraudA"),
    ("Fraud involving others", "P_fraudB"),
    ("There are no violations or possible violations", "P_viol"),
    ("We Certifies that there was no notice issued", "P_notice"),
    ("The company has complied with all aspect", "P_contract"),
    ("Related party transaction during the year", "P_rpt"),
    ("There were no contingent liabilities", "P_conting"),
    ("The Company has the bank account which was duly reconciled", "P_bank"),
    ("We certified that there is no other expense", "P_otherexp"),
    ("We Certifies that the advance paid for running", "P_dirloan"),
    ("None of the directors are disqualified", "P_disq"),
    ("To the best of our knowledge and belief, no events have occurred", "P_subseq"),
]
def mrl(sub, whole, sig):
    common(sub); ca(sub)
    sub(r"Date:\s*02-07-2026", "Date: {{letter_date}}")
    for prefix, tok in MRL_WHOLE: whole(prefix, tok)
    sub(r"Rs\.1,92,757/-", "Rs.{{cash}}/-", must=True)
    sub(r"Rs\.45,27,096/-", "Rs.{{stock}}/-", must=True)
    sub(r"Rs\.2,16,14,180/-", "Rs.{{debtors}}/-", must=True)
    sub(r"Rs\.62,65,050/-", "Rs.{{creditors}}/-", must=True)
    sub(r"17,45,73,072/-", "{{revenue_abs}}/-", must=True)
    sub(r"March 31\s*st of 2026", "{{m31_of}}", must=True)
    sub(r"31\s*st\s*March,\s*2026", "{{fy_end_ord}}")
    sub(r"31\s*st\s*March 2026", "{{fy_end_ord_nc}}")
    sub(r"31-03-2026", "{{fy_end_dmy}}")
    sig()

run("directors", lists); run("shareholders", lists); run("dsc", dsc)
run("index", index); run("policies", policies); run("mrl", mrl)
