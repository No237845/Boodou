# Boodou — Safety, Reporting & Protection (Burkina Faso)

POC hackathon OSF & Andela : signalement anonyme d'incidents (VBG, violences, menaces, terrorisme), routage vers les acteurs de terrain (relais communautaires, points focaux VBG, action sociale, gestionnaires de cas), accès aux hotlines et ressources de protection. Français / Mooré / Dioula / English. Web faible bande passante, WhatsApp, SMS, et une API pour l'application mobile.

## Démarrer

```bash
pip install -r requirements.txt
python -m scripts.gen_keys          # copier REPORT_SECRET_KEY dans .env (et la sauvegarder hors serveur)
cp .env.example .env                # puis renseigner DATABASE_URL, REPORT_SECRET_KEY et ADMIN_KEY
uvicorn app.main:app --reload --no-access-log
```

Ouvrir http://127.0.0.1:8000 — les tables sont créées, les migrations jouées et l'annuaire (`app/data/resources.json`) chargé automatiquement au démarrage.

Puis créer les comptes des acteurs sur http://127.0.0.1:8000/admin (clé `ADMIN_KEY`) → *Comptes acteurs* : au minimum un point focal VBG et un agent de l'action sociale par région, et les relais communautaires par commune.

> **Mise à jour depuis la version « sealed box »** : les signalements créés avant la refonte sont chiffrés avec l'ancienne clé publique. Pour les relire, une fois, sur le serveur :
> `REPORT_PRIVATE_KEY=<ancienne clé privée> python -m scripts.reencrypt`

### Base de données : PostgreSQL

La base est un PostgreSQL hébergé (Neon, Supabase, Railway, Render…), pas de base locale. Coller l'URL de connexion fournie par l'hébergeur dans `DATABASE_URL` ; les formats `postgres://` et `postgresql://` sont acceptés et convertis vers le driver `psycopg` (v3). Ajouter `?sslmode=require` si l'hébergeur l'exige.

## Le circuit

Ce que les acteurs de terrain ont décrit, et que l'application reproduit :

```
Usager ──► Relais communautaire ──┐
Usager ──► Action sociale ────────┼──► Action sociale ────────┐
           Point focal VBG ───────┘    Gestionnaire de cas ────┴──► pris en charge → réglé
           (relit tous les cas VBG      (ONG : HCR, UNICEF…)
            de sa région, reformule,
            oriente)
```

| Rôle (`ActorRole`) | Qui | Voit | Peut |
|---|---|---|---|
| `RELAIS` | Bénévole du village / de la commune | Les signalements que des usagers lui ont adressés, ceux qu'il a saisis ou transmis | **Relayer seulement** : reformuler clairement la plainte (obligatoire) et la transmettre (point focal, action sociale, gestionnaire) ; saisir un cas reçu en personne. Ne change jamais le statut. |
| `POINT_FOCAL` | Point focal VBG de la région | Tous les cas VBG de sa région tant qu'ils ne sont pas pris en charge | Reformuler (obligatoire) et transmettre (action sociale, gestionnaire). Ne change jamais le statut. |
| `ACTION_SOCIALE` | Acteur étatique | Ce qui est adressé à l'action sociale dans sa zone, ce qu'il a pris en charge | **Traiter seulement** : prendre en charge, régler, écrire à la personne. Ne relaie pas, ne reformule pas, ne saisit pas de cas. |
| `GESTIONNAIRE` | Gestionnaire de cas (ONG) | Idem pour son rôle | Idem. |

Seuls l'action sociale et les gestionnaires de cas **prennent en charge et changent le statut** (`CASE_HANDLERS`). Relais et point focal ne font que relayer, et ne peuvent pas transmettre sans reformulation (`MUST_SUMMARIZE`) — la règle est appliquée par le serveur (`services.forward`, `services.set_status`), pas seulement par les écrans.

Chaque signalement a un **destinataire** : une personne (`assignee_id`, un relais choisi par l'usager) ou un rôle dans une zone (`target_role`, « n'importe quel agent de l'action sociale de la région »). Transmettre change le destinataire ; prendre en charge, c'est se l'attribuer. L'historique (`report_events`) garde qui a fait quoi.

**Types de cas.** Deux familles, `GBV` et `SECURITE`, et des sous-types. VBG : viol, agression sexuelle, agression physique, mariage forcé, déni de ressources / d'opportunités / de services, violence psychologique ou émotionnelle. Sécurité : violence physique, menace, attaque terroriste (les anciens types de premier niveau, inchangés pour que l'annuaire reste valide).

## Parcours usager (web)

| Étape | URL |
|---|---|
| 1. Choix de la langue | `/` → `/fr`, `/mos`, `/dyu`, `/en` |
| 2. « Signaler un incident » | `/{lang}` |
| 3. De quoi s'agit-il (sous-type), région, commune | `/{lang}/signaler` |
| 4. À qui l'envoyer (relais de la commune ou action sociale), description | `POST /{lang}/signaler` |
| 5. « Envoyer anonymement » | `POST /{lang}/signaler/envoyer` |
| 6. Confirmation « Merci » + **code de suivi** | `/{lang}/merci` |
| 7. Hotlines + centres d'aide locaux | `/{lang}/ressources?type=GBV&region=Kuilsé` |
| 8. Suivre son signalement plus tard | `/{lang}/suivi` |

Deux pages pour le formulaire parce que la liste des relais dépend de la commune et qu'il n'y a pas de JavaScript. Le même parcours existe sur WhatsApp / SMS (`app/bot/engine.py`) et dans l'API pour l'application mobile.

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

**Les quatre états** :

| État | Qui le déclenche | Ce que la personne lit |
|---|---|---|
| `RECU` | Le dépôt | Arrivé, en attente d'être lu par son destinataire |
| `TRANSMIS` | Un relais ou le point focal qui transmet | Relu et transmis à l'action sociale ou à un gestionnaire de cas |
| `PRIS_EN_CHARGE` | Action sociale / gestionnaire | Quelqu'un s'occupe du dossier |
| `REGLE` | Action sociale / gestionnaire | Dossier terminé |

L'acteur de prise en charge peut y joindre un message court (280 caractères), affiché tel quel
à la personne. **Ce message est en clair en base** — le serveur doit pouvoir
l'afficher — donc jamais de nom ni de détail identifiant ; l'interface le
rappelle à la saisie.

**Ce que le suivi ne révèle jamais** : ni la description, ni le type d'incident, ni la région. Quelqu'un qui met la main sur un
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

- **Aucun identifiant côté usager** : pas de compte, pas de cookie, pas de session. Les logs d'accès sont désactivés (pas d'IP, pas d'URL visitée). Seuls les acteurs (relais, point focal…) ont un compte.
- **Localisation grossière** : région et commune chef-lieu. Jamais de GPS, ni de quartier.
- **Récit chiffré au repos** (libsodium SecretBox, XSalsa20-Poly1305) avec `REPORT_SECRET_KEY`, qui n'est que dans l'environnement du serveur. Le serveur déchiffre uniquement pour un acteur connecté et autorisé à voir ce signalement (`services.visible_reports_stmt`). Une fuite de la base seule ne révèle que le type, la région et la date. Le chiffrement de bout en bout de la première version a été abandonné : un signalement passe de main en main et se fait reformuler, chaque destinataire aurait dû rechiffrer pour le suivant depuis son téléphone.
- **Reformulation chiffrée comme le récit**, même sensibilité.
- Identifiants de signalement aléatoires (non séquentiels), `Cache-Control: no-store`, `Referrer-Policy: no-referrer`, CSP stricte (aucun script tiers possible).
- Aucun JavaScript : les pages font < 2 Ko de CSS et fonctionnent en 2G.

Export complet (récits en clair, à manipuler comme un document sensible) :

```bash
curl -H "X-Admin-Key: $ADMIN_KEY" https://<serveur>/admin/reports -o reports.json
```

## Espace acteurs

`/espace` — connexion avec l'identifiant et le mot de passe créés par l'admin (cookie HttpOnly, 8 h). Boîte de réception filtrée par statut, fiche d'un signalement avec récit, reformulation, historique, et selon le rôle : formulaire **Transmettre** (à une personne ou à un rôle, avec reformulation) et formulaire **Prise en charge** (statut + message à la personne). `/espace/nouveau` : un relais enregistre le cas d'une personne venue le voir et le transmet dans la foulée ; le code de suivi s'affiche, à remettre à la personne.

L'application mobile fait exactement la même chose via `/api` (voir plus bas).

## Assistant de reformulation (facultatif)

Un relais doit reformuler chaque plainte de façon concise avant de la transmettre. Pour aller vite, un bouton **✨ Proposer une reformulation** (espace web et app mobile, à la saisie d'un cas comme sur la fiche d'un signalement reçu) demande à un agent (`app/api_ai/agent_description.py`, agent 3 `agent_reformulation`) un texte de 3 à 6 phrases, anonyme, sans invention, avec l'urgence estimée, les éléments identifiants repérés dans le récit d'origine et ce qui manque. La proposition **remplit le champ, ne s'enregistre pas** : le relais relit, corrige, et c'est lui qui transmet.

- Activation : `OPENAI_API_KEY` dans `.env` (`OPENAI_MODEL`, défaut `gpt-4o-mini`). Sans clé, le bouton n'existe pas et `ai_available` vaut `false` dans `/api/me`.
- Endpoints (jeton acteur) : `POST /api/ai/reformulate` `{text, region?, commune?, subtype?}` pour un récit en cours de saisie ; `POST /api/inbox/{id}/suggest-summary` pour un signalement reçu. Réponse `{summary, urgency, anonymity_risks, missing}` ; `503 ai_unavailable` si le fournisseur ne répond pas — la transmission reste possible à la main.
- **Confidentialité** : à chaque demande, le récit (et lui seul : ni code, ni relais, ni canal) quitte le serveur vers OpenAI. C'est une exception à la règle « seules les personnes chargées du dossier lisent le récit » : à décider avec les partenaires, et à mentionner dans la formation des relais. Les deux autres agents du fichier (fiche structurée, vérificateur) restent disponibles en ligne de commande, non branchés.

## Dictée vocale (facultatif)

Pour qui lit ou écrit peu : sur l'écran « Que s'est-il passé ? » de l'app mobile (et sur la saisie d'un cas par un relais), un bouton **Parler au lieu d'écrire** enregistre la personne (2 min max, AAC mono léger), envoie le fichier à `POST /api/transcribe` et place le texte dans le champ, où elle le relit ou se le fait relire avant d'envoyer. Le serveur relaie l'audio à Gladia (mode pré-enregistré : upload → travail → résultat) et **ne conserve rien** ; le texte ne revient qu'au téléphone.

- Activation : `GLADIA_API_KEY` dans `.env` (`GLADIA_MODEL`, défaut `solaria-1`). Sans clé, `GET /api/features` renvoie `{"speech": false}` et le bouton n'apparaît pas.
- Public (la personne n'a pas de compte), donc protégé : 10 enregistrements / 15 min par client, 8 Mo max, `503 speech_unavailable` si Gladia ne répond pas — on peut toujours écrire.
- Langues : français et anglais reconnus explicitement ; mooré et dioula ne sont pas couverts par Gladia, la détection automatique fera au mieux (l'app le dit à la personne).
- Pourquoi pas le mode temps réel (websocket) : il exige un flux PCM brut continu depuis le téléphone, fragile en 2G/3G ; un fichier de 30 s à 2 min passe partout.
- **Confidentialité** : la voix de la personne quitte le serveur vers un tiers. L'app l'annonce avant l'enregistrement ; à valider avec les partenaires comme pour l'assistant de reformulation. Le site web (sans JavaScript) n'a pas ce bouton.

## Administration

`/admin` — connexion avec `ADMIN_KEY` (1 h). Vue de tous les signalements (récits déchiffrés), filtres type / région / statut, changement de statut. `/admin/acteurs` : créer un compte, le désactiver (ses sessions mobiles tombent aussitôt), changer son mot de passe. Mots de passe hachés (scrypt), jetons de session stockés hachés.

## WhatsApp (API Cloud de Meta, numéro réel)

Le choix de langue en tête de parcours propose `1-Français · 2-Mooré ·
3-Dioula · 4-English`. Le bot suit ensuite le menu de la fiche, enrichi du suivi
et de l'effacement :
`1-Signaler · 2-Aide VBG · 3-Aide sécurité · 4-Parler à quelqu'un ·
5-Suivre un signalement · 6-Effacer cette conversation`. Un signalement enchaîne
type → sous-type → région → commune → destinataire (relais de la commune ou action
sociale ; la question est sautée s'il n'y a pas de relais) → description. Tester sans Meta :

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

## Application mobile

`mobile/` : React Native + Expo, même parcours usager (4 langues) et même espace acteurs que le web, via `/api`. Voir [mobile/README.md](mobile/README.md) pour lancer avec Expo Go et produire un APK.

## API (application mobile, SMS et autres canaux)

Documentation interactive : `/api/docs`.

**Public (parcours usager)** — dans l'ordre des écrans de l'app :

- `GET /api/types?lang=fr` — types et sous-types avec libellés
- `GET /api/regions` — régions et communes
- `GET /api/relais?region=Kuilsé&commune=Kaya` — relais communautaires à proposer comme personne ressource
- `POST /api/reports` — `{subtype, region, commune, description, assignee_id? | target_role?, channel: "MOBILE", lang}` → **code de suivi**. `assignee_id` = id d'un relais, `target_role: "ACTION_SOCIALE"` = directement à l'action sociale. Sans les deux : point focal pour un cas VBG, action sociale sinon.
- `GET /api/reports/{code}` — état d'un signalement (statut, dates, message) ; 10 consultations / 15 min
- `GET /api/resources?type=GBV&region=Kadiogo&category=SANTE` — ressources filtrées

**Acteurs** (`Authorization: Bearer <jeton>`, jeton valable 30 jours) :

- `POST /api/auth/login` — `{username, password}` → `{token, actor}` ; `actor.can_forward_to` et `actor.can_set_status` disent quoi afficher
- `POST /api/auth/logout`, `GET /api/me`
- `GET /api/inbox?status=` — mes signalements, récit et reformulation déchiffrés
- `GET /api/inbox/{id}` — détail + historique
- `GET /api/targets` — à qui je peux transmettre
- `POST /api/inbox/{id}/forward` — `{to_actor_id | to_role, summary?, note?}` : transmettre, avec reformulation
- `POST /api/inbox/{id}/status` — `{status, note?}` : action sociale et gestionnaires seulement
- `POST /api/reports` avec un jeton — saisie « au nom de » (relais qui enregistre un cas reçu en personne)

**Admin** : `GET /admin/stats`, `GET /admin/reports` — en-tête `X-Admin-Key` ou session admin.
**Webhooks** : `GET/POST /webhooks/whatsapp` (Meta), `POST /webhooks/sms` (Africa's Talking).

## Structure

```
app/
  main.py          FastAPI, middleware confidentialité, /quitter
  config.py        variables d'environnement
  models.py        Report (+ sous-type, routage, reformulation), Actor, ActorToken, ReportEvent, Resource
  migrations.py    migrations versionnées (schema_migrations), jouées au démarrage
  services.py      logique métier partagée web / API / bots / espace acteurs
  auth.py          mots de passe (scrypt), jetons de session, dépendances FastAPI
  crypto.py        SecretBox libsodium (clé serveur) + lecture de l'ancien format
  ratelimit.py     limite consultations de codes et connexions, sans conserver d'IP
  i18n.py          traductions avec repli sur le français
  routers/         web.py (HTML usager), api.py (JSON), espace.py (acteurs), admin.py, whatsapp.py, sms.py
  api_ai/          agent_description.py + service.py (reformulation), transcribe.py (dictée vocale Gladia)
  bot/engine.py    moteur de menu numéroté, commun WhatsApp / SMS
  templates/       Jinja2, zéro JS
  locales/         fr.json, mos.json, dyu.json, en.json (textes web + bot)
  data/            regions.json (17 régions, 2025), resources.json
mobile/            application React Native / Expo (voir mobile/README.md)
scripts/
  gen_keys.py      génération de REPORT_SECRET_KEY
  reencrypt.py     rechiffre les signalements de l'ancien schéma (une fois)
  bot_sim.py       simulateur du bot en ligne de commande
```

## À faire avant la démo

- [ ] **Créer les comptes** (`/admin/acteurs`) : un point focal VBG et un agent de l'action sociale par région pilote, les relais par commune. Un usager d'une commune sans relais ne voit que l'option « directement à l'action sociale ».
- [ ] **Lancer `scripts/reencrypt.py`** avec l'ancienne clé privée pour relire les signalements antérieurs.
- [ ] **Traduire les nouvelles clés** en Mooré (`_todo` dans `mos.json` : sous-types, destinataire, statuts) — elles s'affichent en français en attendant.
- [ ] **Vérifier les numéros** dans `app/data/resources.json` (`verified: false`) : UNFPA, CHU Yalgado, AFJ/BF, Croix-Rouge, ligne d'écoute. Seuls 17 / 16 / 18 sont confirmés.
- [ ] **Faire relire le Mooré par un locuteur natif.** `app/locales/mos.json` couvre désormais les 94 clés (plus aucun repli sur le français), mais **rien n'est validé** : toutes les clés sont dans `_auto`. `app/locales/mos_review.md` liste les 94 paires FR / Mooré côte à côte ; retirer une clé de `_auto` une fois relue. Priorité : `bot_wipe` et `bot_wipe_hint` (textes de sécurité), puis `bot_menu`, `bot_ask_description`, `confirm_code_*`.
- [ ] **Traduire le Dioula** (`app/locales/dyu.json` : 19 clés sur 94, le reste s'affiche en français). L'anglais (`en.json`) et le français sont complets.
- [ ] **Nom neutre** pour le profil WhatsApp Business (voir plus haut).
- [ ] **Convenir avec l'organisation partenaire** de qui met les statuts à jour et sous quel délai : le suivi ne vaut que si les dossiers avancent réellement.
- [ ] Pour compléter le Dioula, `python -m scripts.translate_locales --lang dyu` produit un premier jet (modèle NLLB local, dépendances `requirements-ml.txt`, hors prod) : les clés obtenues vont dans `_auto`, celles que le modèle rejette dans `_todo`, à traduire à la main.
- [ ] Brancher le numéro WhatsApp réel (section ci-dessus) et tester depuis un téléphone.
- [ ] SMS (Africa's Talking / Orange API) : même moteur `app/bot/engine.py`, il ne manque que le webhook.
- [ ] Déploiement (Railway / Render), rate limiting sur `POST /api/reports`, sauvegarde de `REPORT_SECRET_KEY` hors serveur.
