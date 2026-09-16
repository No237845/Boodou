"""Logique métier partagée par le web, l'API et (plus tard) les bots WhatsApp/SMS."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import crypto
from .models import (
    PARTNER_NOTE_MAX,
    Channel,
    Report,
    ReportStatus,
    ReportType,
    Resource,
    ResourceCategory,
    normalize_code,
)
from .seed import region_names

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


def create_report(
    db: Session,
    *,
    type_: str,
    region: str,
    description: str,
    commune: str | None = None,
    channel: Channel = Channel.WEB,
    lang: str = "fr",
) -> Report:
    description = (description or "").strip()
    if not type_ or not region or not description:
        raise ValidationError("report_error_required")
    if len(description) > MAX_DESCRIPTION:
        raise ValidationError("report_error_too_long", max=MAX_DESCRIPTION)
    try:
        rtype = ReportType(type_)
    except ValueError:
        raise ValidationError("report_error_required") from None
    if region not in region_names():
        raise ValidationError("report_error_required")

    report = Report(
        type=rtype,
        region=region,
        commune=(commune or "").strip()[:64] or None,
        ciphertext=crypto.encrypt(description),
        channel=channel,
        lang=lang,
    )
    db.add(report)
    db.commit()
    return report


# --------------------------------------------------------------------------- suivi


def find_report(db: Session, code: str) -> Report | None:
    """Retrouve un signalement à partir d'un code de suivi saisi à la main."""
    code = normalize_code(code)
    if not code:
        return None
    return db.get(Report, code)


def set_status(
    db: Session,
    report: Report,
    *,
    status: ReportStatus,
    note: str | None = None,
) -> Report:
    """Fait avancer un signalement. Appelé par l'espace partenaire uniquement."""
    report.status = status
    if note is not None:
        report.partner_note = note.strip()[:PARTNER_NOTE_MAX] or None
    report.status_at = datetime.now(timezone.utc)
    db.commit()
    return report


def find_resources(
    db: Session,
    *,
    type_: ReportType | None = None,
    region: str | None = None,
    category: ResourceCategory | None = None,
) -> list[Resource]:
    stmt = select(Resource)
    if category is not None:
        stmt = stmt.where(Resource.category == category)
    rows = db.execute(stmt).scalars().all()
    rows = [r for r in rows if r.matches(type_, region)]
    # Urgences d'abord, puis vérifiés avant non vérifiés, puis local avant national.
    rows.sort(
        key=lambda r: (
            CATEGORY_ORDER.index(r.category),
            not r.verified,
            r.region == "*",
            r.name,
        )
    )
    return rows


def group_by_category(resources: list[Resource]) -> list[tuple[ResourceCategory, list[Resource]]]:
    groups: dict[ResourceCategory, list[Resource]] = {}
    for r in resources:
        groups.setdefault(r.category, []).append(r)
    return [(c, groups[c]) for c in CATEGORY_ORDER if c in groups]
