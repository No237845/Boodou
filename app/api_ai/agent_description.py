"""
Agents pour AlerteSécurité BF — Structuration & Validation des Récits de Victimes
Permet aux relais communautaires de générer/adapter rapidement des récits anonymes.

Deux agents :
1. Agent Structurateur : organise le récit brut, anonymise, identifie éléments clés
2. Agent Vérificateur : contrôle anonymat, exactitude, sensibilité, complétude
"""

from __future__ import annotations

import json
import os
from datetime import datetime

from openai import OpenAI

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

MODELE = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")


def _api_key() -> str:
    # Même source que le reste de l'application (app/config.py, .env à la racine).
    try:
        from ..config import settings

        if settings.openai_api_key:
            os.environ.setdefault("OPENAI_MODEL", settings.openai_model)
            return settings.openai_api_key
    except Exception:  # noqa: BLE001 — utilisable aussi hors application (CLI de démo)
        pass
    return os.environ.get("OPENAI_API_KEY", "")

_openai_client: OpenAI | None = None


def get_openai_client() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        api_key = _api_key()
        if not api_key:
            raise RuntimeError("Clé OpenAI manquante. Définis OPENAI_API_KEY dans le .env à la racine du projet.")
        _openai_client = OpenAI(api_key=api_key)
    return _openai_client


PROMPT_AGENT_STRUCTURATEUR = """Tu es un agent STRUCTURATEUR pour AlerteSécurité BF, plateforme de signalement anonyme et sécurisée pour violences, abus, menaces au Burkina Faso.

## TON RÔLE
Un relais communautaire (personne de confiance locale) a pris le temps d'écouter une victime et a transcrit son récit brut. Ce récit peut être :
- Désorganisé, avec des sauts temporels
- Contenir des identifiants (noms, lieux précis, contacts)
- Mélanger plusieurs incidents
- Inclure des détails non-pertinents ou personnels
- Être incomplet sur les faits importants

Ta mission : STRUCTURER ce récit pour :
1. ✓ Anonymiser complètement (aucun nom, adresse exacte, contact personnel)
2. ✓ Organiser chronologiquement les faits
3. ✓ Identifier les éléments clés (type d'incident, date, acteurs, conséquences)
4. ✓ Séparer les faits vérifiés du contexte/opinions
5. ✓ Préserver la voix et dignité de la victime
6. ✓ Préparer pour transmission sécurisée

## CATÉGORIES D'INCIDENTS
- Violence domestique / conjugale
- Harcèlement sexuel / menaces
- Abus d'enfant / mariage précoce
- Violences communautaires / menaces
- Discrimination / exclusion
- Autres

## PROCESSUS DE STRUCTURATION

### 1. ANONYMISATION (CRITIQUE)
- Remplace tous les noms propres par : Victime, Agresseur(s), Famille, Témoins
- Remplace les lieux précis par : [Région], [Commune], [Quartier], [Lieu public type: marché/école]
- Supprime : numéros de téléphone, adresses exactes, noms de voisins, identifiants sociaux
- Conserve : contexte géographique large (région), type de relation, contexte socio-économique pertinent

### 2. ORGANISATION
Structure le récit ainsi :
```
## FICHE DE SIGNALEMENT ANONYME

### Informations Générales
- Type d'incident : [catégorie]
- Région : [région]
- Commune : [commune]
- Date de l'incident : [date approximative ou période]
- État actuel de la victime : [sécurité immédiate, urgence]

### Contexte
- Relation entre victime et agresseur(s) : [type relation]
- Durée/historique : [si applicable]
- Contexte local pertinent : [famille, travail, communauté]

### Récit des Faits (Chronologique)
[Récit organisé, clair, basé uniquement sur ce que la victime a décrit]

### Conséquences Documentées
- Santé physique : [blessures, traumatismes]
- Santé mentale : [peur, stress, dépression]
- Impact social/économique : [exclusion, perte d'emploi]
- Sécurité actuelle : [risque résiduel]

### Ressources Recommandées
[Suggestions adaptées à la région et type d'incident]

### Notes de Structuration
- Éléments clés identifiés : [liste]
- Informations incomplètes : [ce qui manque]
- Raison du classement/catégorie : [justification]
```

### 3. QUALITÉ DE SORTIE
- Langage : simple, direct, respectueux
- Longueur : assez détaillé pour comprendre, pas de superflu
- Ton : neutre, documentant les faits, respectueux de la dignité
- Complétude : identifie ce qui manque pour la sécurité/suivi

## DONNÉES D'ENTRÉE

Récit brut de la victime (tel que transcrit par relais communautaire) :
\"\"\"
{RECIT_BRUT}
\"\"\"

Informations optionnelles (fournies séparément par relais, anonymes) :
- Région : {REGION}
- Commune : {COMMUNE}
- Type d'incident signalé : {TYPE_INCIDENT}

## FORMAT DE SORTIE
Réponds UNIQUEMENT avec un objet JSON valide, sans texte avant ou après :

{
  "fiche_structuree": "Le récit complet structuré selon le modèle ci-dessus (markdown formaté)",
  "type_incident": "catégorie identifiée (violence domestique / harcèlement / etc.)",
  "region": "région anonymisée ou déduite",
  "commune": "commune anonymisée",
  "score_anonymisation": "parfait / bon / attention (0-3 risques d'identification)",
  "risques_anonymite": ["liste des risques potentiels détectés (vides si parfait)"],
  "elements_manquants": ["liste de ce qui serait utile pour safer categorization/routing"],
  "recommandations_relais": "conseil court pour le relais sur comment affiner les informations lors de la prochaine visite",
  "confiance_recit": "basse / moyenne / haute (basée sur cohérence et clarté)",
  "prêt_pour_transmission": true ou false
}

## RÈGLES STRICTES
- JAMAIS d'hallucination : respecte exactement ce que la victime a dit
- JAMAIS de jugement : documente les faits, ne commente pas
- TOUJOURS anonyme : si le moindre risque existe, signale-le
- RESPECT : la victime a eu du courage à partager, préserve sa dignité
- TRAUMA-INFORMED : le ton est doux, non-culpabilisant, empathique
- CONTEXTE LOCAL : accepte les détails culturels/locaux, ne force pas un format occidental
"""


PROMPT_AGENT_VERIFICATEUR = """Tu es un agent VÉRIFICATEUR pour AlerteSécurité BF.

## TON RÔLE
L'Agent Structurateur a déjà traité le récit brut d'une victime. Ta mission est de :
1. Vérifier que l'anonymat est RÉELLEMENT préservé
2. Vérifier que aucune information n'a été inventée ou amplifiée
3. Vérifier que le classement (type d'incident) est cohérent
4. Identifier les risques manqués pour la sécurité du relais / de la victime
5. Approuver ou recommander des corrections

## POINTS DE CONTRÔLE CRITIQUES

### 1. ANONYMAT (Critique)
- Aucun nom propre n'apparaît ? ✓
- Aucune adresse exacte, numéro de téléphone ? ✓
- Les lieux ne permettent-ils pas d'identifier la victime ? ✓
- Les détails spécifiques (cicatrices, travail unique) risquent-ils identification ? ⚠
- Relais communautaire lui-même identifiable ? ⚠

### 2. EXACTITUDE
- L'Agent a-t-il ajouté des détails non présents dans le récit brut ? ✗
- Les interprétations sont-elles respectueuses du ressenti victime ? ✓
- Le contexte reste-t-il factuel ? ✓

### 3. COMPLÉTUDE & RISQUES
- Le type d'incident est-il correctement catégorisé ?
- Manque-t-il une information critique pour la sécurité immédiate ?
- Existe-t-il un risque légal ou éthique non signalé ?

### 4. SENSIBILITÉ
- Le ton est-il approprié et respectueux ?
- Les détails traumatisants sont-ils présentés de manière sensible ?
- Existe-t-il un risque de re-traumatisation ?

## FORMAT DE SORTIE
Réponds UNIQUEMENT avec JSON, sans texte avant ou après :

{
  "anonymat_verifie": true ou false,
  "niveau_risque_anonymat": "critique / moyen / faible",
  "risques_anonymat_manques": ["détails à revoir si niveau > faible"],
  "exactitude_verifiee": true ou false,
  "hallucinations_detectees": ["inventions/amplifications si exactitude=false"],
  "categorie_correcte": true ou false,
  "categorie_recommandee": "si correcte=false, la bonne catégorie",
  "risques_securite_manques": ["alertes non soulevées par agent 1"],
  "recommandations_corrections": "liste des modifications avant transmission",
  "pret_pour_transmission_final": true ou false,
  "justification": "résumé factuel de l'évaluation"
}
"""


def agent_structurateur(
    recit_brut: str,
    region: str = "",
    commune: str = "",
    type_incident: str = ""
) -> dict:
    """Agent 1 : Structure et anonymise le récit brut."""
    prompt = PROMPT_AGENT_STRUCTURATEUR.replace("{RECIT_BRUT}", recit_brut or "")
    prompt = prompt.replace("{REGION}", region or "[À déterminer]")
    prompt = prompt.replace("{COMMUNE}", commune or "[À déterminer]")
    prompt = prompt.replace("{TYPE_INCIDENT}", type_incident or "[À déterminer]")

    reponse = get_openai_client().chat.completions.create(
        model=MODELE,
        temperature=0,  # Pas de créativité, juste structuration
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": prompt}],
    )
    return json.loads(reponse.choices[0].message.content)


def agent_verificateur(recit_brut: str, fiche_structuree: dict) -> dict:
    """Agent 2 : Vérifie anonymat, exactitude, risques."""

    prompt = PROMPT_AGENT_VERIFICATEUR
    prompt = prompt.replace("{RECIT_BRUT}", recit_brut or "")
    prompt += f"\n\n## FICHE STRUCTURÉE (À VÉRIFIER)\n{json.dumps(fiche_structuree, ensure_ascii=False, indent=2)}"

    reponse = get_openai_client().chat.completions.create(
        model=MODELE,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": prompt}],
    )
    return json.loads(reponse.choices[0].message.content)


def traiter_recit(
    recit_brut: str,
    region: str = "",
    commune: str = "",
    type_incident: str = ""
) -> dict:
    """
    Pipeline complet :
    1. Agent Structurateur : organise & anonymise
    2. Agent Vérificateur : valide anonymat & exactitude
    3. Résultat final prêt pour transmission
    """
    print("⏳ Structuration du récit...")
    fiche = agent_structurateur(recit_brut, region, commune, type_incident)

    print("⏳ Vérification anonymat & exactitude...")
    verification = agent_verificateur(recit_brut, fiche)

    # Décision finale
    anonymat_ok = fiche.get("score_anonymisation") != "attention" and verification.get("anonymat_verifie", False)
    exactitude_ok = verification.get("exactitude_verifiee", False)
    pret_transmission = fiche.get("prêt_pour_transmission", False) and verification.get("pret_pour_transmission_final", False)

    statut = "valide" if (anonymat_ok and exactitude_ok and pret_transmission) else "a_revoir"

    # Message pour relais
    if statut == "valide":
        message_relais = (
            "✓ Le récit a été structuré et anonymisé avec succès. "
            "Il est prêt pour être transmis aux ressources d'aide."
        )
    else:
        corrections = verification.get("recommandations_corrections", "Veuillez revoir les éléments signalés.")
        message_relais = f"⚠ Corrections recommandées avant transmission :\n{corrections}"

    return {
        "timestamp": datetime.now().isoformat(),
        "statut": statut,
        "recit_structure": fiche.get("fiche_structuree", ""),
        "type_incident": fiche.get("type_incident", ""),
        "region": fiche.get("region", ""),
        "commune": fiche.get("commune", ""),

        # Sécurité
        "anonymat_verifie": anonymat_ok,
        "niveau_risque_anonymat": fiche.get("score_anonymisation", ""),
        "risques_anonymite": fiche.get("risques_anonymite", []),

        # Qualité
        "exactitude_verifiee": exactitude_ok,
        "hallucinations": verification.get("hallucinations_detectees", []),

        # Complétude
        "elements_manquants": fiche.get("elements_manquants", []),
        "risques_securite": verification.get("risques_securite_manques", []),

        # Conseils
        "recommandations_relais": fiche.get("recommandations_relais", ""),
        "recommandations_corrections": verification.get("recommandations_corrections", ""),

        # Décision
        "pret_transmission": pret_transmission,
        "message_relais": message_relais,

        # Raw agents
        "agent_1_output": fiche,
        "agent_2_output": verification,
    }


# ============================================
# Agent 3 : reformulation concise (branché dans l'application)
# ============================================
#
# Les deux agents ci-dessus produisent une fiche complète. Dans l'espace
# acteurs et l'app mobile, le relais a besoin d'autre chose : une proposition
# courte, claire, anonyme, qu'il relit et corrige avant de transmettre.
# Il reste l'auteur : la proposition ne part jamais sans lui.

PROMPT_AGENT_REFORMULATION = """Tu aides un relais communautaire d'AlerteSécurité BF (Burkina Faso) à transmettre la plainte d'une victime à l'action sociale ou à un gestionnaire de cas.

## TA MISSION
Reformule le récit ci-dessous de façon CONCISE et CLAIRE, en français simple, pour la personne qui va prendre en charge.

## RÈGLES STRICTES
- 3 à 6 phrases maximum. Pas de titres, pas de listes, pas de markdown.
- Faits d'abord : ce qui s'est passé, quand (approximativement), où (commune ou type de lieu, jamais d'adresse), qui est l'agresseur par rapport à la victime (mari, voisin, inconnu…), conséquences, besoin urgent.
- ANONYMISE : aucun nom propre, aucun numéro de téléphone, aucune adresse, aucun quartier, aucun employeur, aucun établissement précis. Écris « la victime », « son mari », « un voisin », « ses enfants ».
- N'invente rien, n'amplifie rien, ne juge pas. Si une information manque, ne la devine pas.
- Ton neutre et respectueux. Si le récit est dans une autre langue, reformule en français.

## RÉCIT (transcrit par le relais)
\"\"\"
{RECIT_BRUT}
\"\"\"

## CONTEXTE DÉJÀ CONNU (ne pas répéter inutilement)
- Type de cas : {TYPE_INCIDENT}
- Région : {REGION}
- Commune : {COMMUNE}

## FORMAT DE SORTIE
Réponds UNIQUEMENT avec un objet JSON valide :
{
  "reformulation": "le texte concis, 3 à 6 phrases",
  "urgence": "haute | moyenne | basse",
  "risques_anonymat": ["chaque élément identifiant présent dans le RÉCIT D'ORIGINE (nom, prénom, numéro de téléphone, adresse, quartier ou secteur, employeur, école…), cité tel quel pour que le relais le retire ; liste vide seulement si le récit n'en contient aucun"],
  "elements_manquants": ["informations utiles absentes du récit, vide si rien"]
}
"""


def agent_reformulation(recit_brut: str, region: str = "", commune: str = "", type_incident: str = "") -> dict:
    """Agent 3 : proposition de reformulation concise, à relire par le relais."""
    prompt = PROMPT_AGENT_REFORMULATION.replace("{RECIT_BRUT}", recit_brut or "")
    prompt = prompt.replace("{REGION}", region or "non précisée")
    prompt = prompt.replace("{COMMUNE}", commune or "non précisée")
    prompt = prompt.replace("{TYPE_INCIDENT}", type_incident or "non précisé")

    reponse = get_openai_client().chat.completions.create(
        model=MODELE,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": prompt}],
    )
    return json.loads(reponse.choices[0].message.content)


# ============================================
# Interface CLI simple pour relais communautaire
# ============================================

if __name__ == "__main__":
    import sys

    print("=" * 70)
    print("🛡️  AlerteSécurité BF - Structuration Anonyme des Récits")
    print("=" * 70)
    print()

    # Pour démo simple
    recit_exemple = """
    Bonjour, je m'appelle Aminata et j'habite à Ouagadougou, dans le quartier de Nongrin.
    Mon mari s'appelle Ousmane. Il boit beaucoup, et quand il rentre tard la nuit,
    il me frappe. Hier, il m'a frappée parce que je n'avais pas assez cuisiné.
    J'ai une grosse bleu sur le bras. Mes enfants Karim et Fatoumata ont peur aussi.

    Ça dure depuis 3 ans. Je ne sais pas où aller. Ma mère habite à Bobo-Dioulasso,
    je l'appelle au 70 12 34 56, mais elle ne peut pas m'aider financièrement.

    Hier j'ai pensé à me faire du mal, mais mes enfants m'ont retenue.
    Je travaille à la pharmacie Wend-Lasso, près du marché de Nongrin.
    """

    print("📝 Traitement d'un exemple de récit...\n")
    resultat = traiter_recit(
        recit_brut=recit_exemple,
        region="Centre",
        commune="Ouagadougou",
        type_incident="Violence domestique"
    )

    print(f"✓ Statut: {resultat['statut'].upper()}")
    print(f"✓ Type incident: {resultat['type_incident']}")
    print(f"✓ Anonymat: {'VÉRIFIÉ' if resultat['anonymat_verifie'] else '⚠ À REVOIR'}")
    print(f"✓ Prêt transmission: {'OUI' if resultat['pret_transmission'] else 'NON'}")
    print()
    print("📄 FICHE STRUCTURÉE :")
    print("-" * 70)
    print(resultat['recit_structure'])
    print()
    print("💬 Message pour relais communautaire :")
    print(resultat['message_relais'])
    print()
    print("⚠️  Recommandations :")
    if resultat['recommandations_relais']:
        print(f"  • {resultat['recommandations_relais']}")
    if resultat['recommandations_corrections']:
        print(f"  • {resultat['recommandations_corrections']}")
    print()
    print("=" * 70)
