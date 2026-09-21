"""Traduction FR -> Mooré via l'API Burkimbia.

Deux usages, même client :
- hors ligne, `scripts/translate_locales.py` remplit mos.json (interface) ;
- en production, le contenu qui n'est pas dans les fichiers de langue
  (annuaire, messages des acteurs) est traduit en tâche de fond et mis en
  cache (`translate_cache.py`) ; en attendant, ou si l'API est absente ou en
  panne, il reste en français.

Ce qui part chez Burkimbia : du texte d'interface, l'annuaire, les messages
écrits par un point focal à la personne. Jamais le récit d'un signalement.

L'API a deux défauts mesurés qui imposent de prétraiter chaque texte :
- les retours à la ligne sont écrasés (un menu « 1 - … » sur trois lignes
  revient sur une seule) : on traduit ligne par ligne ;
- les placeholders `{phone}` sont parfois « traduits » (`{telefõ]`) : on les
  remplace par des nombres-sentinelles que le modèle recopie tels quels.
Toute sortie suspecte (chiffre perdu, répétition, balise cassée) est REJETÉE :
pour un service de signalement, une traduction fausse est pire que le français.
"""

import logging
import re
from collections.abc import Callable

import httpx

from ..config import settings

log = logging.getLogger("translate")

API_URL = "https://api.burkimbia.com/api/v1/translate"
TIMEOUT = 30.0

# Codes du site -> noms de langues attendus par l'API. Testé le 2026-09-19 :
# seul français <-> mooré répond ; dioula et anglais rendent une erreur 500.
# dyu.json reste donc à traduire à la main, et le contenu dynamique reste en
# français pour ces deux langues.
LANG_CODES = {"fr": "french", "mos": "moore"}

# Préfixe d'une ligne de menu ("1 - ", "99 - ", "• ") : conservé tel quel.
_PREFIX = re.compile(r"^(\s*(?:\d+\s*-\s*|[•\-]\s+))")
# Emojis / symboles en tête de ligne (✅ ⚠️ 🔒 📞 …) : conservés tel quel.
# Sauf `{` (placeholder) et `*` / `_` (balises WhatsApp), traités plus loin.
_LEADING_SYMBOLS = re.compile(r"^([^\w\s{*_]+\s*)", re.UNICODE)
# Placeholders str.format : remplacés par un nombre, que le modèle recopie.
_PLACEHOLDER = re.compile(r"\{(\w+)\}")
_PLACEHOLDER_ONLY = re.compile(r"^\s*\{\w+\}\s*$")
# Artefacts de dictionnaire vus dans les sorties des modèles.
_GARBAGE = ("expression:", "v.inaccompli", "v.accompli", "interrogatif", "[ã-ê]", "adverbe", "adjectif", "nom:", "verbe:")
_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)
_LETTERS = re.compile(r"[A-Za-zÀ-ÿ]")


class Rejected(Exception):
    """Traduction jugée non fiable : on garde le français."""


class TranslateUnavailable(Exception):
    """Pas de clé, ou service en panne : on garde le français.

    `quota` = la clé a épuisé son quota (HTTP 429) : inutile de réessayer
    avant un bon moment.
    """

    def __init__(self, why: str, quota: bool = False) -> None:
        super().__init__(why)
        self.quota = quota


def enabled() -> bool:
    return bool(settings.burkimbia_api_key)


def supported(src: str, tgt: str) -> bool:
    return src != tgt and src in LANG_CODES and tgt in LANG_CODES


# --- Garde-fous -------------------------------------------------------------


def check(src: str, out: str) -> None:
    """Rejette les sorties suspectes plutôt que de livrer un contresens."""
    if not out.strip():
        raise Rejected("sortie vide")
    low = out.lower()
    if any(g in low for g in _GARBAGE):
        raise Rejected("artefact de dictionnaire")
    words = _WORD.findall(low)
    if len(words) >= 3 and any(words[i] == words[i + 1] == words[i + 2] for i in range(len(words) - 2)):
        raise Rejected("répétition")
    if len(set(words)) < len(words) / 3 and len(words) >= 6:
        raise Rejected("répétition")
    # Chiffres (numéros d'urgence, options de menu) : tous doivent survivre.
    for num in re.findall(r"\d+", src):
        if num not in out:
            raise Rejected(f"nombre {num} perdu")
    n_src = len(_WORD.findall(src))
    if n_src >= 5 and len(words) < 0.3 * n_src:
        raise Rejected(f"trop court ({len(words)} mots pour {n_src})")
    # Balises markdown WhatsApp (*gras*, _italique_) : doivent rester appariées.
    for mark in "*_":
        if src.count(mark) != out.count(mark):
            raise Rejected(f"balise {mark} perdue")


def _split_line(line: str) -> tuple[str, str, str, list[str]] | None:
    """Sépare une ligne en (préfixe, balise, texte à traduire, placeholders).

    None = rien à traduire (ligne vide, placeholder seul, chiffres seuls).
    """
    if not line.strip() or _PLACEHOLDER_ONLY.match(line):
        return None
    prefix = ""
    m = _PREFIX.match(line)
    if m:
        prefix, line = m.group(1), line[m.end():]
    m = _LEADING_SYMBOLS.match(line)
    if m and m.group(1).strip():
        prefix, line = prefix + m.group(1), line[m.end():]
    if not line.strip():
        return None

    # Markdown WhatsApp : *gras* / _italique_ qui englobe toute la ligne.
    wrap = ""
    if len(line) > 2 and line[0] == line[-1] and line[0] in "*_":
        wrap, line = line[0], line[1:-1]

    names: list[str] = []

    def _swap(mm: re.Match) -> str:
        names.append(mm.group(1))
        return str(9000 + len(names))

    text = _PLACEHOLDER.sub(_swap, line)
    if not _LETTERS.search(text):
        return None
    return prefix, wrap, text, names


def _join_line(prefix: str, wrap: str, translated: str, names: list[str]) -> str:
    for i, name in enumerate(names, start=1):
        if str(9000 + i) not in translated:
            raise Rejected(f"placeholder {{{name}}} perdu")
        translated = translated.replace(str(9000 + i), "{" + name + "}")
    return prefix + wrap + translated + wrap


def _check_menu(src: str, out: list[str]) -> None:
    """Options de menu : deux choix différents en FR ne doivent pas se confondre."""
    src_opts = [_PREFIX.sub("", l).strip() for l in src.split("\n") if _PREFIX.match(l)]
    out_opts = [_PREFIX.sub("", l).strip() for l in out if _PREFIX.match(l)]
    if len(set(src_opts)) == len(src_opts) and len(set(out_opts)) < len(out_opts):
        raise Rejected("deux options de menu traduites à l'identique")


def translate_with(text: str, sentence: Callable[[str], str]) -> str:
    """Traduit un texte ligne par ligne avec n'importe quel moteur synchrone.

    `sentence` reçoit une ligne nettoyée et rend sa traduction. Lève Rejected.
    """
    out: list[str] = []
    for line in text.split("\n"):
        parts = _split_line(line)
        if parts is None:
            out.append(line)
            continue
        prefix, wrap, core, names = parts
        translated = sentence(core).strip()
        check(core, translated)
        out.append(_join_line(prefix, wrap, translated, names))
    _check_menu(text, out)
    return "\n".join(out)


# --- Client Burkimbia ------------------------------------------------------


def _payload(text: str, src: str, tgt: str) -> tuple[dict, dict]:
    if not enabled():
        raise TranslateUnavailable("disabled")
    if not supported(src, tgt):
        raise TranslateUnavailable(f"paire {src}->{tgt} non gérée")
    headers = {"X-API-Key": settings.burkimbia_api_key}
    body = {"text": text, "src_lang": LANG_CODES[src], "tgt_lang": LANG_CODES[tgt], "model": settings.burkimbia_model}
    return headers, body


def _output(r: httpx.Response) -> str:
    if r.status_code != 200:
        raise TranslateUnavailable(f"HTTP {r.status_code}: {r.text[:200]}", quota=r.status_code == 429)
    out = r.json().get("output")
    if not isinstance(out, str):
        raise TranslateUnavailable("réponse sans champ output")
    return out


def sentence_sync(text: str, src: str = "fr", tgt: str = "mos") -> str:
    """Un appel API, une phrase. Pour le script hors ligne."""
    headers, body = _payload(text, src, tgt)
    try:
        return _output(httpx.post(API_URL, headers=headers, json=body, timeout=TIMEOUT))
    except httpx.HTTPError as e:
        raise TranslateUnavailable(str(e)) from e


def translate_sync(text: str, src: str = "fr", tgt: str = "mos") -> str:
    """Texte complet via Burkimbia. Lève TranslateUnavailable ou Rejected.

    Bloquant (2 à 4 s par ligne) : à appeler depuis le script ou le fil de
    fond de `translate_cache`, jamais dans une requête.
    """
    return translate_with(text, lambda s: sentence_sync(s, src, tgt))
