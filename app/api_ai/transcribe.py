"""Transcription d'un enregistrement vocal (Gladia, mode pré-enregistré).

Pour qui lit ou écrit peu : la personne parle, le texte remplit le champ, elle
relit (ou se fait relire) et envoie. Le serveur relaie l'audio à Gladia et ne
garde rien : ni fichier sur disque, ni texte — celui-ci ne revient qu'au client.

Mode pré-enregistré plutôt que temps réel : une plainte dure 30 s à 2 min, et
un envoi de fichier passe là où un flux websocket en PCM brut décroche (2G/3G).
Trois appels : upload → création du travail → lecture du résultat (sondage).

⚠ L'audio quitte le serveur vers un service tiers : à décider avec les
partenaires, et dit à la personne avant qu'elle n'enregistre.
"""

import asyncio
import logging

import httpx

from ..config import settings

log = logging.getLogger("speech")

GLADIA = "https://api.gladia.io/v2"
# Langues que Gladia transcrit avec un modèle dédié. Mooré et dioula n'y sont
# pas : on laisse la détection automatique, qui rendra au mieux du français.
KNOWN_LANGS = {"fr", "en"}
POLL_INTERVAL = 1.0
POLL_TIMEOUT = 90.0


class SpeechUnavailable(Exception):
    """Pas de clé, ou service en panne : la personne écrit à la main."""


def enabled() -> bool:
    return bool(settings.gladia_api_key)


async def transcribe(audio: bytes, filename: str, content_type: str, lang: str) -> str:
    if not enabled():
        raise SpeechUnavailable("disabled")
    headers = {"x-gladia-key": settings.gladia_api_key}
    body: dict = {"model": settings.gladia_model}
    if lang in KNOWN_LANGS:
        body["language_config"] = {"languages": [lang], "code_switching": False}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(f"{GLADIA}/upload", headers=headers, files={"audio": (filename, audio, content_type)})
            r.raise_for_status()
            body["audio_url"] = r.json()["audio_url"]
            r = await client.post(f"{GLADIA}/pre-recorded", headers=headers, json=body)
            r.raise_for_status()
            result_url = r.json()["result_url"]
            waited = 0.0
            while waited < POLL_TIMEOUT:
                r = await client.get(result_url, headers=headers)
                r.raise_for_status()
                data = r.json()
                if data.get("status") == "done":
                    return (data["result"]["transcription"]["full_transcript"] or "").strip()
                if data.get("status") == "error":
                    raise SpeechUnavailable("gladia_error")
                await asyncio.sleep(POLL_INTERVAL)
                waited += POLL_INTERVAL
    except SpeechUnavailable:
        raise
    except Exception as e:  # noqa: BLE001 — réseau, quota, réponse inattendue : même issue pour la personne
        # Jamais le contenu ni l'audio dans les journaux.
        log.warning("Transcription indisponible : %s", type(e).__name__)
        raise SpeechUnavailable(type(e).__name__) from None
    raise SpeechUnavailable("timeout")
