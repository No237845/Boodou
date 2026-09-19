"""Comptes acteurs : mots de passe, jetons de session, dépendances FastAPI.

Deux façons de présenter un jeton, pour un même mécanisme :
- cookie `espace_session` (espace web, HttpOnly, SameSite=Strict) ;
- en-tête `Authorization: Bearer …` (application mobile).

Le jeton n'est stocké qu'haché (SHA-256) dans `actor_tokens`.
"""

import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Cookie, Depends, Header, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .db import get_db
from .models import Actor, ActorToken

SESSION_COOKIE = "espace_session"

# scrypt (stdlib) : pas de dépendance supplémentaire, résistant au matériel
# dédié. n=2^14 ≈ 50 ms par vérification sur un petit serveur : assez lent
# pour freiner une attaque en ligne, assez rapide pour ne pas gêner l'usager.
_SCRYPT_N, _SCRYPT_R, _SCRYPT_P = 2**14, 8, 1
PASSWORD_MIN = 8


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P)
    return "scrypt$" + _b64(salt) + "$" + _b64(digest)


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, salt_b64, digest_b64 = stored.split("$")
        if scheme != "scrypt":
            return False
        salt, expected = _unb64(salt_b64), _unb64(digest_b64)
    except (ValueError, TypeError):
        return False
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P)
    return hmac.compare_digest(digest, expected)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("ascii")).hexdigest()


def authenticate(db: Session, username: str, password: str) -> Actor | None:
    actor = db.execute(select(Actor).where(Actor.username == (username or "").strip().lower())).scalar_one_or_none()
    if actor is None:
        # Même coût qu'une vraie vérification : un temps de réponse différent
        # révélerait quels identifiants existent.
        verify_password(password, hash_password("x"))
        return None
    if not actor.active or not verify_password(password, actor.password_hash):
        return None
    return actor


def issue_token(db: Session, actor: Actor, *, ttl: int) -> str:
    token = secrets.token_urlsafe(32)
    db.add(
        ActorToken(
            token_hash=_token_hash(token),
            actor_id=actor.id,
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=ttl),
        )
    )
    # Ménage opportuniste : les jetons expirés partent au fil de l'eau.
    db.execute(delete(ActorToken).where(ActorToken.expires_at < datetime.now(timezone.utc)))
    db.commit()
    return token


def revoke_token(db: Session, token: str | None) -> None:
    if token:
        db.execute(delete(ActorToken).where(ActorToken.token_hash == _token_hash(token)))
        db.commit()


def revoke_all(db: Session, actor: Actor) -> None:
    """Déconnecte l'acteur partout : changement de mot de passe, désactivation."""
    db.execute(delete(ActorToken).where(ActorToken.actor_id == actor.id))
    db.commit()


def actor_from_token(db: Session, token: str | None) -> Actor | None:
    if not token:
        return None
    row = db.get(ActorToken, _token_hash(token))
    if row is None or row.expires_at < datetime.now(timezone.utc):
        return None
    actor = db.get(Actor, row.actor_id)
    if actor is None or not actor.active:
        return None
    return actor


# --------------------------------------------------------------------------- dépendances


def optional_actor(
    authorization: str = Header(default=""),
    espace_session: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> Actor | None:
    token = None
    if authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    return actor_from_token(db, token or espace_session)


def current_actor(actor: Actor | None = Depends(optional_actor)) -> Actor:
    if actor is None:
        raise HTTPException(status_code=401, detail="unauthorized")
    return actor


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _unb64(s: str) -> bytes:
    return base64.b64decode(s)
