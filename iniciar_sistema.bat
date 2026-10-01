@echo off
echo ===================================================
echo Iniciando Portal Emissor NF-e - NFT Logistics
echo ===================================================

cd /d "%~dp0gerador"

IF NOT EXIST "venv\Scripts\python.exe" (
    echo [1] Criando ambiente virtual Python...
    python -m venv venv
) ELSE (
    echo [1] Ambiente virtual ja existe.
)

echo [2] Ativando ambiente virtual...
call venv\Scripts\activate.bat

echo [3] Instalando/Verificando dependencias...
pip install -r requirements.txt

echo [4] Inicializando banco de dados (se nao existir)...
python init_db.py

echo [5] Abrindo Portal de Modulos em http://localhost:5000...
start http://localhost:5000
python app.py

pause
