"""Génère la paire de clés de chiffrement des signalements.

    python -m scripts.gen_keys

- La clé PUBLIQUE va dans le .env du serveur (REPORT_PUBLIC_KEY).
- La clé PRIVÉE est remise à l'organisation partenaire et ne doit JAMAIS
  être copiée sur le serveur.
"""

from app.crypto import generate_keypair

if __name__ == "__main__":
    private, public = generate_keypair()
    print("# --- À mettre dans .env (serveur) ---")
    print(f"REPORT_PUBLIC_KEY={public}")
    print()
    print("# --- À conserver HORS serveur (organisation partenaire) ---")
    print(f"REPORT_PRIVATE_KEY={private}")
