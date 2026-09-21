"""Premier jet des traductions Mooré à partir de fr.json.

Usage :
    python -m scripts.translate_locales                  # clés manquantes + _todo, via Burkimbia
    python -m scripts.translate_locales --force          # retraduit aussi les clés déjà auto-traduites
    python -m scripts.translate_locales --keys bot_menu bot_invalid
    python -m scripts.translate_locales --engine local   # ancien modèle NLLB en local

Moteurs :
- burkimbia (défaut) : API https://api.burkimbia.com (clé BURKIMBIA_API_KEY
  dans .env). Le texte d'interface part chez un tiers ; c'est du texte public,
  jamais un signalement. Nettement meilleur que le modèle local ;
- local : sawadogosalif/MooreFR-SaChi-translationv0 (NLLB-200 600M), tourne
  sur la machine, faible sur les phrases longues. pip install -r requirements-ml.txt.

Dans les deux cas le résultat est un BROUILLON à relire par un locuteur natif.
Le prétraitement (ligne par ligne, placeholders, préfixes de menu) et les
garde-fous (chiffres perdus, répétitions, balises) sont dans
app/api_ai/translate.py, partagés avec la traduction à la volée en production.
Une sortie suspecte est rejetée : la clé reste absente (donc affichée en
français) et va dans "_todo".

Sortie :
- app/locales/mos.json : clés ajoutées, listées dans "_auto" tant qu'elles ne
  sont pas validées (retirer une clé de "_auto" une fois relue) ; "_todo" liste
  les clés à traduire à la main ;
- app/locales/mos_review.md : tableau FR / Mooré pour la relecture.
"""

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path

from app.api_ai import translate as bia

LOCALES = Path(__file__).resolve().parent.parent / "app" / "locales"
LOCAL_MODEL = "sawadogosalif/MooreFR-SaChi-translationv0"
LOCAL_SRC_LANG = "fra_Latn"
LOCAL_TGT_LANG_CANDIDATES = ("moor_Latn", "mos_Latn")

# Jamais traduites : nom de marque, ou déjà multilingues par construction.
SKIP_KEYS = {"app_name", "_note", "_auto", "_todo", "bot_welcome"}


def local_engine(lang: str) -> Callable[[str], str]:
    if lang != "mos":
        sys.exit("Le modèle local ne produit que du mooré (fr -> mos).")
    try:
        import torch
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    except ImportError:
        sys.exit("Dépendances manquantes : pip install -r requirements-ml.txt")

    print(f"Chargement de {LOCAL_MODEL} (CPU)…", flush=True)
    tok = AutoTokenizer.from_pretrained(LOCAL_MODEL, src_lang=LOCAL_SRC_LANG)
    model = AutoModelForSeq2SeqLM.from_pretrained(LOCAL_MODEL).eval()
    unk = tok.unk_token_id
    for code in LOCAL_TGT_LANG_CANDIDATES:
        bos = tok.convert_tokens_to_ids(code)
        if bos != unk:
            break
    else:
        sys.exit(f"Aucun code langue Mooré reconnu parmi {LOCAL_TGT_LANG_CANDIDATES}")
    print(f"Cible : {code}", flush=True)

    def sentence(text: str) -> str:
        with torch.no_grad():
            inputs = tok(text, return_tensors="pt", truncation=True, max_length=256)
            out = model.generate(
                **inputs,
                forced_bos_token_id=bos,
                num_beams=5,
                max_new_tokens=128,
                repetition_penalty=1.3,
                no_repeat_ngram_size=3,
            )
        return tok.batch_decode(out, skip_special_tokens=True)[0]

    return sentence


def burkimbia_engine(lang: str) -> Callable[[str], str]:
    if not bia.enabled():
        sys.exit("BURKIMBIA_API_KEY manquante dans .env")
    if not bia.supported("fr", lang):
        sys.exit(f"L'API Burkimbia ne gère pas fr -> {lang} (langues : {', '.join(bia.LANG_CODES)})")
    return lambda text: bia.sentence_sync(text, "fr", lang)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _dump(path: Path, data: dict) -> None:
    # Métadonnées en fin de fichier, pour la lisibilité.
    meta = {k: data.pop(k) for k in ("_auto", "_todo") if k in data}
    data.update(meta)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lang", default="mos", help="langue cible (défaut : mos)")
    ap.add_argument("--engine", choices=("burkimbia", "local"), default="burkimbia")
    ap.add_argument("--force", action="store_true", help="retraduit aussi les clés déjà dans _auto")
    ap.add_argument("--keys", nargs="*", help="ne traiter que ces clés")
    args = ap.parse_args()

    fr = _load(LOCALES / "fr.json")
    target_path = LOCALES / f"{args.lang}.json"
    target = _load(target_path)
    # Une clé listée dans _auto mais absente du fichier a été retirée à la main : on l'oublie.
    auto: list[str] = [k for k in target.get("_auto", []) if k in target]
    manual: list[str] = list(target.get("_todo", []))

    if args.keys:
        todo = [k for k in args.keys if k in fr]
    else:
        # Les clés en _todo sont retentées à chaque passage : un autre moteur
        # peut réussir là où le précédent a été rejeté.
        todo = [
            k for k in fr
            if k not in SKIP_KEYS and (k not in target or k in manual or (args.force and k in auto))
        ]
    if not todo:
        print("Rien à traduire.")
        return

    sentence = burkimbia_engine(args.lang) if args.engine == "burkimbia" else local_engine(args.lang)
    n_ok = n_rejected = 0
    for i, key in enumerate(todo, start=1):
        try:
            result = bia.translate_with(fr[key], sentence)
        except bia.TranslateUnavailable as why:
            print(f"[{i}/{len(todo)}] {key} : API indisponible ({why}), arrêt.", flush=True)
            break
        except bia.Rejected as why:
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
