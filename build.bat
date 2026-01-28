@echo on
setlocal EnableExtensions
title PDF Mixer Pro - Build (simplu, venv-safe)

REM === SETEAZA NUMELE SCRIPTULUI ===
set "APP=PDF_Mixer_Pro_Alex_Dambu_v1.2_nometa"
set "ICON=app.ico"

echo Director curent: "%cd%"
echo Verific scriptul: "%APP%.py"

if not exist "%APP%.py" (
  echo [Eroare] Nu gasesc "%APP%.py" in "%cd%".
  echo Fisiere .py gasite aici:
  dir /b *.py
  echo ---
  echo Daca numele difera, modifica linia: set "APP=..."
  pause
  exit /b 1
)

REM === VENV (NU ne bazam pe activate; folosim direct python din venv) ===
if not exist ".venv\Scripts\python.exe" (
  py -m venv .venv || (echo [Eroare] venv & pause & exit /b 1)
)

set "VENV_PY=%cd%\.venv\Scripts\python.exe"
echo Using venv python: "%VENV_PY%"
"%VENV_PY%" -c "import sys; print('sys.executable =', sys.executable)" || (echo [Eroare] venv python & pause & exit /b 1)

REM === DEPENDINTE ===
"%VENV_PY%" -m pip install --upgrade pip || (echo [Eroare] pip upgrade & pause & exit /b 1)

REM deps runtime + build
"%VENV_PY%" -m pip install pyinstaller pypdf tkinterdnd2 pywin32 pillow || (echo [Eroare] pip install & pause & exit /b 1)

REM optional (recomandat pe masina de build; poate fi ignorat daca da eroare)
"%VENV_PY%" -m pywin32_postinstall -install || echo [Info] pywin32_postinstall a dat eroare (poate fi ignorat)

REM === PYINSTALLER (apel direct din venv) ===
if exist "%ICON%" (
  "%VENV_PY%" -m PyInstaller --noconfirm --onefile --noconsole --name "%APP%" --icon "%ICON%" --collect-data tkinterdnd2 "%cd%\%APP%.py" ^
    || (echo [Eroare] PyInstaller & pause & exit /b 1)
) else (
  "%VENV_PY%" -m PyInstaller --noconfirm --onefile --noconsole --name "%APP%" --collect-data tkinterdnd2 "%cd%\%APP%.py" ^
    || (echo [Eroare] PyInstaller & pause & exit /b 1)
)

echo.
echo ===== GATA =====
echo EXE: ".\dist\%APP%.exe"
pause
exit /b 0
