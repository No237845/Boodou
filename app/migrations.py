"""Micro-migrations idempotentes, jouées au démarrage.

`Base.metadata.create_all` ne crée que les tables absentes : il n'ajoute jamais
une colonne à une table qui existe déjà. La base est un PostgreSQL hébergé,
déjà peuplé de signalements — on ajoute donc les nouvelles colonnes à la main.

Chaque instruction doit pouvoir être rejouée sans effet : le serveur redémarre
à chaque déploiement.
"""

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from .models import PARTNER_NOTE_MAX, ReportStatus

log = logging.getLogger("app")

STATEMENTS = [
    # Suivi des signalements (chantier « fermer la boucle de confiance »).
    f"ALTER TABLE reports ADD COLUMN IF NOT EXISTS status VARCHAR(16) "
    f"NOT NULL DEFAULT '{ReportStatus.RECU.value}'",
    f"ALTER TABLE reports ADD COLUMN IF NOT EXISTS partner_note VARCHAR({PARTNER_NOTE_MAX})",
    "ALTER TABLE reports ADD COLUMN IF NOT EXISTS status_at TIMESTAMPTZ",
]


def run(engine: Engine) -> None:
    # Une transaction par instruction : sous PostgreSQL, une erreur avorte toute
    # la transaction en cours et ferait échouer les instructions suivantes.
    for statement in STATEMENTS:
        try:
            with engine.begin() as conn:
                conn.execute(text(statement))
        except Exception as e:  # noqa: BLE001 — un échec ici ne doit pas bloquer le démarrage
            log.warning("Migration ignorée (%s…) : %s", statement[:60], e)
