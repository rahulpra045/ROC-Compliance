const TAB_OF = {"co": "common", "agm": "notice", "dir": "common", "bm": "notice", "sh": "common", "biz": "notice", "fin": "fin", "debt": "notice", "s186": "notice", "disc": "notice", "aud": "notice"};
let TX = { doc: "notice", scope: "", filter: "", dirty: {}, last: null }, PV_CUR = null, TAB = "common", SEL = null, ORD = null, PV_SCOPE = [], SCHEMA = {}, S = null, HINTS = {}, COMPANIES = [], HAS_MAP = false, CLOSED = {};
const $ = (s) => document.querySelector(s);
const slug = (s) => (s.trim().replace(/[^A-Za-z0-9]+/g, "_").replace(/^_+|_+$/g, "")) || "company";
const fyLabel = (y) => `${y - 1}-${String(y).slice(2)}`;
const dmyDisp = (s) => (s && /^\d{4}-\d\d-\d\d$/.test(s)) ? s.split("-").reverse().join("-") : "";

function el(tag, attrs = {}, kids = []) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") e.className = v; else if (k.startsWith("on")) e[k] = v; else if (v === false) continue; else if (v !== undefined && v !== null) e.setAttribute(k, v === true ? "" : v);
  }
  (Array.isArray(kids) ? kids : [kids]).forEach((c) => e.append(c && c.nodeType ? c : document.createTextNode(c ?? "")));
  return e;
}
function field(label, obj, key, o = {}) {
  let inp;
  if (o.options) {
    inp = el("select", {}, o.options.map((x) => { const [v, t] = Array.isArray(x) ? x : [x, x]; const op = el("option", { value: v }, t); return op; }));
    inp.value = obj[key] ?? o.options[0]?.[0] ?? o.options[0];
    if (obj[key] === undefined) obj[key] = inp.value;
  } else if (o.area) { inp = el("textarea"); inp.value = obj[key] ?? ""; }
  else { inp = el("input", { type: o.type || "text", placeholder: o.ph || "" }); inp.value = obj[key] ?? ""; if (o.step) inp.step = o.step; }
  inp.oninput = inp.onchange = () => { obj[key] = o.num ? inp.value : inp.value; o.onchange && o.onchange(inp.value); };
  const lab = el("label", { class: o.cls || "" }, [label, inp]);
  if (o.hint) lab.append(el("span", { class: "hint" }, o.hint));
  return lab;
}
function section(id, title, sub, bodyFn) {
  const body = el("div", { class: "body" });
  const card = el("section", { "data-id": id, class: "card" + (CLOSED[id] ? " closed" : "") }, [
    el("h2", { onclick: () => { CLOSED[id] = !CLOSED[id]; card.classList.toggle("closed"); } }, [el("span", {}, title), el("small", {}, sub || "")]), body]);
  bodyFn(body);
  return card;
}
function resize(arr, n, mk) { while (arr.length < n) arr.push(mk()); while (arr.length > n) arr.pop(); }
function countBox(label, arr, mk, min = 0) {
  const i = el("input", { type: "number", min, max: 60 }); i.value = arr.length;
  i.onchange = () => { resize(arr, Math.max(min, +i.value || 0), mk); render(); };
  return el("label", {}, [label, i]);
}
function listTable(cols, arr, rowFn, extra) {
  const t = el("table", { class: "t" });
  t.append(el("tr", {}, cols.map((c) => el("th", {}, c))));
  arr.forEach((it, i) => t.append(el("tr", {}, [...rowFn(it, i).map((c) => el("td", {}, c)),
    extra === false ? "" : el("td", {}, el("button", { class: "x", onclick: () => { arr.splice(i, 1); render(); } }, "✕"))])));
  return t;
}
const mini = (obj, key, o = {}) => { const l = field("", obj, key, o); return l.querySelector("input,select,textarea"); };

// ---------------------------------------------------------------- form
function render() {
  const root = $("#form"); const sy = window.scrollY; root.innerHTML = "";
  if (!S) return;
  const h = HINTS || {};
  const SECS = {}; const add = (t, n) => (SECS[t] = SECS[t] || []).push(n);
  if (!SEL) SEL = Object.fromEntries((SCHEMA.modules || []).map((m) => [m.id, true]));
  if (!ORD) ORD = SCHEMA.modules.map((m) => m.id);
  S.mods = S.mods || {}; S.ca = S.ca || {};

  add(TAB_OF["co"], section("co", "2 · Company details (fixed every year)", S.company || "", (b) => {
    const g = el("div", { class: "grid" }); b.append(g);
    g.append(field("Company name (full, e.g. ABC Private Limited)", S, "company", { cls: "wide" }),
      field("CIN", S, "cin"), field("Category", S, "category", { options: SCHEMA.categories }),
      field("Registered office address", S, "address", { cls: "full" }),
      field("Email", S, "email"), field("Phone 1", S, "phone1"), field("Phone 2 (optional)", S, "phone2"),
      field("Date of incorporation", S, "reg_date", { type: "date" }),
      field("Listed company?", S, "listed", { options: ["Not Applicable", "Yes - Listed"] }),
      field("Registrar & Transfer Agent", S, "rta"),
      field("Shares held in", S, "holding_form", { options: ["Physical", "Demat"] }),
      field("Face value per share (Rs.)", S, "face_value", { type: "number" }));
    const cid = slug(S.company || "");
    const up = el("input", { type: "file", accept: "image/*" });
    up.onchange = async () => { const fd = new FormData(); fd.append("file", up.files[0]); const r = await fetch("/api/routemap/" + cid, { method: "POST", body: fd }); if (r.ok) { HAS_MAP = true; render(); } };
    b.append(el("div", { class: "sub" }, "Route map image (Notice last page)"),
      el("div", { class: "hint" }, HAS_MAP ? "✓ Route map stored for this company – upload again to replace." : S.company ? "No route map stored yet – upload a screenshot of the AGM venue map." : "Enter the company name first, then upload the route map."), S.company ? up : "");
  }));

  add(TAB_OF["agm"], section("agm", "AGM details", `FY ${fyLabel(S.fy_end_year)}`, (b) => {
    const g = el("div", { class: "grid" }); b.append(g);
    g.append(field("AGM number (1,2,3…)", S, "agm_no", { type: "number" }),
      field("AGM date", S, "agm_date", { type: "date", hint: h.agm_date ? "Last year: " + dmyDisp(h.agm_date) : "" }),
      field("AGM time", S, "agm_time", { type: "time" }),
      field("AGM venue", S, "venue_mode", { options: [["registered", "At registered office"], ["other", "Other venue"]], onchange: render }));
    if (S.venue_mode === "other") g.append(field("Venue address", S, "venue_text", { cls: "wide" }));
  }));

  add(TAB_OF["dir"], section("dir", "4 · Directors", `${S.directors.length}`, (b) => {
    b.append(el("div", { class: "grid" }, [countBox("Number of directors", S.directors, () => ({ name: "", din: "", address: "", desig: "Director", appointed: "", ceased: "", remuneration: "" }), 1)]));
    b.append(listTable(["Name", "DIN", "Residential address (for List of Directors)", "Designation", "Date of appointment", "Date of cessation (blank = N.A.)", "Remuneration this year (Rs., blank = none)"], S.directors,
      (d) => [mini(d, "name"), mini(d, "din"), mini(d, "address"), mini(d, "desig", { options: ["Director", "Managing Director", "Whole-time Director", "Additional Director"] }), mini(d, "appointed", { type: "date" }), mini(d, "ceased", { type: "date" }), mini(d, "remuneration", { type: "number", step: "any" })]));
    b.append(el("div", { class: "hint" }, "Remuneration feeds the Annexure II remuneration table and the AOC-2 related-party table. Signatories = directors without a cessation date."));
  }));

  add(TAB_OF["bm"], section("bm", "5 · Board meetings", `${S.meetings.length}`, (b) => {
    b.append(el("div", { class: "grid" }, [countBox("Number of board meetings held", S.meetings, () => ({ date: "", absent: [] }))]));
    const t = el("table", { class: "t" }); t.append(el("tr", {}, ["#", "Date of meeting", "Directors on leave of absence (tick if absent)"].map((x) => el("th", {}, x))));
    S.meetings.forEach((m, i) => {
      const chips = el("div", { class: "chips" }, S.directors.filter((d) => d.name).map((d) => {
        const c = el("input", { type: "checkbox" }); c.checked = (m.absent || []).includes(d.name);
        c.onchange = () => { m.absent = (m.absent || []).filter((x) => x !== d.name); if (c.checked) m.absent.push(d.name); };
        return el("label", {}, [c, d.name]);
      }));
      t.append(el("tr", {}, [el("td", {}, i + 1), el("td", {}, [mini(m, "date", { type: "date" }), h.meetings && h.meetings[i] ? el("div", { class: "hint" }, "Last year: " + dmyDisp(h.meetings[i])) : ""]), el("td", {}, chips)]));
    });
    b.append(t, el("div", { class: "hint" }, "Directors shown for each meeting are worked out from appointment / cessation dates."));
  }));

  add(TAB_OF["sh"], section("sh", "6 · Share capital & shareholders", `${S.shareholders.length} holders`, (b) => {
    b.append(el("div", { class: "grid" }, [countBox("Number of shareholders", S.shareholders, () => ({ name: "", type: "Individual/HUF", promoter: true, begin: "", end: "" }), 1)]));
    b.append(listTable(["Name", "Type", "Promoter?", "Shares at start of year", "Shares at end of year"], S.shareholders,
      (s) => [mini(s, "name"), mini(s, "type", { options: ["Individual/HUF", "Body Corporate"] }),
        mini(s, "promoter", { options: [["true", "Yes"], ["false", "No (public)"]], onchange: (v) => { s.promoter = v === "true"; } }),
        mini(s, "begin", { type: "number" }), mini(s, "end", { type: "number" })]));
    // fix select values for boolean
    b.querySelectorAll("select").forEach((sel) => { if (sel.options[0]?.value === "true") { const i = [...b.querySelectorAll("select")].indexOf(sel); } });
    const tot = (k) => S.shareholders.reduce((a, s) => a + (+s[k] || 0), 0);
    b.append(el("div", { class: "hint" }, `Total shares: start ${tot("begin").toLocaleString("en-IN")} · end ${tot("end").toLocaleString("en-IN")} · paid-up capital Rs. ${(tot("end") * (+S.face_value || 0)).toLocaleString("en-IN")}`));
    b.append(el("div", { class: "grid" }, [field("Class of shares (List of Shareholders)", S, "share_class", { options: ["Equity", "Preference", "Equity & Preference"] })]));
    b.append(el("div", { class: "grid" }, [field("Details of change in shareholding (shown in Annexure II-C; leave blank if none)", S, "sh_change_note", { area: true, cls: "full", hint: "e.g. Transfer of 2,500 shares from A to B on 12-08-2025" })]));
    yesNo(b, "Share capital changed during the year?", S.capital, "Yes → write your own sentence", () => "During the Financial Year " + fyLabel(S.fy_end_year) + ", the paid-up share capital of the Company changed as follows: ____", null);
  }));

  add(TAB_OF["biz"], section("biz", "7 · Business activity (NIC code)", "", (b) => {
    b.append(el("div", { class: "grid" }, [countBox("Number of activities", S.nic, () => ({ desc: "", code: "", pct: "" }), 1)]));
    b.append(listTable(["Description of main products / services", "NIC code", "% of turnover"], S.nic, (n) => [mini(n, "desc"), mini(n, "code"), mini(n, "pct")]));
  }));

  add(TAB_OF["fin"], section("fin", "8 · Financial highlights", S.unit, (b) => {
    const g = el("div", { class: "grid" }); b.append(g);
    g.append(field("Amounts are in", S, "unit", { options: Object.entries(SCHEMA.units), onchange: render }));
    const rows = [["rev", "Revenue from operations & other income"], ["exp", "Expenditure"], ["dep", "Less: Depreciation"], ["exc", "Add: Exceptional items"], ["tax", "Current tax"], ["dtax", "Deferred tax (negative = credit)"], ["reserve", "Transfer to reserve (blank = Profit after tax)"]];
    const t = el("table", { class: "t" }); t.append(el("tr", {}, ["", `Current year (FY ${fyLabel(S.fy_end_year)})`, `Previous year (FY ${fyLabel(S.fy_end_year - 1)})`].map((x) => el("th", {}, x))));
    const out = el("div", { class: "hint" });
    S.fin = S.fin || { cur: {}, prev: {} };
    rows.forEach(([k, lab]) => t.append(el("tr", {}, [el("td", {}, lab), el("td", {}, mini(S.fin.cur, k, { type: "number", step: "any", onchange: calc })), el("td", {}, mini(S.fin.prev, k, { type: "number", step: "any", onchange: calc }))])));
    function calc() {
      const f = (c) => { const n = (x) => +x[c] || 0; const c0 = S.fin[c === "cur" ? "cur" : "prev"]; return 0; };
      const one = (c) => { const n = (k) => +(c[k] || 0); const pbdt = n("rev") - n("exp"), pbt = pbdt - n("dep") + n("exc"), pat = pbt - n("tax") - n("dtax"); return { pbdt, pbt, pat }; };
      const a = one(S.fin.cur), p = one(S.fin.prev); const fm = (x) => x.toLocaleString("en-IN", { maximumFractionDigits: 2 });
      out.textContent = `Auto-calculated → Current: PBT ${fm(a.pbt)} · PAT ${fm(a.pat)}   |   Previous: PBT ${fm(p.pbt)} · PAT ${fm(p.pat)}`;
    }
    calc(); b.append(t, out, el("div", { class: "hint" }, "Profit before depreciation / tax, profit after tax and EPS are calculated automatically. Previous year is rolled forward from last year's saved data."));
    b.append(el("div", { class: "sub" }, "Foreign exchange"), el("div", { class: "grid" }, [field("Foreign exchange earning – this year (blank = NIL)", S, "fx_earn", { type: "number", step: "any" }), field("Foreign exchange outgo – this year (blank = NIL)", S, "fx_out", { type: "number", step: "any" }), field("Foreign exchange earning – previous year", S, "fx_earn_prev", { type: "number", step: "any" }), field("Foreign exchange outgo – previous year", S, "fx_out_prev", { type: "number", step: "any" })]));
  }));

  add(TAB_OF["debt"], section("debt", "9 · Indebtedness (MGT-7)", "", (b) => {
    S.debt = S.debt || {};
    b.append(el("div", { class: "grid" }, [
      field("Opening principal – secured loans (Rs.)", S.debt, "open_sec", { type: "number", step: "any", hint: "Rolled forward from last year's closing" }),
      field("Opening principal – unsecured loans (Rs.)", S.debt, "open_unsec", { type: "number", step: "any" }),
      field("Addition during year – secured", S.debt, "add_sec", { type: "number", step: "any" }), field("Addition – unsecured", S.debt, "add_unsec", { type: "number", step: "any" }),
      field("Reduction during year – secured", S.debt, "red_sec", { type: "number", step: "any" }), field("Reduction – unsecured", S.debt, "red_unsec", { type: "number", step: "any" })]));
  }));

  add(TAB_OF["s186"], section("s186", "10 · Loans, investments, guarantees & related parties", "default: none", (b) => {
    const blk = (title, key, cols, fields) => {
      S[key] = S[key] || [];
      b.append(el("div", { class: "sub" }, title), el("div", { class: "hint" }, S[key].length ? "" : "None (document shows “-”). Add a row to change this."));
      if (S[key].length) b.append(listTable(cols, S[key], (r) => fields.map(([k, o]) => mini(r, k, o))));
      b.append(el("button", { onclick: () => { S[key].push({}); render(); } }, "+ Add row"));
    };
    const d = { type: "date" };
    blk("Loans given", "loans", ["Date", "Borrower", "Amount", "Purpose", "Period", "Date of BR", "Date of SR", "Interest rate", "Security"], [["date", d], ["party", {}], ["amount", {}], ["purpose", {}], ["period", {}], ["br", d], ["sr", d], ["rate", {}], ["security", {}]]);
    blk("Investments made", "investments", ["Date", "Investee", "Amount", "Date of BR", "Date of SR", "Expected return"], [["date", d], ["party", {}], ["amount", {}], ["br", d], ["sr", d], ["rate", {}]]);
    blk("Guarantees / security provided", "guarantees", ["Date", "Recipient", "Amount", "Purpose", "Date of BR", "Date of SR"], [["date", d], ["party", {}], ["amount", {}], ["purpose", {}], ["br", d], ["sr", d]]);
    blk("Other related-party transactions (AOC-2) – director remuneration is added automatically", "rpt", ["Party & relationship", "Nature", "Duration", "Date of Board approval", "Amount"], [["party", {}], ["nature", {}], ["duration", {}], ["br_date", d], ["amount", {}]]);
  }));

  add(TAB_OF["disc"], section("disc", "11 · Standard statements – answer Yes only where the default “No / nothing to report” sentence does not apply", "default: all No", (b) => {
    SCHEMA.toggles.forEach((t) => yesNo(b, t.label, (S.toggles[t.key] = S.toggles[t.key] || {}), t.default, () => t.hint, t));
    b.append(el("div", { class: "sub" }, "Website / Annual-return web link"));
    S.website = S.website || { has: "No", url: "" };
    b.append(el("div", { class: "grid" }, [field("Company has a website?", S.website, "has", { options: ["No", "Yes"], onchange: render }), S.website.has === "Yes" ? field("Website URL", S.website, "url", { cls: "wide" }) : ""]));
    b.append(el("div", { class: "sub" }, "Conservation of energy & technology absorption (default “No”)"));
    SCHEMA.inline.forEach((t) => {
      const st = (S.inline[t.key] = S.inline[t.key] || {});
      const g = el("div", { class: "grid" });
      g.append(field(t.label, st, "on", { options: [["", "No"], ["1", "Yes"]], onchange: (v) => { st.on = v === "1"; render(); } }));
      if (st.on) g.append(field("Details / answer", st, "text", { cls: "wide", ph: "Yes" }));
      const sel = g.querySelector("select"); sel.value = st.on ? "1" : "";
      b.append(g);
    });
    b.append(el("div", { class: "grid" }, [field("Year of import (default ----------)", S, "ta_year")]));
  }));

  add(TAB_OF["aud"], section("aud", "13 · Auditor paragraph wording", "", (b) => {
    S.auditor = S.auditor || {};
    b.append(el("div", { class: "hint" }, "Auditor name, FRN and city come from the CA / auditor details on the Common tab."));
    yesNo(b, "Use own wording for the auditor paragraph?", S.auditor, "Standard re-appointment wording", () => "M/s ____, Chartered Accountants, ____ be and are hereby appointed as Statutory Auditors of the company ...", null);
  }));

  // ---------------- common: CA details + signing
  add("common", section("ca", "CA / auditor details", S.ca.firm || "", (b) => {
    const g = el("div", { class: "grid" }); b.append(g);
    g.append(field("Firm name incl. “& Co.” (e.g. SHARMA & CO.)", S.ca, "firm", { cls: "wide" }), field("Firm registration no. (FRN)", S.ca, "frn"),
      field("Address (street, area, city) – printed on letters", S.ca, "address", { cls: "wide" }), field("City (auditor paragraph)", S.ca, "city"),
      field("Pincode", S.ca, "pincode"), field("State", S.ca, "state"), field("Partner / proprietor", S.ca, "partner"),
      field("Membership no.", S.ca, "membership"), field("Phone", S.ca, "phone"), field("Email", S.ca, "email"));
    const btn = el("button", { onclick: async () => { await fetch("/api/defaults", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ca: S.ca, sign_place: S.sign_place }) }); btn.textContent = "Saved ✓ – new companies start with these"; } }, "Save as my default for new companies");
    b.append(el("div", { class: "hint" }, "Used in the DSC letter, Rep. letter, Index cover and the auditor paragraph of the Directors' Report."), btn);
  }));
  add("common", section("sign", "Signing & letter dates", "", (b) => {
    b.append(el("div", { class: "grid" }, [field("Place of signing", S, "sign_place"),
      field("Date of signing (all documents)", S, "sign_date", { type: "date", hint: h.sign_date ? "Last year: " + dmyDisp(h.sign_date) : "" }),
      field("Date on letters (DSC & Rep. letter) – blank = signing date", S, "letter_date", { type: "date" })]));
  }));

  // ---------------- financial tab note
  // ---------------- module tabs
  const mod = (id) => SCHEMA.modules.find((m) => m.id === id);
  const header = (id) => {
    const m = mod(id);
    return el("section", { class: "card" }, [el("b", {}, m.label), el("div", { class: "hint" }, m.desc),
      el("button", { class: "primary", onclick: () => doPreview(id) }, "👁 Preview & download this document")]);
  };
  for (const id of ["notice", "directors", "shareholders", "dsc", "index", "policies", "mrl"]) (SECS[id] = SECS[id] || []).unshift(header(id));
  for (const id of ["directors", "shareholders", "dsc"]) add(id, el("section", { class: "card" }, el("div", { class: "hint" }, "This document is filled from the Common details tab (company, directors, shareholders, CA details, dates). Nothing else to enter.")));

  // Financials Index
  add("index", section("idx", "Attachments listed on the cover", "", (b) => {
    const mi = (S.mods.index = S.mods.index || {}); mi.att = mi.att || {}; mi.extra = mi.extra || [];
    const box = el("div", { class: "chips" });
    SCHEMA.index_att.forEach((lab) => { const c = el("input", { type: "checkbox" }); c.checked = mi.att[lab] !== false; c.onchange = () => (mi.att[lab] = c.checked); box.append(el("label", { style: "display:flex;margin:4px 0" }, [c, lab])); });
    b.append(box, el("div", { class: "sub" }, "Extra attachments"));
    mi.extra.forEach((x, i) => { const t = el("input", { value: x }); t.oninput = () => (mi.extra[i] = t.value); b.append(el("div", { style: "display:flex;gap:6px;margin:3px 0" }, [t, el("button", { class: "x", onclick: () => { mi.extra.splice(i, 1); render(); } }, "✕")])); });
    b.append(el("button", { onclick: () => { mi.extra.push(""); render(); } }, "+ Add attachment"));
  }));
  // Notes on accounts
  add("policies", section("pol", "Notes on Accounts details", "", (b) => {
    b.append(el("div", { class: "grid" }, [
      field("Business of the company (Overview note), e.g. manufacturing of desiccants and silica gel and related products", S, "business_desc", { area: true, cls: "full" }),
      field("Revenue recognition – business wording (blank = same as above)", S, "revenue_desc", { cls: "full" }),
      field("Address where books of accounts are maintained (blank = registered office)", S, "books_address", { cls: "full" })]));
    b.append(el("div", { class: "hint" }, "Deferred tax in note 2.5 and the foreign-currency table come from the Financials tab (negative deferred tax is shown as a deferred tax asset)."));
  }));
  // Management representation letter
  add("mrl", section("mrl", "Amounts as on 31 March (Rs., whole rupees)", "", (b) => {
    const mm = (S.mods.mrl = S.mods.mrl || {}); mm.toggles = mm.toggles || {};
    b.append(el("div", { class: "grid" }, [field("Cash in hand", mm, "cash", { type: "number", step: "any" }), field("Stock in hand", mm, "stock", { type: "number", step: "any" }),
      field("Sundry debtors", mm, "debtors", { type: "number", step: "any" }), field("Sundry creditors", mm, "creditors", { type: "number", step: "any" }),
      field("Revenue for the year (blank = from Financials tab)", mm, "revenue", { type: "number", step: "any" })]));
  }));
  add("mrl", section("mrlt", "Representations – answer Yes only where the standard statement does not apply", "default: standard wording", (b) => {
    const mm = (S.mods.mrl = S.mods.mrl || {}); mm.toggles = mm.toggles || {};
    SCHEMA.mrl_toggles.forEach((t) => yesNo(b, t.label, (mm.toggles[t.key] = mm.toggles[t.key] || {}), t.default, () => t.hint, t));
  }));

  // ---------------- assemble
  const ORDER = ["co", "ca", "sign", "dir", "sh"];
  (SECS.common || []).sort((a, b) => ORDER.indexOf(a.dataset?.id) - ORDER.indexOf(b.dataset?.id));
  window._SECS = SECS; drawTabs();
  window.scrollTo(0, sy);
}

const NAV = () => [
  { group: "Details" }, { id: "common", label: "Common details" }, { id: "fin", label: "Financials" },
  { group: "Documents" }, ...SCHEMA.modules.map((m) => ({ id: m.id, label: m.label })),
  { group: "Output" }, { id: "gen", label: "Select, order & generate" },
  { group: "Customise" }, { id: "texts", label: "Edit default text" }];
function genPage() {
  const mods = (id) => SCHEMA.modules.find((m) => m.id === id);
  const box = el("section", { class: "card" }); box.append(el("b", {}, "Select documents and set their order"),
    el("div", { class: "hint" }, "Tick what you need. Use ▲ ▼ to set the order – it is used for the merged PDF."));
  ORD.forEach((id, i) => {
    const c = el("input", { type: "checkbox" }); c.checked = !!SEL[id]; c.onchange = () => { SEL[id] = c.checked; };
    box.append(el("div", { class: "ord" }, [c, el("span", { class: "n" }, String(i + 1)), el("span", { class: "nm" }, mods(id).label),
      el("button", { disabled: i === 0, onclick: () => { [ORD[i - 1], ORD[i]] = [ORD[i], ORD[i - 1]]; drawNav(); } }, "▲"),
      el("button", { disabled: i === ORD.length - 1, onclick: () => { [ORD[i + 1], ORD[i]] = [ORD[i], ORD[i + 1]]; drawNav(); } }, "▼")]));
  });
  const chosen = () => ORD.filter((id) => SEL[id]);
  const need = () => { if (!S || !S.company.trim()) { alert("Select a company or enter the company name first."); return false; } if (!chosen().length) { alert("Tick at least one document."); return false; } return true; };
  box.append(el("div", { class: "actions" }, [
    el("button", { onclick: () => need() && doPreview(chosen()[0], chosen()) }, "👁 Preview selected"),
    el("button", { class: "primary", onclick: () => need() && finalDownload(chosen()) }, "⬇ Download selected (separate Word files)"),
    el("button", { class: "primary", onclick: () => need() && mergePdf(chosen()) }, "📄 Merge selected into one PDF")]));
  box.append(el("div", { class: "hint" }, "Word files are saved separately in the generated folder. The PDF merges the selected documents in the order above (needs Microsoft Word or LibreOffice on this computer)."));
  return box;
}
function drawNav() {
  const bar = $("#tabs"); bar.innerHTML = ""; const root = $("#form"); root.innerHTML = "";
  NAV().forEach((t) => t.group ? bar.append(el("div", { class: "grp" }, t.group))
    : bar.append(el("button", { class: "nav" + (TAB === t.id ? " on" : ""), onclick: () => { TAB = t.id; drawNav(); window.scrollTo(0, 0); } }, t.label)));
  if (TAB === "texts") root.append(textsPage());
  else if (TAB === "gen") root.append(genPage()); else (window._SECS?.[TAB] || []).forEach((n) => root.append(n));
  // pages that have input fields get a Save button at the bottom (not Directors / Shareholders / DSC / generate pages)
  if (["common", "fin", "notice", "index", "policies", "mrl"].includes(TAB)) {
    const sb = el("button", { class: "primary" }, "💾 Save to database"); sb.onclick = () => saveProgress(sb);
    root.append(el("div", { class: "savebar" }, [el("span", { class: "hint" }, "Saves everything entered so far (all tabs)."), sb]));
  }
}
const drawTabs = drawNav;

// ---------------------------------------------------------------- edit default text
function textsPage() {
  const box = el("div", {});
  const head = el("section", { class: "card" });
  const docSel = el("select"); SCHEMA.modules.forEach((m) => docSel.append(el("option", { value: m.id }, m.label))); docSel.value = TX.doc;
  const scopeSel = el("select");
  scopeSel.append(el("option", { value: "" }, "All companies (default wording for everyone)"));
  COMPANIES.forEach((c) => scopeSel.append(el("option", { value: c.id }, "Only for: " + c.company)));
  scopeSel.value = TX.scope;
  const search = el("input", { placeholder: "Search text…", value: TX.filter });
  docSel.onchange = () => { if (!confirmLoseEdits()) { docSel.value = TX.doc; return; } TX.doc = docSel.value; TX.dirty = {}; drawNav(); };
  scopeSel.onchange = () => { if (!confirmLoseEdits()) { scopeSel.value = TX.scope; return; } TX.scope = scopeSel.value; TX.dirty = {}; drawNav(); };
  head.append(el("b", {}, "Edit the fixed wording of a document"),
    el("div", { class: "hint" }, "Pick a document and who the change is for. Change the text, then press Save. New documents are generated with your wording. Words in {{double braces}} are fields filled in by the program – keep them as they are (or move them inside the sentence)."),
    el("div", { class: "grid" }, [el("label", {}, ["Document", docSel]), el("label", {}, ["Apply changes to", scopeSel]), el("label", {}, ["Find", search])]));
  const body = el("div", {}); box.append(head, body);
  const bar = el("div", { class: "savebar" });
  box.append(bar);

  function confirmLoseEdits() { return !Object.keys(TX.dirty).length || confirm("You have unsaved text changes. Discard them?"); }
  async function load() {
    body.innerHTML = ""; body.append(el("div", { class: "hint" }, "Loading…"));
    const r = await fetch(`/api/texts/${TX.doc}` + (TX.scope ? `?cid=${encodeURIComponent(TX.scope)}` : ""));
    TX.last = await r.json(); draw();
  }
  function srcBadge(it) {
    const map = { original: ["original", "bd-orig"], global: ["edited for all companies", "bd-glob"], company: ["edited for this company", "bd-comp"] };
    const m = map[it.source] || map.original; return el("span", { class: "bd " + m[1] }, m[0]);
  }
  function draw() {
    body.innerHTML = "";
    const q = (search.value || "").toLowerCase(); TX.filter = search.value;
    const data = TX.last;
    const chips = el("div", { class: "chips-row" }, [el("span", { class: "hint" }, "Fields you can insert (click while editing a box): ")]);
    let focusTa = null;
    data.tokens.forEach((t) => chips.append(el("button", { class: "chip", onclick: () => { if (!focusTa) return alert("Click inside a text box first."); const s = focusTa.selectionStart, e = focusTa.selectionEnd; focusTa.setRangeText(`{{${t}}}`, s, e, "end"); focusTa.dispatchEvent(new Event("input")); focusTa.focus(); } }, t)));
    body.append(el("section", { class: "card" }, [chips, el("div", { class: "hint" }, "Tip: type <b>word</b> to make a word bold, <sup>th</sup> for superscript. Other formatting (font, size, alignment) stays as in the document.")]));
    let shown = 0;
    data.items.forEach((it) => {
      if (it.kind === "table") { if (!q) body.append(el("div", { class: "tbl-mark" }, "▦ " + it.note + (it.orig ? " — " + it.orig : ""))); return; }
      const cur = it.pid in TX.dirty ? TX.dirty[it.pid] : it.text;
      if (q && !(cur + " " + (it.label || "")).toLowerCase().includes(q)) return;
      shown++;
      if (it.kind === "locked" || it.kind === "computed") {
        body.append(el("div", { class: "tx-lock" }, [el("div", { class: it.bold ? "b" : "" }, it.kind === "locked" ? it.text : "(automatic paragraph)"), el("div", { class: "hint" }, "🔒 " + it.note)]));
        return;
      }
      const ta = el("textarea", { rows: 2 }); ta.value = cur;
      const fit = () => { ta.style.height = "auto"; ta.style.height = Math.min(ta.scrollHeight + 2, 420) + "px"; };
      const card = el("div", { class: "tx-item" + (it.source !== "original" ? " edited" : "") + (it.pid in TX.dirty ? " dirty" : "") });
      const reset = el("button", { class: "ghost small", title: it.source === "company" ? "Remove this company's change (falls back to the all-companies / original text)" : "Back to the original text" }, "↺ Reset");
      reset.disabled = it.source === "original" && !(it.pid in TX.dirty) || (!TX.scope && it.source === "company");
      reset.onclick = async () => {
        if (it.pid in TX.dirty && it.source === "original") { delete TX.dirty[it.pid]; return draw(); }
        const r = await fetch(`/api/texts/${TX.doc}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ scope: TX.scope ? "company" : "global", cid: TX.scope || null, changes: { [it.pid]: null } }) });
        if (!r.ok) return alert((await r.json().catch(() => ({}))).error || "Failed");
        delete TX.dirty[it.pid]; load();
      };
      ta.oninput = () => { fit(); if (ta.value === it.text) delete TX.dirty[it.pid]; else TX.dirty[it.pid] = ta.value; card.classList.toggle("dirty", it.pid in TX.dirty); updateBar(); };
      ta.onfocus = () => (focusTa = ta);
      card.append(el("div", { class: "tx-top" }, [el("span", { class: "tx-lab" }, it.label || (it.bold ? "Heading" : "")), srcBadge(it), reset]), ta);
      if (it.kind === "std") card.append(el("div", { class: "hint" }, "Standard sentence used when the answer is “No”. Use {fy}, {fy_end_ord}, {company}, {company_upper}, {agm_year} for values."));
      body.append(card); setTimeout(fit, 0);
    });
    if (!shown) body.append(el("div", { class: "hint" }, "Nothing matches."));
    updateBar();
  }
  function updateBar() {
    bar.innerHTML = "";
    const n = Object.keys(TX.dirty).length;
    const prev = el("button", { onclick: () => { if (!S || !S.company.trim()) return alert("Open or enter a company first (Common details) so the preview has data."); if (n && !confirm("Preview uses SAVED text only. Save first?")) return; doPreview(TX.doc); } }, "👁 Preview this document");
    const resetAll = el("button", { class: "ghost", onclick: async () => {
      if (!confirm(TX.scope ? "Remove ALL changes made only for this company in this document?" : "Put ALL paragraphs of this document back to the original wording (for every company)?")) return;
      await fetch(`/api/texts/${TX.doc}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ scope: TX.scope ? "company" : "global", cid: TX.scope || null, changes: {}, reset_all: true }) });
      TX.dirty = {}; load();
    } }, TX.scope ? "Remove this company's changes" : "Reset document to original");
    const save = el("button", { class: "primary" }, n ? `💾 Save ${n} change${n > 1 ? "s" : ""}` : "💾 Save changes"); save.disabled = !n;
    save.onclick = async () => {
      const r = await fetch(`/api/texts/${TX.doc}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ scope: TX.scope ? "company" : "global", cid: TX.scope || null, changes: TX.dirty }) });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) return alert(j.error || "Could not save");
      TX.dirty = {}; await load(); save.textContent = "✓ Saved";
    };
    bar.append(el("span", { class: "hint" }, n ? "Unsaved changes in this document." : ""), resetAll, prev, save);
  }
  search.oninput = () => draw();
  load();
  return box;
}


function yesNo(parent, label, st, std, hintFn, t) {
  const box = el("div", { class: "tg" });
  const sel = el("select"); [["", "No"], ["1", "Yes"]].forEach(([v, x]) => sel.append(el("option", { value: v }, x))); sel.value = st.on ? "1" : "";
  box.append(el("div", {}, el("b", {}, label)), sel);
  if (!st.on) box.append(el("div", { class: "std" }, "Document says: " + std));
  else {
    if (!st.text && hintFn) st.text = hintFn();
    const ta = el("textarea"); ta.value = st.text || ""; ta.oninput = () => (st.text = ta.value);
    box.append(ta, el("div", { class: "std" }, "Placeholders like {fy}, {fy_end_ord} are filled in automatically."));
  }
  sel.onchange = () => { st.on = sel.value === "1"; if (!st.on) st.text = ""; render(); };
  parent.append(box);
}

// ---------------------------------------------------------------- data
async function loadCompanies(selectId, selectFy) {
  COMPANIES = await (await fetch("/api/companies")).json();
  const sel = $("#companySel"); sel.innerHTML = "";
  sel.append(el("option", { value: "" }, "— select a company —"));
  COMPANIES.forEach((c) => sel.append(el("option", { value: c.id }, c.company)));
  if (selectId) sel.value = selectId;
  fillFy(selectFy);
}
function fillFy(keepFy) {
  const c = COMPANIES.find((x) => x.id === $("#companySel").value); const sel = $("#fySel"); sel.innerHTML = "";
  if (!c) { sel.append(el("option", { value: "" }, "—")); return; }
  const next = fyLabel(+c.years[0].slice(0, 4) + 2);
  sel.append(el("option", { value: "" }, `New year: FY ${next} (pre-filled from ${c.years[0]})`));
  c.years.forEach((y) => sel.append(el("option", { value: y }, `Re-open saved FY ${y}`)));
  if (keepFy && c.years.includes(keepFy)) sel.value = keepFy;   // stay on the year being worked on
}
let OPEN_SEQ = 0;
async function openCompany() {
  const id = $("#companySel").value; if (!id) return;
  const fy = $("#fySel").value, my = ++OPEN_SEQ;
  $("#loadedMsg").textContent = "Loading…";
  const r = await (await fetch(`/api/company/${id}` + (fy ? `?fy=${fy}` : ""))).json();
  if (my !== OPEN_SEQ) return;          // a newer selection was made meanwhile
  S = r.form; HINTS = r.hints || {}; HAS_MAP = r.has_map; CLOSED = {}; FY_PENDING = false; $("#loadedMsg").textContent = r.loaded; render();
}
async function newCompany() {
  const r = await (await fetch("/api/new")).json(); S = r.form; HINTS = {}; HAS_MAP = false; CLOSED = {}; FY_PENDING = true;
  $("#companySel").value = ""; fillFy(); $("#loadedMsg").textContent = "New company – fill in the details below; they are saved for next year when you download."; render();
}
$("#companySel").onchange = () => { fillFy(); openCompany(); };
$("#fySel").onchange = openCompany;

// ---------------------------------------------------------------- preview / download
async function doPreview(modId, scope) {
  if (!S) return alert("Select a company or click “New company” first.");
  if (!S.company.trim()) return alert("Please enter the company name.");
  if (!(await confirmFy())) return;
  if (scope) PV_SCOPE = scope; else if (!PV_SCOPE.includes(modId)) PV_SCOPE = [modId];
  const id = modId || PV_SCOPE[0];
  PV_CUR = id;
  $("#status").textContent = "Building preview…";
  const r = await fetch("/api/preview", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ form: S, module: id }) });
  $("#status").textContent = "";
  if (!r.ok) { const e = await r.json().catch(() => ({})); return alert("Could not build the document: " + (e.error || r.status)); }
  const blob = await r.blob();
  const sel = $("#pvMod"); sel.innerHTML = ""; sel.style.display = PV_SCOPE.length > 1 ? "" : "none";
  PV_SCOPE.forEach((mid) => { const m = SCHEMA.modules.find((x) => x.id === mid); const o = el("option", { value: mid }, m.label); if (mid === id) o.selected = true; sel.append(o); });
  const one = PV_SCOPE.length === 1, label = SCHEMA.modules.find((x) => x.id === id).label;
  $("#pvTitle").textContent = one ? "Preview – " + label : `Preview (${PV_SCOPE.length} documents)`;
  const b1 = $("#pvSaveOne"); b1.style.display = one ? "none" : ""; b1.textContent = "⬇ Save & download only “" + label + "”";
  $("#pvSave").textContent = one ? "⬇ Save & download this document" : `⬇ Save & download all ${PV_SCOPE.length} (separate Word files)`;
  $("#modal").classList.remove("hidden"); const body = $("#pvBody"); body.innerHTML = "";
  await docx.renderAsync(blob, body, null, { className: "docx", inWrapper: true, ignoreWidth: false, breakPages: true });
  $("#pvNote").textContent = id === "notice" && !HAS_MAP ? "  ⚠ No route map stored for this company – the last Notice page shows a placeholder." : "";
}
function closePreview() { $("#modal").classList.add("hidden"); }
const isDesktop = () => !!(window.pywebview && window.pywebview.api);
function fetchFile(rel, name) { const a = el("a", { href: "/api/file?rel=" + encodeURIComponent(rel), download: name }); document.body.append(a); a.click(); a.remove(); }
async function finalDownload(ids) {
  const chosen = ids || PV_SCOPE;
  if (!chosen.length) return alert("Tick at least one document to generate.");
  if (!(await confirmFy())) return;
  $("#status").textContent = "Generating…";
  const r = await fetch("/api/generate", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ form: S, modules: chosen }) });
  const j = await r.json().catch(() => ({})); $("#status").textContent = "";
  if (!r.ok) return alert(j.error || "Failed");
  const list = j.saved.map((s) => "• " + s.label).join("\n");
  if (isDesktop()) {
    if (confirm("Saved ✓ " + j.saved.length + " document(s)\n" + j.folder + "\n\n" + list + "\n\nOpen the folder now?"))
      await fetch("/api/openfolder", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ which: "generated", sub: j.cid + "/" + j.fy }) });
  } else if (j.saved.length === 1) fetchFile(j.saved[0].rel, j.saved[0].name);
  else { const a = el("a", { href: "/api/zip?cid=" + encodeURIComponent(j.cid) + "&fy=" + encodeURIComponent(j.fy) }); document.body.append(a); a.click(); a.remove(); }
  closePreview();
  await loadCompanies(slug(S.company), fyLabel(+S.fy_end_year)); $("#loadedMsg").textContent = `Saved ✓ ${j.saved.length} document(s) in ${j.folder}   (data stored in ${j.db})`;
}
async function mergePdf(ids) {
  $("#status").textContent = "Building PDF… (can take a minute)";
  const r = await fetch("/api/pdf", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ form: S, modules: ids }) });
  const j = await r.json().catch(() => ({})); $("#status").textContent = "";
  if (!r.ok) return alert(j.error || "Could not create the PDF");
  if (isDesktop()) { if (confirm("PDF saved ✓\n" + j.path + "\n\nOpen it now?")) await fetch("/api/openfile", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ rel: j.rel }) }); }
  else fetchFile(j.rel, j.name);
  await loadCompanies(j.cid, fyLabel(+S.fy_end_year)); $("#loadedMsg").textContent = "Merged PDF saved ✓ " + j.path + "   (company data saved to the database)";
}
async function saveProgress(btn) {
  if (!S) return alert("Select a company or click “New company” first.");
  if (!S.company.trim()) return alert("Please enter the company name first.");
  if (!(await confirmFy())) return;
  const r = await fetch("/api/save", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ form: S }) });
  const j = await r.json().catch(() => ({})); if (!r.ok) return alert(j.error || "Could not save");
  await loadCompanies(j.cid, j.fy);
  const t = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  $("#loadedMsg").textContent = `Saved to database ✓ (${t}) – FY ${j.fy}`;
  if (btn) { const o = btn.textContent; btn.textContent = "✓ Saved"; setTimeout(() => (btn.textContent = o), 1500); }
}
document.addEventListener("keydown", (e) => { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") { e.preventDefault(); saveProgress(); } });
async function openFolder(which) { await fetch("/api/openfolder", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ which }) }); }

async function openSettings(first) {
  fetch("/api/version").then((r) => r.json()).then((v) => { $("#buildInfo").textContent = "Build " + v.build; });
  fetch("/api/update/info").then((r) => r.json()).then((u) => { $("#updUrl").value = u.manifest_url.includes("OWNER/REPO") ? "" : u.manifest_url; $("#rollBtn").style.display = u.can_rollback ? "" : "none";
    $("#updInfo").textContent = `Installed: version ${u.version} (build ${u.build}). Updates never touch your data (database, generated files, settings).` + (u.frozen ? "" : " Updating works in the installed ROCCompliance.exe."); });
  const c = await (await fetch("/api/config")).json();
  $("#setGen").value = c.generated; $("#setDb").value = c.db; $("#setErr").textContent = "";
  $("#setTitle").textContent = first ? "Welcome – choose where to keep your files" : "Folder settings";
  $("#setIntro").textContent = first ? "Pick these once. You can change them later from ⚙ Settings (top right)." : "Changing a folder does not delete anything in the old one.";
  $("#copyRow").style.display = first ? "none" : "";
  $("#setCancel").style.display = first ? "none" : "";
  $("#settings").classList.remove("hidden");
}
function viewLogo() { $("#lvImg").src = "/api/logo?t=" + Date.now(); $("#logoView").classList.remove("hidden"); }
function closeLogo() { $("#logoView").classList.add("hidden"); }
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeLogo(); });
function refreshLogo() {
  const u = "/api/logo?t=" + Date.now();
  ["#brandLogo", "#logoPrev"].forEach((s) => { const e = $(s); if (e) e.src = u; });
  const f = $("#favLink"); if (f) f.href = u;
}
async function uploadLogo(inp) {
  const file = inp.files[0]; if (!file) return;
  const fd = new FormData(); fd.append("file", file);
  const r = await fetch("/api/logo", { method: "POST", body: fd });
  const j = await r.json().catch(() => ({})); inp.value = "";
  $("#logoMsg").textContent = r.ok ? "Logo updated ✓" : (j.error || "Could not use that image");
  $("#logoMsg").className = "msg" + (r.ok ? "" : " warn");
  if (r.ok) refreshLogo();
}
async function resetLogo() {
  await fetch("/api/logo/reset", { method: "POST" }); $("#logoMsg").textContent = "Default logo restored ✓"; refreshLogo();
}
async function browse(id) {
  if (window.pywebview && window.pywebview.api && window.pywebview.api.pick_folder) {
    const p = await window.pywebview.api.pick_folder($("#" + id).value); if (p) $("#" + id).value = p;
  } else alert("Type or paste the folder path into the box (the Browse dialog is available in the desktop app).");
}
async function saveSettings() {
  const r = await fetch("/api/config", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ generated: $("#setGen").value, db: $("#setDb").value, copy: $("#setCopy").checked }) });
  const j = await r.json(); if (!r.ok) { $("#setErr").textContent = j.error; return; }
  $("#settings").classList.add("hidden"); await loadCompanies(); $("#loadedMsg").textContent = "Folders saved ✓  Files: " + j.generated + "   Database: " + j.db;
}

(async () => { SCHEMA = await (await fetch("/api/schema")).json(); await loadCompanies(); if (!S) await newCompany(); const c = await (await fetch("/api/config")).json(); if (!c.configured) openSettings(true); })();


// ---------------------------------------------------------------- application updates
let UPD = null;
async function jpost(url, body) { const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) }); return r.json().catch(() => ({})); }
async function checkUpdate(manual) {
  const m = $("#updMsg"); if (manual) m.textContent = "Checking…";
  let r; try { r = await jpost("/api/update/check"); } catch (e) { r = { ok: false, error: "Could not reach the app." }; }
  if (!r.ok) { if (manual) m.textContent = r.error; return; }
  if (!r.available) { UPD = null; if (manual) { m.textContent = "You have the latest version."; $("#updNow").classList.add("hidden"); } return; }
  UPD = r;
  const txt = `Update available: ${r.version}` + (r.notes ? ` – ${r.notes}` : "");
  $("#updText").textContent = txt; $("#updBanner").classList.remove("hidden");
  if (manual) { m.textContent = txt; $("#updNow").classList.remove("hidden"); }
}
async function installUpdate() {
  if (!UPD) return;
  if (!confirm("Install the update now? ROC Compliance will close and reopen. Your data is not touched.")) return;
  $("#updText").textContent = "Downloading update… please wait"; $("#updMsg").textContent = "Downloading update… please wait";
  const r = await jpost("/api/update/install", { url: UPD.url, sha256: UPD.sha256 });
  if (!r.ok) { $("#updText").textContent = "Update failed: " + (r.error || ""); $("#updMsg").textContent = "Update failed: " + (r.error || ""); return; }
  document.body.innerHTML = '<div style="font:16px sans-serif;padding:60px;text-align:center">Updating… ROC Compliance will reopen in a few seconds.</div>';
}
async function updateFromFile(inp) {
  const f = inp.files[0]; if (!f) return;
  if (!confirm("Install " + f.name + " as the new version? The app will close and reopen. Your data is not touched.")) { inp.value = ""; return; }
  const fd = new FormData(); fd.append("file", f);
  $("#updMsg").textContent = "Installing…";
  const r = await (await fetch("/api/update/file", { method: "POST", body: fd })).json().catch(() => ({}));
  inp.value = "";
  if (!r.ok) { $("#updMsg").textContent = "Update failed: " + (r.error || ""); return; }
  document.body.innerHTML = '<div style="font:16px sans-serif;padding:60px;text-align:center">Updating… ROC Compliance will reopen in a few seconds.</div>';
}
async function rollbackUpdate() {
  if (!confirm("Go back to the previous version? The app will close and reopen. Your data is not touched.")) return;
  const r = await jpost("/api/update/rollback");
  if (!r.ok) { $("#updMsg").textContent = r.error || "Could not roll back."; return; }
  document.body.innerHTML = '<div style="font:16px sans-serif;padding:60px;text-align:center">Rolling back… ROC Compliance will reopen in a few seconds.</div>';
}
async function saveUpdSrc() {
  const b = { manifest_url: $("#updUrl").value }; if ($("#updTok").value) b.token = $("#updTok").value;
  await jpost("/api/update/config", b); $("#updMsg").textContent = "Update source saved."; $("#updTok").value = "";
}
setTimeout(() => checkUpdate(false), 3000);


// ---------------------------------------------------------------- light / dark mode
function curTheme() { return document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light"; }
function paintThemeBtn() { const b = $("#themeBtn"); if (b) { const d = curTheme() === "dark"; b.textContent = d ? "☀️" : "🌙"; b.title = d ? "Switch to light mode" : "Switch to dark mode"; } }
function toggleTheme() {
  const t = curTheme() === "dark" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", t);
  try { localStorage.setItem("roc_theme", t); } catch (e) {}
  paintThemeBtn();
}
paintThemeBtn();


// ---------------------------------------------------------------- which financial year?
let FY_PENDING = false, FY_RES = null;
const curFyEnd = () => { const n = new Date(); return n.getMonth() >= 3 ? n.getFullYear() + 1 : n.getFullYear(); };   // Apr-Mar
function paintFy() {
  const e = $("#fyNow"); if (!e) return;
  e.innerHTML = "";
  if (!S || $("#companySel").value) return;      // a saved company: the year list above already says which year
  e.append(el("span", {}, "Working on: "), el("b", {}, "FY " + fyLabel(+S.fy_end_year) + (FY_PENDING ? " (not confirmed yet)" : "")), " ",
    el("a", { href: "#", class: "fy-link", onclick: (ev) => { ev.preventDefault(); changeFy(); } }, "Change year"));
}
function parseFy(t) {
  t = (t || "").trim(); let m;
  if ((m = t.match(/^(\d{4})\s*[-–\/]\s*(\d{2}|\d{4})$/))) { const a = +m[1], b = m[2].length === 2 ? Math.floor(a / 100) * 100 + +m[2] : +m[2]; return b === a + 1 || (m[2].length === 2 && (a + 1) % 100 === +m[2]) ? a + 1 : null; }
  if ((m = t.match(/^(\d{4})$/))) return +m[1];      // a single year = the year ending 31 March
  return null;
}
function askFy(must) {
  return new Promise((res) => {
    FY_RES = res; $("#fyAskWarn").classList.toggle("hidden", !must); $("#fyAskCancel").classList.toggle("hidden", !!must); const cur = curFyEnd(), sel = $("#fyAskSel"); sel.innerHTML = "";
    $("#fyAskCur").textContent = `Today the current financial year is ${fyLabel(cur)}.`;
    for (let y = cur; y >= cur - 6; y--) sel.append(el("option", { value: y }, fyLabel(y) + (y === cur ? "  (current)" : "")));
    sel.append(el("option", { value: "other" }, "Other – type manually…"));
    const have = +S.fy_end_year; sel.value = (have <= cur && have >= cur - 6 && !FY_PENDING) ? have : cur;
    $("#fyAskOtherRow").classList.add("hidden"); $("#fyAskOther").value = ""; $("#fyAskErr").textContent = "";
    sel.onchange = () => $("#fyAskOtherRow").classList.toggle("hidden", sel.value !== "other");
    $("#fyAsk").classList.remove("hidden");
  });
}
function fyAskDone(v) { $("#fyAsk").classList.add("hidden"); const r = FY_RES; FY_RES = null; if (r) r(v); }
function fyAskOk() {
  const sel = $("#fyAskSel"); let y = sel.value === "other" ? parseFy($("#fyAskOther").value) : +sel.value;
  if (!y || y < 1990 || y > 2100) { $("#fyAskErr").textContent = "Please type a year like 2021-22."; return; }
  fyAskDone(y);
}
async function changeFy() {
  const y = await askFy(false); if (!y) return;
  S.fy_end_year = y; FY_PENDING = false; render();
}
async function confirmFy() {
  if (!FY_PENDING) return true;
  const y = await askFy(false); if (!y) return false;
  S.fy_end_year = y; FY_PENDING = false; paintFy(); render(); return true;
}
// keep "Working on" line in step with the form
const _render = render; render = function () { _render.apply(this, arguments); paintFy(); };

// starting to fill a NEW company without having chosen the year -> warn and ask first
let FY_ASKING = false;
document.addEventListener("input", async (e) => {
  if (!FY_PENDING || FY_ASKING || !S || !e.target.closest || !e.target.closest("#form")) return;
  FY_ASKING = true;
  const y = await askFy(true);
  FY_ASKING = false;
  if (y && FY_PENDING) { S.fy_end_year = y; FY_PENDING = false; paintFy(); render(); }
}, true);
