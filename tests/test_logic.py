"""
Tests des fonctions « pures » (sans réseau) : nettoyage des sous-titres,
choix de langue, métadonnées, formatage, cookies, décodage audio.

Lancer :   python -m pytest -q
"""

import math
import os
import struct
import sys
import tempfile
import wave

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import extractor  # noqa: E402


# --- Nettoyage des sous-titres VTT -------------------------------------------

def test_vtt_supprime_minutage_et_balises():
    vtt = (
        "WEBVTT\nKind: captions\nLanguage: fr\n\n"
        "1\n00:00:00.000 --> 00:00:02.000\n"
        "Bonjour <00:00:01.000><c> tout</c> le monde\n"
    )
    assert extractor._vtt_to_text(vtt) == "Bonjour tout le monde"


def test_vtt_deduplique_les_repetitions():
    vtt = (
        "WEBVTT\n\n"
        "00:00.000 --> 00:01.000\nSalut le monde\n\n"
        "00:01.000 --> 00:02.000\nSalut le monde\n\n"
        "00:02.000 --> 00:03.000\nVoici une astuce\n"
    )
    assert extractor._vtt_to_text(vtt) == "Salut le monde Voici une astuce"


def test_vtt_vide_renvoie_chaine_vide():
    assert extractor._vtt_to_text("WEBVTT\n\n") == ""


# --- Choix de la langue ------------------------------------------------------

def test_pick_lang_prefere_le_francais():
    assert extractor._pick_sub_lang({"en": 1, "fr": 1, "de": 1}) == "fr"


def test_pick_lang_repli_anglais():
    assert extractor._pick_sub_lang({"de": 1, "en-US": 1}) == "en-US"


def test_pick_lang_prend_ce_qui_existe():
    assert extractor._pick_sub_lang({"es": 1}) == "es"


def test_pick_lang_aucune():
    assert extractor._pick_sub_lang({}) is None


# --- Métadonnées -------------------------------------------------------------

def test_build_meta_formate_date_et_duree():
    meta = extractor._build_meta({
        "webpage_url": "https://x/y",
        "extractor_key": "TikTok",
        "title": "Démo",
        "uploader": "@bob",
        "upload_date": "20260630",
        "duration": 95,
        "description": "  coucou  ",
    })
    assert meta["url"] == "https://x/y"
    assert meta["source"] == "TikTok"
    assert meta["upload_date"] == "30/06/2026"
    assert meta["duration"] == "1 min 35 s"
    assert meta["description"] == "coucou"


def test_build_meta_champs_manquants():
    meta = extractor._build_meta({})
    assert meta["duration"] is None
    assert meta["source"] == "Web"


def test_flatten_prend_premier_element_non_nul():
    out = extractor._flatten({"entries": [None, {"title": "A"}, {"title": "B"}]})
    assert out["title"] == "A"


def test_flatten_objet_simple_inchange():
    obj = {"title": "seul"}
    assert extractor._flatten(obj) is obj


# --- Formatage pour Claude ---------------------------------------------------

def test_format_inclut_legende_et_transcription():
    txt = extractor.format_for_claude({
        "source": "Instagram", "url": "u", "uploader": "@a", "title": "T",
        "description": "ma légende", "transcript": "mon texte", "method": "sous-titres",
    })
    assert "Source : Instagram" in txt
    assert "— Légende / description —\nma légende" in txt
    assert "— Transcription (sous-titres) —\nmon texte" in txt


def test_format_sans_transcription():
    txt = extractor.format_for_claude({"source": "X", "description": "juste une légende"})
    assert "Transcription" not in txt
    assert "juste une légende" in txt


# --- Stratégies de cookies ---------------------------------------------------

def test_cookies_sans_config_essaie_navigateurs(monkeypatch):
    monkeypatch.setattr(extractor, "COOKIES_FILE", None)
    monkeypatch.setattr(extractor, "COOKIES_FROM_BROWSER", None)
    cands = list(extractor._cookie_candidates())
    assert cands[0] == {}  # d'abord sans cookies
    assert any("cookiesfrombrowser" in c for c in cands[1:])  # puis navigateurs


def test_cookies_fichier_explicite_prioritaire(monkeypatch):
    monkeypatch.setattr(extractor, "COOKIES_FILE", "cookies.txt")
    cands = list(extractor._cookie_candidates())
    assert cands == [{"cookiefile": "cookies.txt"}]


# --- Décodage audio réel (sans ffmpeg système) -------------------------------

def test_decode_audio_sans_ffmpeg():
    from faster_whisper.audio import decode_audio
    path = tempfile.mktemp(suffix=".wav")
    with wave.open(path, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        for i in range(16000):
            w.writeframes(struct.pack("<h", int(3000 * math.sin(2 * math.pi * 440 * i / 16000))))
    audio = decode_audio(path, sampling_rate=16000)
    os.remove(path)
    assert len(audio) == 16000
