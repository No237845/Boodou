"""Logique métier partagée par le web, l'API, l'espace acteurs et les bots WhatsApp/SMS."""

from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from . import crypto
from .models import (
    CASE_HANDLERS,
    FORWARD_TARGETS,
    MUST_SUMMARIZE,
    PARTNER_NOTE_MAX,
    PUBLIC_TARGET_ROLES,
    SUBTYPES,
    Actor,
    ActorRole,
    Channel,
    EventKind,
    Report,
    ReportEvent,
    ReportStatus,
    ReportSubtype,
    ReportType,
    Resource,
    ResourceCategory,
    normalize_code,
    type_of,
)
from .seed import communes_of, region_names

MAX_DESCRIPTION = 2000

# Ordre d'affichage des catégories dans les listes de ressources.
CATEGORY_ORDER = [
    ResourceCategory.URGENCE,
    ResourceCategory.SANTE,
    ResourceCategory.JUSTICE,
    ResourceCategory.ONG,
]


class ValidationError(ValueError):
    def __init__(self, key: str, **params: object):
        super().__init__(key)
        self.key = key
        self.params = params


class Forbidden(Exception):
    """L'acteur n'a pas le droit de faire ça sur ce signalement."""


# --------------------------------------------------------------------------- signalement


def _now() -> datetime:
    return datetime.now(timezone.utc)


def parse_subtype(type_: str, subtype: str | None) -> tuple[ReportType, ReportSubtype | None]:
    """Valide le couple type / sous-type. Un sous-type seul suffit à déduire le type."""
    sub = None
    if subtype:
        try:
            sub = ReportSubtype(subtype)
        except ValueError:
            raise ValidationError("report_error_required") from None
    if not type_ and sub is not None:
        return type_of(sub), sub
    try:
        rtype = ReportType(type_)
    except ValueError:
        raise ValidationError("report_error_required") from None
    if sub is not None and sub not in SUBTYPES[rtype]:
        raise ValidationError("report_error_required")
    return rtype, sub


def default_target_role(rtype: ReportType) -> ActorRole:
    """À qui va un signalement quand l'usager n'a choisi personne.

    VBG : au point focal, dont c'est justement le travail de relire et
    d'orienter. Sécurité : à l'action sociale, l'acteur étatique de la zone.
    """
    return ActorRole.POINT_FOCAL if rtype == ReportType.GBV else ActorRole.ACTION_SOCIALE


def create_report(
    db: Session,
    *,
    type_: str,
    region: str,
    description: str,
    subtype: str | None = None,
    commune: str | None = None,
    assignee_id: int | None = None,
    target_role: str | None = None,
    channel: Channel = Channel.WEB,
    lang: str = "fr",
    created_by: Actor | None = None,
    summary: str | None = None,
) -> Report:
    """Enregistre un signalement et le met dans la boîte du bon destinataire.

    Destinataire : soit une personne précise (`assignee_id`), soit un rôle
    (`target_role`), soit personne — et alors le rôle par défaut du type.

    - Usager anonyme : un relais de sa commune, ou l'action sociale.
    - Acteur connecté (`created_by`, un relais qui saisit un cas reçu en
      personne) : n'importe qui vers qui il a le droit de transmettre. Le
      signalement part alors *transmis* du premier coup : le relais a choisi
      son destinataire à la saisie, on ne le lui redemande pas.
    """
    description = (description or "").strip()
    if (not type_ and not subtype) or not region or not description:
        raise ValidationError("report_error_required")
    if len(description) > MAX_DESCRIPTION:
        raise ValidationError("report_error_too_long", max=MAX_DESCRIPTION)
    rtype, sub = parse_subtype(type_, subtype)
    if region not in region_names():
        raise ValidationError("report_error_required")
    commune = (commune or "").strip()[:64] or None
    if commune and commune not in communes_of(region):
        raise ValidationError("report_error_commune")

    assignee = None
    role = None
    if assignee_id is not None:
        assignee = db.get(Actor, assignee_id)
        if assignee is None or not assignee.active:
            raise ValidationError("report_error_recipient")
        if created_by is not None:
            # Même règle que pour transmettre : un rôle autorisé, dans sa région.
            if assignee.role not in FORWARD_TARGETS[created_by.role] or assignee.region != created_by.region:
                raise ValidationError("report_error_recipient")
        # Seul un relais actif de la commune du signalement peut être choisi
        # par l'usager : la liste qu'on lui montre est construite pareil.
        elif (
            assignee.role != ActorRole.RELAIS
            or assignee.region != region
            or (commune and assignee.commune and assignee.commune != commune)
        ):
            raise ValidationError("report_error_recipient")
        role = assignee.role
    elif target_role:
        try:
            role = ActorRole(target_role)
        except ValueError:
            raise ValidationError("report_error_recipient") from None
        # Un acteur connecté peut viser n'importe quel rôle qu'il a le droit de
        # transmettre ; l'usager anonyme, seulement l'action sociale.
        allowed = FORWARD_TARGETS[created_by.role] if created_by else PUBLIC_TARGET_ROLES
        if role not in allowed:
            raise ValidationError("report_error_recipient")
    else:
        role = default_target_role(rtype)

    # Saisi par un relais / point focal : il l'a déjà relayé, en une fois —
    # et il a reformulé, comme pour toute transmission.
    relayed = created_by is not None and created_by.role in MUST_SUMMARIZE
    summary = (summary or "").strip()
    if len(summary) > MAX_DESCRIPTION:
        raise ValidationError("report_error_too_long", max=MAX_DESCRIPTION)
    if relayed and not summary:
        raise ValidationError("report_error_summary_required")
    report = Report(
        type=rtype,
        subtype=sub,
        region=region,
        commune=commune,
        ciphertext=crypto.encrypt(description),
        channel=channel,
        lang=lang,
        created_by=created_by.id if created_by else None,
        assignee_id=assignee.id if assignee else None,
        target_role=role,
        status=ReportStatus.TRANSMIS if relayed else ReportStatus.RECU,
        status_at=_now() if relayed else None,
        summary_ciphertext=crypto.encrypt(summary) if summary else None,
        summary_by=created_by.id if summary else None,
        summary_at=_now() if summary else None,
    )
    db.add(report)
    db.flush()
    db.add(
        ReportEvent(
            report_id=report.id,
            kind=EventKind.CREATED,
            actor_id=created_by.id if created_by else None,
            to_actor_id=report.assignee_id,
            to_role=role,
        )
    )
    if relayed:
        db.add(
            ReportEvent(
                report_id=report.id, kind=EventKind.FORWARDED, actor_id=created_by.id, to_actor_id=report.assignee_id, to_role=role
            )
        )
    db.commit()
    return report


# --------------------------------------------------------------------------- suivi public


def find_report(db: Session, code: str) -> Report | None:
    """Retrouve un signalement à partir d'un code de suivi saisi à la main."""
    code = normalize_code(code)
    if not code:
        return None
    return db.get(Report, code)


# --------------------------------------------------------------------------- acteurs


def visible_reports_stmt(actor: Actor):
    """Les signalements qu'un acteur a le droit de voir.

    - ceux qui lui sont assignés nommément ;
    - ceux adressés à son rôle dans sa zone, sans personne nommée ;
    - ceux sur lesquels il est déjà intervenu (saisis, transmis, pris en
      charge) : un relais qui a passé un cas à l'action sociale doit pouvoir
      dire à la personne où il en est ;
    - pour le point focal VBG : tous les cas VBG de sa région tant qu'ils ne
      sont pas pris en charge — c'est lui qui relit et oriente.
    """
    mine = Report.assignee_id == actor.id
    for_my_role = (Report.assignee_id.is_(None)) & (Report.target_role == actor.role) & (Report.region == actor.region)
    if actor.commune:
        for_my_role = for_my_role & or_(Report.commune.is_(None), Report.commune == actor.commune)
    touched = Report.id.in_(select(ReportEvent.report_id).where(ReportEvent.actor_id == actor.id))
    conds = [mine, for_my_role, touched]
    if actor.role == ActorRole.POINT_FOCAL:
        conds.append(
            (Report.type == ReportType.GBV)
            & (Report.region == actor.region)
            & Report.status.in_([ReportStatus.RECU, ReportStatus.TRANSMIS])
        )
    return select(Report).where(or_(*conds)).order_by(Report.created_at.desc())


def inbox(db: Session, actor: Actor, *, status: ReportStatus | None = None, limit: int = 500) -> list[Report]:
    stmt = visible_reports_stmt(actor)
    if status is not None:
        stmt = stmt.where(Report.status == status)
    return list(db.execute(stmt.limit(limit)).scalars().all())


def get_visible_report(db: Session, actor: Actor, report_id: str) -> Report:
    report = db.execute(visible_reports_stmt(actor).where(Report.id == normalize_code(report_id))).scalar_one_or_none()
    if report is None:
        raise Forbidden()
    return report


def forward_targets(db: Session, actor: Actor) -> list[Actor]:
    """Personnes à qui cet acteur peut transmettre : rôles autorisés, même région."""
    roles = FORWARD_TARGETS[actor.role]
    stmt = (
        select(Actor)
        .where(Actor.active.is_(True), Actor.role.in_(roles), Actor.region == actor.region, Actor.id != actor.id)
        .order_by(Actor.role, Actor.name)
    )
    return list(db.execute(stmt).scalars().all())


def forward(
    db: Session,
    actor: Actor,
    report: Report,
    *,
    to_actor_id: int | None = None,
    to_role: str | None = None,
    summary: str | None = None,
    note: str | None = None,
) -> Report:
    """Transmet un signalement à une personne ou à un rôle, avec éventuelle reformulation."""
    target = None
    role = None
    if to_actor_id is not None:
        target = db.get(Actor, to_actor_id)
        if (
            target is None
            or not target.active
            or target.role not in FORWARD_TARGETS[actor.role]
            or target.region != actor.region
        ):
            raise ValidationError("report_error_recipient")
        role = target.role
    else:
        try:
            role = ActorRole(to_role or "")
        except ValueError:
            raise ValidationError("report_error_recipient") from None
        if role not in FORWARD_TARGETS[actor.role]:
            raise ValidationError("report_error_recipient")

    summary = (summary or "").strip()
    if len(summary) > MAX_DESCRIPTION:
        raise ValidationError("report_error_too_long", max=MAX_DESCRIPTION)
    # Un relais ou un point focal ne transmet jamais un récit brut : c'est sa
    # reformulation qui permet à l'action sociale de prendre en charge vite.
    if not summary and actor.role in MUST_SUMMARIZE:
        raise ValidationError("report_error_summary_required")
    if summary:
        report.summary_ciphertext = crypto.encrypt(summary)
        report.summary_by = actor.id
        report.summary_at = _now()

    report.assignee_id = target.id if target else None
    report.target_role = role
    # Transmettre ne fait jamais reculer un dossier déjà pris en charge :
    # un gestionnaire qui passe le relais à l'action sociale ne remet pas la
    # personne « en attente » sur sa page de suivi.
    if report.status == ReportStatus.RECU:
        report.status = ReportStatus.TRANSMIS
        report.status_at = _now()
    db.add(
        ReportEvent(
            report_id=report.id,
            kind=EventKind.FORWARDED,
            actor_id=actor.id,
            to_actor_id=report.assignee_id,
            to_role=role,
            note=(note or "").strip()[:PARTNER_NOTE_MAX] or None,
        )
    )
    db.commit()
    return report


def update_summary(db: Session, actor: Actor, report: Report, summary: str) -> Report:
    """Remplace la reformulation, sans toucher au destinataire ni au statut.

    Sert au relais qui a déjà transmis et veut préciser sa reformulation :
    il ne rechoisit pas à qui, il corrige seulement son texte.
    """
    summary = (summary or "").strip()
    if not summary:
        raise ValidationError("report_error_summary_required")
    if len(summary) > MAX_DESCRIPTION:
        raise ValidationError("report_error_too_long", max=MAX_DESCRIPTION)
    report.summary_ciphertext = crypto.encrypt(summary)
    report.summary_by = actor.id
    report.summary_at = _now()
    db.commit()
    return report


def set_status(
    db: Session,
    report: Report,
    *,
    status: ReportStatus,
    note: str | None = None,
    actor: Actor | None = None,
) -> Report:
    """Fait avancer un signalement. Réservé aux acteurs de prise en charge (et à l'admin)."""
    if actor is not None and actor.role not in CASE_HANDLERS:
        raise Forbidden()
    report.status = status
    if note is not None:
        report.partner_note = note.strip()[:PARTNER_NOTE_MAX] or None
    report.status_at = _now()
    # Prendre en charge, c'est aussi dire « c'est moi qui m'en occupe ».
    if actor is not None and status in (ReportStatus.PRIS_EN_CHARGE, ReportStatus.REGLE) and report.assignee_id != actor.id:
        report.assignee_id = actor.id
        report.target_role = actor.role
    db.add(
        ReportEvent(
            report_id=report.id,
            kind=EventKind.STATUS,
            actor_id=actor.id if actor else None,
            status=status,
        )
    )
    db.commit()
    return report


def public_relais(db: Session, region: str, commune: str | None = None) -> list[Actor]:
    """Relais communautaires qu'un usager peut choisir comme personne ressource."""
    stmt = select(Actor).where(Actor.active.is_(True), Actor.role == ActorRole.RELAIS, Actor.region == region)
    if commune:
        stmt = stmt.where(or_(Actor.commune == commune, Actor.commune.is_(None)))
    return list(db.execute(stmt.order_by(Actor.commune, Actor.name)).scalars().all())


def decrypt_texts(report: Report) -> dict:
    """Récit et reformulation en clair. L'appelant a déjà vérifié le droit de voir."""
    return {
        "description": crypto.try_decrypt(report.ciphertext),
        "summary": crypto.try_decrypt(report.summary_ciphertext),
        "legacy": crypto.is_legacy(report.ciphertext),
    }


# --------------------------------------------------------------------------- ressources

# Nombre de fiches affichées par catégorie. Une personne qui vient de signaler une
# agression ne lit pas quarante cartes : elle appelle la première qui correspond.
# Le tri ci-dessous garantit que les meilleures sont en tête, le plafond coupe la queue.
MAX_PER_CATEGORY = 5


def find_resources(
    db: Session,
    *,
    type_: ReportType | None = None,
    subtype: ReportSubtype | None = None,
    region: str | None = None,
    category: ResourceCategory | None = None,
    limit_per_category: int | None = MAX_PER_CATEGORY,
) -> list[Resource]:
    stmt = select(Resource)
    if category is not None:
        stmt = stmt.where(Resource.category == category)
    rows = db.execute(stmt).scalars().all()
    rows = [r for r in rows if r.matches(type_, region, subtype)]
    # Urgences d'abord, puis vérifiés avant non vérifiés, puis appelables avant
    # ceux dont on ignore le numéro, puis local avant national. Une fiche sans
    # téléphone reste utile (ses `notes` disent où se rendre) mais en situation
    # d'urgence un numéro qu'on peut composer passe devant.
    rows.sort(
        key=lambda r: (
            CATEGORY_ORDER.index(r.category),
            not r.verified,
            r.phone is None,
            r.region == "*",
            r.name,
        )
    )
    if limit_per_category is not None:
        kept: list[Resource] = []
        seen: dict[ResourceCategory, int] = {}
        for r in rows:
            n = seen.get(r.category, 0)
            if n < limit_per_category:
                kept.append(r)
                seen[r.category] = n + 1
        rows = kept
    return rows


def group_by_category(resources: list[Resource]) -> list[tuple[ResourceCategory, list[Resource]]]:
    groups: dict[ResourceCategory, list[Resource]] = {}
    for r in resources:
        groups.setdefault(r.category, []).append(r)
    return [(c, groups[c]) for c in CATEGORY_ORDER if c in groups]
