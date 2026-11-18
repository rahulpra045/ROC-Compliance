"""In-app updates: check a published version.json, download + verify the new exe, swap it in on restart.
Data (db, generated, config.json) is never touched: only ROCCompliance.exe is replaced."""
import os, sys, json, hashlib, subprocess, urllib.request, urllib.parse, ssl
from paths import RES, DATA, FROZEN

EXE = sys.executable if FROZEN else None
STAGE = os.path.join(DATA, "_update")


def _opener(token=""):
    h = {"User-Agent": "ROC-Compliance-Updater"}
    if token: h["Authorization"] = "Bearer " + token
    return h


def default_manifest():
    try: return json.load(open(os.path.join(RES, "update_config.json"), encoding="utf-8")).get("manifest_url", "")
    except Exception: return ""


def _get(url, token="", timeout=20):
    req = urllib.request.Request(url, headers=_opener(token))
    return urllib.request.urlopen(req, timeout=timeout, context=ssl.create_default_context())


def check(manifest_url, current_build, token=""):
    if not manifest_url or "OWNER/REPO" in manifest_url:
        return {"ok": False, "error": "Update address is not set. Open Settings > Application updates and enter your GitHub version.json address."}
    try:
        m = json.loads(_get(manifest_url, token).read().decode("utf-8-sig"))
        b = int(m["build"])
    except Exception as e:
        return {"ok": False, "error": f"Could not read the update information ({e.__class__.__name__}: {e})."}
    url = m.get("url") or urllib.parse.urljoin(manifest_url, "ROCCompliance.exe")
    return {"ok": True, "available": b > current_build, "build": b, "version": m.get("version", str(b)),
            "notes": m.get("notes", ""), "sha256": (m.get("sha256") or "").lower(), "url": urllib.parse.urljoin(manifest_url, url)}


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""): h.update(ch)
    return h.hexdigest()


def _validate(path, sha=""):
    if os.path.getsize(path) < 5_000_000 or open(path, "rb").read(2) != b"MZ":
        raise ValueError("This is not a valid ROCCompliance.exe file.")
    if sha and _sha(path) != sha.lower():
        raise ValueError("Checksum mismatch - the downloaded file is damaged or not the published one. Nothing was changed.")


def download(url, sha, token=""):
    if not FROZEN: raise RuntimeError("Updates apply to the installed ROCCompliance.exe (not when running from source).")
    os.makedirs(STAGE, exist_ok=True)
    dest = os.path.join(STAGE, "ROCCompliance.new.exe")
    with _get(url, token, 120) as r, open(dest, "wb") as out:
        while True:
            ch = r.read(1 << 20)
            if not ch: break
            out.write(ch)
    try: _validate(dest, sha)
    except Exception:
        os.remove(dest); raise
    return dest


def stage_file(data, sha=""):
    if not FROZEN: raise RuntimeError("Updates apply to the installed ROCCompliance.exe (not when running from source).")
    os.makedirs(STAGE, exist_ok=True)
    dest = os.path.join(STAGE, "ROCCompliance.new.exe")
    open(dest, "wb").write(data)
    try: _validate(dest, sha)
    except Exception:
        os.remove(dest); raise
    return dest


def has_previous(): return bool(EXE) and os.path.exists(EXE + ".prev")


def _run_bat(lines):
    os.makedirs(STAGE, exist_ok=True)
    bat = os.path.join(STAGE, "apply.bat")
    open(bat, "w", encoding="mbcs", errors="replace").write("\r\n".join(lines) + "\r\n")
    flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NO_WINDOW", 0)
    # The relaunched exe must NOT inherit PyInstaller's variables, or it looks for this process's
    # (soon deleted) temp folder and fails with "Failed to load Python DLL ... python312.dll".
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith(("_MEI", "_PYI"))}
    subprocess.Popen(["cmd", "/c", bat], creationflags=flags, close_fds=True, cwd=DATA, env=env)


def apply_new(new_exe):
    """Swap after this process exits; keep the old exe as ROCCompliance.exe.prev for rollback."""
    cur, prev = EXE, EXE + ".prev"
    _run_bat(["@echo off", "set n=0", ":w", "set /a n+=1", "if %n% gtr 40 goto done", "timeout /t 2 /nobreak >nul",
              f'if exist "{prev}" del /f /q "{prev}" >nul 2>&1',
              f'move /y "{cur}" "{prev}" >nul 2>&1', "if errorlevel 1 goto w",
              f'move /y "{new_exe}" "{cur}" >nul', f'start "" "{cur}"', ":done", 'del "%~f0"'])


def rollback():
    cur, prev, tmp = EXE, EXE + ".prev", EXE + ".swap"
    if not os.path.exists(prev): raise RuntimeError("There is no previous version to go back to.")
    _run_bat(["@echo off", "set n=0", ":w", "set /a n+=1", "if %n% gtr 40 goto done", "timeout /t 2 /nobreak >nul",
              f'move /y "{cur}" "{tmp}" >nul 2>&1', "if errorlevel 1 goto w",
              f'move /y "{prev}" "{cur}" >nul', f'move /y "{tmp}" "{prev}" >nul', f'start "" "{cur}"', ":done", 'del "%~f0"'])
