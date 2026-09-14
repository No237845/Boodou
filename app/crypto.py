"""Chiffrement des signalements : libsodium "sealed box" (X25519 + XSalsa20-Poly1305).

Le serveur ne possède que la clé PUBLIQUE. Une fois chiffré, un signalement
ne peut être lu que par le détenteur de la clé PRIVÉE (organisation partenaire),
même en cas de fuite complète de la base de données ou du serveur.
"""

import base64

from nacl.public import PrivateKey, PublicKey, SealedBox

from .config import settings


def generate_keypair() -> tuple[str, str]:
    """Retourne (clé_privée_b64, clé_publique_b64)."""
    sk = PrivateKey.generate()
    return _b64(bytes(sk)), _b64(bytes(sk.public_key))


def encrypt(plaintext: str, public_key_b64: str | None = None) -> str:
    key_b64 = public_key_b64 or settings.report_public_key
    if not key_b64:
        raise RuntimeError(
            "REPORT_PUBLIC_KEY manquante. Lancez `python -m scripts.gen_keys` et copiez la clé publique dans .env"
        )
    box = SealedBox(PublicKey(_unb64(key_b64)))
    return _b64(box.encrypt(plaintext.encode("utf-8")))


def decrypt(ciphertext_b64: str, private_key_b64: str) -> str:
    """Utilisé uniquement côté partenaire (scripts/decrypt.py), jamais par le serveur."""
    box = SealedBox(PrivateKey(_unb64(private_key_b64)))
    return box.decrypt(_unb64(ciphertext_b64)).decode("utf-8")


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _unb64(s: str) -> bytes:
    return base64.b64decode(s)
