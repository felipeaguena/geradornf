@echo off
cd /d "%~dp0"

REM 1. Tenta usar o pythonw ou python do venv local
if exist "venv\Scripts\pythonw.exe" (
    start "" "venv\Scripts\pythonw.exe" app.py
    exit /b 0
)

if exist "venv\Scripts\python.exe" (
    start "" /min "venv\Scripts\python.exe" app.py
    exit /b 0
)

REM 2. Se o venv nao existir, usa o Python do sistema (PATH)
where pythonw >nul 2>&1
if %ERRORLEVEL% equ 0 (
    start "" pythonw app.py
    exit /b 0
)

where python >nul 2>&1
if %ERRORLEVEL% equ 0 (
    start "" /min python app.py
    exit /b 0
)

REM 3. Tenta o inicializador padrao do Windows (py launcher)
where py >nul 2>&1
if %ERRORLEVEL% equ 0 (
    start "" /min py app.py
    exit /b 0
)

echo [ERRO] Nenhum interpretador Python funcional foi localizado nesta maquina.
pause
exit /b 1
