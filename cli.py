"""
Version ligne de commande (pratique pour automatiser ou intégrer ailleurs).

Exemple :
    python cli.py "https://www.instagram.com/reel/XXXX/"

Affiche directement le texte prêt à coller dans une conversation.
"""

import sys
from extractor import extract_content


def main():
    if len(sys.argv) < 2:
        print("Usage : python cli.py <url>")
        sys.exit(1)
    url = sys.argv[1].strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    result = extract_content(url)
    print(result.get("text_for_claude") or result.get("warning") or "(Rien extrait.)")


if __name__ == "__main__":
    main()
