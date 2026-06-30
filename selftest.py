"""
Auto-test : vérifie que l'outil est bien installé et prêt à fonctionner.

Lance simplement :   python selftest.py

Il vérifie, étape par étape :
  1. Les librairies sont installées.
  2. Le décodage audio fonctionne (sans ffmpeg système).
  3. yt-dlp est opérationnel.
  4. Le modèle Whisper se charge (téléchargé au 1er lancement).
  5. Une transcription complète fonctionne (sur un court audio de test).
"""

import math
import os
import struct
import tempfile
import wave

OK = "[OK]"
KO = "[X]"


def step(n, label):
    print(f"\n[{n}] {label}")


def _make_test_wav(path, freq=440, seconds=1, rate=16000):
    with wave.open(path, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        for i in range(int(rate * seconds)):
            w.writeframes(struct.pack("<h", int(3000 * math.sin(2 * math.pi * freq * i / rate))))


def main():
    print("=" * 56)
    print("  Auto-test de « Give it to AI »")
    print("=" * 56)
    failures = 0

    # 1. Imports
    step(1, "Vérification des librairies…")
    try:
        import yt_dlp  # noqa
        import faster_whisper  # noqa
        import av  # noqa
        import fastapi  # noqa
        print(f"   {OK} yt-dlp, faster-whisper, PyAV, FastAPI sont installés.")
    except Exception as e:
        print(f"   {KO} Librairie manquante : {e}")
        print("   -> Lance d'abord l'installation (start.sh / start.bat).")
        return 1

    # 2. Décodage audio (sans ffmpeg système)
    step(2, "Test du décodage audio…")
    try:
        from faster_whisper.audio import decode_audio
        tmp = tempfile.mktemp(suffix=".wav")
        _make_test_wav(tmp)
        audio = decode_audio(tmp, sampling_rate=16000)
        os.remove(tmp)
        assert len(audio) > 0
        print(f"   {OK} Décodage audio OK ({len(audio)} échantillons).")
    except Exception as e:
        failures += 1
        print(f"   {KO} Échec du décodage audio : {e}")

    # 3. yt-dlp opérationnel
    step(3, "Vérification de yt-dlp…")
    try:
        import yt_dlp
        print(f"   {OK} yt-dlp version {yt_dlp.version.__version__}.")
    except Exception as e:
        failures += 1
        print(f"   {KO} yt-dlp indisponible : {e}")

    # 4. Chargement du modèle Whisper
    step(4, "Chargement du modèle Whisper (téléchargé la 1re fois, patiente)…")
    model = None
    try:
        from faster_whisper import WhisperModel
        name = os.environ.get("WHISPER_MODEL", "base")
        model = WhisperModel(name, device="cpu", compute_type="int8")
        print(f"   {OK} Modèle « {name} » chargé.")
    except Exception as e:
        failures += 1
        print(f"   {KO} Impossible de charger le modèle : {e}")
        print("   -> Vérifie ta connexion Internet (le modèle se télécharge 1 fois).")

    # 5. Transcription complète sur un audio de test
    if model is not None:
        step(5, "Test d'une transcription complète…")
        try:
            tmp = tempfile.mktemp(suffix=".wav")
            _make_test_wav(tmp, freq=300, seconds=2)
            segments, info = model.transcribe(tmp, vad_filter=False)
            list(segments)  # force l'exécution
            os.remove(tmp)
            print(f"   {OK} Transcription exécutée sans erreur "
                  f"(langue détectée : {getattr(info, 'language', '?')}).")
        except Exception as e:
            failures += 1
            print(f"   {KO} Échec de la transcription : {e}")

    print("\n" + "=" * 56)
    if failures == 0:
        print(f"  {OK} TOUT EST BON. L'outil est prêt à l'emploi !")
        print("  Lance-le avec start.sh (Mac/Linux) ou start.bat (Windows).")
    else:
        print(f"  {KO} {failures} problème(s) détecté(s). Voir les messages ci-dessus.")
    print("=" * 56)
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
