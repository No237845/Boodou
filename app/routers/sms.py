"""Canal SMS via Africa's Talking.

- POST /webhooks/sms          : réception d'un SMS entrant (form-urlencoded).
- POST /webhooks/sms/statut   : accusés de livraison (facultatif côté AT).

Le message est traité par le même moteur de menu que WhatsApp (app.bot.engine),
avec Channel.SMS. Le moteur ignore tout de l'opérateur ; ce fichier ne fait que
traduire entre l'API d'Africa's Talking et `engine.handle`.

Africa's Talking ne signe pas ses callbacks : l'URL déclarée chez eux doit donc
porter `?token=...` (SMS_WEBHOOK_TOKEN), sinon n'importe qui peut injecter de
faux SMS entrants et faire répondre le service à un numéro arbitraire.

Confidentialité : même règle que WhatsApp. Le numéro ne vit qu'en mémoire le
temps de répondre, n'est jamais journalisé, et le moteur n'en garde qu'un hash.
"""

import hmac
import logging
import re
import time

import httpx
from fastapi import APIRouter, BackgroundTasks, Form, HTTPException, Query

from ..bot import engine
from ..config import settings
from ..db import SessionLocal
from ..models import Channel

router = APIRouter(prefix="/webhooks/sms", tags=["sms"])
log = logging.getLogger("sms")

# Un segment SMS concaténé fait 153 caractères en GSM-7, mais seulement 67 en
# UCS-2 — et l'opérateur bascule en UCS-2 dès le premier caractère hors alphabet
# GSM. Nos textes sont pleins d'accents (é, à), et le mooré ajoute ẽ, ɩ, ɛ : en
# pratique tout part en UCS-2. 459 caractères = 3 segments GSM-7, 7 en UCS-2.
# Le moteur, lui, découpe pour WhatsApp (3000) : on redécoupe ici pour le SMS.
SMS_MAX_CHARS = 459

# Africa's Talking réémet un callback tant qu'il n'a pas reçu de 200.
_seen: dict[str, float] = {}
SEEN_TTL = 10 * 60


def _check_token(token: str) -> None:
    if not settings.sms_webhook_token:
        log.warning("SMS_WEBHOOK_TOKEN absent : callback SMS non authentifié (dev uniquement).")
        return
    if not hmac.compare_digest(token or "", settings.sms_webhook_token):
        raise HTTPException(status_code=403, detail="bad token")


def _is_duplicate(message_id: str) -> bool:
    now = time.time()
    for k in [k for k, ts in _seen.items() if ts < now - SEEN_TTL]:
        _seen.pop(k, None)
    if not message_id:
        return False
    if message_id in _seen:
        return True
    _seen[message_id] = now
    return False


# Le moteur écrit pour WhatsApp : gras `*...*`, emojis, puces « • », points
# médians. Rien de tout cela ne survit à un téléphone à touches, et surtout
# chaque caractère hors alphabet GSM-7 bascule le message entier en UCS-2, où un
# segment ne porte plus que 67 caractères au lieu de 153 — le SMS coûte alors
# deux fois plus cher. On remplace donc la typographie et on retire les emojis.
#
# On ne touche PAS aux lettres accentuées : é et à sont dans GSM-7, et les
# caractères du mooré (ẽ, ɩ, ɛ) n'y sont pas mais les abîmer rendrait le message
# illisible. Ces messages-là partiront en UCS-2, et c'est le bon compromis.
_SMS_SUBSTITUTIONS = {
    "•": "-", "·": "-", "—": "-", "–": "-", "…": "...",
    "’": "'", "‘": "'", "“": '"', "”": '"', " ": " ",
}
_EMOJI = re.compile(
    "[\U0001f000-\U0001faff☀-➿←-⇿⬀-⯿️⃣]"
)


def to_sms_text(text: str) -> str:
    """Adapte un message écrit pour WhatsApp à un affichage SMS."""
    for src, dst in _SMS_SUBSTITUTIONS.items():
        text = text.replace(src, dst)
    text = _EMOJI.sub("", text)
    text = text.replace("*", "")  # gras WhatsApp : sans effet en SMS
    # Les retraits d'emojis laissent des doubles espaces et des lignes vides.
    text = re.sub(r"[ \t]{2,}", " ", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def split_for_sms(text: str) -> list[str]:
    """Découpe un texte en messages <= SMS_MAX_CHARS, de préférence sur un saut de ligne."""
    parts: list[str] = []
    text = text.strip()
    while len(text) > SMS_MAX_CHARS:
        cut = text.rfind("\n", 0, SMS_MAX_CHARS)
        if cut <= 0:
            cut = text.rfind(" ", 0, SMS_MAX_CHARS)
        if cut <= 0:
            cut = SMS_MAX_CHARS
        parts.append(text[:cut].rstrip())
        text = text[cut:].lstrip()
    if text:
        parts.append(text)
    return parts


# --------------------------------------------------------------------------- réception


@router.post("", include_in_schema=False)
async def receive(
    background: BackgroundTasks,
    token: str = Query(default=""),
    # Champs postés par Africa's Talking (application/x-www-form-urlencoded).
    # `to`, `date` et `linkId` sont déclarés pour documenter la charge utile ;
    # le moteur n'en a pas besoin, et on ne les journalise pas.
    from_: str = Form(default="", alias="from"),
    text: str = Form(default=""),
    message_id: str = Form(default="", alias="id"),
    to: str = Form(default=""),
    date: str = Form(default=""),
    link_id: str = Form(default="", alias="linkId"),
):
    _check_token(token)
    if from_ and not _is_duplicate(message_id):
        # Répondre hors du cycle de la requête : AT attend un 200 rapide.
        background.add_task(_process, from_, text)
    # Toujours 200, sinon Africa's Talking réessaie.
    return {"status": "ok"}


@router.post("/statut", include_in_schema=False)
async def delivery_report(
    token: str = Query(default=""),
    status: str = Form(default=""),
    failure_reason: str = Form(default="", alias="failureReason"),
):
    """Accusés de livraison. On ne journalise que l'échec, et jamais le numéro."""
    _check_token(token)
    if status not in ("Success", "Sent", "Submitted"):
        log.warning("SMS non délivré (%s) : %s", status or "?", failure_reason or "sans motif")
    return {"status": "ok"}


async def _process(sender: str, text: str) -> None:
    with SessionLocal() as db:
        replies = engine.handle(db, Channel.SMS, sender, text)
    async with httpx.AsyncClient(timeout=20) as client:
        for reply in replies:
            for part in split_for_sms(to_sms_text(reply)):
                await send_sms(client, sender, part)


# --------------------------------------------------------------------------- envoi


async def send_sms(client: httpx.AsyncClient, to: str, message: str) -> bool:
    """Envoie un SMS. Retourne False en cas de refus, sans lever d'exception :
    un échec d'envoi ne doit jamais faire tomber le traitement du message suivant."""
    if not settings.sms_enabled:
        log.error("AT_USERNAME / AT_API_KEY absents : SMS non envoyé.")
        return False

    data = {"username": settings.at_username, "to": to, "message": message}
    if settings.at_sender_id:
        data["from"] = settings.at_sender_id

    try:
        r = await client.post(
            settings.at_base_url,
            data=data,
            headers={
                "apiKey": settings.at_api_key,
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
        )
    except httpx.HTTPError as e:
        log.error("Envoi SMS impossible : %s", type(e).__name__)
        return False

    if r.status_code >= 400:
        # On journalise l'erreur de l'opérateur, jamais le destinataire ni le contenu.
        log.error("Envoi SMS refusé (%s) : %s", r.status_code, r.text[:300])
        return False

    # AT répond 201 même quand un destinataire est rejeté : le vrai verdict est
    # dans statusCode (101 = Success, 102 = Queued). Tout le reste est un échec.
    recipients = r.json().get("SMSMessageData", {}).get("Recipients", [])
    failed = [x for x in recipients if x.get("statusCode") not in (101, 102)]
    if failed or not recipients:
        log.error("SMS rejeté par l'opérateur : %s", [x.get("status") for x in failed])
        return False
    return True
