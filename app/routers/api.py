"""API JSON, utilisée par les bots WhatsApp/SMS et par toute autre interface."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Channel, ReportType, ResourceCategory
from ..seed import load_regions, region_names
from ..services import MAX_DESCRIPTION, ValidationError, create_report, find_resources

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
    # Pas d'identifiant renvoyé : rien à conserver côté utilisateur.


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
        create_report(
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
    return ReportOut()


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
