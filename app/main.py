import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from .config import BASE_DIR, settings
from .db import Base, SessionLocal, engine
from .routers import admin, api, web, whatsapp
from .seed import seed_resources

# Aucun log d'accès : on ne veut ni IP, ni user-agent, ni URL visitée dans les journaux.
logging.getLogger("uvicorn.access").disabled = True


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_resources(db)
    if not settings.report_public_key:
        logging.getLogger("app").warning(
            "REPORT_PUBLIC_KEY absente : les signalements échoueront. Voir README."
        )
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan, docs_url="/api/docs", redoc_url=None)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.middleware("http")
async def privacy_headers(request: Request, call_next):
    """En-têtes de confidentialité sur toutes les réponses.

    - no-store : rien en cache navigateur (historique d'un téléphone partagé).
    - no-referrer : la page d'origine n'est jamais transmise au site "Quitter vite".
    - CSP stricte : aucun script/tracker tiers ne peut se charger.
    """
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; form-action 'self'"
    )
    return response


@app.get("/quitter", include_in_schema=False)
def quick_exit():
    """Bouton "Quitter vite" : redirection immédiate vers un site neutre."""
    return RedirectResponse(settings.quick_exit_url, status_code=303)


@app.get("/healthz", include_in_schema=False)
def healthz():
    return {"ok": True}


app.include_router(api.router)
app.include_router(admin.router)
app.include_router(whatsapp.router)
app.include_router(web.router)  # en dernier : /{lang} est un attrape-tout
#& ".\safety_venv\Scripts\uvicorn.exe" app.main:app --reload --no-access-log --port 8000