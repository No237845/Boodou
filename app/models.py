import enum
import secrets
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class ReportType(str, enum.Enum):
    VIOLENCE = "VIOLENCE"
    MENACE = "MENACE"
    GBV = "GBV"
    TERRORISME = "TERRORISME"


class Channel(str, enum.Enum):
    WEB = "WEB"
    WHATSAPP = "WHATSAPP"
    SMS = "SMS"


class ReportStatus(str, enum.Enum):
    """Où en est le signalement. C'est la seule chose que l'utilisateur peut relire."""

    RECU = "RECU"          # arrivé sur le serveur, pas encore ouvert
    TRANSMIS = "TRANSMIS"  # un partenaire l'a lu et pris en charge
    CLOTURE = "CLOTURE"    # traité, ou sans suite


class ResourceCategory(str, enum.Enum):
    SANTE = "SANTE"      # Santé / GBV
    JUSTICE = "JUSTICE"  # Police / Gendarmerie / justice communautaire
    ONG = "ONG"          # ONG / humanitaires
    URGENCE = "URGENCE"  # Numéros d'urgence nationaux


def _now() -> datetime:
    return datetime.now(timezone.utc)


# Alphabet Crockford base32 : ni I, ni L, ni O, ni U. Personne ne confond un 1
# avec un I en recopiant un code sur un bout de papier ou en le dictant.
CODE_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
CODE_LENGTH = 10  # 50 bits : indevinable, même sans limitation de débit.

# Longueur max du message du partenaire vers la personne qui a signalé.
PARTNER_NOTE_MAX = 280


def _report_id() -> str:
    # Identifiant aléatoire non séquentiel : impossible d'estimer le volume ou
    # l'ordre des signalements depuis l'extérieur. Sert aussi de code de suivi.
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


def format_code(code: str) -> str:
    """`K7M3PQR8TZ` -> `K7M3P-QR8TZ` : deux groupes de 5, plus faciles à noter."""
    return f"{code[:5]}-{code[5:]}" if len(code) == CODE_LENGTH else code


def normalize_code(raw: str) -> str:
    """Nettoie un code saisi à la main.

    Tolère les minuscules, les espaces, les tirets, et applique les règles de
    lecture Crockford (I et L se lisent 1, O se lit 0) : quelqu'un qui recopie
    `k7m3p-qr8tz` ou `K7M3P QR8TZ` retrouve son signalement.
    """
    s = "".join(c for c in (raw or "").upper() if c.isalnum())
    return s.replace("I", "1").replace("L", "1").replace("O", "0")[:CODE_LENGTH]


class Report(Base):
    """Signalement anonyme. Seules des métadonnées grossières sont en clair."""

    __tablename__ = "reports"

    # Sert aussi de code de suivi : c'est le seul lien entre la personne qui a
    # signalé et son signalement, et il n'est écrit nulle part ailleurs.
    id: Mapped[str] = mapped_column(String(24), primary_key=True, default=_report_id)
    type: Mapped[ReportType] = mapped_column(Enum(ReportType), nullable=False)
    region: Mapped[str] = mapped_column(String(64), nullable=False)
    commune: Mapped[str | None] = mapped_column(String(64))
    # Description chiffrée (sealed box libsodium, base64). Le serveur ne peut pas la lire.
    ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[Channel] = mapped_column(Enum(Channel), nullable=False, default=Channel.WEB)
    lang: Mapped[str] = mapped_column(String(8), nullable=False, default="fr")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    # --- Suivi ---
    # native_enum=False : stocké en VARCHAR plutôt qu'en type PostgreSQL, ce qui
    # permet d'ajouter la colonne à une table déjà en production (voir migrations.py).
    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus, native_enum=False, length=16), nullable=False, default=ReportStatus.RECU
    )
    # Message court du partenaire vers la personne qui a signalé. EN CLAIR en base :
    # le serveur doit pouvoir l'afficher sur la page de suivi. Jamais d'information
    # identifiante ici — l'interface partenaire le rappelle.
    partner_note: Mapped[str | None] = mapped_column(String(PARTNER_NOTE_MAX))
    status_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Resource(Base):
    """Organisation / hotline / centre d'aide."""

    __tablename__ = "resources"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    category: Mapped[ResourceCategory] = mapped_column(Enum(ResourceCategory), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32))
    # "*" = couverture nationale, sinon nom de région.
    region: Mapped[str] = mapped_column(String(64), nullable=False, default="*")
    city: Mapped[str | None] = mapped_column(String(64))
    hours: Mapped[str | None] = mapped_column(String(64))
    # Langues parlées, séparées par des virgules : "fr,mos,dyu"
    languages: Mapped[str] = mapped_column(String(32), default="fr")
    # Types d'incident pour lesquels la ressource est pertinente : "GBV,VIOLENCE" ou "*"
    for_types: Mapped[str] = mapped_column(String(64), default="*")
    notes: Mapped[str | None] = mapped_column(Text)
    verified: Mapped[bool] = mapped_column(default=False)

    def matches(self, type_: ReportType | None, region: str | None) -> bool:
        ok_type = self.for_types == "*" or (type_ is not None and type_.value in self.for_types.split(","))
        ok_region = self.region == "*" or region is None or self.region == region
        return ok_type and ok_region
