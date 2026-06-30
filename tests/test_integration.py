"""
Tests d'intégration : chemins sous-titres / transcription et API web,
avec yt-dlp et le modèle Whisper SIMULÉS (le réseau réel n'est pas requis).

Lancer :   python -m pytest -q
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import extractor  # noqa: E402
import app as webapp  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


# --- Faux yt-dlp -------------------------------------------------------------

class FakeYDL:
    """Imite yt_dlp.YoutubeDL : écrit des fichiers selon outtmpl, comme le vrai."""

    written = "vtt"      # "vtt" ou "audio" : type de fichier que download() crée
    sub_text = "WEBVTT\n\n00:00.000 --> 00:01.000\nTexte de sous-titre\n"

    def __init__(self, opts):
        self.opts = opts

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def extract_info(self, url, download=False):
        return {"webpage_url": url, "title": "Vidéo test", "subtitles": {}, "automatic_captions": {}}

    def download(self, urls):
        out = self.opts.get("outtmpl", "out")
        if FakeYDL.written == "vtt":
            with open(out + ".fr.vtt", "w", encoding="utf-8") as f:
                f.write(FakeYDL.sub_text)
        else:  # audio
            d = os.path.dirname(out)
            with open(os.path.join(d, "audio.wav"), "wb") as f:
                f.write(b"\x00")  # contenu factice : le modèle est simulé


class FakeSegment:
    def __init__(self, text):
        self.text = text


class FakeInfo:
    language = "fr"


class FakeModel:
    def transcribe(self, path, **kw):
        return [FakeSegment(" Première phrase."), FakeSegment(" Deuxième phrase.")], FakeInfo()


# --- Chemin sous-titres ------------------------------------------------------

def test_try_subtitles_nettoie_le_vtt(monkeypatch):
    monkeypatch.setattr(extractor.yt_dlp, "YoutubeDL", FakeYDL)
    FakeYDL.written = "vtt"
    info = {"subtitles": {"fr": [{"ext": "vtt"}]}, "automatic_captions": {}}
    text, method, lang = extractor._try_subtitles("http://x", info)
    assert text == "Texte de sous-titre"
    assert method == "sous-titres"
    assert lang == "fr"


def test_try_subtitles_aucun_disponible(monkeypatch):
    monkeypatch.setattr(extractor.yt_dlp, "YoutubeDL", FakeYDL)
    text, method, lang = extractor._try_subtitles("http://x", {})
    assert text == ""
    assert method is None


# --- Chemin transcription ----------------------------------------------------

def test_transcribe_audio_assemble_les_segments(monkeypatch):
    monkeypatch.setattr(extractor.yt_dlp, "YoutubeDL", FakeYDL)
    monkeypatch.setattr(extractor, "_get_model", lambda: FakeModel())
    FakeYDL.written = "audio"
    text, lang = extractor._transcribe_audio("http://x")
    assert text == "Première phrase. Deuxième phrase."
    assert lang == "fr"


# --- Chaîne complète extract_content -----------------------------------------

def test_extract_content_bout_en_bout_simule(monkeypatch):
    monkeypatch.setattr(extractor.yt_dlp, "YoutubeDL", FakeYDL)
    monkeypatch.setattr(extractor, "_get_model", lambda: FakeModel())
    # extract_info renvoie des sous-titres vides -> on passe par la transcription audio
    FakeYDL.written = "audio"
    result = extractor.extract_content("http://exemple/clip")
    assert result["title"] == "Vidéo test"
    assert "Première phrase" in result["transcript"]
    assert "Première phrase" in result["text_for_claude"]


# --- API web -----------------------------------------------------------------

def test_api_page_accueil():
    client = TestClient(webapp.app)
    r = client.get("/")
    assert r.status_code == 200
    assert "Give it to AI" in r.text


def test_api_url_vide_renvoie_400():
    client = TestClient(webapp.app)
    r = client.post("/api/extract", json={"url": ""})
    assert r.status_code == 400


def test_api_complete_avec_extraction_simulee(monkeypatch):
    def fake_extract(url):
        res = {"url": url, "source": "Instagram", "title": "Recette",
               "description": "3 ingrédients", "transcript": "Mélangez",
               "method": "Whisper local (base)"}
        res["text_for_claude"] = extractor.format_for_claude(res)
        return res

    monkeypatch.setattr(webapp, "extract_content", fake_extract)
    client = TestClient(webapp.app)
    r = client.post("/api/extract", json={"url": "instagram.com/reel/abc"})
    assert r.status_code == 200
    data = r.json()
    # L'URL sans schéma doit être complétée en https://
    assert data["url"].startswith("https://")
    assert "Recette" in data["text_for_claude"]
