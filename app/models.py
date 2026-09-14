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


class ResourceCategory(str, enum.Enum):
    SANTE = "SANTE"      # Santé / GBV
    JUSTICE = "JUSTICE"  # Police / Gendarmerie / justice communautaire
    ONG = "ONG"          # ONG / humanitaires
    URGENCE = "URGENCE"  # Numéros d'urgence nationaux


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _report_id() -> str:
    # Identifiant aléatoire non séquentiel : impossible d'estimer le volume
    # ou l'ordre des signalements depuis l'extérieur.
    return secrets.token_urlsafe(12)


class Report(Base):
    """Signalement anonyme. Seules des métadonnées grossières sont en clair."""

    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(24), primary_key=True, default=_report_id)
    type: Mapped[ReportType] = mapped_column(Enum(ReportType), nullable=False)
    region: Mapped[str] = mapped_column(String(64), nullable=False)
    commune: Mapped[str | None] = mapped_column(String(64))
    # Description chiffrée (sealed box libsodium, base64). Le serveur ne peut pas la lire.
    ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[Channel] = mapped_column(Enum(Channel), nullable=False, default=Channel.WEB)
    lang: Mapped[str] = mapped_column(String(8), nullable=False, default="fr")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


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
