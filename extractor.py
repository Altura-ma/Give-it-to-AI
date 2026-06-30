"""
Cœur de l'outil : récupère le contenu d'une URL (Instagram, TikTok, X, YouTube...)
et le transforme en texte lisible.

Stratégie pour rester GRATUIT et rapide :
  1. On lit d'abord les informations (titre, auteur, légende/description).
  2. Si la vidéo a déjà des sous-titres -> on les utilise (instantané, 0 calcul).
  3. Sinon, on télécharge l'audio et on le transcrit avec Whisper EN LOCAL
     (modèle open-source, aucune API payante).

Aucune clé d'API n'est nécessaire.
"""

import os
import re
import glob
import tempfile

import yt_dlp

# --- Réglages (modifiables via variables d'environnement) ---------------------

# Taille du modèle Whisper : "tiny", "base", "small", "medium", "large-v3"
#   - "base"  : bon compromis vitesse/qualité (défaut)
#   - "small" : meilleur pour le français, un peu plus lent
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "base")

# Optionnel : fichier de cookies pour les contenus qui demandent une connexion
# (souvent nécessaire pour Instagram). Voir le README.
COOKIES_FILE = os.environ.get("COOKIES_FILE")
# Ou bien récupérer les cookies directement depuis un navigateur, ex: "chrome"
COOKIES_FROM_BROWSER = os.environ.get("COOKIES_FROM_BROWSER")

# Langues de sous-titres préférées, dans l'ordre
PREFERRED_SUB_LANGS = ["fr", "fr-FR", "en", "en-US"]

_model = None


def _get_model():
    """Charge le modèle Whisper une seule fois (au premier besoin)."""
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        # int8 = léger et rapide sur un simple processeur, sans carte graphique
        _model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
    return _model


# Navigateurs essayés automatiquement pour récupérer les cookies si un contenu
# demande d'être connecté (ex. Instagram). On s'arrête au premier qui fonctionne.
_AUTO_BROWSERS = ("chrome", "edge", "firefox", "brave", "chromium", "opera", "safari", "vivaldi")


def _ydl_opts(cookies=None, **extra):
    """Options communes pour yt-dlp. `cookies` = dict d'options cookies à appliquer."""
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "skip_download": True,
        "socket_timeout": 30,
        "retries": 3,
        "ignoreerrors": False,
        # Un en-tête de navigateur réduit les blocages sur certains sites
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0 Safari/537.36"
            )
        },
    }
    if cookies:
        opts.update(cookies)
    opts.update(extra)
    return opts


def _cookie_candidates():
    """Stratégies de cookies à essayer, dans l'ordre."""
    # 1) Configuration explicite par l'utilisateur (prioritaire, on s'y tient)
    if COOKIES_FILE:
        yield {"cookiefile": COOKIES_FILE}
        return
    if COOKIES_FROM_BROWSER:
        yield {"cookiesfrombrowser": (COOKIES_FROM_BROWSER,)}
        return
    # 2) Sans cookies (suffisant pour la plupart des contenus publics)
    yield {}
    # 3) Essai automatique des navigateurs installés (pour Instagram & co.)
    for browser in _AUTO_BROWSERS:
        yield {"cookiesfrombrowser": (browser,)}


def _flatten(info):
    """Si l'URL pointe vers une liste (profil, playlist...), prend le 1er élément."""
    if info and info.get("entries"):
        entries = [e for e in info["entries"] if e]
        if entries:
            return entries[0]
    return info


def _probe(url):
    """
    Récupère les métadonnées sans rien télécharger.
    Essaie successivement les stratégies de cookies jusqu'à ce qu'une marche.
    Renvoie (info, cookies_qui_ont_marché).
    """
    last_error = None
    for cookies in _cookie_candidates():
        try:
            with yt_dlp.YoutubeDL(_ydl_opts(cookies=cookies)) as ydl:
                info = ydl.extract_info(url, download=False)
            if info:
                return _flatten(info), cookies
        except Exception as e:
            last_error = e
            continue
    # Toutes les stratégies ont échoué
    raise last_error if last_error else RuntimeError("Contenu introuvable.")


def _build_meta(info):
    """Extrait les informations utiles (titre, auteur, légende...)."""
    duration = info.get("duration")
    if duration:
        m, s = divmod(int(duration), 60)
        duration_str = f"{m} min {s:02d} s"
    else:
        duration_str = None

    upload_date = info.get("upload_date")  # format AAAAMMJJ
    if upload_date and len(upload_date) == 8:
        upload_date = f"{upload_date[6:8]}/{upload_date[4:6]}/{upload_date[0:4]}"

    return {
        "url": info.get("webpage_url") or info.get("original_url"),
        "source": (info.get("extractor_key") or "").replace("Generic", "Web") or "Web",
        "title": info.get("title"),
        "uploader": info.get("uploader") or info.get("channel") or info.get("uploader_id"),
        "upload_date": upload_date,
        "duration": duration_str,
        "description": (info.get("description") or "").strip(),
    }


def _vtt_to_text(vtt_content):
    """Nettoie un fichier de sous-titres (.vtt) pour n'en garder que le texte."""
    lines = []
    for raw in vtt_content.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith(("WEBVTT", "NOTE", "Kind:", "Language:")):
            continue
        if "-->" in line:  # ligne de minutage
            continue
        if re.match(r"^\d+$", line):  # numéro de séquence
            continue
        line = re.sub(r"<[^>]+>", "", line)  # balises internes <00:00:00.000>, <c> ...
        line = re.sub(r"\s+", " ", line).strip()  # espaces multiples -> un seul
        if line:
            lines.append(line)

    # Supprime les répétitions consécutives (fréquent dans les sous-titres auto)
    cleaned = []
    for l in lines:
        if not cleaned or cleaned[-1] != l:
            cleaned.append(l)
    return " ".join(cleaned).strip()


def _pick_sub_lang(available):
    """Choisit la meilleure langue de sous-titres disponible."""
    if not available:
        return None
    for lang in PREFERRED_SUB_LANGS:
        if lang in available:
            return lang
    # sinon, n'importe quelle langue dont le code commence par fr ou en
    for lang in available:
        if lang.split("-")[0] in ("fr", "en"):
            return lang
    return next(iter(available))


def _try_subtitles(url, info, cookies=None):
    """Tente de récupérer des sous-titres existants. Renvoie (texte, méthode, langue)."""
    manual = info.get("subtitles") or {}
    auto = info.get("automatic_captions") or {}

    for source, label in ((manual, "sous-titres"), (auto, "sous-titres auto")):
        lang = _pick_sub_lang(source)
        if not lang:
            continue
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "sub")
            opts = _ydl_opts(
                cookies=cookies,
                writesubtitles=(source is manual),
                writeautomaticsub=(source is auto),
                subtitleslangs=[lang],
                subtitlesformat="vtt",
                outtmpl=out,
            )
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([url])
            except Exception:
                continue
            files = glob.glob(os.path.join(tmp, "*.vtt"))
            if not files:
                continue
            with open(files[0], "r", encoding="utf-8", errors="ignore") as f:
                text = _vtt_to_text(f.read())
            if text:
                return text, label, lang
    return "", None, None


def _transcribe_audio(url, cookies=None):
    """Télécharge l'audio et le transcrit avec Whisper. Renvoie (texte, langue)."""
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "audio.%(ext)s")
        opts = _ydl_opts(
            cookies=cookies, skip_download=False, format="bestaudio/best", outtmpl=out
        )
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
        files = glob.glob(os.path.join(tmp, "audio.*"))
        if not files:
            return "", None
        model = _get_model()
        segments, tinfo = model.transcribe(files[0], vad_filter=True)
        text = " ".join(seg.text.strip() for seg in segments).strip()
        return text, getattr(tinfo, "language", None)


def format_for_claude(result):
    """Assemble un bloc de texte propre, prêt à coller dans une conversation."""
    parts = []
    head = []
    if result.get("source"):
        head.append(f"Source : {result['source']}")
    if result.get("url"):
        head.append(f"Lien : {result['url']}")
    if result.get("uploader"):
        head.append(f"Auteur : {result['uploader']}")
    if result.get("title"):
        head.append(f"Titre : {result['title']}")
    if result.get("upload_date"):
        head.append(f"Date : {result['upload_date']}")
    if result.get("duration"):
        head.append(f"Durée : {result['duration']}")
    parts.append("\n".join(head))

    if result.get("description"):
        parts.append("— Légende / description —\n" + result["description"])

    if result.get("transcript"):
        label = result.get("method") or "transcription"
        parts.append(f"— Transcription ({label}) —\n" + result["transcript"])

    return "\n\n".join(parts).strip()


def extract_content(url):
    """
    Point d'entrée principal.
    Renvoie un dictionnaire avec les infos + la transcription + un texte tout prêt.
    """
    info, cookies = _probe(url)
    result = _build_meta(info)

    # On utilise l'URL résolue (utile si l'URL d'origine était une liste/profil)
    target_url = info.get("webpage_url") or url

    transcript, method, lang = _try_subtitles(target_url, info, cookies=cookies)
    if not transcript:
        transcript, lang = _transcribe_audio(target_url, cookies=cookies)
        method = f"Whisper local ({WHISPER_MODEL})" if transcript else None

    result["transcript"] = transcript
    result["method"] = method
    result["transcript_language"] = lang

    if not transcript and not result.get("description"):
        result["warning"] = (
            "Aucun texte n'a pu être extrait (ni sous-titres, ni légende, ni audio). "
            "Le contenu est peut-être une image, ou il nécessite une connexion (cookies)."
        )

    result["text_for_claude"] = format_for_claude(result)
    return result
