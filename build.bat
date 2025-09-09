@echo on
setlocal EnableExtensions
title PDF Mixer Pro - Build (simplu)

REM === SETEAZA NUMELE SCRIPTULUI ===
set "APP=PDF_Mixer_Pro_Alex_Dambu_v1_nometa"
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

REM === VENV ===
if not exist ".venv\Scripts\activate.bat" (
  py -m venv .venv || (echo [Eroare] venv & pause & exit /b 1)
)
call .venv\Scripts\activate || (echo [Eroare] activate & pause & exit /b 1)

REM === DEPENDINTE ===
python -m pip install --upgrade pip
python -m pip install pyinstaller pypdf tkinterdnd2 || (echo [Eroare] pip & pause & exit /b 1)

REM === PYINSTALLER (apel direct, fara variabila-comanda) ===
if exist "%ICON%" (
  py -m PyInstaller --noconfirm --onefile --noconsole --name "%APP%" --icon "%ICON%" --collect-data tkinterdnd2 "%cd%\%APP%.py" ^
    || (echo [Eroare] PyInstaller & pause & exit /b 1)
) else (
  py -m PyInstaller --noconfirm --onefile --noconsole --name "%APP%" --collect-data tkinterdnd2 "%cd%\%APP%.py" ^
    || (echo [Eroare] PyInstaller & pause & exit /b 1)
)

echo.
echo ===== GATA =====
echo EXE: ".\dist\%APP%.exe"
pause
exit /b 0
