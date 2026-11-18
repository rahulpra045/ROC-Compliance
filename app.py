"""ROC Compliance – local web app.   Run:  python app.py"""
import copy, io, json, os, re, sys, threading, webbrowser
from datetime import datetime
from decimal import Decimal
from flask import Flask, jsonify, request, send_file, send_from_directory, abort

import engine, modules
from schema import PARA_TOGGLES, INLINE_TOGGLES, UNITS, CATEGORIES, MODULES, MRL_TOGGLES, INDEX_ATTACHMENTS

from paths import RES, DATA, FROZEN
def paths_frozen(): return FROZEN
BASE = DATA
os.chdir(BASE)
_cfg = os.path.join(BASE, "config.json")
_docs = os.path.join(os.path.expanduser("~"), "Documents", "NoticeGenerator")
try:
    CFG = json.load(open(_cfg))
except Exception:
    CFG = {}
CFG.setdefault("port", 5055)
CONFIGURED = bool(CFG.get("configured"))
def _abs(p): return p if os.path.isabs(p) else os.path.join(BASE, p)
GEN = _abs(CFG.get("generated_folder") or os.path.join(_docs, "generated"))
DB = _abs(CFG.get("db_folder") or os.path.join(_docs, "db"))
if CONFIGURED:
    os.makedirs(GEN, exist_ok=True); os.makedirs(DB, exist_ok=True)

import logging
import texts
logging.getLogger("werkzeug").setLevel(logging.ERROR)          # no request lines in the console
try:
    import flask.cli; flask.cli.show_server_banner = lambda *a, **k: None   # no "development server" warning
except Exception: pass
app = Flask(__name__, static_folder=os.path.join(RES, "static"), static_url_path="")


def slug(s):
    return re.sub(r"[^A-Za-z0-9]+", "_", s.strip()).strip("_") or "company"

texts.DB_GETTER = lambda: DB

def db_path(cid): return os.path.join(DB, cid + ".json")
def map_path(cid): return os.path.join(DB, cid + "_routemap.png")

def update_json_safely(path, mutate, default):
    """Read-modify-write under a lock file: two laptops saving at the same moment cannot lose each other's changes."""
    import time
    lock = path + ".lock"
    for _ in range(150):
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY); os.close(fd); break
        except FileExistsError:
            try:
                if time.time() - os.path.getmtime(lock) > 30: os.remove(lock)   # stale lock from a crashed save
            except OSError: pass
            time.sleep(0.1)
    try:
        try: data = json.load(open(path, encoding="utf-8"))
        except FileNotFoundError: data = default
        mutate(data)
        tmp = path + ".tmp"
        json.dump(data, open(tmp, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        os.replace(tmp, path)
        return data
    finally:
        try: os.remove(lock)
        except OSError: pass


def who():
    import getpass, socket
    try: return f"{getpass.getuser()}@{socket.gethostname()}"
    except Exception: return "unknown"


def load(cid):
    try:
        return json.load(open(db_path(cid), encoding="utf-8"))
    except FileNotFoundError:
        return None

def fy_label(end_year): return f"{end_year-1}-{str(end_year)[2:]}"


def get_defaults():
    """CA details used to pre-fill: saved default (db folder, shared) > config.json > built-in seed."""
    for fn in (lambda: json.load(open(os.path.join(DB, "_defaults.json"), encoding="utf-8")),
               lambda: CFG.get("defaults"),
               lambda: json.load(open(os.path.join(RES, "default_ca.json"), encoding="utf-8"))):
        try:
            d = fn()
            if d and (d.get("ca") or d.get("sign_place")): return d
        except Exception:
            pass
    return {}


def fill_ca(f):
    """Pre-fill an entirely empty CA block from the default."""
    ca = f.get("ca") or {}
    if not any(str(v).strip() for v in ca.values()):
        f["ca"] = copy.deepcopy(get_defaults().get("ca") or {})
    if not str(f.get("sign_place", "")).strip():
        f["sign_place"] = get_defaults().get("sign_place", "")
    return f


def blank_form():
    n = datetime.now()
    y = n.year if n.month >= 4 else n.year - 1
    dflt = get_defaults()
    f = {"company": "", "cin": "", "address": "", "email": "", "phone1": "", "phone2": "",
         "category": CATEGORIES[0], "listed": "Not Applicable", "rta": "NA", "reg_date": "",
         "holding_form": "Physical", "fy_end_year": y, "agm_no": 1, "agm_date": "", "agm_time": "11:00",
         "venue_mode": "registered", "venue_text": "", "sign_place": dflt.get("sign_place", ""), "sign_date": "", "face_value": "10",
         "directors": [{"name": "", "din": "", "address": "", "desig": "Director", "appointed": "", "ceased": "", "remuneration": ""}],
         "meetings": [], "shareholders": [{"name": "", "type": "Individual/HUF", "promoter": True, "begin": "", "end": ""}],
         "sh_change_note": "", "nic": [{"desc": "", "code": "", "pct": "100"}], "unit": "hundreds",
         "fin": {"cur": {}, "prev": {}}, "debt": {}, "loans": [], "investments": [], "guarantees": [], "rpt": [],
         "fx_earn": "", "fx_out": "", "fx_earn_prev": "", "fx_out_prev": "", "ta_year": "", "inline": {}, "toggles": {},
         "capital": {"on": False, "text": ""}, "website": {"has": "No", "url": ""},
         "auditor": {"on": False, "text": ""}, "ca": copy.deepcopy(dflt.get("ca") or {}),
         "business_desc": "", "revenue_desc": "", "books_address": "", "letter_date": "", "share_class": "Equity", "mods": {}}
    return modules.migrate(f)


def carry_forward(prev):
    """Next year's form from last year's: fixed data stays, yearly data resets/rolls."""
    prev = modules.migrate(copy.deepcopy(prev))
    f = copy.deepcopy(prev)
    hints = {"agm_date": prev.get("agm_date", ""), "sign_date": prev.get("sign_date", ""),
             "meetings": [m.get("date", "") for m in prev.get("meetings", [])]}
    f["fy_end_year"] = int(prev["fy_end_year"]) + 1
    f["agm_no"] = int(prev.get("agm_no") or 0) + 1
    f["agm_date"] = ""; f["sign_date"] = ""; f["letter_date"] = ""
    f["meetings"] = [{"date": "", "absent": []} for _ in prev.get("meetings", [])]
    for s in f.get("shareholders", []):
        s["begin"] = s.get("end", "")
    f["sh_change_note"] = ""
    f["fin"] = {"cur": {}, "prev": copy.deepcopy((prev.get("fin") or {}).get("cur", {}))}
    try:
        _, gen_f = engine.generate(prev)
        cur = gen_f["_cur"]
        fmt = lambda x: "" if x is None else str(x)
        f["fin"]["prev"] = {k: fmt(cur[k]) for k in ("rev", "exp", "dep", "exc", "tax", "dtax", "reserve")}
    except Exception:
        pass
    d = prev.get("debt") or {}
    g = lambda k: engine.num(d.get(k)) or Decimal(0)
    cs = g("open_sec") + g("add_sec") - g("red_sec"); cu = g("open_unsec") + g("add_unsec") - g("red_unsec")
    f["debt"] = {"open_sec": str(cs) if cs else "", "open_unsec": str(cu) if cu else ""}
    for k in ("loans", "investments", "guarantees", "rpt"): f[k] = []
    f["fx_earn_prev"], f["fx_out_prev"] = prev.get("fx_earn", ""), prev.get("fx_out", "")
    f["fx_earn"] = f["fx_out"] = ""; f["inline"] = {}; f["toggles"] = {}; f["ta_year"] = ""
    f["capital"] = {"on": False, "text": ""}
    f["auditor"] = {"on": False, "text": ""}
    mods = f.setdefault("mods", {})
    mods["mrl"] = {}                       # amounts and Yes/No answers are new every year
    for d_ in f.get("directors", []): d_["remuneration"] = ""
    return f, hints


@app.after_request
def _nocache(r):
    r.headers["Cache-Control"] = "no-store"
    return r

APP_VERSION = "3.2"
APP_BUILD = 3                       # integer; bump for every published release (compared with version.json "build")
BUILD_ID = "3.2 · 18-Nov-2026"
import updater

def _upd_cfg():
    u = CFG.get("update") or {}
    return (u.get("manifest_url") or updater.default_manifest()), (u.get("token") or "")

def _exit_soon():
    threading.Timer(1.0, lambda: os._exit(0)).start()

@app.route("/api/update/info")
def upd_info():
    url, tok = _upd_cfg()
    return jsonify(build=APP_BUILD, version=APP_VERSION, frozen=FROZEN, manifest_url=url, has_token=bool(tok),
                   can_rollback=updater.has_previous())

@app.route("/api/update/config", methods=["POST"])
def upd_config():
    b = request.get_json() or {}
    u = CFG.setdefault("update", {})
    if "manifest_url" in b: u["manifest_url"] = (b["manifest_url"] or "").strip()
    if "token" in b and b["token"] != "__keep__": u["token"] = (b["token"] or "").strip()
    json.dump(CFG, open(_cfg, "w"), indent=2)
    return jsonify(ok=True)

@app.route("/api/update/check", methods=["POST"])
def upd_check():
    url, tok = _upd_cfg()
    return jsonify(updater.check(url, APP_BUILD, tok))

@app.route("/api/update/install", methods=["POST"])
def upd_install():
    _, tok = _upd_cfg()
    b = request.get_json() or {}
    try:
        new = updater.download(b["url"], b.get("sha256", ""), tok)
        updater.apply_new(new)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 400
    _exit_soon()
    return jsonify(ok=True)

@app.route("/api/update/file", methods=["POST"])
def upd_file():
    f = request.files.get("file")
    if not f: return jsonify(ok=False, error="No file chosen."), 400
    try:
        new = updater.stage_file(f.read(), request.form.get("sha256", "").strip())
        updater.apply_new(new)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 400
    _exit_soon()
    return jsonify(ok=True)

@app.route("/api/update/rollback", methods=["POST"])
def upd_rollback():
    try: updater.rollback()
    except Exception as e: return jsonify(ok=False, error=str(e)), 400
    _exit_soon()
    return jsonify(ok=True)

@app.route("/api/version")
def version():
    return jsonify(version=APP_VERSION, build=BUILD_ID, folder=RES, build_no=APP_BUILD)

@app.route("/api/config")
def get_config():
    return jsonify(configured=CONFIGURED, generated=GEN, db=DB)

@app.route("/api/config", methods=["POST"])
def set_config():
    global GEN, DB, CONFIGURED
    b = request.get_json()
    new_gen, new_db = os.path.abspath(b["generated"].strip()), os.path.abspath(b["db"].strip())
    if not b["generated"].strip() or not b["db"].strip():
        return jsonify(error="Please choose both folders"), 400
    try:
        for p in (new_gen, new_db):
            os.makedirs(p, exist_ok=True)
            t = os.path.join(p, ".write_test"); open(t, "w").write("x"); os.remove(t)
    except Exception as e:
        return jsonify(error=f"Cannot write to that folder: {e}"), 400
    moved = 0
    if b.get("copy") and CONFIGURED:
        import shutil
        for old, new in ((GEN, new_gen), (DB, new_db)):
            if os.path.isdir(old) and os.path.abspath(old) != new:
                for root, _, files in os.walk(old):
                    for fn in files:
                        src = os.path.join(root, fn)
                        dst = os.path.join(new, os.path.relpath(src, old))
                        if not os.path.exists(dst):
                            os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.copy2(src, dst); moved += 1
    GEN, DB, CONFIGURED = new_gen, new_db, True
    CFG.update(generated_folder=GEN, db_folder=DB, configured=True)
    json.dump(CFG, open(_cfg, "w"), indent=2)
    return jsonify(ok=True, generated=GEN, db=DB, copied=moved)

@app.route("/api/schema")
def schema():
    return jsonify(toggles=PARA_TOGGLES, inline=INLINE_TOGGLES, units={k: v["label"] for k, v in UNITS.items()},
                   categories=CATEGORIES, folders={"generated": GEN, "db": DB},
                   modules=MODULES, mrl_toggles=MRL_TOGGLES, index_att=[x[0] for x in INDEX_ATTACHMENTS], defaults=get_defaults())

@app.route("/api/companies")
def companies():
    out = []
    if not os.path.isdir(DB):
        return jsonify(out)
    for fn in sorted(os.listdir(DB)):
        if fn.endswith(".json") and not fn.startswith("_"):
            d = json.load(open(os.path.join(DB, fn), encoding="utf-8"))
            out.append({"id": d["id"], "company": d["company"], "years": sorted(d["years"].keys(), reverse=True),
                        "has_map": os.path.exists(map_path(d["id"]))})
    out.sort(key=lambda x: x["company"].lower())
    return jsonify(out)

@app.route("/api/company/<cid>")
def company(cid):
    d = load(cid)
    if not d: abort(404)
    fy = request.args.get("fy")
    if fy and fy in d["years"]:
        y = d["years"][fy]
        return jsonify(form=fill_ca(modules.migrate(y["form"])), hints={}, loaded=f"Saved data for FY {fy} – last saved {y.get('saved_at','')} by {y.get('saved_by','?')}", has_map=os.path.exists(map_path(cid)))
    latest = sorted(d["years"].keys())[-1]
    f, hints = carry_forward(d["years"][latest]["form"])
    f = fill_ca(f)
    return jsonify(form=f, hints=hints, loaded=f"Pre-filled from FY {latest} (saved {d['years'][latest].get('saved_at','')} by {d['years'][latest].get('saved_by','?')}) – fixed details carried over, yearly data reset",
                   has_map=os.path.exists(map_path(cid)))

@app.route("/api/new")
def new():
    return jsonify(form=blank_form(), hints={}, loaded="New company", has_map=False)

def route_bytes(cid):
    p = map_path(cid) if cid else None
    return open(p, "rb").read() if p and os.path.exists(p) else None

def clean(f):
    return f

@app.route("/api/preview", methods=["POST"])
def preview():
    body = request.get_json()
    form = body["form"]; mid = body.get("module") or "notice"
    cid = slug(form.get("company", "")) if form.get("company") else None
    try:
        data = modules.generate_module(mid, form, route_bytes(cid))
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify(error=str(e)), 500
    return send_file(io.BytesIO(data), mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

@app.route("/api/generate", methods=["POST"])
def generate():
    body = request.get_json()
    form = body["form"]
    name = (form.get("company") or "").strip()
    if not name: return jsonify(error="Company name is required"), 400
    mids = body.get("modules") or [m["id"] for m in MODULES]
    cid = slug(name); fy = fy_label(int(form["fy_end_year"]))
    folder = os.path.join(GEN, cid, fy); os.makedirs(folder, exist_ok=True)
    saved, files = [], {}
    for m in MODULES:
        if m["id"] not in mids: continue
        data = modules.generate_module(m["id"], form, route_bytes(cid))
        fname = f"{m['file']}_{cid}_FY{fy}.docx"
        full = os.path.join(folder, fname)
        if os.path.exists(full):  # keep older versions
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            os.replace(full, os.path.join(folder, fname.replace(".docx", f"_old_{stamp}.docx")))
        open(full, "wb").write(data)
        rel = os.path.relpath(full, GEN).replace("\\", "/")
        files[m["id"]] = rel
        saved.append({"module": m["id"], "label": m["label"], "rel": rel, "name": fname, "path": full})
    def mutate(d):
        d["company"] = name
        prev = d["years"].get(fy, {}).get("files", {})
        prev.update(files)
        d["years"][fy] = {"form": form, "saved_at": datetime.now().isoformat(timespec="seconds"), "saved_by": who(), "files": prev}
    update_json_safely(db_path(cid), mutate, {"id": cid, "company": name, "years": {}})
    return jsonify(ok=True, saved=saved, folder=folder, db=db_path(cid), cid=cid, fy=fy)

@app.route("/api/texts/<mid>")
def texts_get(mid):
    if mid not in texts.DOC_FILES: abort(404)
    cid = request.args.get("cid") or None
    return jsonify(items=texts.outline(mid, cid), tokens=texts.allowed_tokens(mid), placeholders=texts.PLACEHOLDERS,
                   has_company_edits=bool(cid and ((texts.load_all().get("company") or {}).get(cid) or {}).get(mid)))

@app.route("/api/texts/<mid>", methods=["POST"])
def texts_save(mid):
    """body: {scope: 'global'|'company', cid, changes: {pid: text | null}, reset_all: bool}"""
    if mid not in texts.DOC_FILES: abort(404)
    b = request.get_json()
    scope, cid = b.get("scope", "global"), b.get("cid")
    if scope == "company" and not cid: return jsonify(error="Choose a company"), 400
    changes = b.get("changes") or {}
    for pid, t in changes.items():
        if t is not None:
            err = texts.validate(mid, pid, t)
            if err: return jsonify(error=err, pid=pid), 400
    p = texts.path()
    if not p: return jsonify(error="Database folder is not set"), 400
    def mutate(d):
        d.setdefault("version", 1)
        bucket = d.setdefault("global", {}) if scope == "global" else d.setdefault("company", {}).setdefault(cid, {})
        docs = bucket.setdefault(mid, {})
        if b.get("reset_all"): docs.clear()
        for pid, t in changes.items():
            if t is None: docs.pop(pid, None)
            else: docs[pid] = t
        if not docs: bucket.pop(mid, None)
        if scope == "company" and not bucket: d["company"].pop(cid, None)
    update_json_safely(p, mutate, {"version": 1, "global": {}, "company": {}})
    return jsonify(ok=True)

@app.route("/api/save", methods=["POST"])
def save_progress():
    """Save the data entered so far (no documents generated)."""
    form = request.get_json()["form"]
    name = (form.get("company") or "").strip()
    if not name: return jsonify(error="Enter the company name first"), 400
    try: fy = fy_label(int(form["fy_end_year"]))
    except Exception: return jsonify(error="Financial year is missing"), 400
    cid = slug(name)
    def mutate(d):
        d["company"] = name
        prev = d["years"].get(fy, {}).get("files", {})
        d["years"][fy] = {"form": form, "saved_at": datetime.now().isoformat(timespec="seconds"), "saved_by": who(), "files": prev}
    update_json_safely(db_path(cid), mutate, {"id": cid, "company": name, "years": {}})
    return jsonify(ok=True, cid=cid, fy=fy, db=db_path(cid))

@app.route("/api/pdf", methods=["POST"])
def merged_pdf():
    import pdfutil
    body = request.get_json(); form = body["form"]
    name = (form.get("company") or "").strip()
    if not name: return jsonify(error="Company name is required"), 400
    mids = [m for m in body.get("modules", []) if any(x["id"] == m for x in MODULES)]  # keeps the user's order
    if not mids: return jsonify(error="Select at least one document"), 400
    cid = slug(name); fy = fy_label(int(form["fy_end_year"]))
    try:
        data = pdfutil.docx_list_to_pdf_bytes([modules.generate_module(m, form, route_bytes(cid)) for m in mids])
    except pdfutil.NoConverter as e:
        return jsonify(error=str(e)), 400
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify(error=f"PDF failed: {e}"), 500
    folder = os.path.join(GEN, cid, fy); os.makedirs(folder, exist_ok=True)
    fname = f"Merged_Documents_{cid}_FY{fy}.pdf"; full = os.path.join(folder, fname)
    if os.path.exists(full):
        os.replace(full, full.replace(".pdf", f"_old_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"))
    open(full, "wb").write(data)
    rel = os.path.relpath(full, GEN).replace("\\", "/")
    def mutate(d):  # the merged PDF also stores the entered data, so next year pre-fills
        d["company"] = name
        prev = d["years"].get(fy, {}).get("files", {})
        prev["merged_pdf"] = rel
        d["years"][fy] = {"form": form, "saved_at": datetime.now().isoformat(timespec="seconds"), "saved_by": who(), "files": prev}
    update_json_safely(db_path(cid), mutate, {"id": cid, "company": name, "years": {}})
    return jsonify(ok=True, rel=rel, name=fname, path=full, cid=cid)

@app.route("/api/zip")
def zipfiles():
    import zipfile
    cid, fy = request.args["cid"], request.args["fy"]
    folder = os.path.normpath(os.path.join(GEN, cid, fy))
    if not folder.startswith(GEN) or not os.path.isdir(folder): abort(404)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for fn in sorted(os.listdir(folder)):
            if fn.endswith(".docx") and "_old_" not in fn: z.write(os.path.join(folder, fn), fn)
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name=f"{cid}_FY{fy}.zip", mimetype="application/zip")

@app.route("/api/defaults", methods=["POST"])
def set_defaults():
    b = request.get_json()
    CFG["defaults"] = {"ca": b.get("ca") or {}, "sign_place": b.get("sign_place") or ""}
    json.dump(CFG, open(_cfg, "w"), indent=2)
    try:
        os.makedirs(DB, exist_ok=True)
        json.dump(CFG["defaults"], open(os.path.join(DB, "_defaults.json"), "w", encoding="utf-8"), indent=2)
    except Exception:
        pass
    return jsonify(ok=True)

@app.route("/api/file")
def getfile():
    rel = request.args["rel"]
    full = os.path.normpath(os.path.join(GEN, rel))
    if not full.startswith(GEN) or not os.path.exists(full): abort(404)
    return send_file(full, as_attachment=True)

@app.route("/api/history/<cid>")
def history(cid):
    d = load(cid)
    if not d: return jsonify([])
    return jsonify([{"fy": k, "saved_at": v["saved_at"], "files": v.get("files", {})} for k, v in sorted(d["years"].items(), reverse=True)])

@app.route("/api/routemap/<cid>", methods=["POST"])
def routemap(cid):
    from PIL import Image
    Image.open(request.files["file"].stream).convert("RGB").save(map_path(cid), "PNG")
    return jsonify(ok=True)

@app.route("/api/openfile", methods=["POST"])
def openfile():
    full = os.path.normpath(os.path.join(GEN, request.get_json()["rel"]))
    if full.startswith(GEN) and os.path.exists(full):
        try:
            if sys.platform.startswith("win"): os.startfile(full)
            elif sys.platform == "darwin": os.system(f'open "{full}"')
            else: os.system(f'xdg-open "{full}" >/dev/null 2>&1 &')
        except Exception: pass
    return jsonify(ok=True)

@app.route("/api/openfolder", methods=["POST"])
def openfolder():
    b = request.get_json()
    which = b.get("which", "generated")
    p = GEN if which == "generated" else DB
    sub = b.get("sub")
    if sub:
        q = os.path.normpath(os.path.join(GEN, sub))
        if q.startswith(GEN) and os.path.isdir(q): p = q
    try:
        if sys.platform.startswith("win"): os.startfile(p)
        elif sys.platform == "darwin": os.system(f'open "{p}"')
        else: os.system(f'xdg-open "{p}" >/dev/null 2>&1 &')
    except Exception: pass
    return jsonify(ok=True, path=p)

@app.route("/")
def index():
    # version the script/style links so a window can never keep showing an older cached page
    html = open(os.path.join(RES, "static", "index.html"), encoding="utf-8").read()
    html = html.replace('href="style.css"', f'href="style.css?v={APP_VERSION}"').replace('src="app.js"', f'src="app.js?v={APP_VERSION}"')
    return html, 200, {"Content-Type": "text/html; charset=utf-8"}

class DesktopApi:
    """Methods the page can call when running inside the desktop window."""
    def pick_folder(self, start=""):
        import webview
        r = webview.windows[0].create_file_dialog(webview.FOLDER_DIALOG, directory=start or "")
        return (r[0] if r else "") if not isinstance(r, str) else r

    def save_copy(self, rel, name):
        import webview, shutil
        win = webview.windows[0]
        dest = win.create_file_dialog(webview.SAVE_DIALOG, save_filename=name, file_types=("Word document (*.docx)",))
        if not dest:
            return ""
        dest = dest if isinstance(dest, str) else dest[0]
        shutil.copyfile(os.path.join(GEN, rel), dest)
        return dest


TITLE = "ROC Compliance"

def logo_paths():
    return os.path.join(DB, "_logo.png"), os.path.join(DB, "_logo.ico")

def apply_window_icon():
    """Windows: put the logo (custom if uploaded, else the built-in one) on the title bar and taskbar."""
    if not sys.platform.startswith("win"): return
    ico = logo_paths()[1]
    if not os.path.exists(ico): ico = os.path.join(RES, "app.ico")
    if not os.path.exists(ico): return
    try:
        import ctypes, time as _t
        u = ctypes.windll.user32
        u.LoadImageW.restype = ctypes.c_void_p; u.FindWindowW.restype = ctypes.c_void_p
        u.SendMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p]
        hwnd = None
        for _i in range(25):
            hwnd = u.FindWindowW(None, TITLE)
            if hwnd: break
            _t.sleep(0.2)
        if not hwnd: return
        for kind, size in ((0, 16), (1, 32)):  # ICON_SMALL (title bar), ICON_BIG (taskbar / alt-tab)
            h = u.LoadImageW(None, ico, 1, size, size, 0x10)
            if h: u.SendMessageW(hwnd, 0x80, kind, h)
    except Exception: pass


def trim_logo(im):
    """Cut away empty margins (transparent or a flat background colour) so the logo fills its box."""
    from PIL import Image, ImageChops
    im = im.convert("RGBA")
    a = im.getchannel("A")
    box = a.point(lambda v: 255 if v > 10 else 0).getbbox()
    if box: im = im.crop(box)
    rgb = im.convert("RGB"); w, h = rgb.size
    corners = [rgb.getpixel(p) for p in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1))]
    bg = tuple(sum(c[i] for c in corners) // 4 for i in range(3))
    if all(max(abs(c[i] - bg[i]) for i in range(3)) <= 24 for c in corners):
        diff = ImageChops.difference(rgb, Image.new("RGB", rgb.size, bg)).convert("L").point(lambda v: 255 if v > 40 else 0)
        b2 = diff.getbbox()
        if b2 and (b2[2] - b2[0]) > w * 0.1 and (b2[3] - b2[1]) > h * 0.1:
            pad = int(max(b2[2] - b2[0], b2[3] - b2[1]) * 0.03)
            im = im.crop((max(0, b2[0] - pad), max(0, b2[1] - pad), min(w, b2[2] + pad), min(h, b2[3] + pad)))
    return im

def save_logo(im):
    from PIL import Image, ImageOps
    im = ImageOps.contain(trim_logo(im), (640, 640))
    png, ico = logo_paths(); os.makedirs(DB, exist_ok=True)
    im.save(png, "PNG")
    side = max(im.size); sq = Image.new("RGBA", (side, side), (0, 0, 0, 0)); sq.paste(im, ((side - im.width) // 2, (side - im.height) // 2))
    sq.resize((256, 256), Image.LANCZOS).save(ico, sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    open(png + ".v2", "w").write("2")

@app.route("/api/logo")
def logo_get():
    png = logo_paths()[0]
    if os.path.exists(png):
        if not os.path.exists(png + ".v2"):          # logo saved by an older version: trim it once
            try:
                from PIL import Image
                save_logo(Image.open(png))
            except Exception: pass
        return send_file(png, mimetype="image/png")
    return send_from_directory(app.static_folder, "logo.png")

@app.route("/api/logo", methods=["POST"])
def logo_set():
    from PIL import Image, ImageOps
    f = request.files.get("file")
    if not f: return jsonify(error="No image received"), 400
    raw = f.read()
    if len(raw) > 15 * 1024 * 1024: return jsonify(error="Image is too large (max 15 MB)"), 400
    try:
        im = Image.open(io.BytesIO(raw)); im = ImageOps.exif_transpose(im).convert("RGBA")
    except Exception:
        return jsonify(error="That file is not a supported image (use JPG, PNG, GIF, BMP or WEBP)"), 400
    save_logo(im)
    threading.Thread(target=apply_window_icon, daemon=True).start()
    return jsonify(ok=True)

@app.route("/api/logo/reset", methods=["POST"])
def logo_reset():
    for p in list(logo_paths()) + [logo_paths()[0] + ".v2"]:
        try: os.remove(p)
        except OSError: pass
    threading.Thread(target=apply_window_icon, daemon=True).start()
    return jsonify(ok=True)


def free_port(start):
    """first free local port from `start` (a copy of the app that is still running in the background keeps its port)"""
    import socket
    for p in range(start, start + 30):
        with socket.socket() as s:
            try: s.bind(("127.0.0.1", p)); return p
            except OSError: continue
    return start


def main():
    port = free_port(CFG.get("port", 5055))
    if "--browser" not in sys.argv:
        try:
            import webview
        except Exception:
            webview = None
    else:
        webview = None
    if webview is None:  # fallback: use the normal browser
        threading.Timer(1.0, lambda: webbrowser.open(f"http://127.0.0.1:{port}")).start()
        app.run(host="127.0.0.1", port=port, debug=False)
        return
    threading.Thread(target=lambda: app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False), daemon=True).start()
    import time, urllib.request
    for _ in range(50):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/api/schema", timeout=1); break
        except Exception:
            time.sleep(0.2)
    if sys.platform.startswith("win"):
        try:  # own taskbar identity, so Windows shows our icon instead of python.exe's
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ROCCompliance.App")
        except Exception: pass
    win = webview.create_window(TITLE, f"http://127.0.0.1:{port}", width=1280, height=860,
                                min_size=(1000, 700), js_api=DesktopApi())
    win.events.shown += lambda *_: apply_window_icon()
    webview.start(apply_window_icon)
    os._exit(0)


if __name__ == "__main__":
    if paths_frozen() or sys.stdout is None:
        sys.stdout = sys.stderr = open(os.path.join(BASE, "app.log"), "a", buffering=1)
    main()
