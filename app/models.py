import enum
import secrets
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class ReportType(str, enum.Enum):
    """Famille de signalement. Le détail est dans `ReportSubtype`."""

    GBV = "GBV"            # Violences basées sur le genre
    SECURITE = "SECURITE"  # Violence, menace, attaque


class ReportSubtype(str, enum.Enum):
    # --- VBG : les six types de cas retenus par les acteurs de terrain ---
    VIOL = "VIOL"
    AGRESSION_SEXUELLE = "AGRESSION_SEXUELLE"
    AGRESSION_PHYSIQUE = "AGRESSION_PHYSIQUE"
    MARIAGE_FORCE = "MARIAGE_FORCE"
    DENI_RESSOURCES = "DENI_RESSOURCES"                # déni de ressources, d'opportunités ou de services
    VIOLENCE_PSYCHOLOGIQUE = "VIOLENCE_PSYCHOLOGIQUE"  # violences psychologiques / émotionnelles
    # --- Sécurité : les anciens types de premier niveau, conservés tels quels
    # pour que les signalements et l'annuaire existants restent valides ---
    VIOLENCE = "VIOLENCE"
    MENACE = "MENACE"
    TERRORISME = "TERRORISME"


SUBTYPES: dict[ReportType, list[ReportSubtype]] = {
    ReportType.GBV: [
        ReportSubtype.VIOL,
        ReportSubtype.AGRESSION_SEXUELLE,
        ReportSubtype.AGRESSION_PHYSIQUE,
        ReportSubtype.MARIAGE_FORCE,
        ReportSubtype.DENI_RESSOURCES,
        ReportSubtype.VIOLENCE_PSYCHOLOGIQUE,
    ],
    ReportType.SECURITE: [ReportSubtype.VIOLENCE, ReportSubtype.MENACE, ReportSubtype.TERRORISME],
}


def type_of(subtype: ReportSubtype) -> ReportType:
    return next(t for t, subs in SUBTYPES.items() if subtype in subs)


class Channel(str, enum.Enum):
    WEB = "WEB"
    WHATSAPP = "WHATSAPP"
    SMS = "SMS"
    MOBILE = "MOBILE"  # application mobile


class ReportStatus(str, enum.Enum):
    """Où en est le signalement. C'est la seule chose que l'utilisateur peut relire."""

    RECU = "RECU"                      # arrivé, personne ne l'a encore traité
    TRANSMIS = "TRANSMIS"              # un relais / point focal l'a relu et transmis à un acteur de prise en charge
    PRIS_EN_CHARGE = "PRIS_EN_CHARGE"  # l'action sociale ou un gestionnaire de cas s'en occupe
    REGLE = "REGLE"                    # dossier réglé


class ActorRole(str, enum.Enum):
    """Qui intervient sur un signalement, et dans quel ordre.

    Usager -> RELAIS (village / commune) -> ACTION_SOCIALE ou GESTIONNAIRE.
    Le POINT_FOCAL voit tous les cas VBG de sa région, les reformule et les
    dispatche. L'usager peut aussi écrire directement à l'action sociale.
    """

    RELAIS = "RELAIS"                  # relais communautaire (bénévole du village)
    POINT_FOCAL = "POINT_FOCAL"        # point focal VBG : relit, reformule, oriente
    ACTION_SOCIALE = "ACTION_SOCIALE"  # acteur étatique
    GESTIONNAIRE = "GESTIONNAIRE"      # gestionnaire de cas (ONG : HCR, UNICEF…)


# Vers qui chaque rôle peut transmettre un signalement. L'action sociale et
# les gestionnaires de cas ne relaient pas : ils traitent, et ne voient donc
# ni « transmettre », ni « reformuler », ni « saisir un cas ».
FORWARD_TARGETS: dict[ActorRole, list[ActorRole]] = {
    ActorRole.RELAIS: [ActorRole.POINT_FOCAL, ActorRole.ACTION_SOCIALE, ActorRole.GESTIONNAIRE],
    ActorRole.POINT_FOCAL: [ActorRole.ACTION_SOCIALE, ActorRole.GESTIONNAIRE],
    ActorRole.ACTION_SOCIALE: [],
    ActorRole.GESTIONNAIRE: [],
}

# Rôles qui prennent en charge et règlent (ils ont le « dashboard partenaire »).
# Eux seuls changent le statut d'un signalement.
CASE_HANDLERS = {ActorRole.ACTION_SOCIALE, ActorRole.GESTIONNAIRE}

# Rôles qui ne font que relayer : ils ne touchent pas au statut, mais sont
# tenus de reformuler clairement la plainte avant de la transmettre, pour
# qu'elle soit bien prise en charge.
MUST_SUMMARIZE = {ActorRole.RELAIS, ActorRole.POINT_FOCAL}

# Destinataires qu'un usager peut choisir sans passer par une personne nommée.
PUBLIC_TARGET_ROLES = {ActorRole.ACTION_SOCIALE}


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


# native_enum=False partout : stocké en VARCHAR plutôt qu'en type PostgreSQL.
# Un type natif ne peut pas perdre une valeur, et en ajouter une demande une
# instruction hors transaction : c'est incompatible avec des migrations rejouées
# au démarrage sur une base déjà peuplée (voir migrations.py).
def _enum(cls, length: int):
    return Enum(cls, native_enum=False, length=length)


class Actor(Base):
    """Compte d'un acteur du circuit : relais, point focal, action sociale, gestionnaire.

    Rattaché à une région et, pour un relais, à une commune : c'est ce qui
    décide quels signalements il voit. `name` est le nom affiché à l'usager qui
    choisit sa personne ressource — pas de nom de famille obligatoire.
    """

    __tablename__ = "actors"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[ActorRole] = mapped_column(_enum(ActorRole, 20), nullable=False)
    # Structure de rattachement : "Action sociale de Kaya", "HCR", "UNICEF", "Village de X"…
    organisation: Mapped[str | None] = mapped_column(String(128))
    region: Mapped[str] = mapped_column(String(64), nullable=False)
    commune: Mapped[str | None] = mapped_column(String(64))
    # Facultatif. S'il est renseigné pour un relais, l'usager le voit : c'est le
    # but d'une personne ressource, qu'on puisse la joindre.
    phone: Mapped[str | None] = mapped_column(String(32))
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ActorToken(Base):
    """Session d'un acteur : cookie (espace web) ou Bearer (application mobile).

    Seul le hash du jeton est en base : une fuite de la table ne donne aucune
    session utilisable.
    """

    __tablename__ = "actor_tokens"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey("actors.id", ondelete="CASCADE"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    actor: Mapped[Actor] = relationship()


class Report(Base):
    """Signalement anonyme. Métadonnées en clair, récit chiffré au repos."""

    __tablename__ = "reports"

    # Sert aussi de code de suivi : c'est le seul lien entre la personne qui a
    # signalé et son signalement, et il n'est écrit nulle part ailleurs.
    id: Mapped[str] = mapped_column(String(24), primary_key=True, default=_report_id)
    type: Mapped[ReportType] = mapped_column(_enum(ReportType, 16), nullable=False)
    # Nullable : les signalements d'avant la refonte n'en ont pas tous un.
    subtype: Mapped[ReportSubtype | None] = mapped_column(_enum(ReportSubtype, 32))
    region: Mapped[str] = mapped_column(String(64), nullable=False)
    commune: Mapped[str | None] = mapped_column(String(64))
    # Description chiffrée (voir crypto.py). Déchiffrée uniquement pour les
    # acteurs autorisés, jamais renvoyée au suivi public.
    ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[Channel] = mapped_column(_enum(Channel, 16), nullable=False, default=Channel.WEB)
    lang: Mapped[str] = mapped_column(String(8), nullable=False, default="fr")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    # Renseigné quand un relais saisit lui-même le cas d'une personne venue le voir.
    created_by: Mapped[int | None] = mapped_column(ForeignKey("actors.id"))

    # --- Routage ---
    # Soit une personne précise (assignee_id), soit n'importe quel acteur d'un
    # rôle dans la zone (target_role, assignee_id vide).
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("actors.id"))
    target_role: Mapped[ActorRole | None] = mapped_column(_enum(ActorRole, 20))

    # --- Reformulation ---
    # Récit reformulé par le point focal ou le relais avant transmission.
    # Chiffré comme la description : même sensibilité.
    summary_ciphertext: Mapped[str | None] = mapped_column(Text)
    summary_by: Mapped[int | None] = mapped_column(ForeignKey("actors.id"))
    summary_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # --- Suivi ---
    status: Mapped[ReportStatus] = mapped_column(_enum(ReportStatus, 16), nullable=False, default=ReportStatus.RECU)
    # Message court du partenaire vers la personne qui a signalé. EN CLAIR en base :
    # le serveur doit pouvoir l'afficher sur la page de suivi. Jamais d'information
    # identifiante ici — l'interface partenaire le rappelle.
    partner_note: Mapped[str | None] = mapped_column(String(PARTNER_NOTE_MAX))
    status_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    assignee: Mapped[Actor | None] = relationship(foreign_keys=[assignee_id])
    summary_author: Mapped[Actor | None] = relationship(foreign_keys=[summary_by])
    creator: Mapped[Actor | None] = relationship(foreign_keys=[created_by])
    events: Mapped[list["ReportEvent"]] = relationship(
        back_populates="report", order_by="ReportEvent.created_at", cascade="all, delete-orphan"
    )


class EventKind(str, enum.Enum):
    CREATED = "CREATED"
    FORWARDED = "FORWARDED"
    STATUS = "STATUS"


class ReportEvent(Base):
    """Trace de qui a fait quoi sur un signalement. Sert aux acteurs, pas au public."""

    __tablename__ = "report_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[str] = mapped_column(ForeignKey("reports.id", ondelete="CASCADE"), nullable=False)
    kind: Mapped[EventKind] = mapped_column(_enum(EventKind, 16), nullable=False)
    # Vide quand c'est l'usager (anonyme) qui agit.
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("actors.id"))
    to_actor_id: Mapped[int | None] = mapped_column(ForeignKey("actors.id"))
    to_role: Mapped[ActorRole | None] = mapped_column(_enum(ActorRole, 20))
    status: Mapped[ReportStatus | None] = mapped_column(_enum(ReportStatus, 16))
    # Commentaire interne entre acteurs (ex. « urgent, mineure »). En clair,
    # donc même consigne que partner_note : rien d'identifiant.
    note: Mapped[str | None] = mapped_column(String(PARTNER_NOTE_MAX))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    report: Mapped[Report] = relationship(back_populates="events")
    actor: Mapped[Actor | None] = relationship(foreign_keys=[actor_id])
    to_actor: Mapped[Actor | None] = relationship(foreign_keys=[to_actor_id])


class Translation(Base):
    """Cache des traductions à la volée (app/api_ai/translate_cache.py).

    Une ligne par (texte source, langue source, langue cible), identifiée par
    un hachage. `output` NULL = la traduction a été jugée non fiable : on
    affiche le texte source, et on ne réessaie pas. N'y entrent que des textes
    publics ou destinés à la personne (annuaire, note d'un point focal) —
    jamais le récit d'un signalement.
    """

    __tablename__ = "translations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    src_lang: Mapped[str] = mapped_column(String(8), nullable=False)
    tgt_lang: Mapped[str] = mapped_column(String(8), nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    output: Mapped[str | None] = mapped_column(Text)
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
    # Types ou sous-types d'incident pour lesquels la ressource est pertinente :
    # "GBV,VIOLENCE", "SECURITE" ou "*". Les codes de sous-type sécurité
    # (VIOLENCE, MENACE, TERRORISME) sont ceux de l'ancien annuaire, inchangés.
    for_types: Mapped[str] = mapped_column(String(64), default="*")
    notes: Mapped[str | None] = mapped_column(Text)
    verified: Mapped[bool] = mapped_column(default=False)

    def matches(
        self,
        type_: ReportType | None,
        region: str | None,
        subtype: ReportSubtype | None = None,
    ) -> bool:
        ok_region = self.region == "*" or region is None or self.region == region
        if self.for_types == "*" or type_ is None:
            return ok_region
        tokens = set(self.for_types.split(","))
        if type_.value in tokens:
            return ok_region
        if subtype is not None:
            return ok_region and subtype.value in tokens
        # Type sans sous-type (annuaire filtré par famille) : une fiche qui
        # couvre au moins un sous-type de la famille est pertinente.
        return ok_region and any(s.value in tokens for s in SUBTYPES[type_])
