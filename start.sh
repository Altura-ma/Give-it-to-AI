#!/usr/bin/env bash
# Lanceur pour Mac / Linux.
# Double-clique dessus (ou lance ./start.sh) : il installe ce qu'il faut puis ouvre l'outil.

cd "$(dirname "$0")"

# Vérifie que Python est installé
if ! command -v python3 >/dev/null 2>&1; then
  echo "❌ Python 3 n'est pas installé."
  echo "   Installe-le ici : https://www.python.org/downloads/  puis relance."
  read -r -p "Appuie sur Entrée pour fermer…" _
  exit 1
fi

set -e

# 1) Première installation (une seule fois)
if [ ! -d ".venv" ]; then
  echo "Première installation (une seule fois, quelques minutes)…"
  python3 -m venv .venv
  ./.venv/bin/pip install --upgrade pip
  ./.venv/bin/pip install -r requirements.txt
  echo ""
  echo "Vérification que tout fonctionne (et téléchargement du modèle)…"
  ./.venv/bin/python selftest.py || true
fi

# 2) Ouvre le navigateur puis lance le serveur
( sleep 2 && (open http://localhost:8000 2>/dev/null || xdg-open http://localhost:8000 2>/dev/null) ) &
echo "Démarrage… le navigateur va s'ouvrir tout seul sur http://localhost:8000"
./.venv/bin/python app.py
