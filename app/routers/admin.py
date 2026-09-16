"""Espace partenaire : tableau de bord des signalements.

- Interface HTML : /admin (connexion par clé admin, cookie de session HttpOnly).
- API JSON : /admin/stats et /admin/reports (en-tête X-Admin-Key ou session).

Le serveur ne peut PAS déchiffrer les descriptions seul. Le partenaire peut
coller sa clé privée à la connexion : elle est gardée en mémoire (RAM) le temps
de la session, jamais écrite en base ni dans les logs, et disparaît à la
déconnexion, à l'expiration ou au redémarrage du serveur.
"""

import secrets
import time
from urllib.parse import urlencode

from fastapi import APIRouter, Cookie, Depends, Form, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import crypto
from ..config import BASE_DIR, settings
from ..db import get_db
from ..models import PARTNER_NOTE_MAX, Report, ReportStatus, ReportType, format_code
from ..seed import region_names
from ..services import set_status

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory=BASE_DIR / "templates")

SESSION_COOKIE = "admin_session"
SESSION_TTL = 60 * 60  # 1 h

# token -> {"private_key": str | None, "expires": float}. En mémoire uniquement.
_sessions: dict[str, dict] = {}

TYPE_LABELS = {
    ReportType.VIOLENCE: "Violence physique",
    ReportType.MENACE: "Menace / intimidation",
    ReportType.GBV: "Violence basée sur le genre",
    ReportType.TERRORISME: "Attaque / terrorisme",
}

STATUS_LABELS = {
    ReportStatus.RECU: "Reçu",
    ReportStatus.TRANSMIS: "Pris en charge",
    ReportStatus.CLOTURE: "Clôturé",
}


def _session(token: str | None) -> dict | None:
    if not token:
        return None
    s = _sessions.get(token)
    if s is None:
        return None
    if s["expires"] < time.time():
        _sessions.pop(token, None)
        return None
    return s


def _is_admin_key(key: str) -> bool:
    return bool(key) and secrets.compare_digest(key, settings.admin_key)


def require_admin(
    x_admin_key: str = Header(default=""),
    admin_session: str | None = Cookie(default=None),
):
    """Accès JSON : en-tête X-Admin-Key ou session du tableau de bord."""
    if _is_admin_key(x_admin_key) or _session(admin_session) is not None:
        return
    raise HTTPException(status_code=401, detail="unauthorized")


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
    session = _session(admin_session)
    if session is None:
        return templates.TemplateResponse(request, "admin_login.html", {"error": None})

    stmt = select(Report).order_by(Report.created_at.desc())
    if type in ReportType.__members__:
        stmt = stmt.where(Report.type == ReportType(type))
    if region in region_names():
        stmt = stmt.where(Report.region == region)
    if status in ReportStatus.__members__:
        stmt = stmt.where(Report.status == ReportStatus(status))
    reports = db.execute(stmt.limit(500)).scalars().all()

    private_key = session.get("private_key")
    rows = []
    for r in reports:
        description = None
        decrypt_error = False
        if private_key:
            try:
                description = crypto.decrypt(r.ciphertext, private_key)
            except Exception:
                decrypt_error = True
        rows.append(
            {
                "report": r,
                "code": format_code(r.id),
                "description": description,
                "decrypt_error": decrypt_error,
            }
        )

    return templates.TemplateResponse(
        request,
        "admin.html",
        {
            "stats": _stats(db),
            "rows": rows,
            "can_decrypt": bool(private_key),
            "types": list(ReportType),
            "type_labels": TYPE_LABELS,
            "statuses": list(ReportStatus),
            "status_labels": STATUS_LABELS,
            "note_max": PARTNER_NOTE_MAX,
            "regions": region_names(),
            "selected_type": type,
            "selected_region": region,
            "selected_status": status,
        },
    )


@router.post("/login", include_in_schema=False)
def login(
    request: Request,
    admin_key: str = Form(""),
    private_key: str = Form(""),
):
    if not _is_admin_key(admin_key):
        return templates.TemplateResponse(
            request, "admin_login.html", {"error": "Clé admin incorrecte."}, status_code=401
        )
    private_key = private_key.strip() or None
    if private_key:
        try:
            # Vérifie que la clé est bien une clé privée valide avant de l'accepter.
            crypto.decrypt(crypto.encrypt("ok"), private_key)
        except Exception:
            return templates.TemplateResponse(
                request,
                "admin_login.html",
                {"error": "La clé privée ne correspond pas à la clé publique du serveur."},
                status_code=400,
            )

    token = secrets.token_urlsafe(32)
    _sessions[token] = {"private_key": private_key, "expires": time.time() + SESSION_TTL}
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
    aucune page tierce ne peut déclencher cette requête au nom du partenaire.
    """
    if _session(admin_session) is None:
        raise HTTPException(status_code=401, detail="unauthorized")
    if status not in ReportStatus.__members__:
        raise HTTPException(status_code=422, detail="unknown_status")

    report = db.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="not_found")
    set_status(db, report, status=ReportStatus(status), note=partner_note)

    # On revient à la vue filtrée d'où vient le partenaire. Les filtres sont
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
    }


@router.get("/stats", dependencies=[Depends(require_admin)])
def stats(db: Session = Depends(get_db)):
    return _stats(db)


@router.get("/reports", dependencies=[Depends(require_admin)])
def export_reports(db: Session = Depends(get_db)):
    """Export chiffré, à déchiffrer hors ligne avec `python -m scripts.decrypt`."""
    rows = db.execute(select(Report).order_by(Report.created_at.desc())).scalars().all()
    return [
        {
            "id": r.id,
            "type": r.type.value,
            "region": r.region,
            "commune": r.commune,
            "channel": r.channel.value,
            "lang": r.lang,
            "created_at": r.created_at.isoformat(),
            "status": r.status.value,
            "partner_note": r.partner_note,
            "status_at": r.status_at.isoformat() if r.status_at else None,
            "ciphertext": r.ciphertext,
        }
        for r in rows
    ]
