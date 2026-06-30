@echo off
REM Lanceur pour Windows.
REM Double-clique sur ce fichier : il installe ce qu'il faut puis ouvre l'outil.

cd /d "%~dp0"

REM 1) Crée un environnement Python isolé la première fois
if not exist ".venv" (
  echo Premiere installation ^(une seule fois^)...
  python -m venv .venv
  .venv\Scripts\python -m pip install --upgrade pip
  .venv\Scripts\pip install -r requirements.txt
)

REM 2) Ouvre le navigateur puis lance le serveur
start "" http://localhost:8000
echo Demarrage... le navigateur va s'ouvrir tout seul.
.venv\Scripts\python app.py

pause
