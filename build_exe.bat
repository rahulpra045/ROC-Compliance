@echo off
REM One-time build on any Windows PC that has Python 3.10+ installed (clients do NOT need Python).
REM Result: dist\ROCCompliance.exe  (single file). Give clients that file + README_CLIENT.txt.
cd /d "%~dp0"
python -m pip install -r requirements.txt pyinstaller
python -m PyInstaller --noconfirm ROCCompliance.spec
copy /y README_CLIENT.txt dist\ >nul
python make_version_json.py "%~1"
echo.
echo Built: %~dp0dist\ROCCompliance.exe
pause
