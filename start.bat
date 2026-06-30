@echo off
REM Lanceur pour Windows.
REM Double-clique sur ce fichier : il installe ce qu'il faut puis ouvre l'outil.

cd /d "%~dp0"

REM Verifie que Python est installe
where python >nul 2>nul
if errorlevel 1 (
  echo Python 3 n'est pas installe.
  echo Installe-le ici : https://www.python.org/downloads/  ^(coche "Add to PATH"^) puis relance.
  pause
  exit /b 1
)

REM 1) Premiere installation (une seule fois)
if not exist ".venv" (
  echo Premiere installation ^(une seule fois, quelques minutes^)...
  python -m venv .venv
  .venv\Scripts\python -m pip install --upgrade pip
  .venv\Scripts\pip install -r requirements.txt
  echo.
  echo Verification que tout fonctionne ^(et telechargement du modele^)...
  .venv\Scripts\python selftest.py
)

REM 2) Ouvre le navigateur puis lance le serveur
start "" http://localhost:8000
echo Demarrage... le navigateur va s'ouvrir tout seul sur http://localhost:8000
.venv\Scripts\python app.py

pause
