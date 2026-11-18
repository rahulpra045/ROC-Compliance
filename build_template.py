"""One-time script: turns the original sample document into a token template.
Run:  python build_template.py
Output: template/notice_director_report_template.docx
You can open the generated template in Word and edit wording freely – anything written
as {{token}} is filled by the app; {{P_xxx}} paragraphs hold the standard sentences that the
Yes/No options can override.
"""
import re, sys
import docx
from docx_core import *

SRC = "template/original_sample.docx"
OUT = "template/notice_director_report_template.docx"
d = docx.Document(SRC)
allp = list(iter_paragraphs(d))
report = []


def para_by_prefix(prefix, nth=0):
    hits = [p for p in allp if para_text(p).strip().startswith(prefix)]
    if len(hits) <= nth:
        raise SystemExit(f"NOT FOUND: {prefix!r}")
    return hits[nth]


def whole(prefix, token):
    p = para_by_prefix(prefix)
    set_paragraph_text(p, "{{%s}}" % token)
    report.append(("paragraph", token))


def sub_all(pattern, repl, expect_min=0, flags=0):
    rx = re.compile(pattern, flags)
    n = 0
    for p in iter_paragraphs(d):
        n += sub_in_paragraph(p, rx, repl)
    if n < expect_min:
        raise SystemExit(f"NO MATCH: {pattern}")
    report.append((pattern, n))


def sub_para(prefix, pattern, repl):
    p = para_by_prefix(prefix)
    n = sub_in_paragraph(p, re.compile(pattern), repl)
    if not n:
        raise SystemExit(f"NO MATCH in para {prefix!r}: {pattern}")
    report.append((prefix[:30] + " :: " + pattern, n))


# ---- A. whole-paragraph standard sentences (Yes/No overridable) --------------------------
whole("The directors are not recommending any dividend", "P_dividend")
whole("There was no change in the nature of business", "P_nature")
whole("During the Financial Year 2025-26, there has been no change in subscribed", "P_capital")
whole("During the financial year company has earn net profit", "P_reserve")
whole("During the financial year ended 31st March, 2026, the Company has not made any issue of equity shares with differential", "P_diffrights")
whole("The Company Does not have any website", "P_website")
whole("During the financial year ended 31st March, 2026, the company has not made any issue of employee stock options", "P_esop")
whole("During the financial year ended 31st March, 2026, the company has not made any issue of sweat equity", "P_sweat")
whole("During the Financial Year 2025-26, 4 meetings", "P_boardcount")
whole("There has been no qualification, reservation, adverse remark", "P_audremarks")
whole("There are not any material changes", "P_material")
whole("During the financial year ended 31st March, 2026, there is not any company which become", "P_subsid")
whole("There is no change in constitution of board of directors", "P_boardchange")
whole("Further none of the Director is disqualified", "P_disq")
whole("There are not any significant & material orders", "P_orders")
whole("Your Company has not accepted any deposits", "P_deposits")
whole("There was no compliant received from any employee", "P_shcomplaint")
whole("The company does not fall in the category of companies which are required to constitute CSR", "P_csr")
whole("The statutory Auditors have not reported any incidence of fraud", "P_fraud")
whole("The company is not required to appoint Cost Auditor", "P_costaud")
whole("M M/s CA_NAME", "P_auditor")

# ---- B. partial paragraph fields -----------------------------------------------------------
sub_para("Notice is", r"at the registered office of the Company at XXX, Sector-XX, City, State-Pincode, India", "{{agm_venue}}")
sub_para("Notice is", r"2nd Annual", "{{agm_no}} Annual")
sub_para("Notice is", r"Monday the 30th Day of September, 2026", "{{agm_weekday}} the {{agm_day}} Day of {{agm_month}}, {{agm_year}}")
sub_para("Notice is", r"11:00 A\.M\.", "{{agm_time}}")
sub_para("The company during the financial year has achieved", r"17,45,730\.72/-\(in Hundreds\)", "{{cur_rev}}/-{{unit_paren1}}")
sub_para("Foreign Exchange Earning\t", r"19,061\.92/-", "{{fx_earn}}")
sub_para("Foreign Exchange out go\t", r"NIL$", "{{fx_out}}")
sub_para("Steps taken for utilizing alternate", r"energy: No Capital", "energy: {{en_alt}} Capital")
sub_para("Steps taken for utilizing alternate", r"equipment’s: No$", "equipment’s: {{en_capex}}")
sub_para("Efforts made for technology absorption", r"absorption: No Benefits derived: No$", "absorption: {{ta_efforts}} Benefits derived: {{ta_benefits}}")
sub_para("Expenditure on Research", r"if any: No Details of technology imported, if any: No$", "if any: {{ta_rnd}} Details of technology imported, if any: {{ta_import}}")
sub_para("Year of import", r"-+$", "{{ta_year}}")
sub_para("Whether imported technology fully absorbed", r"No$", "{{ta_absorbed}}")
sub_para("Areas where absorption", r"No$", "{{ta_areas}}")

# ---- C. global fields ------------------------------------------------------------------------
sub_all(r"DKS ADSROBENTS PRIVATE LIMITED", "{{company_upper}}", expect_min=0)
sub_all(r"(?i)company\s+private\s+limited", lambda m: "{{company_upper}}" if "PRIVATE" in m.group(0) else "{{company}}")
sub_all(r"UXXXXXXXXXXXXXXXXXX27", "{{cin}}")
sub_all(r"XXX, Sector-XX, City, State-Pincode, India", "{{address}}")
sub_all(r"abc@gmail\.com", "{{email}}")
sub_all(r"\+91 9810xxxxxx, 7428xxxxxx", "{{phones}}")
sub_all(r"9810xxxxxx", "{{phone1}}")
sub_all(r"Sign_City", "{{sign_place}}")
sub_all(r"Sign_Date", "{{sign_date}}")
sub_all(r"31\s*st\s*March,\s*2026", "{{fy_end_ord}}")
sub_all(r"31\s*st\s*March,\s*2025", "{{py_end_ord}}")
sub_all(r"31 March, 2026", "{{fy_end_plain}}")
sub_all(r"ended March, 2026", "ended March, {{fy_end_year}}")
sub_all(r"2025-26", "{{fy}}")
sub_all(r"31-03-2026", "{{fy_end_dmy}}")
sub_all(r"01-04-2025", "{{fy_start_dmy}}")
sub_all(r"31-March-2026", "31-March-{{fy_end_year}}")
sub_all(r"March 31, 2024", "March 31, {{fy_end_year}}")
sub_all(r"\(In hundreds\.\)", "({{unit_label}}.)")
sub_all(r"24th Day of December, 2024", "{{reg_date_long}}")
sub_all(r"Private Limited Company", "{{category}}")

# ---- D. signature blocks: names / designation / DIN lines -----------------------------------
sig = 0
body = d.paragraphs
for i, p in enumerate(body):
    if para_text(p).startswith("Director Name1\tDirector Name2"):
        set_paragraph_text(p, "{{sig_name_1}}\t{{sig_name_2}}")
        set_paragraph_text(body[i + 1], "{{sig_desig_1}}\t{{sig_desig_2}}")
        set_paragraph_text(body[i + 2], "{{sig_din_1}}\t{{sig_din_2}}")
        sig += 1
report.append(("signature blocks", sig))

d.save(OUT)
for r in report:
    print(r)
print("saved", OUT)
