"""Administration : vue d'ensemble des signalements et gestion des comptes acteurs.

- Interface HTML : /admin (connexion par clé admin, cookie de session HttpOnly).
- Comptes : /admin/acteurs (créer, désactiver, réinitialiser un mot de passe).
- API JSON : /admin/stats et /admin/reports (en-tête X-Admin-Key ou session).

L'admin est le coordinateur du dispositif : il voit tout, y compris les récits
déchiffrés. C'est lui qui crée les comptes des relais, points focaux, agents
de l'action sociale et gestionnaires de cas.
"""

import secrets
import time
from urllib.parse import urlencode

from fastapi import APIRouter, Cookie, Depends, Form, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import PASSWORD_MIN, hash_password, revoke_all
from ..config import BASE_DIR, settings
from ..db import get_db
from ..i18n import translator
from ..models import PARTNER_NOTE_MAX, Actor, ActorRole, Report, ReportStatus, ReportType, format_code
from ..seed import communes_of, load_regions, region_names
from ..services import decrypt_texts, set_status
from .espace import ROLE_LABELS, STATUS_LABELS

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory=BASE_DIR / "templates")

SESSION_COOKIE = "admin_session"
SESSION_TTL = 60 * 60  # 1 h

# token -> expiration. En mémoire uniquement.
_sessions: dict[str, float] = {}

_t = translator("fr")


def _session_ok(token: str | None) -> bool:
    if not token:
        return False
    expires = _sessions.get(token)
    if expires is None:
        return False
    if expires < time.time():
        _sessions.pop(token, None)
        return False
    return True


def _is_admin_key(key: str) -> bool:
    return bool(key) and secrets.compare_digest(key, settings.admin_key)


def require_admin(
    x_admin_key: str = Header(default=""),
    admin_session: str | None = Cookie(default=None),
):
    """Accès JSON : en-tête X-Admin-Key ou session du tableau de bord."""
    if _is_admin_key(x_admin_key) or _session_ok(admin_session):
        return
    raise HTTPException(status_code=401, detail="unauthorized")


def _base_ctx(**extra) -> dict:
    return {
        "t": _t,
        "types": list(ReportType),
        "statuses": list(ReportStatus),
        "status_labels": STATUS_LABELS,
        "role_labels": ROLE_LABELS,
        "roles": list(ActorRole),
        "regions": region_names(),
        **extra,
    }


# --------------------------------------------------------------------------- HTML


@router.get("", response_class=HTMLResponse, include_in_schema=False)
def dashboard(
    request: Request,
    type: str = "",
    region: str = "",
    status: str = "",
    admin_session: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
):
    if not _session_ok(admin_session):
        return templates.TemplateResponse(request, "admin_login.html", {"error": None})

    stmt = select(Report).order_by(Report.created_at.desc())
    if type in ReportType.__members__:
        stmt = stmt.where(Report.type == ReportType(type))
    if region in region_names():
        stmt = stmt.where(Report.region == region)
    if status in ReportStatus.__members__:
        stmt = stmt.where(Report.status == ReportStatus(status))
    reports = db.execute(stmt.limit(500)).scalars().all()
    rows = [{"report": r, "code": format_code(r.id), **decrypt_texts(r)} for r in reports]

    return templates.TemplateResponse(
        request,
        "admin.html",
        _base_ctx(
            stats=_stats(db),
            rows=rows,
            note_max=PARTNER_NOTE_MAX,
            selected_type=type,
            selected_region=region,
            selected_status=status,
        ),
    )


@router.post("/login", include_in_schema=False)
def login(request: Request, admin_key: str = Form("")):
    if not _is_admin_key(admin_key):
        return templates.TemplateResponse(
            request, "admin_login.html", {"error": "Clé admin incorrecte."}, status_code=401
        )
    token = secrets.token_urlsafe(32)
    _sessions[token] = time.time() + SESSION_TTL
    response = RedirectResponse("/admin", status_code=303)
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=SESSION_TTL,
        httponly=True,
        samesite="strict",
        secure=request.url.scheme == "https",
        path="/admin",
    )
    return response


@router.post("/reports/{report_id}/statut", include_in_schema=False)
def update_status(
    report_id: str,
    status: str = Form(""),
    partner_note: str = Form(""),
    f_type: str = Form(""),
    f_region: str = Form(""),
    f_status: str = Form(""),
    admin_session: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
):
    """Fait avancer un signalement et écrit, au besoin, un mot à la personne.

    Pas de jeton anti-CSRF : le cookie de session est `SameSite=Strict`, donc
    aucune page tierce ne peut déclencher cette requête au nom de l'admin.
    """
    if not _session_ok(admin_session):
        raise HTTPException(status_code=401, detail="unauthorized")
    if status not in ReportStatus.__members__:
        raise HTTPException(status_code=422, detail="unknown_status")

    report = db.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="not_found")
    set_status(db, report, status=ReportStatus(status), note=partner_note)

    # On revient à la vue filtrée d'où vient l'admin. Les filtres sont
    # revalidés ici plutôt que réinjectés tels quels depuis le formulaire.
    back = {
        "type": f_type if f_type in ReportType.__members__ else "",
        "region": f_region if f_region in region_names() else "",
        "status": f_status if f_status in ReportStatus.__members__ else "",
    }
    return RedirectResponse(f"/admin?{urlencode(back)}", status_code=303)


@router.post("/logout", include_in_schema=False)
def logout(admin_session: str | None = Cookie(default=None)):
    if admin_session:
        _sessions.pop(admin_session, None)
    response = RedirectResponse("/admin", status_code=303)
    response.delete_cookie(SESSION_COOKIE, path="/admin")
    return response


# --------------------------------------------------------------------------- comptes acteurs


def _actors_page(request: Request, db: Session, error: str | None = None, info: str | None = None, form: dict | None = None, status_code: int = 200):
    actors = db.execute(select(Actor).order_by(Actor.region, Actor.role, Actor.name)).scalars().all()
    return templates.TemplateResponse(
        request,
        "admin_actors.html",
        _base_ctx(actors=actors, regions_full=load_regions(), error=error, info=info, form=form or {}),
        status_code=status_code,
    )


@router.get("/acteurs", response_class=HTMLResponse, include_in_schema=False)
def actors(request: Request, info: str = "", admin_session: str | None = Cookie(default=None), db: Session = Depends(get_db)):
    if not _session_ok(admin_session):
        return templates.TemplateResponse(request, "admin_login.html", {"error": None})
    return _actors_page(request, db, info=info or None)


@router.post("/acteurs", response_class=HTMLResponse, include_in_schema=False)
def create_actor(
    request: Request,
    username: str = Form(""),
    password: str = Form(""),
    name: str = Form(""),
    role: str = Form(""),
    organisation: str = Form(""),
    region: str = Form(""),
    commune: str = Form(""),
    phone: str = Form(""),
    admin_session: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
):
    if not _session_ok(admin_session):
        raise HTTPException(status_code=401, detail="unauthorized")
    form = {
        "username": username, "name": name, "role": role, "organisation": organisation,
        "region": region, "commune": commune, "phone": phone,
    }
    username = username.strip().lower()
    name = name.strip()
    commune = commune.strip()
    error = None
    if not username or not name or role not in ActorRole.__members__ or region not in region_names():
        error = "Identifiant, nom, rôle et région sont obligatoires."
    elif len(password) < PASSWORD_MIN:
        error = f"Le mot de passe doit faire au moins {PASSWORD_MIN} caractères."
    elif commune and commune not in communes_of(region):
        error = "Cette commune n'est pas dans la région choisie."
    elif db.execute(select(Actor).where(Actor.username == username)).scalar_one_or_none() is not None:
        error = "Cet identifiant existe déjà."
    if error:
        return _actors_page(request, db, error=error, form=form, status_code=422)

    db.add(
        Actor(
            username=username,
            password_hash=hash_password(password),
            name=name,
            role=ActorRole(role),
            organisation=organisation.strip() or None,
            region=region,
            commune=commune or None,
            phone=phone.strip() or None,
        )
    )
    db.commit()
    return RedirectResponse(f"/admin/acteurs?{urlencode({'info': f'Compte « {username} » créé.'})}", status_code=303)


@router.post("/acteurs/{actor_id}/actif", include_in_schema=False)
def toggle_actor(actor_id: int, admin_session: str | None = Cookie(default=None), db: Session = Depends(get_db)):
    if not _session_ok(admin_session):
        raise HTTPException(status_code=401, detail="unauthorized")
    actor = db.get(Actor, actor_id)
    if actor is None:
        raise HTTPException(status_code=404, detail="not_found")
    actor.active = not actor.active
    db.commit()
    if not actor.active:
        # Un compte désactivé perd ses sessions tout de suite, y compris sur mobile.
        revoke_all(db, actor)
    return RedirectResponse("/admin/acteurs", status_code=303)


@router.post("/acteurs/{actor_id}/mot-de-passe", include_in_schema=False)
def reset_password(
    request: Request,
    actor_id: int,
    password: str = Form(""),
    admin_session: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
):
    if not _session_ok(admin_session):
        raise HTTPException(status_code=401, detail="unauthorized")
    actor = db.get(Actor, actor_id)
    if actor is None:
        raise HTTPException(status_code=404, detail="not_found")
    if len(password) < PASSWORD_MIN:
        return _actors_page(request, db, error=f"Le mot de passe doit faire au moins {PASSWORD_MIN} caractères.", status_code=422)
    actor.password_hash = hash_password(password)
    db.commit()
    revoke_all(db, actor)
    return RedirectResponse(f"/admin/acteurs?{urlencode({'info': f'Mot de passe de « {actor.username} » changé.'})}", status_code=303)


# --------------------------------------------------------------------------- JSON


def _stats(db: Session) -> dict:
    by_type = db.execute(select(Report.type, func.count()).group_by(Report.type)).all()
    by_region = db.execute(select(Report.region, func.count()).group_by(Report.region)).all()
    by_channel = db.execute(select(Report.channel, func.count()).group_by(Report.channel)).all()
    by_status = db.execute(select(Report.status, func.count()).group_by(Report.status)).all()
    return {
        "total": db.scalar(select(func.count()).select_from(Report)) or 0,
        "by_type": {t.value: n for t, n in by_type},
        "by_region": dict(sorted(by_region, key=lambda x: -x[1])),
        "by_channel": {c.value: n for c, n in by_channel},
        "by_status": {s.value: n for s, n in by_status},
        "actors": db.scalar(select(func.count()).select_from(Actor).where(Actor.active.is_(True))) or 0,
    }


@router.get("/stats", dependencies=[Depends(require_admin)])
def stats(db: Session = Depends(get_db)):
    return _stats(db)


@router.get("/reports", dependencies=[Depends(require_admin)])
def export_reports(db: Session = Depends(get_db)):
    """Export complet, récits en clair : à manipuler comme un document sensible."""
    rows = db.execute(select(Report).order_by(Report.created_at.desc())).scalars().all()
    out = []
    for r in rows:
        texts = decrypt_texts(r)
        out.append(
            {
                "id": r.id,
                "type": r.type.value,
                "subtype": r.subtype.value if r.subtype else None,
                "region": r.region,
                "commune": r.commune,
                "channel": r.channel.value,
                "lang": r.lang,
                "created_at": r.created_at.isoformat(),
                "status": r.status.value,
                "status_at": r.status_at.isoformat() if r.status_at else None,
                "assignee": r.assignee.username if r.assignee else None,
                "target_role": r.target_role.value if r.target_role else None,
                "partner_note": r.partner_note,
                "description": texts["description"],
                "summary": texts["summary"],
                "legacy_ciphertext": r.ciphertext if texts["legacy"] else None,
            }
        )
    return out
