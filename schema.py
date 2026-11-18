"""Single source of truth for the Yes/No options (served to the browser and used by the engine).

Each PARA toggle:  default = standard sentence in the document ("No" answer)
                   hint    = text pre-filled in the box when the user switches the answer to Yes
Placeholders usable inside texts:  {fy} {fy_end_ord} {fy_end_dmy} {company} {company_upper} {agm_year}
"""

PARA_TOGGLES = [
    dict(key="dividend", token="P_dividend", label="Dividend recommended?",
         default="The directors are not recommending any dividend for this Financial Year.",
         hint="The directors recommend a dividend of Rs. ____ per equity share for the Financial Year {fy}."),
    dict(key="nature", token="P_nature", label="Change in nature of business?",
         default="There was no change in the nature of business taken place during the financial year.",
         hint="During the financial year there was a change in the nature of business of the Company, details: ____"),
    dict(key="diffrights", token="P_diffrights", label="Equity shares with differential rights issued?",
         default="During the financial year ended {fy_end_ord}, the Company has not made any issue of equity shares with differential rights with respect to the existing share holders.",
         hint="During the financial year ended {fy_end_ord}, the Company has issued ____ equity shares with differential rights."),
    dict(key="esop", token="P_esop", label="Employee stock options issued?",
         default="During the financial year ended {fy_end_ord}, the company has not made any issue of employee stock options.",
         hint="During the financial year ended {fy_end_ord}, the company has issued employee stock options: ____"),
    dict(key="sweat", token="P_sweat", label="Sweat equity shares issued?",
         default="During the financial year ended {fy_end_ord}, the company has not made any issue of sweat equity shares.",
         hint="During the financial year ended {fy_end_ord}, the company has issued ____ sweat equity shares."),
    dict(key="audremarks", token="P_audremarks", label="Auditor qualification / adverse remark?",
         default="There has been no qualification, reservation, adverse remark or disclaimer given by the statutory auditor in his Audit Report.",
         hint="The statutory auditor has made the following remark in the Audit Report: ____  Explanation of the Board: ____"),
    dict(key="material", token="P_material", label="Material changes after balance-sheet date?",
         default="There are not any material changes / events occurring after balance sheet date till the date of the report to be stated.",
         hint="The following material changes / events occurred after the balance sheet date: ____"),
    dict(key="subsid", token="P_subsid", label="Subsidiary / JV / Associate became or ceased?",
         default="During the financial year ended {fy_end_ord}, there is not any company which become or ceased to be subsidiaries, joint ventures or associate companies of the {company_upper}.",
         hint="During the financial year ended {fy_end_ord}, ____ became / ceased to be a subsidiary / joint venture / associate of the {company_upper}."),
    dict(key="boardchange", token="P_boardchange", label="Change in constitution of Board?",
         default="There is no change in constitution of board of directors during the year.",
         hint="During the year the constitution of the Board changed as follows: ____"),
    dict(key="disq", token="P_disq", label="Any director disqualified u/s 164?",
         default="Further none of the Director is disqualified under section 164 of companies act 2013.",
         hint="____ is disqualified under section 164 of the Companies Act, 2013."),
    dict(key="orders", token="P_orders", label="Significant orders by regulators / courts?",
         default="There are not any significant & material orders passed by the regulators or courts or tribunal or any other authorities which impacts the going concern status and company’s operations in future.",
         hint="The following significant & material orders were passed: ____"),
    dict(key="deposits", token="P_deposits", label="Deposits accepted?",
         default="Your Company has not accepted any deposits within the meaning of Section 73 of the Companies Act, 2013 and the Companies (Acceptance of Deposits) Rules, 2014.",
         hint="Your Company has accepted deposits of Rs. ____ during the year ____"),
    dict(key="shcomplaint", token="P_shcomplaint", label="Sexual-harassment complaint received?",
         default="There was no compliant received from any employee during the financial year {fy} and hence no complaint is outstanding as on {fy_end_dmy} for redressal.",
         hint="During the financial year {fy}, ____ complaint(s) were received and ____ disposed of; ____ outstanding as on {fy_end_dmy}."),
    dict(key="csr", token="P_csr", label="CSR applicable to the company?",
         default="The company does not fall in the category of companies which are required to constitute CSR Committee and develop and implement corporate social responsibility Policies as per the provision of section 135 of the Companies Act, 2013 read with Companies (Corporate Social Responsibility Policy) Rules, 2014.",
         hint="CSR provisions of section 135 are applicable. CSR expenditure for the year: Rs. ____"),
    dict(key="fraud", token="P_fraud", label="Fraud reported by auditors?",
         default="The statutory Auditors have not reported any incidence of fraud to the Board during the financial year to which this report relates.",
         hint="The statutory Auditors have reported the following fraud(s): ____"),
    dict(key="costaud", token="P_costaud", label="Cost auditor required?",
         default="The company is not required to appoint Cost Auditor as it does not fall in the categories of the company prescribed in section 148 of the Companies Act, 2013.",
         hint="The company has appointed ____ as Cost Auditor under section 148."),
]

# short inline answers ("No" in the document) – token name, label
INLINE_TOGGLES = [
    dict(key="en_alt", label="Energy: steps for utilising alternate sources"),
    dict(key="en_capex", label="Energy: capital investment on conservation equipment"),
    dict(key="ta_efforts", label="Technology: efforts made for absorption"),
    dict(key="ta_benefits", label="Technology: benefits derived"),
    dict(key="ta_rnd", label="Technology: expenditure on R&D"),
    dict(key="ta_import", label="Technology: details of technology imported"),
    dict(key="ta_absorbed", label="Technology: imported technology fully absorbed"),
    dict(key="ta_areas", label="Technology: areas where absorption has not taken place"),
]

UNITS = {
    "hundreds":  dict(label="In hundreds", p1="(in Hundreds)", p2="(hundreds)", mult=100, rs="Rs.in “00"),
    "thousands": dict(label="In thousands", p1="(in Thousands)", p2="(thousands)", mult=1000, rs="Rs.in “000"),
    "lakhs":     dict(label="In lakhs", p1="(in Lakhs)", p2="(lakhs)", mult=100000, rs="Rs.in Lakhs"),
    "absolute":  dict(label="In Rupees", p1="", p2="", mult=1, rs="Rs."),
}

CATEGORIES = ["Private Limited Company", "One Person Company", "Public Limited Company",
              "Private Limited Company (Small Company)", "Section 8 Company"]


MODULES = [
    dict(id="notice", label="Notice & Directors' Report", file="Notice_and_Directors_Report",
         desc="Notice of AGM, Directors' Report, AOC-2 and MGT-7 extract"),
    dict(id="directors", label="List of Directors", file="List_of_Directors", desc="Uses the common details only"),
    dict(id="shareholders", label="List of Shareholders", file="List_of_Shareholders", desc="Uses the common details only"),
    dict(id="dsc", label="DSC Consent Letter", file="DSC_Consent_Letter", desc="Authorisation to the CA to use the directors' DSC"),
    dict(id="index", label="Financials Index (cover)", file="Index", desc="Cover page listing the attachments"),
    dict(id="policies", label="Notes on Accounts", file="Notes_on_Accounts", desc="Overview, significant accounting policies, notes"),
    dict(id="mrl", label="Management Representation Letter", file="Management_Representation_Letter", desc="Letter to the auditor"),
]

INDEX_ATTACHMENTS = [
    ("Auditor’s Report", "Auditor"), ("Balance Sheet (Rounded off & complete figures)", "Balance Sheet"),
    ("Profit & Loss Account", "Profit & Loss"), ("Notes on Accounts", "Notes on Accounts"), ("ITR V", "ITR V"),
    ("Computation of taxable income", "Computation"), ("Notice of AGM", "Notice of AGM"), ("Director’s Report", "Director"),
    ("List of Directors", "List of Directors"), ("List of Shareholders", "List of Shareholders"),
    ("AOC-4 Receipt", "AOC-4"), ("MGT7A Receipt", "MGT7A"),
]

# Management representation letter – standard statements (default = wording in your document)
MRL_TOGGLES = [
    dict(key="comm", token="P_comm", label="Communications from regulators about non-compliance?",
         default="There have been no communications from regulatory agencies concerning noncompliance with or deficiencies in financial reporting practices.",
         hint="We have received the following communication(s) from regulatory agencies: ____"),
    dict(key="unrec", token="P_unrec", label="Material transactions not recorded?",
         default="There are no material transactions that have not been properly recorded in the accounting records underlying the financial statements.",
         hint="The following material transactions have not been recorded: ____"),
    dict(key="fraudA", token="P_fraudA", label="Fraud involving management / employees?",
         default="Fraud involving management or employees who have significant roles in internal control.",
         hint="Fraud involving management or employees: ____"),
    dict(key="fraudB", token="P_fraudB", label="Fraud involving others?",
         default="Fraud involving others that could have a material effect on the financial Statements.",
         hint="Fraud involving others: ____"),
    dict(key="viol", token="P_viol", label="Violations of laws or regulations?",
         default="There are no violations or possible violations of laws or regulations whose effects should be considered for disclosure in the financial statements or as a basis for recording a loss contingency.",
         hint="The following violations / possible violations exist: ____"),
    dict(key="notice", token="P_notice", label="Notice for statutory dues / penalty / interest?",
         default="We Certifies that there was no notice issued for statutory dues or for any penalty or interest from any legal regulatory (Income Tax, GST, Sales Tax).",
         hint="The following notice(s) were issued: ____"),
    dict(key="contract", token="P_contract", label="Non-compliance with contractual agreements?",
         default="The company has complied with all aspect of contractual agreements that would have a material effect on the financial statement in the event of non-compliance.",
         hint="The company has not complied with the following agreement(s): ____"),
    dict(key="rpt", token="P_rpt", label="Related-party transactions note",
         default="Related party transaction during the year had been properly disclosed",
         hint="Related party transactions during the year: ____"),
    dict(key="conting", token="P_conting", label="Contingent liabilities / litigation / commitments?",
         default="There were no contingent liabilities, potential liabilities, threatened litigations or capital commitments other than shown in notes to accounts.",
         hint="Contingent liabilities / threatened litigation / commitments: ____"),
    dict(key="bank", token="P_bank", label="Bank account reconciliation",
         default="The Company has the bank account which was duly reconciled up to {fy_end_slash}.",
         hint="The Company has the bank account(s) reconciled up to ____ except ____"),
    dict(key="otherexp", token="P_otherexp", label="Other income / expense not disclosed?",
         default="We certified that there is no other expense and income other than that is disclosed in Financial Statement.",
         hint="Other income / expense not disclosed in the financial statements: ____"),
    dict(key="dirloan", token="P_dirloan", label="Directors' unsecured loans – source of funds",
         default="We Certifies that the advance paid for running of business by directors as unsecured loan was from their personal account as self-financed, and Not from any borrowed fund.",
         hint="The advance by directors as unsecured loan was funded as follows: ____"),
    dict(key="disq", token="P_disq", label="Any director disqualified?",
         default="None of the directors are disqualified as on {fy_end_ord_nc}.",
         hint="____ is disqualified as on {fy_end_ord_nc}."),
    dict(key="subseq", token="P_subseq", label="Events after balance-sheet date?",
         default="To the best of our knowledge and belief, no events have occurred subsequent to the balance sheet date and through the date of this letter that would require adjustment to or disclosure in the aforesaid financial statements.",
         hint="The following events occurred after the balance sheet date: ____"),
]
