@echo off
REM ===========================================================
REM CodeRoute Guinée — Démarrage développement (Windows)
REM Usage : start_dev.bat
REM         set SEED_ON_START=true && start_dev.bat
REM ===========================================================

echo 🇬🇳 CodeRoute Guinée — Démarrage
echo =================================

if not exist ".env" (
    echo ERREUR : .env manquant — copiez .env.example et configurez les variables
    exit /b 1
)

REM Charger les variables .env
for /f "tokens=1,2 delims==" %%a in (.env) do (
    if not "%%a"=="" if not "%%b"=="" set %%a=%%b
)

REM Backend
cd backend
pip install -q -r requirements.txt

if "%SEED_ON_START%"=="true" (
    echo Chargement des données de test...
    set PYTHONPATH=.
    set ALLOW_DEMO_SEED_NON_DEV=true
    python -m app.seed_full
)

set PYTHONPATH=.
python -m alembic upgrade head

echo Démarrage du backend...
start "CodeRoute Backend" cmd /k "set PYTHONPATH=. && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

REM Frontend
cd ..\frontend
call npm ci --silent
echo Démarrage du frontend...
start "CodeRoute Frontend" cmd /k "npm run dev"

echo.
echo ✅ CodeRoute Guinée opérationnel
echo API  : http://localhost:8000/docs
echo App  : http://localhost:5173
echo.
echo Comptes : super_admin@coderoute.gov.gn / CodeRoute2026!
echo Fermez les fenêtres backend et frontend pour arrêter.
cd ..
