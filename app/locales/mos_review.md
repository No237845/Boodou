# Relecture mos — traduction complète à valider

Traduction Mooré intégrale de `fr.json`, **non encore validée par un locuteur natif**. Corriger directement dans `app/locales/mos.json`, puis retirer la clé de `_auto`.

Priorité de relecture : `bot_wipe` et `bot_wipe_hint` (textes de sécurité), puis `bot_menu`, `bot_ask_description` et `confirm_code_*` (ils conditionnent la compréhension du parcours).

Ne pas toucher : les chiffres des menus (`1 -`, `0 -`, `99 -`), les numéros d'urgence (17 / 16 / 18), les variables entre accolades (`{code}`, `{regions}`, `{max}`, `{status}`, `{help}`, `{sent}`, `{note}`) et les mots que le moteur reconnaît : « Bonjour » et « EFFACER ».

## `app_name`

**FR**

```
Boodou
```

**MOS**

```
Boodou
```

## `tagline`

**FR**

```
Signaler. Être aidé. En toute sécurité.
```

**MOS**

```
Wilgẽ. Sõngã. Ne yãmb yĩngẽ.
```

## `choose_lang`

**FR**

```
Choisissez votre langue
```

**MOS**

```
Yãk yãmb gomde
```

## `quick_exit`

**FR**

```
Quitter vite
```

**MOS**

```
Wilgẽ vɩɩm
```

## `quick_exit_hint`

**FR**

```
Ce bouton vous envoie sur un site neutre.
```

**MOS**

```
Buttonã wã na n yãmb tʋm n yɩɩlẽ website sẽn ka ning yãmb yĩngẽ.
```

## `anon_banner`

**FR**

```
Ce service est 100 % anonyme : aucun compte, aucun cookie, aucune adresse IP enregistrée.
```

**MOS**

```
Sõngã wã yaa 100 % anonyme : ka compte, ka cookie, ka IP adresse sẽn na n ningẽ.
```

## `home_report`

**FR**

```
Signaler un incident
```

**MOS**

```
Wilgẽ bõn-bõn sẽn yĩngẽ
```

## `home_report_sub`

**FR**

```
Violence, menace, abus, attaque
```

**MOS**

```
Wãsgã, yãmb yĩngẽ, tʋʋmã wã, kẽerga
```

## `home_help_gbv`

**FR**

```
Aide : violences faites aux femmes et aux filles
```

**MOS**

```
Sõngã : wãsgã sẽn tʋm ne pagba la biisã
```

## `home_help_gbv_sub`

**FR**

```
Hotlines, santé, écoute
```

**MOS**

```
Hotlines, santé, gomd ne yãmb
```

## `home_help_security`

**FR**

```
Aide : sécurité
```

**MOS**

```
Sõngã : yãmb sẽn na n yãk yĩngẽ
```

## `home_help_security_sub`

**FR**

```
Police, gendarmerie, urgences
```

**MOS**

```
Polis, gendarmerie, urgence
```

## `home_talk`

**FR**

```
Parler à quelqu'un
```

**MOS**

```
Gomd ne ned
```

## `home_talk_sub`

**FR**

```
Lignes d'écoute et ONG
```

**MOS**

```
Lignes d'écoute la ONG
```

## `home_track`

**FR**

```
Suivre un signalement
```

**MOS**

```
Tõogẽ n yãk yãmb wilgã
```

## `home_track_sub`

**FR**

```
Avec votre code de suivi
```

**MOS**

```
Ne yãmb suivi code
```

## `home_emergency`

**FR**

```
Urgence immédiate ?
```

**MOS**

```
Urgence la yãmb yĩngẽ ?
```

## `home_whatsapp`

**FR**

```
Aussi disponible sur WhatsApp et SMS
```

**MOS**

```
Yãmb tõe n yãk a ne WhatsApp la SMS
```

## `report_title`

**FR**

```
Signaler un incident
```

**MOS**

```
Wilgẽ bõn-bõn sẽn yĩngẽ
```

## `report_intro`

**FR**

```
Ne donnez aucun nom ni numéro. Décrivez seulement ce qui s'est passé.
```

**MOS**

```
Wẽnd n ka yãk yãmb yĩnga wall yãmb numérod. Gomd bala bõn-bõn sẽn yĩngẽ.
```

## `report_type`

**FR**

```
De quoi s'agit-il ?
```

**MOS**

```
Bõn-bõn la wãsgã ?
```

## `type_VIOLENCE`

**FR**

```
Violence physique
```

**MOS**

```
Wãsgã ne yãmb yĩngẽ
```

## `type_MENACE`

**FR**

```
Menace ou intimidation
```

**MOS**

```
Yãmb yĩngẽ wall yãmb sɩdga
```

## `type_GBV`

**FR**

```
Violence faite à une femme ou une fille
```

**MOS**

```
Wãsgã sẽn tʋm ne paga wall biiga
```

## `type_TERRORISME`

**FR**

```
Attaque ou activité terroriste
```

**MOS**

```
Kẽerga wall tʋʋm sẽn yaa terroriste
```

## `report_region`

**FR**

```
Région (approximative)
```

**MOS**

```
Région (sẽn ka yaa yãmb yirã)
```

## `report_commune`

**FR**

```
Commune (facultatif)
```

**MOS**

```
Commune (ka yaa obligatoire)
```

## `report_commune_hint`

**FR**

```
Ne mettez pas votre quartier ni votre maison.
```

**MOS**

```
Wẽnd n ka yãk yãmb quartier wall yãmb yirã.
```

## `report_description`

**FR**

```
Que s'est-il passé ?
```

**MOS**

```
Bõn-bõn la sẽn yĩngẽ ?
```

## `report_description_hint`

**FR**

```
Ce texte est chiffré : seule l'organisation partenaire peut le lire. Ni nous, ni un pirate.
```

**MOS**

```
Gomdã wã chifré la a ye : organisation partenaire bala la tõe n yãk a. Yãmb ka tõe n yãk a, pirate ka tõe n yãk a.
```

## `report_submit`

**FR**

```
Envoyer anonymement
```

**MOS**

```
Tʋm n ka yãk yãmb yĩnga
```

## `report_error_required`

**FR**

```
Merci de choisir un type, une région et d'écrire une description.
```

**MOS**

```
Yãmb pʋgẽ, yãk type, région la gomd bõn-bõn sẽn yĩngẽ.
```

## `report_error_too_long`

**FR**

```
La description est trop longue (max {max} caractères).
```

**MOS**

```
Gomdã wã yaa wãsgã (max {max} caractères).
```

## `confirm_title`

**FR**

```
Merci.
```

**MOS**

```
Barka.
```

## `confirm_body`

**FR**

```
Votre signalement a été envoyé de façon anonyme et chiffrée.
```

**MOS**

```
Yãmb wilgã wã tʋmame n ka yãk yãmb yĩnga la a chifré.
```

## `confirm_resources`

**FR**

```
Ressources disponibles pour vous :
```

**MOS**

```
Sõngã sẽn tõe n sõng yãmb :
```

## `confirm_nothing_stored`

**FR**

```
Aucune information permettant de vous identifier n'a été conservée.
```

**MOS**

```
Bõn-kãnga fãa sẽn tõe n wilg yãmb yĩnga ka ningẽ.
```

## `confirm_code_title`

**FR**

```
Votre code de suivi
```

**MOS**

```
Yãmb suivi code
```

## `confirm_code_body`

**FR**

```
Notez ce code. Il vous permet de savoir, plus tard, ce qu'est devenu votre signalement. C'est le seul moyen : nous n'avons aucune autre façon de vous reconnaître.
```

**MOS**

```
Gũs n yãk code wã. A na n sõng yãmb n yãka, tɩɩmẽ, bõn-bõn sẽn kẽes yãmb wilgã. A yaa nẽ code bala : ka bõn-kãnga wã sẽn na n sõng n yãmb yĩnga.
```

## `confirm_code_warning`

**FR**

```
Ne le montrez à personne en qui vous n'avez pas confiance. Pensez à appuyer sur « Quitter vite » avant de rendre le téléphone.
```

**MOS**

```
Wẽnd n ka wilg code wã ne ned sẽn ka yaa yãmb yĩnga. Sẽn na n kẽes téléphone wã, yãk « Wilgẽ vɩɩm ».
```

## `track_title`

**FR**

```
Suivre un signalement
```

**MOS**

```
Tõogẽ n yãk yãmb wilgã
```

## `track_intro`

**FR**

```
Entrez le code reçu au moment de votre signalement. Vous verrez où il en est — jamais ce que vous avez écrit.
```

**MOS**

```
Kẽes suivi code sẽn yãmb yãk tɩɩmẽ. Yãmb na n yãk bõn-bõn sẽn yĩngẽ wã — ka yãmb gomdã.
```

## `track_code_label`

**FR**

```
Code de suivi
```

**MOS**

```
Suivi code
```

## `track_code_hint`

**FR**

```
10 caractères, par exemple K7M3P-QR8TZ. Les majuscules et les tirets n'ont pas d'importance.
```

**MOS**

```
Gomd 10, misaal K7M3P-QR8TZ. Majuscule la tiret ka yaa yĩnga.
```

## `track_submit`

**FR**

```
Voir où en est mon signalement
```

**MOS**

```
Yãk bõn-bõn sẽn yĩngẽ
```

## `track_not_found`

**FR**

```
Aucun signalement ne correspond à ce code. Vérifiez les caractères et réessayez.
```

**MOS**

```
Wilgã ka ning ne code wã. Yãk n ges lettres la chiffresã, n tʋʋm n lebg.
```

## `track_too_many`

**FR**

```
Trop de tentatives. Réessayez dans un quart d'heure.
```

**MOS**

```
Yãmb tʋmã wã yaa wãsgã. Gũs 15 minutes n tʋʋm n lebg.
```

## `track_sent_on`

**FR**

```
Envoyé le
```

**MOS**

```
Tʋmã le
```

## `track_updated_on`

**FR**

```
mis à jour le
```

**MOS**

```
lebga le
```

## `track_partner_note`

**FR**

```
Message de l'organisation partenaire
```

**MOS**

```
Organisation partenaire sẽn yãk gomd
```

## `status_RECU`

**FR**

```
Reçu
```

**MOS**

```
Yãkame
```

## `status_RECU_help`

**FR**

```
Votre signalement est arrivé, chiffré. Il attend d'être ouvert par un partenaire.
```

**MOS**

```
Yãmb wilgã wã kẽesame, a chifré la. A gũus n yãkẽ organisation partenaire.
```

## `status_TRANSMIS`

**FR**

```
Pris en charge
```

**MOS**

```
Yãkame n tʋm
```

## `status_TRANSMIS_help`

**FR**

```
Une organisation partenaire l'a lu et s'en occupe.
```

**MOS**

```
Organisation partenaire yãkame n ges yãmb wilgã la a tʋm ne a.
```

## `status_CLOTURE`

**FR**

```
Clôturé
```

**MOS**

```
Kẽesã wã wã
```

## `status_CLOTURE_help`

**FR**

```
Le dossier est terminé. Vous pouvez signaler à nouveau si la situation continue.
```

**MOS**

```
Dossierã wã kẽesame. Sẽn yaa yãmb pʋgẽ wã n lebg n kẽes, yãmb tõe n wilgẽ n lebg.
```

## `resources_title`

**FR**

```
Ressources d'aide
```

**MOS**

```
Sõngã ressources
```

## `resources_filter_region`

**FR**

```
Filtrer par région
```

**MOS**

```
Yãk région
```

## `resources_all_regions`

**FR**

```
Toutes les régions
```

**MOS**

```
Région fãa
```

## `resources_call`

**FR**

```
Appeler
```

**MOS**

```
Yãk téléphonã
```

## `resources_national`

**FR**

```
National
```

**MOS**

```
National
```

## `resources_unverified`

**FR**

```
Numéro à confirmer
```

**MOS**

```
Numéro sẽn ka yɩɩlga
```

## `resources_none`

**FR**

```
Aucune ressource trouvée pour ce filtre.
```

**MOS**

```
Sõngã ressource ka ning ne yãmb filtre wã.
```

## `cat_URGENCE`

**FR**

```
Numéros d'urgence
```

**MOS**

```
Numéros d'urgence
```

## `cat_SANTE`

**FR**

```
Santé et soutien aux victimes
```

**MOS**

```
Saaga la sõngã ne victimes
```

## `cat_JUSTICE`

**FR**

```
Police, gendarmerie, justice
```

**MOS**

```
Polis, gendarmerie, justice
```

## `cat_ONG`

**FR**

```
ONG et humanitaires
```

**MOS**

```
ONG la organisations humanitaires
```

## `nav_home`

**FR**

```
Accueil
```

**MOS**

```
Yir
```

## `nav_resources`

**FR**

```
Ressources
```

**MOS**

```
Sõngã
```

## `nav_track`

**FR**

```
Suivi
```

**MOS**

```
Suivi
```

## `footer`

**FR**

```
Service anonyme. Vos données sont chiffrées de bout en bout.
```

**MOS**

```
Sõngã wã yaa anonyme. Yãmb data fãa chifré la.
```

## `bot_welcome`

**FR**

```
Bonjour, ici *Boodou* 🛡️
Service anonyme de signalement et d'aide.

Choisissez votre langue / Yãk y buud-gomde / I ka kan sugandi :
1 - Français
2 - Mooré
3 - Dioula
```

**MOS**

```
Ne yibeo *Boodou* 🛡️
Sõngã sẽn ka yãmb yĩnga n wilgẽ la n sõngã.

Yãk yãmb gomde / Yãk y buud-gomde / I ka kan sugandi :
1 - Français
2 - Mooré
3 - Dioula
```

## `bot_menu`

**FR**

```
Que cherchez-vous ?

1 - Signaler un incident
2 - Ressources d'aide (violences faites aux femmes)
3 - Ressources d'aide (sécurité)
4 - Parler à quelqu'un
5 - Suivre un signalement
6 - Effacer cette conversation

_Urgence : Police 17 · Gendarmerie 16 · Pompiers 18_
```

**MOS**

```
Bõn-bõn la yãmb na n yãkẽ ?

1 - Wilgẽ bõn-bõn sẽn yĩngẽ
2 - Sõngã (wãsgã ne pagba)
3 - Sõngã (sécurité)
4 - Gomd ne ned
5 - Tõogẽ n yãk yãmb wilgã
6 - Yãk gomdã wã fãa n yĩngẽ

_Urgence : Polis 17 · Gendarmerie 16 · Pompiers 18_
```

## `bot_invalid`

**FR**

```
Je n'ai pas compris. Répondez avec le numéro de votre choix.
Tapez 0 pour revenir au menu.
```

**MOS**

```
Mam ka ning yãmb gomdã. Yãk chiffre sẽn yaa yãmb yĩngẽ.
Tõogẽ 0 n lebg n menuyã.
```

## `bot_ask_type`

**FR**

```
De quoi s'agit-il ?

1 - Violence physique
2 - Menace ou intimidation
3 - Violence faite à une femme ou une fille
4 - Attaque ou activité terroriste

0 - Retour au menu
```

**MOS**

```
Bõn-bõn la wãsgã ?

1 - Wãsgã ne yãmb yĩngẽ
2 - Yãmb yĩngẽ wall yãmb sɩdga
3 - Wãsgã sẽn tʋm ne paga wall biiga
4 - Kẽerga wall tʋʋm sẽn yaa terroriste

0 - Lebg n menuyã
```

## `bot_ask_region`

**FR**

```
Dans quelle région ? (approximatif, jamais votre adresse)

{regions}

0 - Retour au menu
```

**MOS**

```
Région wã yaa bõn-bõn ? (ka yaa yãmb yirã, approximation bala)

{regions}

0 - Lebg n menuyã
```

## `bot_ask_region_optional`

**FR**

```
Dans quelle région cherchez-vous de l'aide ?

{regions}

99 - Peu importe / national
0 - Retour au menu
```

**MOS**

```
Région bõn-bõn la yãmb na n yãk sõngã ?

{regions}

99 - Ka yaa yĩnga / national
0 - Lebg n menuyã
```

## `bot_ask_description`

**FR**

```
Décrivez ce qui s'est passé, en quelques phrases.
⚠️ Ne donnez aucun nom ni numéro de téléphone.

🔒 Votre message sera chiffré : seule l'organisation partenaire pourra le lire.

0 - Annuler
```

**MOS**

```
Gomd sẽn yĩngẽ wã, gomd ne yãmb gomdã ne sõma.
⚠️ Wẽnd n ka yãk ned yĩngã wall téléphone.

🔒 Yãmb gomdã wã chifré la a ye : organisation partenaire bala la na n tõe n yãk a.

0 - Yãk n yĩnga
```

## `bot_report_done`

**FR**

```
✅ *Merci.* Votre signalement a été envoyé de façon anonyme et chiffrée.
Aucune information permettant de vous identifier n'a été conservée.
```

**MOS**

```
✅ *Barka.* Yãmb wilgã wã tʋmame n ka yãk yãmb yĩnga la a chifré.
Bõn-kãnga fãa sẽn tõe n wilg yãmb yĩnga ka ningẽ.
```

## `bot_report_code`

**FR**

```
🔑 *Votre code de suivi : {code}*

Notez-le sur un papier, pas dans ce téléphone. Tapez 5 au menu pour savoir plus tard ce qu'est devenu votre signalement. C'est le seul moyen : nous n'avons aucune autre façon de vous reconnaître.
```

**MOS**

```
🔑 *Yãmb suivi code : {code}*

Gũs n yãk a ne paper, ka téléphone wã pʋgẽ. Tõogẽ 5 n lebg n yãk bõn-bõn sẽn yĩngẽ ne yãmb wilgã. A yaa nẽ code bala : ka bõn-kãnga wã sẽn na n sõng n yãmb yĩnga.
```

## `bot_ask_code`

**FR**

```
Entrez votre code de suivi (10 caractères, par exemple K7M3P-QR8TZ).

0 - Retour au menu
```

**MOS**

```
Kẽes yãmb suivi code (gomd 10, misaal K7M3P-QR8TZ).

0 - Lebg n menuyã
```

## `bot_track_not_found`

**FR**

```
Aucun signalement ne correspond à ce code. Vérifiez les caractères et réessayez.
```

**MOS**

```
Wilgã ka ning ne code wã. Yãk n ges lettres la chiffresã, n tʋʋm n lebg.
```

## `bot_track_too_many`

**FR**

```
Trop de tentatives. Réessayez dans un quart d'heure.
```

**MOS**

```
Yãmb tʋmã wã yaa wãsgã. Gũs 15 minutes n tʋʋm n lebg.
```

## `bot_track_result`

**FR**

```
🔑 *{code}*

État : *{status}*
{help}

Envoyé le {sent}.
```

**MOS**

```
🔑 *{code}*

Yãmb wilgã wã : *{status}*
{help}

Tʋmã le {sent}.
```

## `bot_track_note`

**FR**

```


💬 *Message de l'organisation partenaire :*
{note}
```

**MOS**

```


💬 *Organisation partenaire sẽn tʋm gomd :*
{note}
```

## `bot_resources_intro`

**FR**

```
Ressources disponibles :
```

**MOS**

```
Sõngã sẽn tõe n sõng yãmb :
```

## `bot_resources_none`

**FR**

```
Aucune ressource trouvée pour cette région. Voici les numéros nationaux :
```

**MOS**

```
Sõngã ka ning ne région wã. Yãmb tõe n yãk numéros nationaux :
```

## `bot_back_hint`

**FR**

```


Tapez 0 pour revenir au menu.
```

**MOS**

```


Tõogẽ 0 n lebg n menuyã.
```

## `bot_talk`

**FR**

```
Vous n'êtes pas seul(e). Voici des lignes d'écoute confidentielles :
```

**MOS**

```
Yãmb ka yaa yĩngã bala. Sõngã sẽn tõe n yãk yãmb gomdã ne confidence :
```

## `bot_call`

**FR**

```
Appeler
```

**MOS**

```
Yãk téléphonã
```

## `bot_unverified`

**FR**

```
(à confirmer)
```

**MOS**

```
(sẽn ka yɩɩlga)
```

## `bot_wipe`

**FR**

```
🧹 *Effacé de notre côté.*
Votre langue et votre menu en cours sont oubliés. Nous n'avons jamais eu votre numéro en clair, et rien de cette conversation n'est gardé chez nous.

⚠️ *Mais cette discussion est sur VOTRE téléphone.* Nous n'avons aucun moyen de l'effacer à distance. Vous seul(e) pouvez le faire, en 3 gestes :

📱 *Android*
1. Retour à la liste des discussions
2. Appui long sur cette discussion
3. Touchez l'icône 🗑️

📱 *iPhone*
1. Retour à la liste des discussions
2. Glissez cette discussion vers la gauche
3. « Plus » puis « Supprimer »

💡 *Pour que ça s'efface tout seul la prochaine fois :* ouvrez cette discussion, touchez le nom en haut, puis « Messages éphémères » → *24 heures*. Tout ce qu'on s'écrit disparaîtra ensuite sans que vous ayez à y penser.

_Écrivez « Bonjour » quand vous voulez revenir._
```

**MOS**

```
🧹 *Yãmb gomdã wã kẽesã wã pʋgẽ fãa kẽesame.*
Yãmb gomde la yãmb menuyã wã ka ningẽ. Tɩɩmã pʋgẽ, tõogẽ n yãk yãmb numéro ne yãmb yĩnga, la bõn-kãnga wã ka ning yãmb pʋgẽ.

⚠️ *La gomdã wã yaa yãmb téléphone wã pʋgẽ.* Tõogẽ ka ningẽ n yãk a ne yãmb téléphone tɩɩmẽ. Yãmb bala la tõe n yãk a, ne tʋʋmã 3 :

📱 *Android*
1. Lebg n kẽes discussionsã wã list pʋgẽ
2. Gũs ne yãmb n yãk gomdã wã
3. Tõogẽ 🗑️

📱 *iPhone*
1. Lebg n kẽes discussionsã wã list pʋgẽ
2. Yãk gomdã wã n zĩigã n kẽesẽ
3. « Plus » n yãk « Supprimer »

💡 *Sẽn na n yãk a yɩɩlẽ tɩɩmẽ :* kẽes gomdã wã pʋgẽ, yãk yãmb yĩngẽ ne yãmb yĩngã, n yãk « Messages éphémères » → *24 heures*. Gomdã fãa na n yãkẽ tɩɩmẽ ne yãmb ka na n tʋʋm bõn-kãnga.

_Gomd « Bonjour » tɩ yãmb na n lebg._
```

## `bot_wipe_hint`

**FR**

```


🧹 Tapez *EFFACER* pour savoir comment supprimer cette conversation de votre téléphone.
```

**MOS**

```


🧹 Tõogẽ *EFFACER* n yãk bõn-bõn sẽn na n sõng yãmb n yãk gomdã wã ne yãmb téléphone.
```

## `bot_session_expired`

**FR**

```
Votre session a expiré. On recommence :
```

**MOS**

```
Yãmb sessionã wã kẽesame. Tõogẽ n lebg n tʋʋm :
```
