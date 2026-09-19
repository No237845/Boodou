# Boodou — application mobile

React Native + Expo (SDK 57), Expo Router. Une seule base de code Android / iOS.
L'app ne fait que parler à l'API du serveur (`../app/routers/api.py`) : aucune
donnée de signalement n'est stockée sur le téléphone.

## Lancer en développement

```bash
cd mobile
npm install
cp .env.example .env        # EXPO_PUBLIC_API_URL = IP de la machine qui lance uvicorn
npm start                   # puis scanner le QR code avec Expo Go (Android / iOS)
```

Le serveur doit écouter sur toutes les interfaces pour être joignable depuis le
téléphone : `uvicorn app.main:app --host 0.0.0.0 --port 8000`.

> Windows : le chemin du projet contient `&` (« Safety, Reporting & Protection »), ce qui casse
> les raccourcis `npx expo …` et `node_modules/.bin`. Les scripts `npm run …` appellent donc le
> CLI par `node node_modules/expo/bin/cli`. Pour toute autre commande Expo, faire de même :
> `node node_modules/expo/bin/cli install <paquet>`.

Vérification des types : `npm run typecheck`.

## Ce que fait l'app

**Usager (anonyme, 4 langues)** — même parcours que le web et WhatsApp :

| Écran | Fichier |
|---|---|
| Choix de la langue (premier lancement) | `app/lang.tsx` |
| Accueil : signaler, aide VBG / sécurité, parler à quelqu'un, suivre, urgences | `app/home.tsx` |
| 1/4 De quoi s'agit-il (sous-type, groupé VBG / sécurité) | `app/report/type.tsx` |
| 2/4 Région, commune | `app/report/where.tsx` |
| 3/4 À qui : relais communautaire de la commune, ou directement l'action sociale | `app/report/to.tsx` |
| 4/4 Description, envoi | `app/report/describe.tsx` |
| Code de suivi + ressources | `app/report/done.tsx` |
| Suivi par code (statut seulement) | `app/track.tsx` |
| Annuaire filtré | `app/resources.tsx` |

**Acteurs (relais, point focal VBG, action sociale, gestionnaire de cas)** — en français, comme `/espace` :

| Écran | Fichier |
|---|---|
| Connexion (identifiants créés par l'admin) | `app/actor/login.tsx` |
| Boîte de réception, filtre par statut, tirer pour rafraîchir | `app/actor/inbox.tsx` |
| Fiche : récit, reformulation, historique, **Transmettre** (personne ou rôle, avec reformulation), **Prise en charge** (action sociale / gestionnaire) | `app/actor/[id].tsx` |
| Saisir un cas reçu en personne et le transmettre ; code à remettre à la personne | `app/actor/new.tsx` |

Ce qui est affiché dépend de `actor.can_forward_to` et `actor.can_set_status`
renvoyés par `POST /api/auth/login` : l'app ne décide pas des droits, le serveur oui.

## Design

Présentation sobre, alignée sur le site web (`app/static/style.css`) : un seul accent vert profond
`#0b5d3b`, fond neutre, police système (rien à charger), bordures fines, rouge réservé aux actions
irréversibles. Mode sombre automatique. Les icônes de contour (`@expo/vector-icons`, inclus dans Expo)
aident à repérer les choix sans lire ; les correspondances type / statut / rôle → icône sont dans `src/theme.ts`.

Les icônes d'application (`assets/`) sont encore celles du gabarit Expo : à remplacer par le logo Boodou.

## Confidentialité

- Rien n'est écrit sur le téléphone à propos d'un signalement : ni brouillon, ni
  code de suivi (l'usager le copie ou le note lui-même). Le brouillon vit en
  mémoire et disparaît si l'app est fermée.
- Seuls la langue et, pour un acteur connecté, son jeton de session sont
  conservés — dans `expo-secure-store` (chiffré par l'OS). Le jeton tombe si
  l'admin désactive le compte.
- Les textes viennent de `../app/locales/*.json` (via `metro.config.js`) : une
  seule source pour le web, le bot et le mobile. Le Mooré et le Dioula retombent
  sur le français pour les clés non traduites.

## Structure

```
app/                écrans (Expo Router : le chemin du fichier = la route)
src/api.ts          client de l'API, types partagés
src/config.ts       URL du serveur, langues
src/i18n.tsx        traductions (contexte React)
src/session.tsx     session acteur (jeton + profil)
src/draft.tsx       brouillon du signalement entre les 4 écrans
src/ui.tsx          composants : Screen, Button, ActionCard, Choice, Chip, Field, Banner, Stepper, CodeBox…
src/theme.ts        couleurs (clair / sombre, les mêmes que le web), espacements, icônes par type / statut / rôle
src/strings.ts      textes propres à l'app et à l'espace acteurs
src/errors.ts       message lisible pour une erreur API
src/voice.tsx       dictée vocale (expo-audio → POST /api/transcribe), affichée si le serveur a une clé Gladia
src/suggestion.tsx  bouton « Proposer une reformulation » (assistant IA), affiché si le serveur a une clé OpenAI
```

## Distribuer

APK Android hors store (le plus simple pour des relais sur le terrain) :

```bash
npm install -g eas-cli
eas login
eas build --platform android --profile preview
```

Le profil `preview` produit un `.apk` installable directement. Pour iOS il faut
un compte développeur Apple (TestFlight).
