"""Webhook WhatsApp Cloud API (Meta Graph API).

- GET  /webhooks/whatsapp : vérification du webhook par Meta (hub.challenge).
- POST /webhooks/whatsapp : réception des messages, signés par l'App Secret.

Chaque message est traité par le moteur de menu (app.bot.engine), puis les
réponses sont envoyées via POST /{phone_number_id}/messages.

Confidentialité : le numéro de l'expéditeur ne transite qu'en mémoire, le temps
de répondre. Il n'est ni journalisé ni stocké (le moteur n'en garde qu'un hash).
"""

import hashlib
import hmac
import logging
import time

import httpx
from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from ..bot import engine
from ..config import settings
from ..db import SessionLocal
from ..models import Channel

router = APIRouter(prefix="/webhooks/whatsapp", tags=["whatsapp"])
log = logging.getLogger("whatsapp")

# Meta renvoie un webhook tant qu'il n'a pas reçu de 200 : on ignore les doublons.
_seen: dict[str, float] = {}
SEEN_TTL = 10 * 60


def _graph_url() -> str:
    return f"https://graph.facebook.com/{settings.whatsapp_api_version}/{settings.whatsapp_phone_number_id}/messages"


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {settings.whatsapp_access_token}", "Content-Type": "application/json"}


# --------------------------------------------------------------------------- vérification


@router.get("", include_in_schema=False)
def verify(
    mode: str = Query("", alias="hub.mode"),
    token: str = Query("", alias="hub.verify_token"),
    challenge: str = Query("", alias="hub.challenge"),
):
    if mode == "subscribe" and settings.whatsapp_verify_token and hmac.compare_digest(token, settings.whatsapp_verify_token):
        return PlainTextResponse(challenge)
    raise HTTPException(status_code=403, detail="verification failed")


def _check_signature(body: bytes, signature: str) -> None:
    if not settings.whatsapp_app_secret:
        log.warning("WHATSAPP_APP_SECRET absent : signature des webhooks non vérifiée (dev uniquement).")
        return
    expected = "sha256=" + hmac.new(settings.whatsapp_app_secret.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature or ""):
        raise HTTPException(status_code=403, detail="bad signature")


# --------------------------------------------------------------------------- réception


@router.post("", include_in_schema=False)
async def receive(
    request: Request,
    background: BackgroundTasks,
    x_hub_signature_256: str = Header(default=""),
):
    body = await request.body()
    _check_signature(body, x_hub_signature_256)
    payload = await request.json()

    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for message in value.get("messages", []):
                if _is_duplicate(message.get("id", "")):
                    continue
                sender = message.get("from", "")
                text = _extract_text(message)
                if sender and text is not None:
                    # Répondre hors du cycle de la requête : Meta attend un 200 rapide.
                    background.add_task(_process, sender, text, message.get("id"))
    # Toujours 200, sinon Meta réessaie indéfiniment.
    return {"status": "ok"}


def _is_duplicate(message_id: str) -> bool:
    now = time.time()
    for k in [k for k, ts in _seen.items() if ts < now - SEEN_TTL]:
        _seen.pop(k, None)
    if message_id in _seen:
        return True
    _seen[message_id] = now
    return False


def _extract_text(message: dict) -> str | None:
    """Texte du message, ou choix d'un bouton/liste interactive. None si non géré."""
    mtype = message.get("type")
    if mtype == "text":
        return message.get("text", {}).get("body", "")
    if mtype == "interactive":
        inter = message.get("interactive", {})
        reply = inter.get("button_reply") or inter.get("list_reply") or {}
        return reply.get("id") or reply.get("title", "")
    if mtype == "button":
        return message.get("button", {}).get("text", "")
    # Image, audio, localisation... : on renvoie au menu plutôt que d'ignorer.
    return "0"


async def _process(sender: str, text: str, message_id: str | None) -> None:
    with SessionLocal() as db:
        replies = engine.handle(db, Channel.WHATSAPP, sender, text)
    async with httpx.AsyncClient(timeout=15) as client:
        if message_id:
            await _mark_read(client, message_id)
        for reply in replies:
            await send_text(client, sender, reply)


# --------------------------------------------------------------------------- envoi


async def send_text(client: httpx.AsyncClient, to: str, text: str) -> None:
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {"preview_url": False, "body": text},
    }
    r = await client.post(_graph_url(), headers=_headers(), json=payload)
    if r.status_code >= 400:
        # On journalise l'erreur Meta mais jamais le destinataire ni le contenu.
        log.error("Envoi WhatsApp refusé (%s) : %s", r.status_code, r.text[:300])


async def _mark_read(client: httpx.AsyncClient, message_id: str) -> None:
    payload = {"messaging_product": "whatsapp", "status": "read", "message_id": message_id}
    try:
        await client.post(_graph_url(), headers=_headers(), json=payload)
    except httpx.HTTPError:
        pass
