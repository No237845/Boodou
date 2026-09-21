"""Moteur de conversation par menus numérotés, indépendant du canal.

WhatsApp et SMS appellent `handle(channel, phone, text)` et reçoivent une liste
de messages texte à renvoyer. Le moteur ne connaît ni l'API Meta ni l'API SMS.

Confidentialité :
- le numéro de téléphone n'est jamais stocké : il est haché (SHA-256 + sel) pour
  servir de clé de session, en mémoire uniquement, purgée après `bot_session_ttl` ;
- la description du signalement est chiffrée par `services.create_report` comme
  sur le web ; seuls type / région / canal / langue restent en clair.

États :  LANG -> MENU -> REPORT_TYPE -> REPORT_SUBTYPE -> REPORT_REGION
                      -> REPORT_COMMUNE -> REPORT_TO -> REPORT_DESC -> MENU
         LANG -> MENU -> RES_REGION -> MENU
         LANG -> MENU -> TRACK_CODE -> MENU
"""

import hashlib
import hmac
import time
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from .. import ratelimit
from ..api_ai import translate_cache
from ..config import settings
from ..i18n import t
from ..models import SUBTYPES, ActorRole, Channel, ReportSubtype, ReportType, ResourceCategory, format_code
from ..seed import communes_of, region_names
from ..services import ValidationError, create_report, find_report, find_resources, public_relais

LANG_CHOICES = {"1": "fr", "2": "mos", "3": "dyu", "4": "en", "5": "pt", "6": "ar"}
TYPES = list(SUBTYPES)  # VBG puis sécurité, dans l'ordre du menu
MENU_KEYWORDS = {"0", "menu", "annuler", "retour", "stop"}
RESTART_KEYWORDS = {"bonjour", "salut", "hello", "hi", "start", "langue", "language"}
# Reconnus dans n'importe quel état, y compris au milieu d'une description :
# quelqu'un qui tape ça est en train de paniquer, on ne lui demande rien d'autre.
WIPE_KEYWORDS = {"supprimer", "effacer", "supprime", "efface", "delete", "clear"}

# Longueur max d'un message WhatsApp : 4096 caractères. On coupe bien avant.
MAX_MESSAGE = 3000


@dataclass
class BotSession:
    lang: str = settings.default_lang
    state: str = "LANG"
    data: dict = field(default_factory=dict)
    expires: float = 0.0
    # Numéro haché : sert à limiter le débit sans jamais manipuler le numéro.
    key: str = ""

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
        session = _sessions[key] = BotSession(key=key)
    session.touch()
    return session


def reset_session(phone: str) -> None:
    _sessions.pop(phone_key(phone), None)


# --------------------------------------------------------------------------- rendu


def _numbered(items: list[str]) -> str:
    return "\n".join(f"{i} - {label}" for i, label in enumerate(items, start=1))


def _pick(msg: str, items: list) -> object | None:
    """Élément choisi par son numéro (1..n), ou None."""
    if msg.isdigit() and 1 <= int(msg) <= len(items):
        return items[int(msg) - 1]
    return None


def _regions_list() -> str:
    return _numbered(region_names())


def _types_list(lang: str) -> str:
    return _numbered([t(lang, "type_" + ty.value) for ty in TYPES])


def _subtypes_list(lang: str, rtype: ReportType) -> str:
    return _numbered([t(lang, "subtype_" + s.value) for s in SUBTYPES[rtype]])


def _format_resources(lang: str, resources, intro: str = "") -> list[str]:
    lines = [intro] if intro else []
    current_cat = None
    for r in resources:
        if r.category != current_cat:
            current_cat = r.category
            lines.append(f"\n*{t(lang, 'cat_' + r.category.value)}*")
        where = r.city or (t(lang, "resources_national") if r.region == "*" else r.region)
        phone = f" 📞 {r.phone}" if r.phone else ""
        hours = translate_cache.localized(r.hours, lang)
        lines.append(f"• {r.name}{phone}\n  {where}{' · ' + hours if hours else ''}")
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

    # Effacement. Traité ici et pas dans `_menu` parce que c'est le seul endroit
    # où l'on connaît le numéro, donc la session à purger.
    if low in WIPE_KEYWORDS or (session.state == "MENU" and msg == "6"):
        reset_session(phone)
        return [t(lang, "bot_wipe")]

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
        return [t(lang, "bot_ask_type", choices=_types_list(lang))]
    if msg in ("2", "3", "4"):
        s.state, s.data = "RES_REGION", {"choice": msg}
        return [t(lang, "bot_ask_region_optional", regions=_regions_list())]
    if msg == "5":
        s.state, s.data = "TRACK_CODE", {}
        return [t(lang, "bot_ask_code")]
    return [t(lang, "bot_invalid"), t(lang, "bot_menu")]


# --------------------------------------------------------------------------- signalement


def _report_type(db: Session, channel: Channel, s: BotSession, msg: str) -> list[str]:
    lang = s.lang
    rtype = _pick(msg, TYPES)
    if rtype is None:
        return [t(lang, "bot_invalid"), t(lang, "bot_ask_type", choices=_types_list(lang))]
    s.data["type"] = rtype
    s.state = "REPORT_SUBTYPE"
    return [t(lang, "bot_ask_subtype", choices=_subtypes_list(lang, rtype))]


def _report_subtype(db: Session, channel: Channel, s: BotSession, msg: str) -> list[str]:
    lang = s.lang
    rtype: ReportType = s.data["type"]
    sub = _pick(msg, SUBTYPES[rtype])
    if sub is None:
        return [t(lang, "bot_invalid"), t(lang, "bot_ask_subtype", choices=_subtypes_list(lang, rtype))]
    s.data["subtype"] = sub
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
    s.state = "REPORT_COMMUNE"
    return [t(lang, "bot_ask_commune", communes=_numbered(communes_of(region)))]


def _report_commune(db: Session, channel: Channel, s: BotSession, msg: str) -> list[str]:
    lang = s.lang
    communes = communes_of(s.data["region"])
    commune = _pick(msg, communes) or next((c for c in communes if c.lower() == msg.lower()), None)
    if commune is None:
        return [t(lang, "bot_invalid"), t(lang, "bot_ask_commune", communes=_numbered(communes))]
    s.data["commune"] = commune
    return _ask_recipient(db, s)


def _recipients(db: Session, s: BotSession) -> list[tuple[str, int | None]]:
    """Choix proposés : (libellé, id du relais ou None pour l'action sociale)."""
    lang = s.lang
    choices: list[tuple[str, int | None]] = [(t(lang, "bot_recipient_action_sociale"), None)]
    for a in public_relais(db, s.data["region"], s.data["commune"]):
        where = f", {a.commune}" if a.commune else ""
        choices.append((t(lang, "bot_recipient_relais", name=a.name, where=where), a.id))
    return choices


def _ask_recipient(db: Session, s: BotSession) -> list[str]:
    choices = _recipients(db, s)
    if len(choices) == 1:
        # Pas de relais dans cette commune : inutile de poser la question.
        s.data["assignee_id"] = None
        s.state = "REPORT_DESC"
        return [t(s.lang, "bot_ask_description")]
    s.state = "REPORT_TO"
    return [t(s.lang, "bot_ask_recipient", choices=_numbered([label for label, _ in choices]))]


def _report_to(db: Session, channel: Channel, s: BotSession, msg: str) -> list[str]:
    lang = s.lang
    choices = _recipients(db, s)
    picked = _pick(msg, choices)
    if picked is None:
        return [t(lang, "bot_invalid"), t(lang, "bot_ask_recipient", choices=_numbered([c for c, _ in choices]))]
    s.data["assignee_id"] = picked[1]
    s.state = "REPORT_DESC"
    return [t(lang, "bot_ask_description")]


def _report_desc(db: Session, channel: Channel, s: BotSession, msg: str) -> list[str]:
    lang = s.lang
    rtype: ReportType = s.data["type"]
    sub: ReportSubtype = s.data["subtype"]
    region: str = s.data["region"]
    assignee_id = s.data.get("assignee_id")
    try:
        report = create_report(
            db,
            type_=rtype.value,
            subtype=sub.value,
            region=region,
            commune=s.data.get("commune"),
            description=msg,
            assignee_id=assignee_id,
            target_role=None if assignee_id else ActorRole.ACTION_SOCIALE.value,
            channel=channel,
            lang=lang,
        )
    except ValidationError as e:
        return [t(lang, e.key, **e.params), t(lang, "bot_ask_description")]
    s.state, s.data = "MENU", {}
    resources = find_resources(db, type_=rtype, subtype=sub, region=region)
    # Le code part dans son propre message : sur WhatsApp il reste isolable,
    # donc copiable et transférable sans le reste de la conversation.
    out = [t(lang, "bot_report_done"), t(lang, "bot_report_code", code=format_code(report.id))]
    out += _format_resources(lang, resources, intro=t(lang, "bot_resources_intro"))
    # Le rappel d'effacement clôt le dernier message : c'est le moment le plus
    # sensible, et c'est ce qui reste sous les yeux de la personne.
    out[-1] += t(lang, "bot_back_hint") + t(lang, "bot_wipe_hint")
    return out


# --------------------------------------------------------------------------- suivi / ressources


def _track_code(db: Session, channel: Channel, s: BotSession, msg: str) -> list[str]:
    lang = s.lang
    # Même limite que sur le web, indexée sur le numéro haché de la session.
    if not ratelimit.allow(s.key):
        s.state, s.data = "MENU", {}
        return [t(lang, "bot_track_too_many"), t(lang, "bot_menu")]

    report = find_report(db, msg)
    if report is None:
        return [t(lang, "bot_track_not_found"), t(lang, "bot_ask_code")]

    s.state, s.data = "MENU", {}
    # Ni type, ni région, ni description : un code intercepté n'apprend rien
    # sur l'incident lui-même.
    text = t(
        lang,
        "bot_track_result",
        code=format_code(report.id),
        status=t(lang, "status_" + report.status.value),
        help=t(lang, "status_" + report.status.value + "_help"),
        sent=report.created_at.strftime("%d/%m/%Y"),
    )
    if report.partner_note:
        # Le mot du partenaire peut être parlant pour qui lit par-dessus l'épaule.
        text += t(lang, "bot_track_note", note=translate_cache.localized(report.partner_note, lang))
        return _chunk(text + t(lang, "bot_back_hint") + t(lang, "bot_wipe_hint"))
    return _chunk(text + t(lang, "bot_back_hint"))


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
    "REPORT_SUBTYPE": _report_subtype,
    "REPORT_REGION": _report_region,
    "REPORT_COMMUNE": _report_commune,
    "REPORT_TO": _report_to,
    "REPORT_DESC": _report_desc,
    "RES_REGION": _res_region,
    "TRACK_CODE": _track_code,
}
