"""Traduction à la volée du contenu hors fichiers de langue, avec cache.

Ce qui n'est pas dans app/locales/ — horaires et notes de l'annuaire, note
d'un point focal sur un dossier — est traduit une seule fois par Burkimbia,
puis servi depuis la mémoire (et la table `translations`, qui survit à un
redémarrage).

Jamais dans une requête : l'API met 2 à 4 s par phrase, et l'annuaire entier
plusieurs minutes. `localized()` rend donc immédiatement ce qu'il a — la
traduction si elle est en cache, sinon le texte source — et met le manquant
dans une file qu'un fil de fond vide. Au démarrage, l'annuaire est mis en file
d'office (`warm`), pour que la première personne en mooré ne voie pas du
français.

Ce qui passe ici est public ou destiné à la personne. Le récit d'un
signalement ne doit JAMAIS transiter par ce module.
"""

import hashlib
import logging
import queue
import threading
import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import SessionLocal
from ..models import Resource, Translation
from . import translate

log = logging.getLogger("translate")

# Après une panne de l'API, on attend avant de reprendre la file. Quota de la
# clé épuisé : bien plus long, il ne se recharge pas en quelques minutes.
RETRY_DELAY = 60.0
QUOTA_DELAY = 60 * 60.0

# id -> traduction, ou None si rejetée (on garde la source, sans réessayer).
_cache: dict[str, str | None] = {}
_queue: "queue.Queue[tuple[str, str, str, str]]" = queue.Queue()
_queued: set[str] = set()
_lock = threading.Lock()
_started = False


def _id(text: str, src: str, tgt: str) -> str:
    return hashlib.sha256(f"{src}\n{tgt}\n{text}".encode()).hexdigest()


def targets() -> list[str]:
    """Langues du site que l'API sait produire depuis le français."""
    return [l for l in settings.languages if translate.supported(settings.default_lang, l)]


def localized(text: str | None, tgt: str, src: str | None = None) -> str | None:
    """Traduction de `text` vers `tgt` si elle est prête, sinon `text` tel quel.

    Sans clé, ou pour une paire non gérée (dioula, anglais -> mooré…), rend
    la source : le site reste utilisable, juste pas traduit.
    """
    src = src or settings.default_lang
    if not text or not text.strip() or tgt == src or not translate.enabled() or not translate.supported(src, tgt):
        return text
    key = _id(text, src, tgt)
    if key in _cache:
        return _cache[key] or text
    with _lock:
        if key not in _queued:
            _queued.add(key)
            _queue.put((key, text, src, tgt))
    return text


def load(db: Session) -> None:
    """Recharge le cache mémoire depuis la base (au démarrage)."""
    rows = db.execute(select(Translation.id, Translation.output)).all()
    _cache.update({row.id: row.output for row in rows})
    log.info("translate: %d traductions en cache", len(_cache))


def warm(db: Session) -> None:
    """Met l'annuaire en file pour chaque langue cible, avant toute visite."""
    for r in db.execute(select(Resource)).scalars():
        for tgt in targets():
            localized(r.hours, tgt)
            localized(r.notes, tgt)


def _store(key: str, text: str, src: str, tgt: str, output: str | None) -> None:
    with SessionLocal() as db:
        db.merge(Translation(id=key, src_lang=src, tgt_lang=tgt, source=text, output=output))
        db.commit()
    _cache[key] = output


def _worker() -> None:
    while True:
        key, text, src, tgt = _queue.get()
        try:
            output = translate.translate_sync(text, src, tgt)
        except translate.Rejected as why:
            log.info("translate: %s -> %s rejeté (%s), source conservée", src, tgt, why)
            output = None
        except translate.TranslateUnavailable as why:
            # Le texte repasse en fin de file : il sera retenté après la pause.
            delay = QUOTA_DELAY if why.quota else RETRY_DELAY
            log.warning("translate: API indisponible (%s), pause %ss", why, delay)
            _queue.put((key, text, src, tgt))
            time.sleep(delay)
            continue
        except Exception:  # noqa: BLE001 — le fil ne doit jamais mourir
            log.exception("translate: erreur inattendue")
            with _lock:
                _queued.discard(key)
            time.sleep(RETRY_DELAY)
            continue
        try:
            _store(key, text, src, tgt, output)
        except Exception:  # noqa: BLE001
            log.exception("translate: écriture en base impossible")
            _cache[key] = output  # au moins pour ce processus
        with _lock:
            _queued.discard(key)


def start(db: Session) -> None:
    """À appeler une fois au démarrage : charge le cache et lance le fil de fond."""
    global _started
    if _started or not translate.enabled() or not targets():
        return
    load(db)
    warm(db)
    threading.Thread(target=_worker, name="translate", daemon=True).start()
    _started = True
    log.info("translate: fil de fond démarré, %d texte(s) en attente", _queue.qsize())
