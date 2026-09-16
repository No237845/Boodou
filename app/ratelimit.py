"""Limitation de débit en mémoire, pour la consultation des codes de suivi.

Un code fait 50 bits : le deviner au hasard est déjà hors de portée. La limite
sert surtout à empêcher qu'un script balaie l'espace des codes pour compter les
signalements d'une région.

Confidentialité : l'IP n'est jamais stockée telle quelle ni écrite quelque part.
On en garde un HMAC tronqué, en mémoire seulement, purgé avec la fenêtre — même
principe que le hachage des numéros de téléphone dans `app/bot/engine.py`.
"""

import hashlib
import hmac
import time

from .config import settings

WINDOW = 15 * 60  # secondes
MAX_ATTEMPTS = 10  # essais par fenêtre et par client

# clé -> liste d'horodatages, en mémoire uniquement.
_hits: dict[str, list[float]] = {}


def _key(client: str) -> str:
    return hmac.new(settings.bot_phone_salt.encode(), client.encode(), hashlib.sha256).hexdigest()[:16]


def allow(client: str | None) -> bool:
    """True si ce client peut encore tenter une consultation."""
    now = time.time()
    # Purge des fenêtres écoulées : la table ne grossit pas indéfiniment.
    for k in [k for k, times in _hits.items() if not times or times[-1] < now - WINDOW]:
        _hits.pop(k, None)

    key = _key(client or "inconnu")
    times = [t for t in _hits.get(key, []) if t > now - WINDOW]
    if len(times) >= MAX_ATTEMPTS:
        _hits[key] = times
        return False
    times.append(now)
    _hits[key] = times
    return True


def reset() -> None:
    """Pour les tests."""
    _hits.clear()
