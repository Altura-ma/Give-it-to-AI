#!/usr/bin/env bash
# Lanceur pour Mac / Linux.
# Double-clique dessus (ou lance ./start.sh) : il installe ce qu'il faut puis ouvre l'outil.

set -e
cd "$(dirname "$0")"

# 1) Crée un environnement Python isolé la première fois
if [ ! -d ".venv" ]; then
  echo "Première installation (une seule fois)…"
  python3 -m venv .venv
  ./.venv/bin/pip install --upgrade pip
  ./.venv/bin/pip install -r requirements.txt
fi

# 2) Ouvre le navigateur puis lance le serveur
( sleep 2 && (open http://localhost:8000 2>/dev/null || xdg-open http://localhost:8000 2>/dev/null) ) &
echo "Démarrage… le navigateur va s'ouvrir tout seul."
./.venv/bin/python app.py
