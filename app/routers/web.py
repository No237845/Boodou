"""Parcours web (faible bande passante) : HTML côté serveur, zéro JavaScript."""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .. import ratelimit
from ..api_ai import translate_cache
from ..config import BASE_DIR, settings
from ..db import get_db
from ..i18n import LANG_NAMES, normalize_lang, translator
from ..models import (
    SUBTYPES,
    ActorRole,
    Channel,
    ReportStatus,
    ReportSubtype,
    ReportType,
    ResourceCategory,
    format_code,
    type_of,
)
from ..seed import communes_of, load_regions, region_names
from ..services import (
    ValidationError,
    create_report,
    find_report,
    find_resources,
    group_by_category,
    parse_subtype,
    public_relais,
)

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# Valeurs du champ « destinataire » de l'étape 2 : `relais:<id>` ou `role:<rôle>`.
RECIPIENT_ACTION_SOCIALE = "role:" + ActorRole.ACTION_SOCIALE.value


def render(request: Request, name: str, lang: str, **ctx):
    lang = normalize_lang(lang)
    return templates.TemplateResponse(
        request,
        name,
        {
            "lang": lang,
            "rtl": lang in settings.rtl_languages,
            "t": translator(lang),
            # t() = textes de l'interface (fichiers de langue) ; tr() = contenu
            # venu de la base (annuaire, note d'un acteur), traduit en fond et
            # servi depuis le cache — ou tel quel tant que ce n'est pas prêt.
            "tr": lambda text: translate_cache.localized(text, lang),
            "languages": [(code, LANG_NAMES[code]) for code in settings.languages],
            # Pas de app_name ici : les gabarits passent par t('app_name'), qui
            # est traduisible. Deux sources pour un même nom, c'est une de trop.
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


# --------------------------------------------------------------------------- signalement
#
# Deux pages, sans JavaScript : la liste des relais dépend de la commune, on
# ne peut donc la montrer qu'après un premier envoi.
#   1. GET  /signaler         : de quoi s'agit-il (sous-type), région, commune
#   2. POST /signaler         : à qui l'envoyer (relais de la commune ou action
#                               sociale) et que s'est-il passé
#   3. POST /signaler/envoyer : enregistrement, puis /merci


def _step1_ctx(form: dict, error: str | None) -> dict:
    return {"regions": load_regions(), "subtypes": SUBTYPES, "form": form, "error": error}


@router.get("/{lang}/signaler", response_class=HTMLResponse)
def report_form(request: Request, lang: str):
    return render(request, "report.html", lang, **_step1_ctx({}, None))


def _validate_step1(subtype: str, region: str, commune: str) -> tuple[ReportSubtype, str, str] | str:
    """Retourne (sous-type, région, commune) ou la clé d'erreur à afficher."""
    try:
        _, sub = parse_subtype("", subtype)
    except ValidationError:
        return "report_error_required"
    if sub is None or region not in region_names():
        return "report_error_required"
    if not commune:
        return "report_error_required"
    if commune not in communes_of(region):
        return "report_error_commune"
    return sub, region, commune


@router.post("/{lang}/signaler", response_class=HTMLResponse)
def report_step2(
    request: Request,
    lang: str,
    subtype: str = Form(""),
    region: str = Form(""),
    commune: str = Form(""),
    db: Session = Depends(get_db),
):
    lang = normalize_lang(lang)
    form = {"subtype": subtype, "region": region, "commune": commune}
    checked = _validate_step1(subtype, region, commune)
    if isinstance(checked, str):
        return render(request, "report.html", lang, **_step1_ctx(form, translator(lang)(checked)))
    sub, region, commune = checked
    return render(
        request,
        "report_to.html",
        lang,
        form={**form, "recipient": "", "description": ""},
        subtype=sub,
        relais=public_relais(db, region, commune),
        action_sociale=RECIPIENT_ACTION_SOCIALE,
        error=None,
    )


@router.post("/{lang}/signaler/envoyer", response_class=HTMLResponse)
def report_submit(
    request: Request,
    lang: str,
    subtype: str = Form(""),
    region: str = Form(""),
    commune: str = Form(""),
    recipient: str = Form(""),
    description: str = Form(""),
    db: Session = Depends(get_db),
):
    lang = normalize_lang(lang)
    t = translator(lang)
    form = {"subtype": subtype, "region": region, "commune": commune, "recipient": recipient, "description": description}
    checked = _validate_step1(subtype, region, commune)
    if isinstance(checked, str):
        # Les champs de l'étape 1 ont été altérés : on y renvoie.
        return render(request, "report.html", lang, **_step1_ctx(form, t(checked)))
    sub, region, commune = checked

    assignee_id = None
    target_role = None
    kind, _, value = recipient.partition(":")
    if kind == "relais" and value.isdigit():
        assignee_id = int(value)
    elif kind == "role":
        target_role = value
    else:
        return _step2_error(request, lang, form, sub, db, t("report_error_recipient"))

    try:
        report = create_report(
            db,
            type_="",
            subtype=sub.value,
            region=region,
            commune=commune,
            description=description,
            assignee_id=assignee_id,
            target_role=target_role,
            channel=Channel.WEB,
            lang=lang,
        )
    except ValidationError as e:
        return _step2_error(request, lang, form, sub, db, t(e.key, **e.params))
    # PRG : un rafraîchissement ne renvoie jamais le formulaire une deuxième fois.
    # Type, région et code de suivi passent dans l'URL. Sur un téléphone partagé
    # l'historique les expose — c'est le même arbitrage que pour type/région, et
    # la page rappelle à la personne d'utiliser "Quitter vite" en partant.
    return RedirectResponse(
        f"/{lang}/merci?subtype={sub.value}&region={region}&code={report.id}", status_code=303
    )


def _step2_error(request: Request, lang: str, form: dict, sub: ReportSubtype, db: Session, error: str):
    return render(
        request,
        "report_to.html",
        lang,
        form=form,
        subtype=sub,
        relais=public_relais(db, form["region"], form["commune"]),
        action_sociale=RECIPIENT_ACTION_SOCIALE,
        error=error,
    )


@router.get("/{lang}/merci", response_class=HTMLResponse)
def confirmation(
    request: Request,
    lang: str,
    subtype: str = "",
    region: str = "",
    code: str = "",
    db: Session = Depends(get_db),
):
    sub = ReportSubtype(subtype) if subtype in ReportSubtype.__members__ else None
    rtype = type_of(sub) if sub else None
    region = region if region in region_names() else None
    resources = find_resources(db, type_=rtype, subtype=sub, region=region)
    # Le code n'est affiché que s'il correspond à un signalement réel : une URL
    # bricolée à la main n'invente pas un code de suivi.
    report = find_report(db, code) if code else None
    return render(
        request,
        "confirm.html",
        lang,
        groups=group_by_category(resources),
        code=format_code(report.id) if report else None,
    )


# --------------------------------------------------------------------------- suivi


@router.get("/{lang}/suivi", response_class=HTMLResponse)
def track_form(request: Request, lang: str):
    return render(request, "track.html", lang, report=None, code="", error=None, statuses=list(ReportStatus))


@router.post("/{lang}/suivi", response_class=HTMLResponse)
def track_lookup(
    request: Request,
    lang: str,
    code: str = Form(""),
    db: Session = Depends(get_db),
):
    """Consultation d'un code de suivi.

    Réponse rendue directement (pas de redirection) : le code reste dans le
    corps de la requête, jamais dans l'URL ni dans l'historique du navigateur.
    Un rafraîchissement rejoue une simple lecture, sans effet de bord.
    """
    lang = normalize_lang(lang)
    t = translator(lang)
    ctx = {"statuses": list(ReportStatus)}
    # request.client.host seulement : un en-tête X-Forwarded-For est falsifiable
    # et permettrait de contourner la limite en variant sa valeur.
    if not ratelimit.allow(request.client.host if request.client else None):
        return render(request, "track.html", lang, report=None, code="", error=t("track_too_many"), **ctx)

    report = find_report(db, code)
    if report is None:
        return render(request, "track.html", lang, report=None, code=code, error=t("track_not_found"), **ctx)
    return render(request, "track.html", lang, report=report, code=format_code(report.id), error=None, **ctx)


# --------------------------------------------------------------------------- ressources


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
    # Ici la personne consulte l'annuaire et filtre elle-même : pas de plafond,
    # contrairement à l'écran de confirmation où la liste doit rester courte.
    found = find_resources(db, type_=rtype, region=region, category=category, limit_per_category=None)
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
