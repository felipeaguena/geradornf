@echo off
title Encerrando Servidor NFT Logistics
echo ========================================================
echo Encerrando Servidor NFT Logistics (Porta 1652)...
echo ========================================================

REM 1. Notifica o backend para desligamento e fechamento das janelas
curl -s -X POST http://127.0.0.1:1652/api/shutdown >nul 2>&1

REM 2. Forca o fechamento das janelas do sistema pelo titulo nativo
powershell -Command "Get-Process | Where-Object { $_.MainWindowTitle -like '*NFT Logistics*' -or $_.MainWindowTitle -like '*Emissor NF-e*' } | ForEach-Object { $_.CloseMainWindow() }" >nul 2>&1

REM 3. Finaliza qualquer processo ouvindo na porta 1652
for /f "tokens=5" %%a in ('netstat -aon ^| findstr /r ":1652[ ]" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

REM 4. Garante encerramento de instancias python executando app.py (sem depender do wmic)
powershell -Command "Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { ($_.Name -like 'python*.exe') -and ($_.CommandLine -like '*app.py*') } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>&1

echo.
echo Servidor encerrado com sucesso!
ping -n 2 127.0.0.1 >nul
