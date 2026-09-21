"""API JSON : application mobile, bots WhatsApp/SMS et toute autre interface.

Deux faces :
- publique (aucun compte) : référentiels, dépôt d'un signalement, suivi par code ;
- acteurs (`Authorization: Bearer <jeton>`) : connexion, boîte de réception,
  transmission, prise en charge. C'est ce qu'utilisent le relais et le point
  focal depuis l'application mobile.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import ratelimit
from ..api_ai import service as ai
from ..api_ai import transcribe as speech
from ..api_ai import translate_cache
from ..auth import authenticate, current_actor, issue_token, optional_actor, revoke_token
from ..config import settings
from ..db import get_db
from ..i18n import normalize_lang, t
from ..models import (
    CASE_HANDLERS,
    FORWARD_TARGETS,
    MUST_SUMMARIZE,
    SUBTYPES,
    Actor,
    ActorRole,
    Channel,
    Report,
    ReportStatus,
    ReportSubtype,
    ReportType,
    ResourceCategory,
    format_code,
)
from ..seed import load_regions, region_names
from ..services import (
    MAX_DESCRIPTION,
    Forbidden,
    ValidationError,
    create_report,
    decrypt_texts,
    find_report,
    find_resources,
    forward,
    forward_targets,
    get_visible_report,
    inbox,
    public_relais,
    set_status,
    update_summary,
)

router = APIRouter(prefix="/api", tags=["api"])


# --------------------------------------------------------------------------- schémas


class ReportIn(BaseModel):
    type: ReportType | None = None
    # Le sous-type suffit : le type s'en déduit. Les deux ensemble sont vérifiés.
    subtype: ReportSubtype | None = None
    region: str
    commune: str | None = None
    description: str = Field(max_length=MAX_DESCRIPTION)
    # Destinataire : un relais (id venant de GET /api/relais) OU un rôle
    # (« ACTION_SOCIALE » pour écrire directement à l'action sociale). Sans
    # rien, le rôle par défaut du type.
    assignee_id: int | None = None
    target_role: ActorRole | None = None
    channel: Channel = Channel.MOBILE
    lang: str = "fr"
    # Saisie par un relais / point focal (jeton) : sa reformulation concise
    # du récit, obligatoire pour ces rôles.
    summary: str | None = Field(default=None, max_length=MAX_DESCRIPTION)


class ReportOut(BaseModel):
    ok: bool = True
    # Code de suivi, à transmettre à la personne : c'est le seul lien qu'elle
    # gardera avec son signalement. Rien n'est conservé de son côté par ailleurs.
    code: str


class TrackOut(BaseModel):
    """Ce qu'on accepte de révéler à qui présente un code.

    Ni type, ni région, ni description : un code intercepté n'apprend rien sur
    l'incident.
    """

    code: str
    status: ReportStatus
    created_at: datetime
    status_at: datetime | None
    partner_note: str | None


class ResourceOut(BaseModel):
    name: str
    category: ResourceCategory
    phone: str | None
    region: str
    city: str | None
    hours: str | None
    languages: list[str]
    verified: bool
    notes: str | None


class RelaisOut(BaseModel):
    id: int
    name: str
    organisation: str | None
    commune: str | None
    phone: str | None


class LoginIn(BaseModel):
    username: str
    password: str


class ActorOut(BaseModel):
    id: int
    username: str
    name: str
    role: ActorRole
    organisation: str | None
    region: str
    commune: str | None
    # Rôles vers lesquels cet acteur peut transmettre.
    can_forward_to: list[ActorRole]
    # Seuls l'action sociale et les gestionnaires de cas changent le statut.
    can_set_status: bool
    # Relais et point focal : la reformulation est obligatoire pour transmettre.
    must_summarize: bool
    # L'assistant de reformulation est-il disponible sur ce serveur ?
    ai_available: bool


class LoginOut(BaseModel):
    token: str
    actor: ActorOut


class EventOut(BaseModel):
    kind: str
    at: datetime
    by: str | None
    by_id: int | None
    to: str | None
    to_role: ActorRole | None
    status: ReportStatus | None
    note: str | None


class InboxItem(BaseModel):
    code: str
    id: str
    type: ReportType
    subtype: ReportSubtype | None
    region: str
    commune: str | None
    channel: Channel
    lang: str
    created_at: datetime
    status: ReportStatus
    status_at: datetime | None
    partner_note: str | None
    assignee: str | None
    target_role: ActorRole | None
    description: str | None
    summary: str | None
    summary_by: str | None
    summary_at: datetime | None
    # True : ancien format de chiffrement, illisible tant que scripts/reencrypt.py n'a pas tourné.
    legacy: bool


class InboxDetail(InboxItem):
    events: list[EventOut]


class ForwardIn(BaseModel):
    to_actor_id: int | None = None
    to_role: ActorRole | None = None
    summary: str | None = Field(default=None, max_length=MAX_DESCRIPTION)
    note: str | None = Field(default=None, max_length=280)


class SummaryIn(BaseModel):
    summary: str = Field(max_length=MAX_DESCRIPTION)


class ReformulateIn(BaseModel):
    """Récit pas encore enregistré (saisie d'un cas reçu en personne)."""

    text: str = Field(max_length=MAX_DESCRIPTION)
    region: str | None = None
    commune: str | None = None
    subtype: ReportSubtype | None = None


class SuggestionOut(BaseModel):
    summary: str
    urgency: str
    anonymity_risks: list[str]
    missing: list[str]


class StatusIn(BaseModel):
    status: ReportStatus
    note: str | None = Field(default=None, max_length=280)


# --------------------------------------------------------------------------- public


@router.get("/regions")
def regions():
    return load_regions()


@router.get("/features")
def features():
    """Ce que ce serveur sait faire en plus du socle : l'app n'affiche que les boutons utiles."""
    return {"speech": speech.enabled()}


@router.post("/transcribe")
async def transcribe_audio(
    request: Request,
    audio: UploadFile = File(...),
    lang: str = Form("fr"),
):
    """Transcrit un enregistrement vocal pour préremplir la description.

    Public (la personne qui signale n'a pas de compte), donc limité : dix
    enregistrements par quart d'heure et par client, taille plafonnée. L'audio
    ne fait que passer : ni écrit sur disque, ni journalisé.
    """
    if not speech.enabled():
        raise HTTPException(status_code=503, detail="speech_unavailable")
    if not ratelimit.allow("speech:" + (request.client.host if request.client else "")):
        raise HTTPException(status_code=429, detail="too_many_attempts")
    data = await audio.read(settings.speech_max_bytes + 1)
    # Taille et type seulement : jamais le contenu.
    speech.log.info("transcribe: %s octets, %s, lang=%s", len(data), audio.content_type, lang)
    if len(data) > settings.speech_max_bytes:
        raise HTTPException(status_code=413, detail="audio_too_large")
    if len(data) < 1000:
        raise HTTPException(status_code=422, detail="audio_empty")
    try:
        text = await speech.transcribe(data, audio.filename or "audio.m4a", audio.content_type or "audio/mp4", normalize_lang(lang))
    except speech.SpeechUnavailable:
        raise HTTPException(status_code=503, detail="speech_unavailable") from None
    return {"text": text}


@router.get("/types")
def types(lang: str = "fr"):
    """Types et sous-types, avec leurs libellés dans la langue demandée."""
    lang = normalize_lang(lang)
    return [
        {
            "code": ty.value,
            "label": t(lang, "type_" + ty.value),
            "subtypes": [{"code": s.value, "label": t(lang, "subtype_" + s.value)} for s in subs],
        }
        for ty, subs in SUBTYPES.items()
    ]


@router.get("/relais", response_model=list[RelaisOut])
def relais(region: str, commune: str | None = None, db: Session = Depends(get_db)):
    """Relais communautaires que l'usager peut choisir comme personne ressource."""
    if region not in region_names():
        raise HTTPException(status_code=422, detail="unknown_region")
    return [
        RelaisOut(id=a.id, name=a.name, organisation=a.organisation, commune=a.commune, phone=a.phone)
        for a in public_relais(db, region, commune)
    ]


@router.post("/reports", response_model=ReportOut, status_code=201)
def post_report(
    payload: ReportIn,
    actor: Actor | None = Depends(optional_actor),
    db: Session = Depends(get_db),
):
    """Dépose un signalement. Avec un jeton acteur, il est saisi « au nom de » :
    c'est le cas d'un relais qui enregistre la plainte d'une personne venue le voir."""
    try:
        report = create_report(
            db,
            type_=payload.type.value if payload.type else "",
            subtype=payload.subtype.value if payload.subtype else None,
            region=payload.region,
            commune=payload.commune,
            description=payload.description,
            assignee_id=payload.assignee_id,
            target_role=payload.target_role.value if payload.target_role else None,
            channel=payload.channel,
            lang=normalize_lang(payload.lang),
            created_by=actor,
            summary=payload.summary,
        )
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.key) from None
    return ReportOut(code=format_code(report.id))


@router.get("/reports/{code}", response_model=TrackOut)
def track_report(code: str, request: Request, lang: str = settings.default_lang, db: Session = Depends(get_db)):
    """Suivi d'un signalement par son code. `lang` : langue de la note du partenaire."""
    if not ratelimit.allow(request.client.host if request.client else None):
        raise HTTPException(status_code=429, detail="too_many_attempts")
    report = find_report(db, code)
    if report is None:
        raise HTTPException(status_code=404, detail="not_found")
    return TrackOut(
        code=format_code(report.id),
        status=report.status,
        created_at=report.created_at,
        status_at=report.status_at,
        partner_note=translate_cache.localized(report.partner_note, normalize_lang(lang)),
    )


@router.get("/resources", response_model=list[ResourceOut])
def get_resources(
    type: ReportType | None = None,
    subtype: ReportSubtype | None = None,
    region: str | None = None,
    category: ResourceCategory | None = None,
    lang: str = settings.default_lang,
    db: Session = Depends(get_db),
):
    """`lang` : horaires et notes traduits si la traduction est prête (sinon en français)."""
    if region is not None and region not in region_names():
        raise HTTPException(status_code=422, detail="unknown_region")
    lang = normalize_lang(lang)
    # L'API sert des partenaires qui paginent eux-mêmes : on renvoie tout.
    rows = find_resources(db, type_=type, subtype=subtype, region=region, category=category, limit_per_category=None)
    return [
        ResourceOut(
            name=r.name,
            category=r.category,
            phone=r.phone,
            region=r.region,
            city=r.city,
            hours=translate_cache.localized(r.hours, lang),
            languages=r.languages.split(","),
            verified=r.verified,
            notes=translate_cache.localized(r.notes, lang),
        )
        for r in rows
    ]


# --------------------------------------------------------------------------- acteurs


def _actor_out(a: Actor) -> ActorOut:
    return ActorOut(
        id=a.id,
        username=a.username,
        name=a.name,
        role=a.role,
        organisation=a.organisation,
        region=a.region,
        commune=a.commune,
        can_forward_to=FORWARD_TARGETS[a.role],
        can_set_status=a.role in CASE_HANDLERS,
        must_summarize=a.role in MUST_SUMMARIZE,
        ai_available=ai.enabled(),
    )


def _item(report: Report) -> InboxItem:
    texts = decrypt_texts(report)
    return InboxItem(
        code=format_code(report.id),
        id=report.id,
        type=report.type,
        subtype=report.subtype,
        region=report.region,
        commune=report.commune,
        channel=report.channel,
        lang=report.lang,
        created_at=report.created_at,
        status=report.status,
        status_at=report.status_at,
        partner_note=report.partner_note,
        assignee=report.assignee.name if report.assignee else None,
        target_role=report.target_role,
        description=texts["description"],
        summary=texts["summary"],
        summary_by=report.summary_author.name if report.summary_author else None,
        summary_at=report.summary_at,
        legacy=texts["legacy"],
    )


@router.post("/auth/login", response_model=LoginOut)
def login(payload: LoginIn, request: Request, db: Session = Depends(get_db)):
    # Même limite que le suivi par code : dix essais par quart d'heure et par client.
    if not ratelimit.allow(request.client.host if request.client else None):
        raise HTTPException(status_code=429, detail="too_many_attempts")
    actor = authenticate(db, payload.username, payload.password)
    if actor is None:
        raise HTTPException(status_code=401, detail="bad_credentials")
    token = issue_token(db, actor, ttl=settings.actor_session_ttl_mobile)
    return LoginOut(token=token, actor=_actor_out(actor))


@router.post("/auth/logout", status_code=204)
def logout(request: Request, actor: Actor = Depends(current_actor), db: Session = Depends(get_db)):
    auth = request.headers.get("authorization", "")
    revoke_token(db, auth[7:].strip() if auth.lower().startswith("bearer ") else None)
    return None


@router.get("/me", response_model=ActorOut)
def me(actor: Actor = Depends(current_actor)):
    return _actor_out(actor)


@router.get("/targets", response_model=list[RelaisOut])
def targets(actor: Actor = Depends(current_actor), db: Session = Depends(get_db)):
    """Personnes à qui cet acteur peut transmettre un signalement."""
    return [
        RelaisOut(id=a.id, name=f"{a.name} ({a.role.value})", organisation=a.organisation, commune=a.commune, phone=a.phone)
        for a in forward_targets(db, actor)
    ]


@router.get("/inbox", response_model=list[InboxItem])
def get_inbox(
    status: ReportStatus | None = None,
    actor: Actor = Depends(current_actor),
    db: Session = Depends(get_db),
):
    return [_item(r) for r in inbox(db, actor, status=status)]


@router.get("/inbox/{report_id}", response_model=InboxDetail)
def get_inbox_item(report_id: str, actor: Actor = Depends(current_actor), db: Session = Depends(get_db)):
    try:
        report = get_visible_report(db, actor, report_id)
    except Forbidden:
        raise HTTPException(status_code=404, detail="not_found") from None
    item = _item(report)
    events = [
        EventOut(
            kind=e.kind.value,
            at=e.created_at,
            by=e.actor.name if e.actor else None,
            by_id=e.actor_id,
            to=e.to_actor.name if e.to_actor else None,
            to_role=e.to_role,
            status=e.status,
            note=e.note,
        )
        for e in report.events
    ]
    return InboxDetail(**item.model_dump(), events=events)


@router.post("/inbox/{report_id}/forward", response_model=InboxItem)
def post_forward(
    report_id: str,
    payload: ForwardIn,
    actor: Actor = Depends(current_actor),
    db: Session = Depends(get_db),
):
    try:
        report = get_visible_report(db, actor, report_id)
        report = forward(
            db,
            actor,
            report,
            to_actor_id=payload.to_actor_id,
            to_role=payload.to_role.value if payload.to_role else None,
            summary=payload.summary,
            note=payload.note,
        )
    except Forbidden:
        raise HTTPException(status_code=404, detail="not_found") from None
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.key) from None
    return _item(report)


def _suggest(text: str, region: str | None, commune: str | None, subtype: ReportSubtype | None, lang: str) -> SuggestionOut:
    try:
        s = ai.suggest_summary(
            text, region=region or "", commune=commune or "", subtype_label=t(lang, "subtype_" + subtype.value) if subtype else ""
        )
    except ai.AiUnavailable:
        raise HTTPException(status_code=503, detail="ai_unavailable") from None
    return SuggestionOut(summary=s.summary, urgency=s.urgency, anonymity_risks=s.anonymity_risks, missing=s.missing)


@router.post("/ai/reformulate", response_model=SuggestionOut)
def reformulate(payload: ReformulateIn, actor: Actor = Depends(current_actor)):
    """Propose une reformulation concise d'un récit que le relais est en train de saisir."""
    return _suggest(payload.text, payload.region, payload.commune, payload.subtype, "fr")


@router.post("/inbox/{report_id}/suggest-summary", response_model=SuggestionOut)
def suggest_summary(report_id: str, actor: Actor = Depends(current_actor), db: Session = Depends(get_db)):
    """Propose une reformulation concise du récit d'un signalement reçu. Rien n'est enregistré."""
    try:
        report = get_visible_report(db, actor, report_id)
    except Forbidden:
        raise HTTPException(status_code=404, detail="not_found") from None
    text = decrypt_texts(report)["description"]
    if not text:
        raise HTTPException(status_code=422, detail="unreadable")
    return _suggest(text, report.region, report.commune, report.subtype, "fr")


@router.post("/inbox/{report_id}/summary", response_model=InboxItem)
def post_summary(
    report_id: str,
    payload: SummaryIn,
    actor: Actor = Depends(current_actor),
    db: Session = Depends(get_db),
):
    """Corrige la reformulation sans retransmettre : le destinataire ne change pas."""
    try:
        report = get_visible_report(db, actor, report_id)
        report = update_summary(db, actor, report, payload.summary)
    except Forbidden:
        raise HTTPException(status_code=404, detail="not_found") from None
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.key) from None
    return _item(report)


@router.post("/inbox/{report_id}/status", response_model=InboxItem)
def post_status(
    report_id: str,
    payload: StatusIn,
    actor: Actor = Depends(current_actor),
    db: Session = Depends(get_db),
):
    try:
        report = get_visible_report(db, actor, report_id)
        report = set_status(db, report, status=payload.status, note=payload.note, actor=actor)
    except Forbidden:
        raise HTTPException(status_code=403, detail="forbidden") from None
    return _item(report)
