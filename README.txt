NOTICE & DIRECTORS' REPORT GENERATOR  (runs on your own computer)

START: install Python 3.9+ once, then double-click run.bat (Windows) or run ./run.sh.
       Your browser opens at http://127.0.0.1:5055

DAILY USE
 1. Pick a company from the list (or "+ New company" the first time).
 2. Choose "New year": fixed details (address, CIN, directors, shareholders, auditor, NIC) are pre-filled;
    last year's closing shareholding becomes opening, last year's figures become "previous year",
    closing debt becomes opening debt. Dates and this year's amounts are blank for you to enter.
 3. Fill dates / amounts; answer Yes where a standard "No" sentence does not apply.
 4. Preview document -> Save & download .docx.

FOLDERS (change in config.json, e.g. to D:\ or a synced drive)
  generated/<Company>/<FY>/...docx   every generated file (older versions kept as *_old_*.docx)
  db/<Company>.json                  all data per company and year (feeds the company list and pre-fill)
  db/<Company>_routemap.png          stored route map

TEMPLATE
  template/notice_director_report_template.docx is your document with {{tokens}}. Wording can be edited
  in Word; keep the {{...}} tokens. build_template.py rebuilds it from template/original_sample.docx.


=== Version 2.0 – 7 modules in one application ===
Documents: Notice & Directors' Report, List of Directors, List of Shareholders,
DSC Consent Letter, Financials Index (cover), Notes on Accounts, Management Representation Letter.
* "Common details" tab: company, directors, shareholders, CA details, place/date of signing - entered ONCE, used in every document.
* Each module tab has an "Include" tick; Preview shows any document (dropdown); Save generates all ticked documents.
* "Save as my default for new companies" stores your CA firm details + sign place.
* Rep. letter amounts/answers and Index attachments are entered each year.
* Rebuild the exe (build_exe.bat) to get this version.

=== Version 2.1 ===
* Modules are in the left menu. "Preview" inside a module previews/downloads only that module.
* "Select, order & generate" page: tick documents, set order with up/down arrows, then
  Preview selected / Download selected (separate Word files) / Merge selected into ONE PDF (in that order).
* Merged PDF needs Microsoft Word (Windows) or LibreOffice on the computer doing the export.
  Word files always work without either.

=== Version 2.2 ===
* The 6 supporting documents keep their own fonts (Bookman Old Style) so page counts match your originals.
* Bold formatting of the reference documents is preserved (totals rows, address in notice, deferred tax amount).
* Place / Date lines are aligned with the first director's signature column.
* Notes on Accounts: Current/Previous Year heading is now a proper table row (no wrapping) with a dotted frame around it and notes 2.8 / 2.9.

=== Version 2.3 ===
* Renamed to "ROC Compliance" (ROCCompliance.exe), new logo/icon, version label removed from the header.
* Fixed packaging: the exe now bundles all 7 document templates.
* Window title-bar and taskbar icons now use the app logo (also when started with run.bat / Python).
* Preview of several documents now has 'Save & download only <selected document>' besides 'Save all'.
* Merged PDF now also saves the company data to the database (previously only the Word download did).
* '💾 Save to database' button (top right, also Ctrl+S) saves your entries at any step without generating documents.
* Save to database button now sits at the bottom of every page that has input fields (Ctrl+S still works).
* run.bat now starts the app without a black console window; pip/Flask notices are hidden.

=== Edit default text ===
Left menu > Customise > Edit default text. Pick a document, choose "All companies" or one company, change the wording and Save.
Edits are stored in the db folder (_text_overrides.json) so every laptop on the LAN uses them. Reset any paragraph (or the whole document) back to the original at any time.
Table layouts, signature blocks and the Index attachment list are built by the program and are locked.

=== ROC Compliance ===
* App renamed to "ROC Compliance" (ROCCompliance.exe; build with ROCCompliance.spec / build_exe.bat).
* Logo: Settings > Logo > Upload image (JPG, JPEG, PNG, GIF, BMP, WEBP) or click the logo. Stored in the db folder, so all laptops share it. "Use default logo" restores the original.
* Click the logo = full-size view (Esc or click outside to close, "Change logo" opens Settings). Click the app name = Settings.
* Uploaded logos are auto-trimmed of empty/flat-colour margins so the picture fills the logo box; the window icon uses a square version.
* If an older copy of the app is still running in the background, the new copy now starts on the next free port instead of showing the old page.
  Settings shows "Build <number>" at the bottom so you can confirm which version you are running. (To close an old copy: Task Manager > end "pythonw.exe".)

Version 3.0: CA / auditor details and "Place" are pre-filled for new companies (and for saved companies whose CA block is empty). "Save as my default" stores them in the db folder (_defaults.json), so they are shared on the LAN and survive exe updates. Built-in starting default: default_ca.json.


UPDATES (no reinstall needed)
 1. One-time: create a GitHub repository, push this folder, and put its address in update_config.json
    (replace OWNER/REPO), e.g. https://github.com/yourname/roc-compliance/releases/latest/download/version.json
    Build the exe once and give it to clients. (Private repo: each laptop needs an access token in
    Settings > Application updates > Update source.)
 2. To publish an update: change the code, raise APP_BUILD in app.py by 1 (and APP_VERSION if you like),
    write the notes in RELEASE_NOTES.txt, then   git tag v3.1  &&  git push origin v3.1
    GitHub builds ROCCompliance.exe and publishes it with version.json (build, version, notes, sha256).
    (Without GitHub: run build_exe.bat "notes" and upload dist\ROCCompliance.exe + dist\version.json to a release.)
 3. Clients: an "Update available" bar appears; click Update now. Settings > Application updates also has
    Check for updates, Install from file, and Roll back (previous exe is kept as ROCCompliance.exe.prev).
    Updates replace only the exe - db, generated files and settings are never touched.
