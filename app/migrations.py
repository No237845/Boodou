"""Migrations jouées au démarrage, une seule fois chacune.

`Base.metadata.create_all` ne crée que les tables absentes : il n'ajoute jamais
une colonne à une table qui existe déjà, ni ne convertit des données. La base
est un PostgreSQL déjà peuplé de signalements — on fait donc le reste ici.

Chaque migration a un nom, inscrit dans `schema_migrations` une fois passée :
les instructions qui transforment des données (« TRANSMIS devient
PRIS_EN_CHARGE ») ne doivent surtout pas être rejouées à chaque redémarrage.
Les instructions elles-mêmes restent idempotentes autant que possible, pour
qu'une migration interrompue puisse repartir.
"""

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from .models import PARTNER_NOTE_MAX, ActorRole, ReportStatus, ReportType

log = logging.getLogger("app")

MIGRATIONS: list[tuple[str, list[str]]] = [
    (
        # Suivi des signalements (chantier « fermer la boucle de confiance »).
        "001_suivi",
        [
            f"ALTER TABLE reports ADD COLUMN IF NOT EXISTS status VARCHAR(16) "
            f"NOT NULL DEFAULT '{ReportStatus.RECU.value}'",
            f"ALTER TABLE reports ADD COLUMN IF NOT EXISTS partner_note VARCHAR({PARTNER_NOTE_MAX})",
            "ALTER TABLE reports ADD COLUMN IF NOT EXISTS status_at TIMESTAMPTZ",
        ],
    ),
    (
        # Circuit VBG : sous-types, acteurs, routage, reformulation, nouveaux statuts.
        "002_circuit_vbg",
        [
            # Les colonnes enum natives deviennent du VARCHAR : on peut alors
            # ajouter et retirer des valeurs sans toucher au type PostgreSQL.
            "ALTER TABLE reports ALTER COLUMN type TYPE VARCHAR(16) USING type::text",
            "ALTER TABLE reports ALTER COLUMN channel TYPE VARCHAR(16) USING channel::text",
            "DROP TYPE IF EXISTS reporttype",
            "DROP TYPE IF EXISTS channel",
            "ALTER TABLE reports ADD COLUMN IF NOT EXISTS subtype VARCHAR(32)",
            "ALTER TABLE reports ADD COLUMN IF NOT EXISTS created_by INTEGER REFERENCES actors(id)",
            "ALTER TABLE reports ADD COLUMN IF NOT EXISTS assignee_id INTEGER REFERENCES actors(id)",
            "ALTER TABLE reports ADD COLUMN IF NOT EXISTS target_role VARCHAR(20)",
            "ALTER TABLE reports ADD COLUMN IF NOT EXISTS summary_ciphertext TEXT",
            "ALTER TABLE reports ADD COLUMN IF NOT EXISTS summary_by INTEGER REFERENCES actors(id)",
            "ALTER TABLE reports ADD COLUMN IF NOT EXISTS summary_at TIMESTAMPTZ",
            # Les anciens types de premier niveau deviennent des sous-types de SECURITE.
            "UPDATE reports SET subtype = type WHERE type IN ('VIOLENCE','MENACE','TERRORISME') AND subtype IS NULL",
            f"UPDATE reports SET type = '{ReportType.SECURITE.value}' WHERE type IN ('VIOLENCE','MENACE','TERRORISME')",
            # Anciens statuts : TRANSMIS voulait dire « un partenaire s'en occupe »,
            # CLOTURE « terminé ». Dans le nouveau circuit, TRANSMIS est une étape
            # intermédiaire (relais -> acteur) : on remappe pour ne pas mentir à
            # la personne qui consulte son code.
            f"UPDATE reports SET status = '{ReportStatus.PRIS_EN_CHARGE.value}' WHERE status = 'TRANSMIS'",
            f"UPDATE reports SET status = '{ReportStatus.REGLE.value}' WHERE status = 'CLOTURE'",
            # Les signalements existants n'ont pas de destinataire : ils vont dans
            # la boîte du rôle par défaut de leur zone.
            f"UPDATE reports SET target_role = CASE WHEN type = '{ReportType.GBV.value}' "
            f"THEN '{ActorRole.POINT_FOCAL.value}' ELSE '{ActorRole.ACTION_SOCIALE.value}' END "
            f"WHERE target_role IS NULL AND assignee_id IS NULL",
        ],
    ),
]


def run(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(
            text("CREATE TABLE IF NOT EXISTS schema_migrations (name VARCHAR(64) PRIMARY KEY, applied_at TIMESTAMPTZ DEFAULT now())")
        )
        applied = {row[0] for row in conn.execute(text("SELECT name FROM schema_migrations"))}

    for name, statements in MIGRATIONS:
        if name in applied:
            continue
        ok = True
        # Une transaction par instruction : sous PostgreSQL, une erreur avorte toute
        # la transaction en cours et ferait échouer les instructions suivantes.
        for statement in statements:
            try:
                with engine.begin() as conn:
                    conn.execute(text(statement))
            except Exception as e:  # noqa: BLE001 — un échec ici ne doit pas bloquer le démarrage
                ok = False
                log.warning("Migration %s : instruction ignorée (%s…) : %s", name, statement[:60], e)
        if ok:
            with engine.begin() as conn:
                conn.execute(text("INSERT INTO schema_migrations (name) VALUES (:n)"), {"n": name})
            log.info("Migration %s appliquée.", name)
        else:
            log.error("Migration %s incomplète : elle sera rejouée au prochain démarrage.", name)
