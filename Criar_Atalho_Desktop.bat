@echo off
title Criar Atalho na Area de Trabalho - NFT Logistics
cd /d "%~dp0"

echo ========================================================
echo Criando atalho na Area de Trabalho...
echo ========================================================

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$desktop = [Environment]::GetFolderPath('Desktop');" ^
  "$ws = New-Object -ComObject WScript.Shell;" ^
  "$sc = $ws.CreateShortcut((Join-Path $desktop 'NFT Emissor NF-e.lnk'));" ^
  "$sc.TargetPath = (Join-Path '%~dp0' 'Iniciar_NFT_Logistics.vbs');" ^
  "$sc.WorkingDirectory = '%~dp0';" ^
  "$ico = Join-Path '%~dp0' 'app_icon.ico';" ^
  "if (Test-Path $ico) { $sc.IconLocation = $ico };" ^
  "$sc.Save();"

echo.
echo Atalho 'NFT Emissor NF-e' criado com sucesso na sua Area de Trabalho!
echo.
pause
