"""Chiffrement des signalements au repos : libsodium SecretBox (XSalsa20-Poly1305).

Le serveur détient la clé (REPORT_SECRET_KEY) et déchiffre lui-même, mais
uniquement pour un acteur connecté et autorisé à voir le signalement (voir
services.visible_reports). Une fuite de la base seule ne révèle que le type,
la région et la date ; il faut aussi la clé, qui n'est que dans l'environnement.

Pourquoi pas de bout en bout ? Un signalement passe de main en main (relais,
point focal, action sociale, gestionnaire de cas) et se fait reformuler en
route. Chaque destinataire devrait rechiffrer pour le suivant, depuis son
propre appareil : intenable pour des relais communautaires sur téléphone.

Format stocké : `v2:` + base64(nonce || ciphertext). Les signalements créés
avant la refonte n'ont pas de préfixe : ils sont en sealed box (clé publique
seule côté serveur) et ne peuvent être relus qu'après `python -m scripts.reencrypt`
avec l'ancienne clé privée.
"""

import base64

from nacl.public import PrivateKey, PublicKey, SealedBox
from nacl.secret import SecretBox
from nacl.utils import random as nacl_random

from .config import settings

PREFIX = "v2:"


class LegacyCiphertext(Exception):
    """Ancien format (sealed box) : le serveur ne peut pas le lire seul."""


def generate_secret_key() -> str:
    return _b64(nacl_random(SecretBox.KEY_SIZE))


def _box(secret_key_b64: str | None = None) -> SecretBox:
    key_b64 = secret_key_b64 or settings.report_secret_key
    if not key_b64:
        raise RuntimeError(
            "REPORT_SECRET_KEY manquante. Lancez `python -m scripts.gen_keys` et copiez la clé dans .env"
        )
    return SecretBox(_unb64(key_b64))


def encrypt(plaintext: str, secret_key_b64: str | None = None) -> str:
    return PREFIX + _b64(_box(secret_key_b64).encrypt(plaintext.encode("utf-8")))


def is_legacy(ciphertext: str) -> bool:
    return not ciphertext.startswith(PREFIX)


def decrypt(ciphertext: str, secret_key_b64: str | None = None) -> str:
    if is_legacy(ciphertext):
        raise LegacyCiphertext()
    return _box(secret_key_b64).decrypt(_unb64(ciphertext[len(PREFIX):])).decode("utf-8")


def try_decrypt(ciphertext: str | None) -> str | None:
    """Texte en clair, ou None si absent / illisible (ancien format, clé absente)."""
    if not ciphertext:
        return None
    try:
        return decrypt(ciphertext)
    except Exception:  # noqa: BLE001 — l'appelant affiche « illisible », rien de plus
        return None


# --------------------------------------------------------------------------- ancien format


def generate_keypair() -> tuple[str, str]:
    """Ancien schéma. Retourne (clé_privée_b64, clé_publique_b64)."""
    sk = PrivateKey.generate()
    return _b64(bytes(sk)), _b64(bytes(sk.public_key))


def legacy_encrypt(plaintext: str, public_key_b64: str) -> str:
    box = SealedBox(PublicKey(_unb64(public_key_b64)))
    return _b64(box.encrypt(plaintext.encode("utf-8")))


def legacy_decrypt(ciphertext_b64: str, private_key_b64: str) -> str:
    """Sealed box : uniquement pour scripts/reencrypt.py, avec l'ancienne clé privée."""
    box = SealedBox(PrivateKey(_unb64(private_key_b64)))
    return box.decrypt(_unb64(ciphertext_b64)).decode("utf-8")


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _unb64(s: str) -> bytes:
    return base64.b64decode(s)
