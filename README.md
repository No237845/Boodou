# AlertSécurité — Safety, Reporting & Protection (Burkina Faso)

POC hackathon OSF & Andela : signalement anonyme d'incidents (violences, menaces, VBG, terrorisme), accès aux hotlines et ressources de protection. Français / Mooré / Dioula / English. Web faible bande passante, puis WhatsApp et SMS.

## Démarrer

```bash
pip install -r requirements.txt
python -m scripts.gen_keys          # copier REPORT_PUBLIC_KEY dans .env, garder la privée hors serveur
cp .env.example .env                # puis renseigner DATABASE_URL, REPORT_PUBLIC_KEY et ADMIN_KEY
uvicorn app.main:app --reload --no-access-log
```

Ouvrir http://127.0.0.1:8000 — les tables sont créées et l'annuaire (`app/data/resources.json`) chargé automatiquement au démarrage.

### Base de données : PostgreSQL

La base est un PostgreSQL hébergé (Neon, Supabase, Railway, Render…), pas de base locale. Coller l'URL de connexion fournie par l'hébergeur dans `DATABASE_URL` ; les formats `postgres://` et `postgresql://` sont acceptés et convertis vers le driver `psycopg` (v3). Ajouter `?sslmode=require` si l'hébergeur l'exige.

## Parcours web (6 étapes de la fiche)

| Étape | URL |
|---|---|
| 1. Choix de la langue | `/` → `/fr`, `/mos`, `/dyu`, `/en` |
| 2. « Signaler un incident » | `/{lang}` |
| 3. Formulaire anonyme (type, région approximative, description) | `/{lang}/signaler` |
| 4. « Envoyer anonymement » | `POST /{lang}/signaler` |
| 5. Confirmation « Merci » + **code de suivi** | `/{lang}/merci` |
| 6. Hotlines + centres d'aide locaux | `/{lang}/ressources?type=GBV&region=Centre` |
| 7. Suivre son signalement plus tard | `/{lang}/suivi` |

Bouton **Quitter vite** (`/quitter`) sur chaque page → redirection vers un site neutre.

## Suivi des signalements

Sans retour, un signalement anonyme est un cri dans le vide : la personne ne
saura jamais s'il a servi à quelque chose, et ne recommencera pas. Le suivi
ferme la boucle sans jamais créer de compte.

**Le code.** À l'envoi, la personne reçoit un code de 10 caractères
(`K7M3P-QR8TZ`) : c'est l'identifiant du signalement, et le seul lien entre elle
et lui. Rien n'est stocké de son côté, aucun numéro n'est demandé. L'alphabet est
celui de Crockford (ni I, ni L, ni O, ni U) pour qu'un code recopié sur un bout
de papier ou dicté au téléphone ne soit jamais ambigu ; à la saisie, minuscules,
espaces et tirets sont tolérés.

**Les trois états**, que le partenaire fait avancer depuis `/admin` :

| État | Ce que la personne lit |
|---|---|
| `RECU` | Arrivé, chiffré, en attente d'ouverture |
| `TRANSMIS` | Une organisation partenaire l'a lu et s'en occupe |
| `CLOTURE` | Dossier terminé |

Le partenaire peut y joindre un message court (280 caractères), affiché tel quel
à la personne. **Ce message est en clair en base** — le serveur doit pouvoir
l'afficher — donc jamais de nom ni de détail identifiant ; l'interface le
rappelle à la saisie.

**Ce que le suivi ne révèle jamais** : ni la description (le serveur ne peut pas
la lire), ni le type d'incident, ni la région. Quelqu'un qui met la main sur un
code n'apprend rien sur l'incident. Le code fait 50 bits d'entropie et les
consultations sont limitées à 10 par quart d'heure et par client
(`app/ratelimit.py`, en mémoire, aucune IP conservée).

Accès : `/{lang}/suivi` sur le web (le code voyage en POST, il ne passe jamais
dans l'URL ni dans l'historique), option **5** du menu WhatsApp/SMS, et
`GET /api/reports/{code}` pour les autres canaux.

> Les signalements créés avant cette version ont un identifiant à l'ancien
> format : ils restent lisibles dans `/admin`, mais leur code n'ayant été
> communiqué à personne, ils ne sont pas consultables via le suivi.

## Anonymat et chiffrement

- **Aucun identifiant** : pas de compte, pas de cookie, pas de session. Les logs d'accès sont désactivés (pas d'IP, pas d'URL visitée).
- **Localisation grossière** : région, commune facultative. Jamais de GPS.
- **Description chiffrée côté serveur avec une sealed box libsodium** (X25519 + XSalsa20-Poly1305). Le serveur ne détient que la clé publique ; seule l'organisation partenaire, avec la clé privée, peut lire les signalements. Une fuite de la base ne révèle que le type, la région et la date.
- Identifiants de signalement aléatoires (non séquentiels), `Cache-Control: no-store`, `Referrer-Policy: no-referrer`, CSP stricte (aucun script tiers possible).
- Aucun JavaScript : les pages font < 2 Ko de CSS et fonctionnent en 2G.

Côté partenaire :

```bash
curl -H "X-Admin-Key: $ADMIN_KEY" https://<serveur>/admin/reports -o reports.json
REPORT_PRIVATE_KEY=... python -m scripts.decrypt reports.json
```

## Espace partenaire

`/admin` — connexion avec `ADMIN_KEY` et, facultativement, la clé privée pour lire les descriptions (gardée en mémoire le temps de la session, 1 h). Tuiles de statistiques, filtres type / région / statut, tableau des incidents.

Chaque ligne porte le code de suivi et un formulaire pour faire avancer le
dossier (statut + message à la personne). C'est la contrepartie du suivi : si
personne ne touche aux statuts, tout reste au stade « Reçu » et la promesse faite
à l'utilisateur ne tient pas.

## WhatsApp (API Cloud de Meta, numéro réel)

Le choix de langue en tête de parcours propose `1-Français · 2-Mooré ·
3-Dioula · 4-English`. Le bot suit ensuite le menu de la fiche, enrichi du suivi
et de l'effacement :
`1-Signaler · 2-Aide VBG · 3-Aide sécurité · 4-Parler à quelqu'un ·
5-Suivre un signalement · 6-Effacer cette conversation`, précédé du choix de
langue. Tester sans Meta :

```bash
python -m scripts.bot_sim                                   # interactif
python -m scripts.bot_sim Bonjour 1 1 4 5 "Description…"    # scénario
```

### Effacer la conversation (option 6 / mot-clé `EFFACER`)

En VBG, la menace la plus proche n'est pas le serveur : c'est le conjoint qui
fouille le téléphone. Le bouton « Quitter vite » protège le web ; sur WhatsApp,
la discussion reste sur l'appareil.

**Ce que l'API de Meta permet — et ne permet pas.** Le point est important pour
ne rien promettre de faux : l'API Cloud n'expose que `POST /messages`. Il n'existe
**aucun endpoint de suppression** : une entreprise ne peut ni retirer un message
envoyé, ni effacer une discussion sur le téléphone de la personne. Le message
d'effacement le dit explicitement plutôt que de laisser croire le contraire.

Ce que le service fait donc réellement :

1. **Purge côté serveur, immédiate et vraie** : la session du bot (langue, étape
   en cours, saisie partielle) est détruite. Il ne restait de toute façon qu'un
   numéro haché en mémoire, jamais le numéro en clair.
2. **Guide pas-à-pas** pour supprimer la discussion, Android et iPhone, en trois
   gestes chacun.
3. **Messages éphémères** : le seul mécanisme qui efface vraiment à distance.
   C'est la personne qui l'active (discussion → nom du contact → « Messages
   éphémères » → 24 h), mais les messages envoyés par l'API y sont soumis comme
   les autres. Le bot explique donc comment l'activer une fois pour toutes.

Le mot-clé `EFFACER` (aussi `SUPPRIMER`, `DELETE`) est reconnu **dans n'importe
quel état**, y compris au milieu de la saisie d'une description : quelqu'un qui
tape ça est en train de paniquer, on ne lui pose aucune question et rien n'est
enregistré. Le rappel est ajouté en fin du dernier message après un signalement
et après l'affichage d'un mot du partenaire — les deux moments où la discussion
devient parlante pour qui lit par-dessus l'épaule.

Le signalement déjà envoyé, lui, n'est pas supprimé : il est anonyme, et le code
de suivi ne doit pas devenir un moyen, pour un agresseur qui met la main sur le
téléphone, de détruire le dossier.

À faire côté Meta : **enregistrer le numéro sous un nom neutre** dans le profil
WhatsApp Business. Un contact affiché « Boodou — signalement VBG » trahit la
personne avant même qu'on ouvre la discussion.

### Mise en place côté Meta (une fois)

1. **Créer l'app** sur https://developers.facebook.com → *Créer une app* → type *Business* → ajouter le produit **WhatsApp**.
2. **Numéro de téléphone** : *WhatsApp > API Setup*. Meta fournit un numéro de test gratuit (5 destinataires max, à enregistrer). Pour votre numéro réel : *Ajouter un numéro de téléphone*, vérification par SMS/appel — le numéro **ne doit pas** déjà être utilisé par une app WhatsApp classique ou Business (sinon le supprimer de l'app d'abord).
3. Relever sur cette page le **Phone number ID** et le **jeton d'accès temporaire** → `.env` (`WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_ACCESS_TOKEN`).
4. **Clé secrète** : *Paramètres de l'app > Général > Clé secrète* → `WHATSAPP_APP_SECRET` (obligatoire en prod : c'est ce qui prouve que le webhook vient bien de Meta).
5. Choisir un `WHATSAPP_VERIFY_TOKEN` quelconque dans `.env`, redémarrer le serveur.

### Exposer le webhook

Meta exige une URL **HTTPS publique**. En local, un tunnel :

```bash
ngrok http 8000          # → https://xxxx.ngrok-free.app
```

Puis *WhatsApp > Configuration > Webhook* :
- **URL de rappel** : `https://xxxx.ngrok-free.app/webhooks/whatsapp`
- **Jeton de vérification** : la valeur de `WHATSAPP_VERIFY_TOKEN`
- *Vérifier et enregistrer* → le serveur répond au `hub.challenge`
- **Champs de webhook** : s'abonner à `messages`

Envoyez « Bonjour » au numéro depuis WhatsApp : le bot répond avec le choix de langue.

### En production

- Remplacer le jeton temporaire (24 h) par un **jeton System User** permanent (*Business Settings > System Users > Générer un jeton*, permission `whatsapp_business_messaging`).
- Les sessions du bot sont en mémoire : un seul worker (`uvicorn --workers 1`), sinon les basculer en base/Redis.
- Meta n'autorise les réponses libres que dans les **24 h** suivant le dernier message de l'utilisateur ; au-delà il faut un *message template* approuvé. Pour ce service ce n'est pas un problème : c'est toujours l'utilisateur qui écrit en premier.

## API (SMS et autres canaux)

Documentation interactive : `/api/docs`.

- `GET /api/regions` — régions et communes
- `GET /api/resources?type=GBV&region=Kadiogo&category=SANTE` — ressources filtrées
- `POST /api/reports` — `{type, region, commune?, description, channel, lang}` → renvoie le **code de suivi**
- `GET /api/reports/{code}` — état d'un signalement (statut, dates, message du partenaire) ; 10 consultations / 15 min
- `GET /admin/stats`, `GET /admin/reports` — en-tête `X-Admin-Key` ou session admin
- `GET/POST /webhooks/whatsapp` — webhook Meta

## Structure

```
app/
  main.py          FastAPI, middleware confidentialité, /quitter
  config.py        variables d'environnement
  models.py        Report, Resource, code de suivi (alphabet Crockford)
  migrations.py    ajout des colonnes manquantes au démarrage
  services.py      logique métier partagée web / API / bots
  crypto.py        sealed box libsodium
  ratelimit.py     limite les consultations de codes, sans conserver d'IP
  i18n.py          traductions avec repli sur le français
  routers/         web.py (HTML), api.py (JSON), admin.py (partenaire), whatsapp.py (webhook Meta)
  bot/engine.py    moteur de menu numéroté, commun WhatsApp / SMS
  templates/       Jinja2, zéro JS
  locales/         fr.json, mos.json, dyu.json, en.json (textes web + bot)
  data/            regions.json (17 régions, 2025), resources.json
scripts/
  gen_keys.py      génération de la paire de clés
  decrypt.py       déchiffrement hors ligne (partenaire)
  bot_sim.py       simulateur du bot en ligne de commande
```

## À faire avant la démo

- [ ] **Vérifier les numéros** dans `app/data/resources.json` (`verified: false`) : UNFPA, CHU Yalgado, AFJ/BF, Croix-Rouge, ligne d'écoute. Seuls 17 / 16 / 18 sont confirmés.
- [ ] **Faire relire le Mooré par un locuteur natif.** `app/locales/mos.json` couvre désormais les 94 clés (plus aucun repli sur le français), mais **rien n'est validé** : toutes les clés sont dans `_auto`. `app/locales/mos_review.md` liste les 94 paires FR / Mooré côte à côte ; retirer une clé de `_auto` une fois relue. Priorité : `bot_wipe` et `bot_wipe_hint` (textes de sécurité), puis `bot_menu`, `bot_ask_description`, `confirm_code_*`.
- [ ] **Traduire le Dioula** (`app/locales/dyu.json` : 19 clés sur 94, le reste s'affiche en français). L'anglais (`en.json`) et le français sont complets.
- [ ] **Nom neutre** pour le profil WhatsApp Business (voir plus haut).
- [ ] **Convenir avec l'organisation partenaire** de qui met les statuts à jour et sous quel délai : le suivi ne vaut que si les dossiers avancent réellement.
- [ ] Pour compléter le Dioula, `python -m scripts.translate_locales --lang dyu` produit un premier jet (modèle NLLB local, dépendances `requirements-ml.txt`, hors prod) : les clés obtenues vont dans `_auto`, celles que le modèle rejette dans `_todo`, à traduire à la main.
- [ ] Brancher le numéro WhatsApp réel (section ci-dessus) et tester depuis un téléphone.
- [ ] SMS (Africa's Talking / Orange API) : même moteur `app/bot/engine.py`, il ne manque que le webhook.
- [ ] Déploiement (Railway / Render), rate limiting sur `POST /api/reports`, retirer la clé privée du `.env`.
