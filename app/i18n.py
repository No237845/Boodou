"""Traductions FR / Mooré (mos) / Dioula (dyu) / Anglais (en).

Chaque langue est un JSON plat dans app/locales/. Une clé absente dans une
langue retombe sur le français, pour que l'interface reste toujours complète.
"""

import json
from functools import lru_cache

from .config import BASE_DIR, settings

LOCALES_DIR = BASE_DIR / "locales"

LANG_NAMES = {"fr": "Français", "mos": "Mooré", "dyu": "Dioula", "en": "English", "pt": "Português", "ar": "العربية"}


@lru_cache
def _load(lang: str) -> dict[str, str]:
    path = LOCALES_DIR / f"{lang}.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def t(lang: str, key: str, **kwargs: object) -> str:
    text = _load(lang).get(key) or _load(settings.default_lang).get(key) or key
    return text.format(**kwargs) if kwargs else text


def translator(lang: str):
    return lambda key, **kw: t(lang, key, **kw)


def normalize_lang(lang: str | None) -> str:
    return lang if lang in settings.languages else settings.default_lang
