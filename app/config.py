from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    """Configuration lue depuis les variables d'environnement / .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Boodou BF"

    # PostgreSQL obligatoire. Format :
    #   postgresql+psycopg://user:password@host:5432/dbname?sslmode=require
    # Les URL "postgres://" / "postgresql://" (Railway, Neon, Supabase, Render)
    # sont normalisées automatiquement vers le driver psycopg.
    database_url: str = ""

    @property
    def sqlalchemy_url(self) -> str:
        url = self.database_url.strip()
        if not url:
            raise RuntimeError("DATABASE_URL manquante : renseignez l'URL PostgreSQL dans .env")
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url[len(prefix):]
        if not url.startswith("postgresql+psycopg://"):
            raise RuntimeError("DATABASE_URL doit être une URL PostgreSQL (postgresql://...)")
        return url

    # Clé publique libsodium (base64). La clé privée n'est JAMAIS sur le serveur :
    # elle reste chez l'organisation partenaire qui déchiffre les signalements.
    report_public_key: str = ""

    # Clé d'accès à l'endpoint /admin (métadonnées uniquement, jamais le contenu).
    admin_key: str = "change-me"

    # Site neutre vers lequel renvoie le bouton "Quitter vite".
    quick_exit_url: str = "https://www.google.com"

    default_lang: str = "fr"
    languages: list[str] = ["fr", "mos", "dyu", "en"]

    # --- WhatsApp Cloud API (Meta) ---
    # Jeton choisi par vous, à recopier dans Meta > WhatsApp > Configuration > Webhook.
    whatsapp_verify_token: str = ""
    # Jeton d'accès (temporaire en dev, "System user" permanent en prod).
    whatsapp_access_token: str = ""
    # "Phone number ID" affiché dans Meta > WhatsApp > API Setup (pas le numéro lui-même).
    whatsapp_phone_number_id: str = ""
    # "App secret" (Meta > Paramètres de l'app > Général) : sert à vérifier la signature des webhooks.
    whatsapp_app_secret: str = ""
    whatsapp_api_version: str = "v21.0"

    # Sel pour hacher les numéros de téléphone (clé de session du bot). Le numéro
    # en clair n'est jamais stocké : seul le hash vit en mémoire ~15 min.
    bot_phone_salt: str = "change-me-too"
    bot_session_ttl: int = 15 * 60


settings = Settings()
