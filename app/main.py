import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from . import migrations
from .api_ai import translate_cache
from .config import BASE_DIR, settings
from .db import Base, SessionLocal, engine
from .routers import admin, api, espace, sms, web, whatsapp
from .seed import seed_resources

# Aucun log d'accès : on ne veut ni IP, ni user-agent, ni URL visitée dans les journaux.
logging.getLogger("uvicorn.access").disabled = True


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    # create_all n'ajoute pas les colonnes manquantes à une table déjà en place.
    migrations.run(engine)
    with SessionLocal() as db:
        seed_resources(db)
        # Annuaire et notes des acteurs en mooré : cache + fil de fond.
        # Sans BURKIMBIA_API_KEY, ne fait rien (contenu dynamique en français).
        translate_cache.start(db)
    if not settings.report_secret_key:
        logging.getLogger("app").warning(
            "REPORT_SECRET_KEY absente : les signalements échoueront. Voir README."
        )
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan, docs_url="/api/docs", redoc_url=None)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# CORS pour l'API appelée depuis un navigateur (app mobile en mode web).
# Sans cookies : les sessions cookie (/admin, /espace) restent donc hors de
# portée d'un site tiers, seuls les jetons Bearer explicites passent.
if settings.cors_origin_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )


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
app.include_router(espace.router)
app.include_router(whatsapp.router)
app.include_router(sms.router)
app.include_router(web.router)  # en dernier : /{lang} est un attrape-tout
#& ".\safety_venv\Scripts\uvicorn.exe" app.main:app --reload --no-access-log --port 8000
#uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --no-access-log                                                                                        