# AlertSécurité — Safety, Reporting & Protection (Burkina Faso)

POC hackathon OSF & Andela : signalement anonyme d'incidents (violences, menaces, VBG, terrorisme), accès aux hotlines et ressources de protection. Français / Mooré / Dioula. Web faible bande passante, puis WhatsApp et SMS.

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
| 1. Choix de la langue | `/` → `/fr`, `/mos`, `/dyu` |
| 2. « Signaler un incident » | `/{lang}` |
| 3. Formulaire anonyme (type, région approximative, description) | `/{lang}/signaler` |
| 4. « Envoyer anonymement » | `POST /{lang}/signaler` |
| 5. Confirmation « Merci. Ressources disponibles ci-dessous » | `/{lang}/merci` |
| 6. Hotlines + centres d'aide locaux | `/{lang}/ressources?type=GBV&region=Centre` |

Bouton **Quitter vite** (`/quitter`) sur chaque page → redirection vers un site neutre.

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

## API (pour WhatsApp / SMS)

Documentation interactive : `/api/docs`.

- `GET /api/regions` — régions et communes
- `GET /api/resources?type=GBV&region=Centre&category=SANTE` — ressources filtrées
- `POST /api/reports` — `{type, region, commune?, description, channel, lang}`
- `GET /admin/stats`, `GET /admin/reports` — en-tête `X-Admin-Key`

## Structure

```
app/
  main.py          FastAPI, middleware confidentialité, /quitter
  config.py        variables d'environnement
  models.py        Report, Resource
  services.py      logique métier partagée web / API / bots
  crypto.py        sealed box libsodium
  i18n.py          traductions avec repli sur le français
  routers/         web.py (HTML), api.py (JSON), admin.py (partenaire)
  templates/       Jinja2, zéro JS
  locales/         fr.json, mos.json, dyu.json
  data/            regions.json, resources.json
scripts/
  gen_keys.py      génération de la paire de clés
  decrypt.py       déchiffrement hors ligne (partenaire)
```

## À faire avant la démo

- [ ] **Vérifier les numéros** dans `app/data/resources.json` (`verified: false`) : UNFPA, CHU Yalgado, AFJ/BF, Croix-Rouge, ligne d'écoute. Seuls 17 / 16 / 18 sont confirmés.
- [ ] **Faire relire les traductions Mooré et Dioula** par un locuteur natif (`app/locales/mos.json`, `dyu.json` — les clés manquantes retombent sur le français).
- [ ] Adapter `regions.json` si l'équipe préfère le découpage 2025 en 17 régions.
- [ ] Phase 3 : bot WhatsApp (Meta Cloud API / Twilio) + SMS (Africa's Talking) sur le moteur de menu, en appelant `/api/*`.
- [ ] Phase 4 : déploiement (Railway / Render), rate limiting sur `POST /api/reports`.
