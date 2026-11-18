"""docx -> pdf conversion (Microsoft Word or LibreOffice) and PDF merging."""
import glob, io, os, shutil, subprocess, sys, tempfile

def _find_soffice():
    for n in ("soffice", "libreoffice", "soffice.exe"):
        p = shutil.which(n)
        if p: return p
    for pat in (r"C:\Program Files\LibreOffice*\program\soffice.exe", r"C:\Program Files (x86)\LibreOffice*\program\soffice.exe",
                "/Applications/LibreOffice.app/Contents/MacOS/soffice"):
        h = glob.glob(pat)
        if h: return h[0]
    return None

class NoConverter(Exception): pass

def _with_word(pairs):
    from docx2pdf import convert  # needs Microsoft Word (Windows/macOS)
    for src, dst in pairs: convert(src, dst)

def _with_soffice(exe, pairs):
    outdir = os.path.dirname(pairs[0][1])
    prof = tempfile.mkdtemp(prefix="lo_prof_")
    try:
        cmd = [exe, f"-env:UserInstallation=file:///{prof.replace(os.sep, '/').lstrip('/')}", "--headless", "--convert-to", "pdf", "--outdir", outdir] + [s for s, _ in pairs]
        subprocess.run(cmd, check=True, capture_output=True, timeout=600)
    finally:
        shutil.rmtree(prof, ignore_errors=True)

def docx_list_to_pdf_bytes(docs):
    """docs: list of docx byte-strings in merge order -> merged pdf bytes."""
    from pypdf import PdfWriter, PdfReader
    tmp = tempfile.mkdtemp(prefix="ng_pdf_")
    try:
        pairs = []
        for i, d in enumerate(docs):
            s = os.path.join(tmp, f"{i:02d}.docx"); open(s, "wb").write(d); pairs.append((s, os.path.join(tmp, f"{i:02d}.pdf")))
        errs = []
        done = False
        if sys.platform.startswith(("win", "darwin")):
            try: _with_word(pairs); done = all(os.path.exists(p) for _, p in pairs)
            except Exception as e: errs.append(f"Word: {e}")
        if not done:
            exe = _find_soffice()
            if exe:
                try: _with_soffice(exe, pairs); done = all(os.path.exists(p) for _, p in pairs)
                except Exception as e: errs.append(f"LibreOffice: {e}")
        if not done:
            raise NoConverter("A PDF needs Microsoft Word or LibreOffice installed on this computer (neither could be used). "
                              "Your Word files are still saved. " + " ".join(errs))
        w = PdfWriter()
        for _, p in pairs:
            for pg in PdfReader(p).pages: w.add_page(pg)
        out = io.BytesIO(); w.write(out); return out.getvalue()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
