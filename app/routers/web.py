"""Parcours web (faible bande passante) : HTML côté serveur, zéro JavaScript."""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..config import BASE_DIR, settings
from ..db import get_db
from ..i18n import LANG_NAMES, normalize_lang, translator
from ..models import Channel, ReportType, ResourceCategory
from ..seed import load_regions, region_names
from ..services import ValidationError, create_report, find_resources, group_by_category

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory=BASE_DIR / "templates")


def render(request: Request, name: str, lang: str, **ctx):
    lang = normalize_lang(lang)
    return templates.TemplateResponse(
        request,
        name,
        {
            "lang": lang,
            "t": translator(lang),
            "languages": [(code, LANG_NAMES[code]) for code in settings.languages],
            "app_name": settings.app_name,
            **ctx,
        },
    )


@router.get("/", response_class=HTMLResponse)
def choose_language(request: Request):
    return render(request, "lang.html", settings.default_lang)


@router.get("/{lang}", response_class=HTMLResponse)
def home(request: Request, lang: str, db: Session = Depends(get_db)):
    emergency = find_resources(db, category=ResourceCategory.URGENCE)
    return render(request, "home.html", lang, emergency=emergency)


@router.get("/{lang}/signaler", response_class=HTMLResponse)
def report_form(request: Request, lang: str):
    return render(request, "report.html", lang, regions=load_regions(), types=list(ReportType), form={}, error=None)


@router.post("/{lang}/signaler", response_class=HTMLResponse)
def report_submit(
    request: Request,
    lang: str,
    type: str = Form(""),
    region: str = Form(""),
    commune: str = Form(""),
    description: str = Form(""),
    db: Session = Depends(get_db),
):
    lang = normalize_lang(lang)
    try:
        create_report(
            db,
            type_=type,
            region=region,
            commune=commune,
            description=description,
            channel=Channel.WEB,
            lang=lang,
        )
    except ValidationError as e:
        t = translator(lang)
        return render(
            request,
            "report.html",
            lang,
            regions=load_regions(),
            types=list(ReportType),
            form={"type": type, "region": region, "commune": commune, "description": description},
            error=t(e.key, **e.params),
        )
    # PRG : un rafraîchissement ne renvoie jamais le formulaire une deuxième fois.
    # Seuls type et région (non identifiants) passent dans l'URL pour cibler les ressources.
    return RedirectResponse(f"/{lang}/merci?type={type}&region={region}", status_code=303)


@router.get("/{lang}/merci", response_class=HTMLResponse)
def confirmation(request: Request, lang: str, type: str = "", region: str = "", db: Session = Depends(get_db)):
    rtype = ReportType(type) if type in ReportType.__members__ else None
    region = region if region in region_names() else None
    resources = find_resources(db, type_=rtype, region=region)
    return render(request, "confirm.html", lang, groups=group_by_category(resources))


@router.get("/{lang}/ressources", response_class=HTMLResponse)
def resources(
    request: Request,
    lang: str,
    cat: str = "",
    type: str = "",
    region: str = "",
    db: Session = Depends(get_db),
):
    category = ResourceCategory(cat) if cat in ResourceCategory.__members__ else None
    rtype = ReportType(type) if type in ReportType.__members__ else None
    region = region if region in region_names() else None
    found = find_resources(db, type_=rtype, region=region, category=category)
    return render(
        request,
        "resources.html",
        lang,
        groups=group_by_category(found),
        regions=region_names(),
        selected_region=region or "",
        selected_cat=cat,
        selected_type=type,
    )
