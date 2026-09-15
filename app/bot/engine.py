"""Moteur de conversation par menus numérotés, indépendant du canal.

WhatsApp et SMS appellent `handle(channel, phone, text)` et reçoivent une liste
de messages texte à renvoyer. Le moteur ne connaît ni l'API Meta ni l'API SMS.

Confidentialité :
- le numéro de téléphone n'est jamais stocké : il est haché (SHA-256 + sel) pour
  servir de clé de session, en mémoire uniquement, purgée après `bot_session_ttl` ;
- la description du signalement est chiffrée par `services.create_report` comme
  sur le web ; seuls type / région / canal / langue restent en clair.

États :  LANG -> MENU -> REPORT_TYPE -> REPORT_REGION -> REPORT_DESC -> MENU
         LANG -> MENU -> RES_REGION -> MENU
"""

import hashlib
import hmac
import time
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from ..config import settings
from ..i18n import t
from ..models import Channel, ReportType, ResourceCategory
from ..seed import region_names
from ..services import ValidationError, create_report, find_resources

LANG_CHOICES = {"1": "fr", "2": "mos", "3": "dyu"}
TYPE_CHOICES = {"1": ReportType.VIOLENCE, "2": ReportType.MENACE, "3": ReportType.GBV, "4": ReportType.TERRORISME}
MENU_KEYWORDS = {"0", "menu", "annuler", "retour", "stop"}
RESTART_KEYWORDS = {"bonjour", "salut", "hello", "hi", "start", "langue", "language"}

# Longueur max d'un message WhatsApp : 4096 caractères. On coupe bien avant.
MAX_MESSAGE = 3000


@dataclass
class BotSession:
    lang: str = settings.default_lang
    state: str = "LANG"
    data: dict = field(default_factory=dict)
    expires: float = 0.0

    def touch(self) -> None:
        self.expires = time.time() + settings.bot_session_ttl


_sessions: dict[str, BotSession] = {}


def phone_key(phone: str) -> str:
    """Hash irréversible du numéro : clé de session, jamais persistée."""
    return hmac.new(settings.bot_phone_salt.encode(), phone.encode(), hashlib.sha256).hexdigest()


def _get_session(phone: str) -> BotSession:
    """Retourne la session du numéro (nouvelle si absente). Purge les sessions expirées."""
    now = time.time()
    for key in [k for k, s in _sessions.items() if s.expires < now]:
        _sessions.pop(key, None)
    key = phone_key(phone)
    session = _sessions.get(key)
    if session is None:
        session = _sessions[key] = BotSession()
    session.touch()
    return session


def reset_session(phone: str) -> None:
    _sessions.pop(phone_key(phone), None)


# --------------------------------------------------------------------------- rendu


def _regions_list() -> str:
    return "\n".join(f"{i} - {name}" for i, name in enumerate(region_names(), start=1))


def _format_resources(lang: str, resources, intro: str = "") -> list[str]:
    lines = [intro] if intro else []
    current_cat = None
    for r in resources:
        if r.category != current_cat:
            current_cat = r.category
            lines.append(f"\n*{t(lang, 'cat_' + r.category.value)}*")
        where = r.city or (t(lang, "resources_national") if r.region == "*" else r.region)
        phone = f" 📞 {r.phone}" if r.phone else ""
        flag = "" if r.verified else f" {t(lang, 'bot_unverified')}"
        lines.append(f"• {r.name}{phone}{flag}\n  {where}{' · ' + r.hours if r.hours else ''}")
    return _chunk("\n".join(lines).strip())


def _chunk(text: str) -> list[str]:
    """Découpe un long texte en messages < MAX_MESSAGE, sur des sauts de ligne."""
    parts: list[str] = []
    while len(text) > MAX_MESSAGE:
        cut = text.rfind("\n", 0, MAX_MESSAGE)
        if cut <= 0:
            cut = MAX_MESSAGE
        parts.append(text[:cut].rstrip())
        text = text[cut:].lstrip()
    if text:
        parts.append(text)
    return parts


# --------------------------------------------------------------------------- moteur


def handle(db: Session, channel: Channel, phone: str, text: str) -> list[str]:
    """Traite un message entrant et renvoie les réponses à envoyer."""
    session = _get_session(phone)
    lang = session.lang
    msg = (text or "").strip()
    low = msg.lower()

    # "Bonjour", "Bonjour Boodou", "start"... : retour au choix de la langue.
    if low in RESTART_KEYWORDS or low.startswith("bonjour"):
        session.state, session.data = "LANG", {}
        return [t(lang, "bot_welcome")]

    if session.state == "LANG":
        if low in LANG_CHOICES:
            session.lang = lang = LANG_CHOICES[low]
            session.state = "MENU"
            return [t(lang, "bot_menu")]
        # Premier message quelconque (emoji, texte libre) : on accueille.
        return [t(lang, "bot_welcome")]

    if low in MENU_KEYWORDS:
        session.state = "MENU"
        session.data = {}
        return [t(lang, "bot_menu")]

    handler = _STATES.get(session.state, _menu)
    return handler(db, channel, session, msg)


def _menu(db: Session, channel: Channel, s: BotSession, msg: str) -> list[str]:
    lang = s.lang
    if msg == "1":
        s.state, s.data = "REPORT_TYPE", {}
        return [t(lang, "bot_ask_type")]
    if msg in ("2", "3", "4"):
        s.state, s.data = "RES_REGION", {"choice": msg}
        return [t(lang, "bot_ask_region_optional", regions=_regions_list())]
    return [t(lang, "bot_invalid"), t(lang, "bot_menu")]


def _report_type(db: Session, channel: Channel, s: BotSession, msg: str) -> list[str]:
    lang = s.lang
    if msg not in TYPE_CHOICES:
        return [t(lang, "bot_invalid"), t(lang, "bot_ask_type")]
    s.data["type"] = TYPE_CHOICES[msg]
    s.state = "REPORT_REGION"
    return [t(lang, "bot_ask_region", regions=_regions_list())]


def _pick_region(msg: str) -> str | None:
    names = region_names()
    if msg.isdigit() and 1 <= int(msg) <= len(names):
        return names[int(msg) - 1]
    # Tolère le nom tapé en toutes lettres.
    return next((n for n in names if n.lower() == msg.lower()), None)


def _report_region(db: Session, channel: Channel, s: BotSession, msg: str) -> list[str]:
    lang = s.lang
    region = _pick_region(msg)
    if region is None:
        return [t(lang, "bot_invalid"), t(lang, "bot_ask_region", regions=_regions_list())]
    s.data["region"] = region
    s.state = "REPORT_DESC"
    return [t(lang, "bot_ask_description")]


def _report_desc(db: Session, channel: Channel, s: BotSession, msg: str) -> list[str]:
    lang = s.lang
    rtype: ReportType = s.data["type"]
    region: str = s.data["region"]
    try:
        create_report(db, type_=rtype.value, region=region, description=msg, channel=channel, lang=lang)
    except ValidationError as e:
        return [t(lang, e.key, **e.params), t(lang, "bot_ask_description")]
    s.state, s.data = "MENU", {}
    resources = find_resources(db, type_=rtype, region=region)
    out = [t(lang, "bot_report_done")]
    out += _format_resources(lang, resources, intro=t(lang, "bot_resources_intro"))
    out[-1] += t(lang, "bot_back_hint")
    return out


def _res_region(db: Session, channel: Channel, s: BotSession, msg: str) -> list[str]:
    lang = s.lang
    if msg == "99":
        region = None
    else:
        region = _pick_region(msg)
        if region is None:
            return [t(lang, "bot_invalid"), t(lang, "bot_ask_region_optional", regions=_regions_list())]

    choice = s.data.get("choice")
    if choice == "2":
        resources = find_resources(db, type_=ReportType.GBV, region=region)
        intro = t(lang, "bot_resources_intro")
    elif choice == "3":
        resources = find_resources(db, region=region, category=ResourceCategory.JUSTICE)
        resources = find_resources(db, region=region, category=ResourceCategory.URGENCE) + resources
        intro = t(lang, "bot_resources_intro")
    else:
        resources = find_resources(db, region=region, category=ResourceCategory.ONG)
        intro = t(lang, "bot_talk")

    if not resources:
        intro = t(lang, "bot_resources_none")
        resources = find_resources(db, category=ResourceCategory.URGENCE)

    s.state, s.data = "MENU", {}
    out = _format_resources(lang, resources, intro=intro)
    out[-1] += t(lang, "bot_back_hint")
    return out


_STATES = {
    "MENU": _menu,
    "REPORT_TYPE": _report_type,
    "REPORT_REGION": _report_region,
    "REPORT_DESC": _report_desc,
    "RES_REGION": _res_region,
}
