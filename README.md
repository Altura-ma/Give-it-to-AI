# 🎬 → 📝 Give it to AI

Colle le lien d'une vidéo ou d'une publication (Instagram, TikTok, X, YouTube…),
et récupère son **contenu en texte** (transcription + légende + infos),
prêt à coller dans une conversation avec Claude.

**100 % gratuit. Aucune API payante. Tout tourne sur ton ordinateur.**

---

## ✨ Ce que ça fait

1. Tu colles un lien.
2. L'outil récupère la vidéo et son texte :
   - s'il existe déjà des **sous-titres** → il les prend (instantané, gratuit) ;
   - sinon, il **transcrit l'audio** avec Whisper, un modèle qui tourne en local
     (gratuit, sans clé d'API).
3. Tu obtiens un beau texte avec un bouton **« Copier pour Claude »**.

Réseaux supportés : Instagram, TikTok, X (Twitter), YouTube, Facebook,
et des centaines d'autres (via [yt-dlp](https://github.com/yt-dlp/yt-dlp)).

---

## 🚀 Démarrage ultra-simple

### Pré-requis (une seule fois)
- Installer **Python 3** : <https://www.python.org/downloads/> (coche « Add to PATH » sur Windows).
- Recommandé : installer **ffmpeg** (améliore la transcription). Optionnel pour démarrer.

### Lancer l'outil

**Sur Windows :** double-clique sur **`start.bat`**

**Sur Mac / Linux :** double-clique sur **`start.sh`**
(ou dans un terminal : `./start.sh`)

La première fois, il installe tout seul ce qu'il faut (ça prend quelques minutes).
Ensuite, ton navigateur s'ouvre sur **http://localhost:8000**.

👉 Colle un lien, clique sur **« Récupérer le texte »**, puis **« Copier pour Claude »**. Voilà !

---

## 🔧 Lancement manuel (pour les curieux)

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Puis ouvre <http://localhost:8000>.

En ligne de commande :

```bash
python cli.py "https://www.tiktok.com/@compte/video/123..."
```

---

## ⚙️ Réglages (optionnels)

On les définit via des variables d'environnement avant de lancer :

| Variable | À quoi ça sert | Défaut |
|---|---|---|
| `WHISPER_MODEL` | Qualité/vitesse de la transcription : `tiny`, `base`, `small`, `medium`, `large-v3`. Pour le français, `small` est meilleur. | `base` |
| `PORT` | Port du serveur web | `8000` |
| `COOKIES_FILE` | Fichier de cookies (voir plus bas) | — |
| `COOKIES_FROM_BROWSER` | Récupère les cookies d'un navigateur, ex. `chrome`, `firefox` | — |

Exemple (Mac/Linux) :
```bash
WHISPER_MODEL=small python app.py
```

---

## 🔐 Contenus Instagram / privés (cookies)

Instagram bloque souvent l'accès sans être connecté. Si un lien échoue, deux options :

1. **Le plus simple** — utiliser les cookies de ton navigateur déjà connecté :
   ```bash
   COOKIES_FROM_BROWSER=chrome python app.py
   ```
2. **Fichier de cookies** — exporte tes cookies (extension « Get cookies.txt »)
   dans un fichier `cookies.txt`, puis :
   ```bash
   COOKIES_FILE=cookies.txt python app.py
   ```

⚠️ Ne partage jamais ton fichier de cookies (il est déjà ignoré par git).

---

## ❓ Problèmes fréquents

- **« python n'est pas reconnu »** → Python n'est pas installé ou pas dans le PATH.
- **La transcription est lente** → la 1re fois, Whisper télécharge le modèle. Ensuite c'est plus rapide. Pour accélérer, utilise `WHISPER_MODEL=tiny`.
- **Une vidéo refuse de se charger** → contenu privé : voir la section cookies ci-dessus.
- **Transcription de mauvaise qualité** → essaie `WHISPER_MODEL=small` et installe ffmpeg.

---

## 💸 Coût

Zéro. Tout est open-source et tourne en local :
`yt-dlp` (téléchargement) + `faster-whisper` (transcription) + `FastAPI` (page web).
