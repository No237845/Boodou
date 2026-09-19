"""Espace acteurs : relais communautaires, points focaux VBG, action sociale, gestionnaires de cas.

- /espace              : boîte de réception (les signalements que je peux voir)
- /espace/s/{id}       : un signalement, avec reformulation / transmission / statut
- /espace/nouveau      : saisir le cas d'une personne venue me voir en personne

Même principe que l'espace admin : HTML côté serveur, français uniquement,
cookie de session HttpOnly + SameSite=Strict (pas de jeton anti-CSRF nécessaire).
L'application mobile fait exactement la même chose via /api (Bearer).
"""

from fastapi import APIRouter, Cookie, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .. import ratelimit
from ..api_ai import service as ai
from ..auth import SESSION_COOKIE, actor_from_token, authenticate, issue_token, revoke_token
from ..config import BASE_DIR, settings
from ..db import get_db
from ..i18n import translator
from ..models import CASE_HANDLERS, FORWARD_TARGETS, MUST_SUMMARIZE, SUBTYPES, Actor, ActorRole, Channel, EventKind, ReportStatus, format_code
from ..seed import communes_of, load_regions
from ..services import (
    Forbidden,
    ValidationError,
    create_report,
    decrypt_texts,
    forward,
    forward_targets,
    get_visible_report,
    inbox,
    set_status,
    update_summary,
)

router = APIRouter(prefix="/espace", include_in_schema=False)
templates = Jinja2Templates(directory=BASE_DIR / "templates")

ROLE_LABELS = {
    ActorRole.RELAIS: "Relais communautaire",
    ActorRole.POINT_FOCAL: "Point focal VBG",
    ActorRole.ACTION_SOCIALE: "Action sociale",
    ActorRole.GESTIONNAIRE: "Gestionnaire de cas",
}

STATUS_LABELS = {
    ReportStatus.RECU: "Reçu",
    ReportStatus.TRANSMIS: "Transmis",
    ReportStatus.PRIS_EN_CHARGE: "Pris en charge",
    ReportStatus.REGLE: "Réglé",
}

# Libellés en français pour l'espace acteurs : ceux de fr.json, sans passer par
# la langue de l'usager.
_t = translator("fr")


def _ctx(actor: Actor, **extra) -> dict:
    return {
        "actor": actor,
        "role_labels": ROLE_LABELS,
        "status_labels": STATUS_LABELS,
        "statuses": list(ReportStatus),
        "t": _t,
        "can_set_status": actor.role in CASE_HANDLERS,
        "must_summarize": actor.role in MUST_SUMMARIZE,
        "ai_available": ai.enabled(),
        "can_forward_to": [ROLE_LABELS[r] for r in FORWARD_TARGETS[actor.role]],
        **extra,
    }


def require_actor(
    espace_session: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> Actor | None:
    return actor_from_token(db, espace_session)


def _login_page(request: Request, error: str | None = None, status_code: int = 200):
    return templates.TemplateResponse(request, "espace_login.html", {"error": error}, status_code=status_code)


# --------------------------------------------------------------------------- session


@router.post("/login")
def login(
    request: Request,
    username: str = Form(""),
    password: str = Form(""),
    db: Session = Depends(get_db),
):
    if not ratelimit.allow(request.client.host if request.client else None):
        return _login_page(request, "Trop de tentatives. Réessayez dans un quart d'heure.", 429)
    actor = authenticate(db, username, password)
    if actor is None:
        return _login_page(request, "Identifiant ou mot de passe incorrect.", 401)
    token = issue_token(db, actor, ttl=settings.actor_session_ttl_web)
    response = RedirectResponse("/espace", status_code=303)
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=settings.actor_session_ttl_web,
        httponly=True,
        samesite="strict",
        secure=request.url.scheme == "https",
        path="/espace",
    )
    return response


@router.post("/logout")
def logout(espace_session: str | None = Cookie(default=None), db: Session = Depends(get_db)):
    revoke_token(db, espace_session)
    response = RedirectResponse("/espace", status_code=303)
    response.delete_cookie(SESSION_COOKIE, path="/espace")
    return response


# --------------------------------------------------------------------------- boîte de réception


@router.get("", response_class=HTMLResponse)
def index(
    request: Request,
    status: str = "",
    actor: Actor | None = Depends(require_actor),
    db: Session = Depends(get_db),
):
    if actor is None:
        return _login_page(request)
    selected = ReportStatus(status) if status in ReportStatus.__members__ else None
    reports = inbox(db, actor, status=selected)
    rows = [{"report": r, "code": format_code(r.id), **decrypt_texts(r)} for r in reports]
    return templates.TemplateResponse(
        request, "espace_inbox.html", _ctx(actor, rows=rows, selected_status=status)
    )


@router.get("/s/{report_id}", response_class=HTMLResponse)
def detail(
    request: Request,
    report_id: str,
    error: str = "",
    info: str = "",
    actor: Actor | None = Depends(require_actor),
    db: Session = Depends(get_db),
):
    if actor is None:
        return _login_page(request)
    try:
        report = get_visible_report(db, actor, report_id)
    except Forbidden:
        raise HTTPException(status_code=404, detail="not_found") from None
    # Un relais / point focal qui a déjà transmis ce signalement n'a plus rien à
    # faire dessus : on ne lui remontre pas le formulaire, il croirait devoir
    # recommencer.
    already = actor.role in MUST_SUMMARIZE and any(
        e.kind == EventKind.FORWARDED and e.actor_id == actor.id for e in report.events
    )
    return templates.TemplateResponse(
        request,
        "espace_report.html",
        _ctx(
            actor,
            report=report,
            code=format_code(report.id),
            targets=forward_targets(db, actor),
            forward_roles=[] if already else FORWARD_TARGETS[actor.role],
            already_forwarded=already,
            created_info=info == "created",
            summary_info=info == "summary",
            # Seules nos propres clés d'erreur sont affichées : pas d'écho d'un texte venu de l'URL.
            error=_t(error) if error.startswith("report_error_") else None,
            **decrypt_texts(report),
        ),
    )


@router.post("/s/{report_id}/transmettre")
def do_forward(
    report_id: str,
    to: str = Form(""),
    summary: str = Form(""),
    note: str = Form(""),
    actor: Actor | None = Depends(require_actor),
    db: Session = Depends(get_db),
):
    """`to` vaut `actor:<id>` (une personne) ou `role:<rôle>` (n'importe qui du rôle)."""
    if actor is None:
        raise HTTPException(status_code=401, detail="unauthorized")
    kind, _, value = to.partition(":")
    try:
        report = get_visible_report(db, actor, report_id)
        forward(
            db,
            actor,
            report,
            to_actor_id=int(value) if kind == "actor" and value.isdigit() else None,
            to_role=value if kind == "role" else None,
            summary=summary,
            note=note,
        )
    except Forbidden:
        raise HTTPException(status_code=404, detail="not_found") from None
    except ValidationError as e:
        return RedirectResponse(f"/espace/s/{report_id}?error={e.key}", status_code=303)
    return RedirectResponse("/espace", status_code=303)


def _render_detail(request: Request, actor: Actor, db: Session, report, **extra):
    already = actor.role in MUST_SUMMARIZE and any(
        e.kind == EventKind.FORWARDED and e.actor_id == actor.id for e in report.events
    )
    ctx = _ctx(
        actor,
        report=report,
        code=format_code(report.id),
        targets=forward_targets(db, actor),
        forward_roles=[] if already else FORWARD_TARGETS[actor.role],
        already_forwarded=already,
        created_info=False,
        summary_info=False,
        error=None,
        **decrypt_texts(report),
    )
    ctx.update(extra)
    return templates.TemplateResponse(request, "espace_report.html", ctx)


@router.post("/s/{report_id}/proposer", response_class=HTMLResponse)
def propose_summary(
    request: Request,
    report_id: str,
    actor: Actor | None = Depends(require_actor),
    db: Session = Depends(get_db),
):
    """Demande une proposition de reformulation et la place dans le champ. Rien n'est enregistré."""
    if actor is None:
        return _login_page(request)
    try:
        report = get_visible_report(db, actor, report_id)
    except Forbidden:
        raise HTTPException(status_code=404, detail="not_found") from None
    text = decrypt_texts(report)["description"] or ""
    try:
        s = ai.suggest_summary(
            text,
            region=report.region,
            commune=report.commune or "",
            subtype_label=_t("subtype_" + report.subtype.value) if report.subtype else "",
        )
    except ai.AiUnavailable:
        return _render_detail(request, actor, db, report, error=_t("ai_unavailable"))
    return _render_detail(request, actor, db, report, draft_summary=s.summary, suggestion=s)


@router.post("/s/{report_id}/reformuler")
def do_summary(
    report_id: str,
    summary: str = Form(""),
    actor: Actor | None = Depends(require_actor),
    db: Session = Depends(get_db),
):
    """Corrige la reformulation d'un signalement déjà transmis, sans rechoisir le destinataire."""
    if actor is None:
        raise HTTPException(status_code=401, detail="unauthorized")
    try:
        report = get_visible_report(db, actor, report_id)
        update_summary(db, actor, report, summary)
    except Forbidden:
        raise HTTPException(status_code=404, detail="not_found") from None
    except ValidationError as e:
        return RedirectResponse(f"/espace/s/{report_id}?error={e.key}", status_code=303)
    return RedirectResponse(f"/espace/s/{report_id}?info=summary", status_code=303)


@router.post("/s/{report_id}/statut")
def do_status(
    report_id: str,
    status: str = Form(""),
    partner_note: str = Form(""),
    actor: Actor | None = Depends(require_actor),
    db: Session = Depends(get_db),
):
    if actor is None:
        raise HTTPException(status_code=401, detail="unauthorized")
    if status not in ReportStatus.__members__:
        raise HTTPException(status_code=422, detail="unknown_status")
    try:
        report = get_visible_report(db, actor, report_id)
        set_status(db, report, status=ReportStatus(status), note=partner_note, actor=actor)
    except Forbidden:
        raise HTTPException(status_code=403, detail="forbidden") from None
    return RedirectResponse(f"/espace/s/{report.id}", status_code=303)


# --------------------------------------------------------------------------- saisie par un acteur


def _new_ctx(actor: Actor, db: Session, form: dict, error: str | None) -> dict:
    return _ctx(
        actor,
        regions=load_regions(),
        subtypes=SUBTYPES,
        targets=forward_targets(db, actor),
        forward_roles=FORWARD_TARGETS[actor.role],
        form=form,
        error=error,
    )


@router.get("/nouveau", response_class=HTMLResponse)
def new_form(request: Request, actor: Actor | None = Depends(require_actor), db: Session = Depends(get_db)):
    if actor is None:
        return _login_page(request)
    if actor.role not in MUST_SUMMARIZE:
        # L'action sociale et les gestionnaires traitent, ils ne relaient pas.
        raise HTTPException(status_code=403, detail="forbidden")
    form = {"region": actor.region, "commune": actor.commune or ""}
    return templates.TemplateResponse(request, "espace_new.html", _new_ctx(actor, db, form, None))


@router.post("/nouveau", response_class=HTMLResponse)
def new_submit(
    request: Request,
    subtype: str = Form(""),
    region: str = Form(""),
    commune: str = Form(""),
    to: str = Form(""),
    description: str = Form(""),
    summary: str = Form(""),
    action: str = Form(""),
    actor: Actor | None = Depends(require_actor),
    db: Session = Depends(get_db),
):
    """Un relais enregistre un cas reçu en personne, le reformule et le transmet dans la foulée.

    `action=proposer` : on ne crée rien, on renvoie le formulaire avec une
    proposition de reformulation dans le champ, que le relais relit.
    """
    if actor is None:
        return _login_page(request)
    if actor.role not in MUST_SUMMARIZE:
        raise HTTPException(status_code=403, detail="forbidden")
    form = {"subtype": subtype, "region": region, "commune": commune, "to": to, "description": description, "summary": summary}
    if action == "proposer":
        try:
            s = ai.suggest_summary(
                description, region=region, commune=commune, subtype_label=_t("subtype_" + subtype) if subtype else ""
            )
        except ai.AiUnavailable:
            return templates.TemplateResponse(request, "espace_new.html", _new_ctx(actor, db, form, _t("ai_unavailable")))
        form["summary"] = s.summary
        return templates.TemplateResponse(request, "espace_new.html", {**_new_ctx(actor, db, form, None), "suggestion": s})
    kind, _, value = to.partition(":")
    try:
        if commune and commune not in communes_of(region):
            raise ValidationError("report_error_commune")
        # Le destinataire est choisi ici, une seule fois : le signalement part
        # directement chez lui, déjà « transmis » (voir services.create_report).
        report = create_report(
            db,
            type_="",
            subtype=subtype,
            region=region,
            commune=commune,
            description=description,
            channel=Channel.WEB,
            created_by=actor,
            target_role=value if kind == "role" else None,
            assignee_id=int(value) if kind == "actor" and value.isdigit() else None,
            summary=summary,
        )
    except ValidationError as e:
        return templates.TemplateResponse(
            request, "espace_new.html", _new_ctx(actor, db, form, _t(e.key, **e.params)), status_code=422
        )
    return RedirectResponse(f"/espace/s/{report.id}?info=created", status_code=303)
