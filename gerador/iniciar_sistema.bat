@echo off
echo =======================================
echo Iniciando Sistema Gerador NF-e Sebrae
echo =======================================

cd /d "%~dp0"

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

IF NOT EXIST "database.db" (
    echo [4] Inicializando banco de dados...
    python init_db.py
) ELSE (
    echo [4] Banco de dados existente verificado e preservado.
)

echo [5] Iniciando servidor web em http://localhost:5000
start http://localhost:5000
python app.py

pause
