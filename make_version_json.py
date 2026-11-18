"""Writes dist/version.json for the exe in dist/. Usage: python make_version_json.py "release notes"
Reads APP_BUILD / APP_VERSION from app.py, so bump APP_BUILD there before every release."""
import hashlib, json, re, sys, os
from datetime import datetime
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.py"), encoding="utf-8").read()
build = int(re.search(r'^APP_BUILD\s*=\s*(\d+)', src, re.M).group(1))
ver = re.search(r'^APP_VERSION\s*=\s*"([^"]+)"', src, re.M).group(1)
notes = sys.argv[1] if len(sys.argv) > 1 else ""
exe = os.path.join("dist", "ROCCompliance.exe")
sha = hashlib.sha256(open(exe, "rb").read()).hexdigest()
d = datetime.now()
out = {"build": build, "version": f"{ver} ({d.day} {d.strftime('%b %Y')})", "notes": notes, "sha256": sha}
json.dump(out, open(os.path.join("dist", "version.json"), "w", encoding="utf-8"), indent=2)
print(json.dumps(out, indent=2))
