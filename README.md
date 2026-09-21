# Boodou — Safety, Reporting & Protection (Burkina Faso)

Service **anonyme** de signalement de violences (VBG, menaces, attaques), d'orientation vers les acteurs de terrain et d'accès aux ressources d'aide. Conçu pour une personne qui lit peu, sur un téléphone partagé, en 2G, et qui ne fait pas confiance aux institutions.

- **Quatre canaux, un même parcours** : site web sans JavaScript (4 Ko), WhatsApp, SMS, application mobile.
- **Six langues** : français, mooré, dioula, anglais, portugais, arabe (écriture de droite à gauche).
- **Aucune donnée personnelle** : ni compte, ni cookie, ni IP ; récits chiffrés au repos ; localisation à la commune.
- **Un circuit de terrain** : relais communautaire → point focal VBG → action sociale / gestionnaire de cas, avec des droits appliqués par le serveur.
- **Un suivi sans compte** : un code de dix caractères pour savoir ce que devient son signalement.

Projet réalisé pour le hackathon **OSF & Andela – Safety, Reporting & Protection**.

---

## Sommaire

1. [Prérequis](#1-prérequis)
2. [Installation et premier lancement](#2-installation-et-premier-lancement)
3. [Configuration (`.env`)](#3-configuration-env)
4. [Application mobile](#4-application-mobile)
5. [Canaux WhatsApp et SMS](#5-canaux-whatsapp-et-sms)
6. [Fonctionnement](#6-fonctionnement)
7. [Confidentialité et sécurité](#7-confidentialité-et-sécurité)
8. [Langues et traduction](#8-langues-et-traduction)
9. [Options IA](#9-options-ia)
10. [API](#10-api)
11. [Structure du dépôt](#11-structure-du-dépôt)
12. [Scripts utiles](#12-scripts-utiles)
13. [Dépannage](#13-dépannage)
14. [État du projet et feuille de route](#14-état-du-projet-et-feuille-de-route)

---

## 1. Prérequis

| Outil | Version | Pour |
|---|---|---|
| Python | 3.12 ou plus | serveur |
| PostgreSQL | 14 ou plus, local ou hébergé (Neon, Supabase, Railway, Render…) | base de données |
| Node.js + npm | 20 ou plus | application mobile uniquement |
| Expo Go | dernière version, sur un téléphone Android/iOS | tester l'app sans build |

Aucune clé d'API n'est nécessaire pour lancer le projet : les fonctions IA (reformulation, dictée vocale, traduction mooré) et les canaux WhatsApp/SMS sont facultatifs et s'activent par variables d'environnement.

## 2. Installation et premier lancement

### 2.1 Récupérer le code et créer l'environnement Python

```bash
git clone <url-du-dépôt> boodou
cd boodou
python -m venv .venv
# Linux / macOS
source .venv/bin/activate
# Windows (PowerShell)
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

### 2.2 Créer la base de données

Avec un PostgreSQL local :

```sql
CREATE DATABASE boodou;
```

Avec un PostgreSQL hébergé : créer un projet et récupérer l'URL de connexion (`postgres://…` ou `postgresql://…`, les deux sont acceptées). Ajouter `?sslmode=require` si l'hébergeur l'exige.

Les tables sont créées, les migrations jouées et l'annuaire (`app/data/resources.json`) chargé **automatiquement au premier démarrage**. Il n'y a rien d'autre à faire côté base.

### 2.3 Configurer

```bash
cp .env.example .env
python -m scripts.gen_keys      # affiche une REPORT_SECRET_KEY à coller dans .env
```

Renseigner au minimum dans `.env` :

```ini
DATABASE_URL=postgresql://user:password@localhost:5432/boodou
REPORT_SECRET_KEY=<valeur affichée par gen_keys>
ADMIN_KEY=<un mot de passe pour /admin>
```

> `REPORT_SECRET_KEY` chiffre tous les récits. **La perdre, c'est perdre tous les signalements** : conservez-en une copie hors serveur (coffre de mots de passe).

### 2.4 Lancer

```bash
uvicorn app.main:app --reload --no-access-log
```

Puis ouvrir :

| URL | Quoi |
|---|---|
| http://127.0.0.1:8000 | site public (choix de langue) |
| http://127.0.0.1:8000/espace | espace acteurs (relais, point focal, action sociale…) |
| http://127.0.0.1:8000/admin | administration (clé `ADMIN_KEY`) |
| http://127.0.0.1:8000/api/docs | documentation interactive de l'API |

### 2.5 Créer les premiers comptes acteurs

Le parcours usager fonctionne sans aucun compte. Pour tester la prise en charge, aller sur `/admin` → **Comptes acteurs** et créer au minimum :

- un **point focal VBG** pour une région ;
- un **agent de l'action sociale** pour la même région ;
- un **relais communautaire** pour une commune de cette région.

Un usager d'une commune sans relais ne voit que l'option « directement à l'action sociale ».

### 2.6 Vérifier que tout marche (2 minutes)

1. `/` → choisir une langue → **Signaler un incident** → remplir → **Envoyer anonymement** → noter le code de suivi.
2. `/espace` → se connecter avec le relais → ouvrir le signalement → **Transmettre** à l'action sociale.
3. `/espace` → se connecter avec l'action sociale → **Prise en charge** → laisser un message.
4. `/` → **Suivre un signalement** → entrer le code : l'état « Pris en charge » et le message apparaissent.

Sans WhatsApp ni SMS branchés, le bot se teste en ligne de commande : `python -m scripts.bot_sim`.

## 3. Configuration (`.env`)

Toutes les variables sont documentées dans [`.env.example`](.env.example). Résumé :

| Variable | Obligatoire | Rôle |
|---|---|---|
| `DATABASE_URL` | oui | URL PostgreSQL |
| `REPORT_SECRET_KEY` | oui | clé de chiffrement des récits (`python -m scripts.gen_keys`) |
| `ADMIN_KEY` | oui | accès à `/admin` |
| `QUICK_EXIT_URL` | non | site neutre du bouton « Quitter vite » (défaut : google.com) |
| `CORS_ORIGINS` | non | origines autorisées sur `/api` depuis un navigateur (app mobile en mode web) |
| `WHATSAPP_*` | non | WhatsApp Cloud API (Meta) — voir [§5](#5-canaux-whatsapp-et-sms) |
| `AT_*`, `SMS_WEBHOOK_TOKEN` | non | SMS via Africa's Talking — voir [§5](#5-canaux-whatsapp-et-sms) |
| `OPENAI_API_KEY` | non | assistant de reformulation — voir [§9](#9-options-ia) |
| `GLADIA_API_KEY` | non | dictée vocale dans l'app mobile — voir [§9](#9-options-ia) |
| `BURKIMBIA_API_KEY` | non | traduction français → mooré — voir [§8](#8-langues-et-traduction) |
| `REPORT_PUBLIC_KEY` | non | uniquement pour relire des signalements d'une ancienne version (`scripts/reencrypt.py`) |

Sans clé facultative, la fonction correspondante est simplement absente de l'interface : rien ne casse.

## 4. Application mobile

React Native + Expo (SDK 57). Même parcours usager et même espace acteurs que le web, via `/api`. Détails dans [mobile/README.md](mobile/README.md).

```bash
cd mobile
npm install
cp .env.example .env
```

Dans `mobile/.env`, `EXPO_PUBLIC_API_URL` doit être l'**adresse IP de la machine** qui lance le serveur, sur le même Wi-Fi que le téléphone — jamais `localhost` (qui désignerait le téléphone) :

```ini
EXPO_PUBLIC_API_URL=http://192.168.1.10:8000
```

Le serveur doit écouter sur toutes les interfaces :

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --no-access-log
```

Puis :

```bash
npm start            # scanner le QR code avec Expo Go
npm run typecheck    # vérification TypeScript
```

> **Windows** : si le chemin du projet contient `&` ou des espaces, `npx expo …` échoue. Les scripts `npm run …` contournent le problème ; pour toute autre commande Expo, utiliser `node node_modules/expo/bin/cli <commande>`.

Icône d'application, écran de démarrage et mise en page miroir arabe ne sont visibles que dans un **build natif** (`expo prebuild` / EAS), pas dans Expo Go.

## 5. Canaux WhatsApp et SMS

Les deux canaux partagent le moteur de menu numéroté `app/bot/engine.py` et les mêmes textes que le web. Ils sont facultatifs.

### WhatsApp (API Cloud de Meta)

1. Sur https://developers.facebook.com : créer une app de type **Business**, ajouter le produit **WhatsApp**.
2. *WhatsApp > API Setup* : relever le **Phone number ID** et le **jeton d'accès** (temporaire 24 h, ou jeton *System User* permanent en production) → `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_ACCESS_TOKEN`.
3. *Paramètres de l'app > Général > Clé secrète* → `WHATSAPP_APP_SECRET` (vérifie la signature des webhooks ; obligatoire en production).
4. Choisir un `WHATSAPP_VERIFY_TOKEN` quelconque, redémarrer le serveur.
5. Exposer le serveur en HTTPS (`ngrok http 8000` en local), puis *WhatsApp > Configuration > Webhook* : URL `https://<hôte>/webhooks/whatsapp`, jeton = `WHATSAPP_VERIFY_TOKEN`, s'abonner au champ `messages`.
6. Envoyer « Bonjour » au numéro : le bot répond avec le choix de langue.

En production : jeton System User permanent, un seul worker (`--workers 1`, les sessions du bot sont en mémoire), et un **nom de profil WhatsApp Business neutre** — un contact « Boodou — signalement VBG » trahit la personne avant même l'ouverture de la discussion.

### SMS (Africa's Talking)

`AT_USERNAME=sandbox` pour tester, sinon le nom du compte ; `AT_API_KEY` ; `SMS_WEBHOOK_TOKEN` à inventer et à ajouter à l'URL de callback déclarée chez l'opérateur : `https://<hôte>/webhooks/sms?token=<SMS_WEBHOOK_TOKEN>` (leurs callbacks ne sont pas signés).

### Tester sans opérateur

```bash
python -m scripts.bot_sim                                    # interactif
python -m scripts.bot_sim Bonjour 1 1 4 5 "Description…"     # scénario
```

## 6. Fonctionnement

### Le parcours d'une personne

`/` langue → accueil (numéros d'urgence en tête) → **Signaler** : de quoi s'agit-il, région, commune → à qui l'envoyer (relais de la commune ou action sociale) → description → **Envoyer anonymement** → **code de suivi** + ressources de la région. Plus tard : **Suivre un signalement** avec le code. Bouton **Quitter vite** sur chaque page.

Deux familles de cas et neuf sous-types. VBG : viol, agression sexuelle, agression physique, mariage forcé, déni de ressources / d'opportunités / de services, violence psychologique. Sécurité : violence physique, menace, attaque terroriste.

### Le circuit des acteurs

```
Usager ──► Relais communautaire ──┐
Usager ──► Action sociale ────────┼──► Action sociale ──────────┐
           Point focal VBG ───────┘    Gestionnaire de cas ──────┴──► pris en charge → réglé
```

| Rôle | Qui | Voit | Peut |
|---|---|---|---|
| `RELAIS` | Bénévole du village / de la commune | Les signalements qui lui sont adressés, ceux qu'il a saisis ou transmis | **Relayer seulement** : reformuler (obligatoire) et transmettre ; saisir un cas reçu en personne |
| `POINT_FOCAL` | Point focal VBG de la région | Tous les cas VBG de sa région non pris en charge | Reformuler et transmettre |
| `ACTION_SOCIALE` | Service de l'État | Ce qui lui est adressé dans sa zone, ce qu'il a pris en charge | **Traiter seulement** : prendre en charge, régler, écrire à la personne |
| `GESTIONNAIRE` | Gestionnaire de cas (ONG) | Idem | Idem |

Ces règles sont appliquées par le serveur (`services.forward`, `services.set_status`), pas seulement par les écrans. L'historique (`report_events`) garde qui a fait quoi.

### Le suivi par code

Code de 10 caractères (alphabet de Crockford : ni I, L, O, U — jamais ambigu recopié ou dicté), 50 bits d'entropie. Quatre états : `RECU` → `TRANSMIS` → `PRIS_EN_CHARGE` → `REGLE`, plus un message court (280 caractères) de l'acteur de prise en charge. Le suivi ne révèle **jamais** le récit, le type ni la région. Consultations limitées à 10 par quart d'heure et par client, sans conserver d'IP.

### Espace acteurs et administration

- `/espace` (web) et l'app mobile : boîte de réception filtrée par statut, fiche avec récit déchiffré, reformulation, historique, formulaires **Transmettre** et **Prise en charge**, saisie d'un cas reçu en personne. Traduit dans les six langues (cookie `espace_lang` limité à `/espace`).
- `/admin` : vue de tous les signalements, filtres, statuts ; création et désactivation des comptes acteurs, réinitialisation des mots de passe. En français.

## 7. Confidentialité et sécurité

- **Aucun identifiant côté usager** : pas de compte, de cookie ni de session ; journaux d'accès désactivés (ni IP, ni URL). Seuls les acteurs ont un compte.
- **Localisation grossière** : région et commune. Jamais de GPS, de quartier ni d'adresse.
- **Récit et reformulation chiffrés au repos** (libsodium SecretBox, XSalsa20-Poly1305) avec `REPORT_SECRET_KEY`, présente uniquement dans l'environnement du serveur. Le serveur ne déchiffre que pour un acteur connecté et autorisé sur ce signalement. Une fuite de la base seule ne révèle que type, région et date.
- **Identifiants aléatoires**, `Cache-Control: no-store`, `Referrer-Policy: no-referrer`, CSP stricte, zéro JavaScript sur le site public.
- **Mots de passe** hachés (scrypt), jetons de session stockés hachés, sessions web courtes (8 h), mobiles longues (30 jours).
- **WhatsApp** : le numéro n'est jamais stocké, seul un hachage salé vit en mémoire 15 minutes. Le mot-clé `EFFACER` purge la session côté serveur et explique honnêtement comment supprimer la discussion du téléphone (l'API de Meta ne permet à personne de le faire à distance) et activer les messages éphémères. Reconnu dans n'importe quel état, même au milieu d'une saisie.
- **Icônes neutres** (app, onglet) : l'anneau du logo, pas la silhouette, pour ne rien trahir sur un téléphone surveillé.

Export complet des signalements (récits en clair, document sensible) : `curl -H "X-Admin-Key: $ADMIN_KEY" https://<serveur>/admin/reports -o reports.json`.

## 8. Langues et traduction

Six langues (`settings.languages`) : `fr`, `mos` (mooré), `dyu` (dioula), `en`, `pt`, `ar`. Une langue = un JSON plat dans `app/locales/`, lu par le web, le bot **et** l'app mobile (une seule source). Clé absente = repli sur le français.

| Langue | Couverture | Relecture native |
|---|---|---|
| Français, anglais | complète | — |
| Portugais, arabe | complète | à faire |
| Mooré | 124 clés sur 129 (API Burkimbia) | **à faire** — `app/locales/mos_review.md` |
| Dioula | 19 clés sur 129 | à traduire |

**Ajouter une langue** : le JSON, `LANG_NAMES` (`app/i18n.py`), `LANG_CHOICES` (`app/bot/engine.py`) et la ligne des langues dans `bot_welcome`, `LANGS` + salutation (`mobile/src/config.ts`, `mobile/app/lang.tsx`), chaînes communes (`mobile/src/strings.ts`). Langue de droite à gauche : `settings.rtl_languages` et `RTL_LANGS` côté mobile.

**Traduction mooré (Burkimbia, facultatif)** — `BURKIMBIA_API_KEY` :

- Interface : `python -m scripts.translate_locales` remplit les clés manquantes de `mos.json` hors ligne. Prétraitement ligne par ligne, placeholders protégés, sorties suspectes (chiffre perdu, balise cassée) **rejetées** — le français vaut mieux qu'un contresens. Le résultat est un brouillon à faire relire.
- Contenu dynamique (annuaire, message d'un acteur) : traduit en tâche de fond et mis en cache (table `translations`) ; affiché en français tant que ce n'est pas prêt.
- Seul français ↔ mooré est disponible sur cette API. Jamais un récit n'y transite. La clé a un quota journalier (~250 appels).

## 9. Options IA

| Fonction | Pour qui | Activation | Ce qui quitte le serveur |
|---|---|---|---|
| **Reformulation** (bouton ✨ dans l'espace acteurs) : résumé anonyme de 3 à 6 phrases, urgence estimée, éléments identifiants repérés, ce qui manque. Remplit le champ, n'enregistre rien. | Relais, point focal | `OPENAI_API_KEY` (`OPENAI_MODEL`, défaut `gpt-4o-mini`) | Le récit seul (ni code, ni relais, ni canal) |
| **Dictée vocale** (« Parler au lieu d'écrire », app mobile) : 2 min max, texte placé dans le champ pour relecture. | La personne, le relais | `GLADIA_API_KEY` (`GLADIA_MODEL`, défaut `solaria-1`) | L'audio, non conservé ; français et anglais reconnus, mooré/dioula au mieux |
| **Traduction mooré** | Tout le monde | `BURKIMBIA_API_KEY` | Textes publics uniquement |

Chaque usage est une exception à la règle « seules les personnes chargées du dossier lisent le récit » : à valider avec les partenaires avant la production. L'IA propose ; l'humain décide et signe.

## 10. API

Documentation interactive : `/api/docs`. Tous les paramètres `lang` acceptent les six codes.

**Public**

| Méthode | Route | Rôle |
|---|---|---|
| GET | `/api/types?lang=` | types et sous-types |
| GET | `/api/regions` | régions et communes |
| GET | `/api/relais?region=&commune=` | relais communautaires d'une commune |
| POST | `/api/reports` | déposer un signalement → code de suivi |
| GET | `/api/reports/{code}?lang=` | état d'un signalement (10 / 15 min) |
| GET | `/api/resources?type=&region=&category=&lang=` | annuaire filtré |
| GET | `/api/features` | fonctions activées (`speech`) |
| POST | `/api/transcribe` | dictée vocale (si activée) |

**Acteurs** (`Authorization: Bearer <jeton>`, 30 jours)

| Méthode | Route | Rôle |
|---|---|---|
| POST | `/api/auth/login`, `/api/auth/logout` | session |
| GET | `/api/me`, `/api/inbox?status=`, `/api/inbox/{id}`, `/api/targets` | lecture |
| POST | `/api/inbox/{id}/forward` | transmettre (avec reformulation) |
| POST | `/api/inbox/{id}/status` | prise en charge (action sociale, gestionnaire) |
| POST | `/api/inbox/{id}/summary`, `/api/inbox/{id}/suggest-summary`, `/api/ai/reformulate` | reformulation, assistant |
| POST | `/api/reports` (avec jeton) | saisir un cas au nom d'une personne |

**Admin** : `GET /admin/stats`, `GET /admin/reports` (en-tête `X-Admin-Key`). **Webhooks** : `GET/POST /webhooks/whatsapp`, `POST /webhooks/sms`.

## 11. Structure du dépôt

```
app/
  main.py            FastAPI, middleware de confidentialité, /quitter, démarrage (migrations, annuaire, cache de traduction)
  config.py          variables d'environnement (pydantic-settings)
  models.py          Report, Actor, ActorToken, ReportEvent, Resource, Translation
  migrations.py      migrations versionnées, jouées au démarrage
  services.py        logique métier partagée (web, API, bots, espace acteurs)
  auth.py            mots de passe (scrypt), jetons, dépendances FastAPI
  crypto.py          chiffrement libsodium
  ratelimit.py       limitation de débit sans IP
  i18n.py            traductions avec repli sur le français
  routers/           web.py (site public), api.py, espace.py (acteurs), admin.py, whatsapp.py, sms.py
  bot/engine.py      moteur de menu commun WhatsApp / SMS
  api_ai/            reformulation (OpenAI), transcribe.py (Gladia), translate.py + translate_cache.py (Burkimbia)
  templates/         Jinja2, zéro JavaScript ; _icons.html = icônes SVG inline
  static/            style.css (10 Ko), logo.png, icon.svg
  locales/           fr, mos, dyu, en, pt, ar (.json) — textes web + bot + mobile
  data/              regions.json (17 régions, 55 communes), resources.json (38 ressources)
mobile/              application React Native / Expo — voir mobile/README.md
scripts/             gen_keys, bot_sim, translate_locales, reencrypt
```

## 12. Scripts utiles

| Commande | Rôle |
|---|---|
| `python -m scripts.gen_keys` | générer `REPORT_SECRET_KEY` |
| `python -m scripts.bot_sim [messages…]` | simuler le bot WhatsApp/SMS sans opérateur |
| `python -m scripts.translate_locales [--lang mos] [--force] [--keys …] [--engine local]` | premier jet des traductions (Burkimbia, ou modèle NLLB local avec `requirements-ml.txt`) |
| `REPORT_PRIVATE_KEY=… python -m scripts.reencrypt` | relire les signalements d'une version antérieure (une fois) |
| `cd mobile && npm run typecheck` | vérification TypeScript de l'app |

## 13. Dépannage

| Symptôme | Cause probable | Solution |
|---|---|---|
| `DATABASE_URL manquante` / `doit être une URL PostgreSQL` au démarrage | `.env` absent ou URL incomplète | `cp .env.example .env`, vérifier l'URL (`postgresql://user:mdp@hôte:5432/base`) |
| Avertissement `REPORT_SECRET_KEY absente` | clé non renseignée | `python -m scripts.gen_keys`, coller la valeur dans `.env` |
| Un signalement ne s'enregistre pas / récit « illisible » | clé absente ou changée depuis l'enregistrement | même clé qu'à l'enregistrement ; pour l'ancien schéma, `scripts/reencrypt.py` |
| L'app mobile affiche « Pas de connexion » | `EXPO_PUBLIC_API_URL` en `localhost`, serveur non exposé, pare-feu | IP du PC sur le Wi-Fi, `--host 0.0.0.0`, autoriser le port 8000 dans le pare-feu |
| `Use port 8082 instead?` au lancement d'Expo | un autre serveur Expo tourne déjà sur 8081 | l'arrêter, ou accepter l'autre port (et ajouter l'origine à `CORS_ORIGINS` en mode web) |
| `npx expo` échoue sous Windows | `&` ou espace dans le chemin du projet | `npm run …` ou `node node_modules/expo/bin/cli …` |
| Icône / splash / RTL arabe inchangés dans Expo Go | ces éléments exigent un build natif | `expo prebuild` ou EAS Build |
| Le bot WhatsApp ne répond pas | webhook non vérifié, tunnel expiré, jeton 24 h périmé | revérifier l'URL dans Meta, relancer ngrok, régénérer le jeton ; tester avec `scripts/bot_sim` |
| `API_KEY_QUOTA_EXCEEDED` dans les logs | quota journalier Burkimbia atteint | le fil de fond réessaie après une heure ; espacer les passes de `translate_locales` |
| Le mooré s'affiche en français par endroits | clé absente de `mos.json` (`_todo`) ou traduction dynamique pas encore prête | traduire la clé à la main ; attendre le fil de fond |

## 14. État du projet et feuille de route

**Fait** : parcours usager sur quatre canaux, espace acteurs web + mobile (quatre rôles, règles côté serveur), suivi par code, administration, six langues avec RTL, effacement WhatsApp, identité visuelle (logo, icônes neutres, splash), reformulation IA, dictée vocale, traduction mooré, ≈ 8 000 lignes.

**À faire avant une mise en service**

- [ ] Faire relire le mooré par un locuteur natif (`mos_review.md`, priorité aux textes de sécurité `bot_wipe*`) et traduire les 5 clés restantes (`_todo`) ; compléter le dioula ; faire relire portugais et arabe.
- [ ] Vérifier les numéros de l'annuaire (`verified: false` dans `resources.json`) : seuls 16 / 17 / 18 sont confirmés.
- [ ] Convenir avec l'organisation partenaire de qui met les statuts à jour et sous quel délai.
- [ ] Brancher un numéro WhatsApp réel sous un nom neutre ; signer le contrat SMS opérateur.
- [ ] Déployer (Railway / Render…), limiter le débit sur `POST /api/reports`, sauvegarder `REPORT_SECRET_KEY` hors serveur.

**Pistes** : formulaire web en écrans successifs, micro-réassurances par champ, « les trois ressources les plus proches », voix en premier en mooré/dioula, carte sur mobile, USSD.
