"""Premier jet des traductions Mooré à partir de fr.json, via un modèle local.

Usage :
    python -m scripts.translate_locales            # traduit les clés manquantes de mos.json
    python -m scripts.translate_locales --force    # retraduit aussi les clés déjà auto-traduites
    python -m scripts.translate_locales --keys bot_menu bot_invalid

Le modèle (sawadogosalif/MooreFR-SaChi-translationv0, NLLB-200 600M fine-tuné
FR<->Mooré) tourne EN LOCAL : aucun texte ne quitte la machine. Il ne sert pas
en production ; il produit un brouillon que doit relire un locuteur natif.

Le modèle est faible sur les phrases longues et peut halluciner (répétitions,
artefacts de dictionnaire, chiffres perdus). Toute sortie suspecte est REJETÉE :
la clé reste absente (donc affichée en français) et va dans "_todo". Pour un
service de signalement, une traduction fausse est pire que le français.

Sortie :
- app/locales/mos.json : clés ajoutées, listées dans "_auto" tant qu'elles ne
  sont pas validées (retirer une clé de "_auto" une fois relue) ; "_todo" liste
  les clés à traduire à la main ;
- app/locales/mos_review.md : tableau FR / Mooré pour la relecture.

Dépendances : pip install -r requirements-ml.txt
"""

import argparse
import json
import re
import sys
from pathlib import Path

LOCALES = Path(__file__).resolve().parent.parent / "app" / "locales"
MODEL = "sawadogosalif/MooreFR-SaChi-translationv0"
SRC_LANG = "fra_Latn"
TGT_LANG_CANDIDATES = ("moor_Latn", "mos_Latn")

# Jamais traduites : nom de marque, ou déjà multilingues par construction.
SKIP_KEYS = {"app_name", "_note", "_auto", "bot_welcome"}

# Préfixe d'une ligne de menu ("1 - ", "99 - ", "• ") : conservé tel quel.
_PREFIX = re.compile(r"^(\s*(?:\d+\s*-\s*|[•\-]\s+))")
# Emojis / symboles en tête de ligne (✅ ⚠️ 🔒 📞 …) : conservés tel quel.
_LEADING_SYMBOLS = re.compile(r"^([\W_]+\s*)", re.UNICODE)
# Placeholders str.format : remplacés par un nombre, que le modèle recopie.
_PLACEHOLDER = re.compile(r"\{(\w+)\}")
_PLACEHOLDER_ONLY = re.compile(r"^\s*\{\w+\}\s*$")
# Artefacts de dictionnaire vus dans les sorties du modèle.
_GARBAGE = ("expression:", "v.inaccompli", "v.accompli", "interrogatif", "[ã-ê]", "adverbe", "adjectif", "nom:", "verbe:")
_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)


class Rejected(Exception):
    """Traduction jugée non fiable : on garde le français."""


def _check(src: str, out: str) -> None:
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


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _dump(path: Path, data: dict) -> None:
    # Métadonnées en fin de fichier, pour la lisibilité.
    meta = {k: data.pop(k) for k in ("_auto", "_todo") if k in data}
    data.update(meta)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class Translator:
    def __init__(self) -> None:
        try:
            import torch
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        except ImportError:
            sys.exit("Dépendances manquantes : pip install -r requirements-ml.txt")

        print(f"Chargement de {MODEL} (CPU)…", flush=True)
        self.tok = AutoTokenizer.from_pretrained(MODEL, src_lang=SRC_LANG)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(MODEL).eval()
        self.torch = torch
        unk = self.tok.unk_token_id
        for code in TGT_LANG_CANDIDATES:
            bos = self.tok.convert_tokens_to_ids(code)
            if bos != unk:
                self.bos, self.tgt = bos, code
                break
        else:
            sys.exit(f"Aucun code langue Mooré reconnu parmi {TGT_LANG_CANDIDATES}")
        print(f"Cible : {self.tgt}", flush=True)

    def sentence(self, text: str) -> str:
        with self.torch.no_grad():
            inputs = self.tok(text, return_tensors="pt", truncation=True, max_length=256)
            out = self.model.generate(
                **inputs,
                forced_bos_token_id=self.bos,
                num_beams=5,
                max_new_tokens=128,
                repetition_penalty=1.3,
                no_repeat_ngram_size=3,
            )
        result = self.tok.batch_decode(out, skip_special_tokens=True)[0].strip()
        _check(text, result)
        return result

    def line(self, line: str) -> str:
        """Traduit une ligne en préservant préfixe de menu, symboles, placeholders et *gras*."""
        if not line.strip() or _PLACEHOLDER_ONLY.match(line):
            return line
        prefix = ""
        m = _PREFIX.match(line)
        if m:
            prefix, line = m.group(1), line[m.end():]
        m = _LEADING_SYMBOLS.match(line)
        if m and m.group(1).strip():
            prefix, line = prefix + m.group(1), line[m.end():]
        if not line.strip():
            return prefix + line

        # Markdown WhatsApp : *gras* / _italique_ qui englobe toute la ligne.
        wrap = ""
        if len(line) > 2 and line[0] == line[-1] and line[0] in "*_":
            wrap, line = line[0], line[1:-1]

        # Placeholders -> nombres sentinelles (recopiés tels quels par le modèle).
        names: list[str] = []

        def _swap(mm: re.Match) -> str:
            names.append(mm.group(1))
            return str(9000 + len(names))

        text = _PLACEHOLDER.sub(_swap, line)
        if not re.search(r"[A-Za-zÀ-ÿ]", text):
            return prefix + wrap + line + wrap  # que des chiffres/ponctuation

        translated = self.sentence(text)
        for i, name in enumerate(names, start=1):
            if str(9000 + i) not in translated:
                raise Rejected(f"placeholder {{{name}}} perdu")
            translated = translated.replace(str(9000 + i), "{" + name + "}")
        return prefix + wrap + translated + wrap

    def text(self, text: str) -> str:
        out = [self.line(l) for l in text.split("\n")]
        # Options de menu : deux choix différents en FR ne doivent pas se confondre.
        src_opts = [_PREFIX.sub("", l).strip() for l in text.split("\n") if _PREFIX.match(l)]
        out_opts = [_PREFIX.sub("", l).strip() for l in out if _PREFIX.match(l)]
        if len(set(src_opts)) == len(src_opts) and len(set(out_opts)) < len(out_opts):
            raise Rejected("deux options de menu traduites à l'identique")
        return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lang", default="mos", help="langue cible (défaut : mos)")
    ap.add_argument("--force", action="store_true", help="retraduit aussi les clés déjà dans _auto")
    ap.add_argument("--keys", nargs="*", help="ne traiter que ces clés")
    args = ap.parse_args()

    fr = _load(LOCALES / "fr.json")
    target_path = LOCALES / f"{args.lang}.json"
    target = _load(target_path)
    auto: list[str] = list(target.get("_auto", []))
    manual: list[str] = list(target.get("_todo", []))

    if args.keys:
        todo = [k for k in args.keys if k in fr]
    else:
        todo = [
            k for k in fr
            if k not in SKIP_KEYS and (k not in target or (args.force and (k in auto or k in manual)))
        ]
    if not todo:
        print("Rien à traduire.")
        return

    tr = Translator()
    n_ok = n_rejected = 0
    for i, key in enumerate(todo, start=1):
        try:
            result = tr.text(fr[key])
        except Rejected as why:
            # On retire toute version auto précédente : mieux vaut le français.
            if key in auto:
                target.pop(key, None)
                auto.remove(key)
            if key not in manual:
                manual.append(key)
            n_rejected += 1
            print(f"[{i}/{len(todo)}] {key} : REJETÉ ({why}) -> à traduire à la main", flush=True)
        else:
            target[key] = result
            if key not in auto:
                auto.append(key)
            if key in manual:
                manual.remove(key)
            n_ok += 1
            print(f"[{i}/{len(todo)}] {key}\n  FR : {fr[key][:70]!r}\n  {args.lang.upper()}: {result[:70]!r}", flush=True)
        # Sauvegarde incrémentale : un Ctrl+C ne perd pas le travail déjà fait.
        target["_auto"], target["_todo"] = auto, manual
        _dump(target_path, target)

    review = [
        f"# Relecture {args.lang} — traductions automatiques à valider\n\n",
        "Généré par `scripts/translate_locales.py`. Corriger directement dans "
        f"`app/locales/{args.lang}.json`, puis retirer la clé de `_auto`.\n",
    ]
    for key in auto:
        review.append(f"\n## `{key}`\n\n**FR**\n\n```\n{fr.get(key, '')}\n```\n\n**{args.lang.upper()}**\n\n```\n{target[key]}\n```\n")
    if manual:
        review.append("\n---\n\n# À traduire à la main (le modèle n'a pas donné de résultat fiable)\n")
        for key in manual:
            review.append(f"\n## `{key}`\n\n```\n{fr.get(key, '')}\n```\n")
    (LOCALES / f"{args.lang}_review.md").write_text("".join(review), encoding="utf-8")
    print(f"\n{n_ok} traduite(s), {n_rejected} rejetée(s) -> {target_path.name} ; relecture : {args.lang}_review.md")


if __name__ == "__main__":
    main()
