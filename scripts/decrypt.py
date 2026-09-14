"""Déchiffre un export de signalements, côté organisation partenaire.

    # 1. Exporter depuis le serveur (métadonnées + descriptions chiffrées)
    curl -H "X-Admin-Key: $ADMIN_KEY" https://<serveur>/admin/reports > reports.json

    # 2. Déchiffrer localement avec la clé privée
    REPORT_PRIVATE_KEY=... python -m scripts.decrypt reports.json

Sortie : un JSON avec les descriptions en clair, sur stdout.
"""

import json
import os
import sys

from app.crypto import decrypt


def main(path: str) -> None:
    private_key = os.environ.get("REPORT_PRIVATE_KEY")
    if not private_key:
        sys.exit("REPORT_PRIVATE_KEY manquante dans l'environnement.")
    # utf-8-sig : tolère le BOM ajouté par PowerShell / Notepad.
    with open(path, encoding="utf-8-sig") as f:
        reports = json.load(f)
    for r in reports:
        r["description"] = decrypt(r.pop("ciphertext"), private_key)
    json.dump(reports, sys.stdout, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage : python -m scripts.decrypt reports.json")
    main(sys.argv[1])
