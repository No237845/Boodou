"""Génère la clé de chiffrement des signalements.

    python -m scripts.gen_keys

À copier dans le .env du serveur (REPORT_SECRET_KEY). Sans elle, rien ne
s'enregistre ni ne se lit. La perdre, c'est perdre tous les récits : gardez-en
une copie hors serveur, dans un coffre de mots de passe.
"""

from app.crypto import generate_secret_key

if __name__ == "__main__":
    print("# --- À mettre dans .env (serveur) et à sauvegarder hors serveur ---")
    print(f"REPORT_SECRET_KEY={generate_secret_key()}")
