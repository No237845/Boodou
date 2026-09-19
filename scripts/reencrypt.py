"""Rechiffre les signalements de l'ancien schéma (sealed box) avec la clé serveur.

    REPORT_PRIVATE_KEY=... python -m scripts.reencrypt

À lancer UNE fois après la refonte, sur le serveur, avec l'ancienne clé privée
(celle qui était chez l'organisation partenaire) dans l'environnement. Les
signalements déjà au nouveau format sont ignorés ; ceux que l'ancienne clé ne
sait pas ouvrir sont laissés tels quels et comptés.

Nécessite REPORT_SECRET_KEY dans .env (clé du nouveau schéma).
"""

import os
import sys

from sqlalchemy import select

from app import crypto
from app.db import SessionLocal
from app.models import Report


def main() -> None:
    private_key = os.environ.get("REPORT_PRIVATE_KEY")
    if not private_key:
        sys.exit("REPORT_PRIVATE_KEY manquante dans l'environnement.")
    done = skipped = failed = 0
    with SessionLocal() as db:
        for r in db.execute(select(Report)).scalars():
            if not crypto.is_legacy(r.ciphertext):
                skipped += 1
                continue
            try:
                r.ciphertext = crypto.encrypt(crypto.legacy_decrypt(r.ciphertext, private_key))
                done += 1
            except Exception:  # noqa: BLE001 — on compte, on ne s'arrête pas
                failed += 1
        db.commit()
    print(f"Rechiffrés : {done} · déjà au nouveau format : {skipped} · illisibles : {failed}")


if __name__ == "__main__":
    main()
