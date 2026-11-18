@echo off
cd /d "%~dp0"
python -m pip install -r requirements.txt --quiet --disable-pip-version-check >nul 2>&1
REM start without a console window (errors, if any, go to app.log)
where pythonw >nul 2>&1 && (start "" pythonw app.py) || (python app.py & pause)
