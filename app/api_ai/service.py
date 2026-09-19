"""Proposition de reformulation pour les relais : façade entre l'application et l'agent.

Ce que l'application garantit, quel que soit l'agent derrière :
- désactivé sans clé (OPENAI_API_KEY) : les écrans ne montrent pas le bouton ;
- le relais reste l'auteur : la proposition remplit le champ, il relit, corrige,
  et c'est lui qui transmet. Rien n'est enregistré automatiquement ;
- une panne du fournisseur ne bloque jamais la transmission : on renvoie une
  erreur lisible, le relais reformule à la main ;
- seul le récit (déjà anonyme par consigne) part chez le fournisseur : ni le
  code de suivi, ni le nom du relais, ni le canal.

⚠ Le récit quitte le serveur pour un service tiers (OpenAI). À décider avec les
partenaires avant activation en production ; voir README, section « Assistant ».
"""

import logging
from dataclasses import dataclass, field

from ..config import settings

log = logging.getLogger("ai")

# Plus court que la description : c'est une reformulation, pas un doublon.
SUMMARY_MAX = 1200


class AiUnavailable(Exception):
    """Pas de clé, ou fournisseur en panne : le relais reformule à la main."""


@dataclass
class Suggestion:
    summary: str
    urgency: str = ""
    anonymity_risks: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)


def enabled() -> bool:
    return bool(settings.openai_api_key)


def suggest_summary(text: str, *, region: str = "", commune: str = "", subtype_label: str = "") -> Suggestion:
    if not enabled():
        raise AiUnavailable("disabled")
    text = (text or "").strip()
    if not text:
        raise AiUnavailable("empty")
    try:
        # Import tardif : le serveur démarre même sans le paquet `openai`.
        from . import agent_description

        out = agent_description.agent_reformulation(text, region=region, commune=commune, type_incident=subtype_label)
    except Exception as e:  # noqa: BLE001 — réseau, quota, JSON invalide : même issue pour le relais
        log.warning("Reformulation indisponible : %s", type(e).__name__)
        raise AiUnavailable(type(e).__name__) from None

    summary = str(out.get("reformulation") or "").strip()[:SUMMARY_MAX]
    if not summary:
        raise AiUnavailable("empty_answer")
    return Suggestion(
        summary=summary,
        urgency=str(out.get("urgence") or ""),
        anonymity_risks=[str(x) for x in out.get("risques_anonymat") or [] if x],
        missing=[str(x) for x in out.get("elements_manquants") or [] if x],
    )
