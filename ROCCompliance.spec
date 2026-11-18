# PyInstaller recipe:  pyinstaller ROCCompliance.spec
a = Analysis(['app.py'],
             datas=[('static', 'static'), ('app.ico', '.'), ('default_ca.json', '.'), ('update_config.json', '.')] + [('template/%s.docx' % n, 'template') for n in ('notice_director_report_template', 'directors', 'shareholders', 'dsc', 'index', 'policies', 'mrl')],
             hiddenimports=['pypdf', 'docx2pdf', 'win32com', 'win32com.client', 'pythoncom', 'PIL', 'lxml', 'lxml.etree', 'webview', 'webview.platforms.edgechromium',
                            'webview.platforms.winforms', 'clr'], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='ROCCompliance', icon='app.ico', console=False, upx=False)
