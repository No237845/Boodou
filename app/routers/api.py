"""API JSON, utilisée par les bots WhatsApp/SMS et par toute autre interface."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import ratelimit
from ..db import get_db
from ..models import Channel, ReportStatus, ReportType, ResourceCategory, format_code
from ..seed import load_regions, region_names
from ..services import MAX_DESCRIPTION, ValidationError, create_report, find_report, find_resources

router = APIRouter(prefix="/api", tags=["api"])


class ReportIn(BaseModel):
    type: ReportType
    region: str
    commune: str | None = None
    description: str = Field(max_length=MAX_DESCRIPTION)
    channel: Channel = Channel.WEB
    lang: str = "fr"


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


@router.get("/regions")
def regions():
    return load_regions()


@router.post("/reports", response_model=ReportOut, status_code=201)
def post_report(payload: ReportIn, db: Session = Depends(get_db)):
    try:
        report = create_report(
            db,
            type_=payload.type.value,
            region=payload.region,
            commune=payload.commune,
            description=payload.description,
            channel=payload.channel,
            lang=payload.lang,
        )
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.key) from None
    return ReportOut(code=format_code(report.id))


@router.get("/reports/{code}", response_model=TrackOut)
def track_report(code: str, request: Request, db: Session = Depends(get_db)):
    """Suivi d'un signalement par son code. Utilisé par les canaux SMS / USSD."""
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
        partner_note=report.partner_note,
    )


@router.get("/resources", response_model=list[ResourceOut])
def get_resources(
    type: ReportType | None = None,
    region: str | None = None,
    category: ResourceCategory | None = None,
    db: Session = Depends(get_db),
):
    if region is not None and region not in region_names():
        raise HTTPException(status_code=422, detail="unknown_region")
    rows = find_resources(db, type_=type, region=region, category=category)
    return [
        ResourceOut(
            name=r.name,
            category=r.category,
            phone=r.phone,
            region=r.region,
            city=r.city,
            hours=r.hours,
            languages=r.languages.split(","),
            verified=r.verified,
            notes=r.notes,
        )
        for r in rows
    ]
