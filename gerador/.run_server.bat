@echo off
cd /d "%~dp0"

REM 1. Tenta usar o Python do venv local caso ele esteja funcional
if exist "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" -c "exit()" >nul 2>&1
    if not errorlevel 1 (
        "venv\Scripts\python.exe" app.py
        exit /b %ERRORLEVEL%
    )
)

REM 2. Se o venv nao funcionar ou nao existir nesta maquina, usa o Python do sistema (PATH)
where python >nul 2>&1
if %ERRORLEVEL% equ 0 (
    python app.py
    exit /b %ERRORLEVEL%
)

REM 3. Tenta o inicializador padrao do Windows (py launcher)
where py >nul 2>&1
if %ERRORLEVEL% equ 0 (
    py app.py
    exit /b %ERRORLEVEL%
)

echo [ERRO] Nenhum interpretador Python funcional foi localizado nesta maquina.
pause
exit /b 1
