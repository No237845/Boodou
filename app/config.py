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

    # Clé symétrique libsodium (base64, 32 octets) qui chiffre les récits au repos.
    # Générée par `python -m scripts.gen_keys`. Sans elle, aucun signalement ne
    # peut être ni enregistré ni lu.
    report_secret_key: str = ""

    # Ancien schéma (sealed box). Ne sert plus qu'à `scripts/reencrypt.py` pour
    # relire les signalements créés avant la refonte. Peut rester vide.
    report_public_key: str = ""

    # Clé d'accès à /admin : gestion des comptes acteurs et vue d'ensemble.
    admin_key: str = "change-me"

    # Origines autorisées à appeler /api depuis un navigateur (CORS), séparées
    # par des virgules. Utile pour l'app mobile en mode web (`expo start --web`,
    # servie sur :8081) ; un téléphone avec Expo Go ou l'APK n'en a pas besoin.
    # "*" = toutes (sans cookies : /api n'utilise que des jetons Bearer).
    cors_origins: str = "http://localhost:8081,http://127.0.0.1:8081"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    # --- Assistant de reformulation (app/api_ai) ---
    # Clé OpenAI. Vide = bouton « Proposer une reformulation » absent partout.
    # ⚠ Avec une clé, le récit d'un signalement est envoyé à OpenAI quand un
    # relais demande une proposition. À valider avec les partenaires.
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # --- Dictée vocale (app/api_ai/transcribe.py, Gladia) ---
    # Clé Gladia. Vide = pas de bouton « Parler au lieu d'écrire » dans l'app.
    # ⚠ Avec une clé, l'enregistrement de la personne est envoyé à Gladia pour
    # être transcrit ; rien n'est conservé côté serveur.
    gladia_api_key: str = ""
    gladia_model: str = "solaria-1"
    # Taille max d'un enregistrement (octets). ~2 min d'AAC mono 32 kbit/s ≈ 500 Ko.
    speech_max_bytes: int = 8 * 1024 * 1024

    # --- Traduction FR -> Mooré (app/api_ai/translate.py, Burkimbia) ---
    # Clé Burkimbia. Sert (1) au script scripts/translate_locales.py pour
    # remplir mos.json hors ligne, (2) en production pour traduire à la volée
    # le contenu qui n'est pas dans les fichiers de langue (annuaire, messages
    # des acteurs). Vide = le contenu dynamique reste en français en mooré.
    # Seul du contenu public ou destiné à la personne est envoyé : jamais le
    # récit d'un signalement.
    burkimbia_api_key: str = ""
    burkimbia_model: str = "bia-translation-v1-fast"

    # Durée des sessions acteurs. Le web est souvent un poste partagé : court.
    # L'application mobile est sur le téléphone du relais : long, sinon il se
    # reconnecte à chaque cas et finit par noter son mot de passe quelque part.
    actor_session_ttl_web: int = 8 * 60 * 60
    actor_session_ttl_mobile: int = 30 * 24 * 60 * 60

    # Site neutre vers lequel renvoie le bouton "Quitter vite".
    quick_exit_url: str = "https://www.google.com"

    default_lang: str = "fr"
    languages: list[str] = ["fr", "mos", "dyu", "en", "pt", "ar"]
    # Langues écrites de droite à gauche : le HTML reçoit dir="rtl".
    rtl_languages: list[str] = ["ar"]

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

    # --- SMS (Africa's Talking) ---
    # "sandbox" pour les tests, sinon le nom d'utilisateur du compte live.
    at_username: str = ""
    # Clé API : Africa's Talking > Settings > API Key.
    at_api_key: str = ""
    # Expéditeur affiché : shortcode loué ou sender ID alphanumérique validé.
    # Vide = numéro partagé de l'opérateur (suffisant en sandbox).
    at_sender_id: str = ""
    # Jeton inventé par vous, ajouté en query string de l'URL de callback
    # déclarée chez Africa's Talking. Leur webhook n'est pas signé : sans ce
    # jeton, n'importe qui peut poster de faux SMS entrants.
    sms_webhook_token: str = ""

    @property
    def at_base_url(self) -> str:
        host = "api.sandbox.africastalking.com" if self.at_username == "sandbox" else "api.africastalking.com"
        return f"https://{host}/version1/messaging"

    @property
    def sms_enabled(self) -> bool:
        return bool(self.at_username and self.at_api_key)

    # Sel pour hacher les numéros de téléphone (clé de session du bot). Le numéro
    # en clair n'est jamais stocké : seul le hash vit en mémoire ~15 min.
    bot_phone_salt: str = "change-me-too"
    bot_session_ttl: int = 15 * 60


settings = Settings()
