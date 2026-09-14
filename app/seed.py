"""Charge l'annuaire des régions et des ressources dans la base.

Idempotent : les ressources existantes sont remplacées par le contenu de
app/data/resources.json à chaque démarrage.
"""

import json
from functools import lru_cache

from sqlalchemy import delete
from sqlalchemy.orm import Session

from .config import BASE_DIR
from .models import Resource, ResourceCategory

DATA_DIR = BASE_DIR / "data"


@lru_cache
def load_regions() -> list[dict]:
    return json.loads((DATA_DIR / "regions.json").read_text(encoding="utf-8"))["regions"]


def region_names() -> list[str]:
    return [r["name"] for r in load_regions()]


def communes_of(region: str) -> list[str]:
    return next((r["communes"] for r in load_regions() if r["name"] == region), [])


def seed_resources(db: Session) -> int:
    items = json.loads((DATA_DIR / "resources.json").read_text(encoding="utf-8"))["resources"]
    db.execute(delete(Resource))
    for item in items:
        db.add(
            Resource(
                name=item["name"],
                category=ResourceCategory(item["category"]),
                phone=item.get("phone"),
                region=item.get("region", "*"),
                city=item.get("city"),
                hours=item.get("hours"),
                languages=item.get("languages", "fr"),
                for_types=item.get("for_types", "*"),
                notes=item.get("notes"),
                verified=bool(item.get("verified", False)),
            )
        )
    db.commit()
    return len(items)
