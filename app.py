"""
Petit serveur web.
Sert la page (le formulaire) et répond à la demande d'extraction.

Lancer avec :   python app.py
Puis ouvrir :   http://localhost:8000
"""

import os
import traceback

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from extractor import extract_content

app = FastAPI(title="Give it to AI")

HERE = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(HERE, "static")


class ExtractRequest(BaseModel):
    url: str


@app.get("/")
def home():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.post("/api/extract")
def api_extract(req: ExtractRequest):
    url = (req.url or "").strip()
    if not url:
        return JSONResponse({"error": "Aucune URL fournie."}, status_code=400)
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        result = extract_content(url)
        return result
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(
            {
                "error": "Impossible de récupérer ce contenu.",
                "detail": str(e),
                "hint": (
                    "Si c'est un contenu Instagram/privé, il faut peut-être fournir "
                    "des cookies (voir le README). Vérifie aussi que l'URL est correcte."
                ),
            },
            status_code=500,
        )


# Sert les fichiers statiques (CSS, etc.) si besoin plus tard
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    print(f"\n  Give it to AI -> ouvre ton navigateur sur  http://localhost:{port}\n")
    uvicorn.run(app, host="0.0.0.0", port=port)
