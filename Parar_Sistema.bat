@echo off
title Encerrando Servidor NFT Logistics
echo ========================================================
echo Encerrando Servidor NFT Logistics (Porta 1652)...
echo ========================================================

REM 1. Notifica o backend para desligamento e fechamento das janelas
curl -s -X POST http://localhost:1652/api/shutdown >nul 2>&1

REM 2. Forca o fechamento das janelas do sistema pelo titulo nativo
powershell -Command "Get-Process | Where-Object { $_.MainWindowTitle -like '*NFT Logistics*' -or $_.MainWindowTitle -like '*Emissor NF-e*' } | ForEach-Object { $_.CloseMainWindow() }" >nul 2>&1

REM 3. Finaliza processos ouvindo na porta 1652
for /f "tokens=5" %%a in ('netstat -aon ^| findstr /r ":1652[ ]" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

REM 4. Garante encerramento de instancias pythonw executando app.py
for /f "tokens=2 delims=," %%p in ('wmic process where "name='pythonw.exe' and commandline like '%%app.py%%'" get processid /format:csv 2^>nul ^| findstr /r "[0-9]"') do (
    taskkill /F /PID %%p >nul 2>&1
)

echo.
echo Servidor encerrado com sucesso!
ping -n 2 127.0.0.1 >nul
