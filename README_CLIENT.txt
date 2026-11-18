NOTICE & DIRECTORS' REPORT GENERATOR
Double-click ROCCompliance.exe - the application opens in its own window (no browser needed).
Requires Windows 10/11 (uses the built-in Microsoft Edge WebView2 component, already present on current Windows).

Folders created next to the .exe:
  generated\   all Word files, per company and year
  db\          saved company data (used to pre-fill next year)
Back up these two folders. If something goes wrong, app.log (next to the .exe) has the details.

OFFICE / SHARED USE (several laptops, one set of data)
 1. On the main laptop, create a folder (e.g. D:\NoticeData) containing two folders, "generated" and "db",
    and share it: right-click the folder > Properties > Sharing > give the office users Read/Write access.
 2. On each laptop, start ROCCompliance.exe > Settings and choose the shared folders, either by Browse
    or by typing the network path, e.g.  \\MAINLAPTOP\NoticeData\generated  and  \\MAINLAPTOP\NoticeData\db
    (a mapped drive such as Z:\ also works).
 3. The main laptop must be switched on and on the network. Back up the shared folder regularly.
 Notes: two people can work on different companies at the same time. If two people save the same company
 and year, the later save replaces the earlier one (the older Word file is kept as *_old_*.docx).
 The app shows who last saved each company and when.

Version 2.0: one app now produces 7 documents. Fill the "Common details" tab once; tick the documents you want; Preview; Save.
