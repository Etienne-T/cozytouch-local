# Cozytouch — écritures IC3 et CETHI, sondes Calypso

Analyse statique locale du 18 novembre 2026. Les captures citées datent du 17 novembre et ne vérifient pas l’état actuel des appareils. L’enquête du 6 avril reste un historique distinct (`../../COZYTOUCH_ANALYSIS.md:3`, `../../REPRISE.md:7`). Aucun accès réseau ou matériel. Aucune trame d’écriture complète ni outil d’émission n’est fourni.

**Conclusion : garder les écritures fermées.** Le catalogue CETHI V4 établit les commandes et leurs conversions métier. Pour l’IC3, les états et les codecs sont identifiés, mais la liaison native des écritures reste à établir. Les trois températures de sonde sont fortement corroborées, pas confirmées par un codec propre à chaque voie.

**Preuves :** **Code** = comportement montré par les sources locales ; **Observé** = capture antérieure ; **Inféré** = rapprochement étayé ; **Inconnu** = preuve manquante. Sauf indication contraire, les références partent de `analyse-2026-11-17/`. **Catalogue** = `lua/all/appsB/overkiz/io-homecontrol/lib/Overkiz/knowledge/io/devices.lua`. Les fichiers `*utils.module.lua` cités sont dans `lua/all/appsB/overkiz/lib/lua/Overkiz/knowledge/`. Les indices et numéros de paramètres désignent des champs du protocole, pas des appareils uniques.

## IC3 52/1 — sèche-serviettes ASAMA

**Code — lecture.** `ModeSsvPiece` (`0x0136`), `TemperatureConsigneEffectiveSsv` (`0x0137`) et `TemperatureConsigneConfortSsv` (`0x0138`) déclarent `READ`. `0x0137` est la consigne en vigueur ; `0x0138` est la cible confort exposée comme `core:TargetTemperatureState`. Les deux consignes sont des entiers non signés sur 16 bits, petit-boutistes, divisés par 10. Le mode tient sur un octet.

*Sources :* `lua/embedded/3c63932b887e/ModeSsvPiece.lua:1`, `lua/embedded/4131e96d2890/TemperatureConsigneEffectiveSsv.lua:1`, `lua/embedded/9bc057c2a3ff/TemperatureConsigneConfortSsv.lua:1` ; `Catalogue:21704`, `:21716`, `:21850`, `:2551`, `:3612`, `:71941` ; `continuation-radio/RESULTAT.md:34`.

| Action | Codec montré par le code | Liaison à l’écriture IC3 |
|---|---|---|
| Consigne | `setElectricalTowelDryerTargetTemperature` produit un `u16` petit-boutiste en dixièmes de °C. La résolution de 0,1 °C ne prouve pas le pas accepté. | **Inconnue.** Le helper ne choisit aucun registre. Aucun alias entre `0x0138` (état IC3) et `0x0103` (confort Adelis) n’est établi. `0x0137` n’est pas une cible d’écriture validée. |
| Mode | `setTowelDryerOperatingMode` produit un octet : `standby=0`, `auto=1`, `internal=2`, `external=3`. Le décodeur renvoie `external` par défaut hors 0–2 ; ce défaut ne valide pas d’autres valeurs à l’écriture. | **Inférée pour le codec**, **inconnue pour l’écriture** : `0x0136` est lié au décodeur en lecture, pas au setter dans le corpus consulté. Ces valeurs ne signifient pas confort, éco, hors-gel et arrêt. |

*Sources :* `common-atlantic-utils.module.lua:831`, `:1090`, `:1096` ; `io-atlantic-utils.module.lua:2` ; `Catalogue:3612`, `:71941` ; `direct-devices/IC3-CONSIGNE.md:7`, `:23`.

**Ne pas transposer Adelis.** Ce profil voisin distingue confort (`0x0103`) et dérogation temporaire (`0x011D`) selon la période du programme. Un autre helper OEM encode une température en FP12 normalisé, mais aucun lien avec IC3 n’est établi. Les bornes, le registre selon le mode, l’ACK et l’effet exact restent inconnus. L’absence de table `commands` dans l’entrée IC3 du catalogue décompilé n’exclut pas une liaison ailleurs (`direct-devices/IC3-CONSIGNE.md:7`, `:19`, `:23` ; `io-atlantic-utils.module.lua:4`).

## CETHI V4 51/0 — chauffe-eau Calypso

**Code — liaison au composant.** L’entrée CETHI V4 (`Catalogue:72406`) sélectionne `slot4[604]`, qui référence `slot4[441]` comme table `commands` (`:35477`). Les commandes ci-dessous proviennent de cette table (`:33079`, `:33098`), pas d’une table d’alias d’une autre variante.

| Commande OEM | Paramètre et valeur métier | Limite de preuve |
|---|---|---|
| `setTargetTemperature` numérique | Écriture MP `65537`. Pour `T` en °C : `arrondi(((T + 273,15) × 100 − min) × 51200 / (max − min))`. Les états `65558` et `65559` fournissent min/max en centièmes de kelvin. Les valeurs dans l’intervalle se codent sur `0–51200`. | Le prototype `0–100 °C` ne fixe pas les bornes sûres. Le convertisseur rejette des bornes absentes, mais ne contrôle pas les bornes égales ou inversées ni une consigne hors intervalle. `Catalogue:27324`, `:30543`, `:32987` ; `io-utils.module.lua:369`, `:381`. |
| `setTargetTemperature` avec libellé | Même MP : `comfort → 0xD80F`, `eco → 0xD812`, `halted → 0xD813`, `secured → 0xD80A`, `anti-frost → 0xD816`. Ce sont des sélecteurs de consigne, pas des degrés ni des modes généraux. | **Code** pour les mots ; **inconnu** pour l’acceptation réelle. Le prototype indique `antifrost`, mais le convertisseur compare `anti-frost`. Garder cette option fermée tant que la divergence n’est pas résolue. `Catalogue:2436`, `:32992`, `:18800`. |
| `setDHWMode` | Écriture privée Atlantic, indice `0x0006` (paramètre `201328129`), Blob d’un octet : `autoMode=0`, `manualEcoActive=1`, `manualEcoInactive=2`. | Le convertisseur laisse `0` par défaut : rejeter les libellés inconnus au lieu de basculer en automatique. Le module d’état déclare `READ` ; la commande catalogue porte `w`. ACK WRITE non observé. `Catalogue:2350`, `:32841`, `:33065`, `:33085`, `:18914` ; `lua/embedded/021062175132/Mode.lua:1`. |
| `setCurrentOperatingMode` | Écriture d’activation `65554` : MP `0xD400`, FP16 `0x4600` pour absence, `0x4A00` pour normal (absence et relance désactivées), `0x4900` pour relance/Boost. Le helper refuse les autres combinaisons. | **Code** pour la charge métier ; **inconnu** pour l’effet de bout en bout. Revenir au normal n’arrête pas le ballon. L’absence n’est pas démontrée équivalente au sélecteur `anti-frost`. `Catalogue:27678`, `:32832`, `:33084` ; `io-atlantic-utils.module.lua:37`. |

**Durées et consignes de référence séparées.** `setAwayModeDuration` vise le privé `0x0005`, accepte `0–99` ou `always` (octet 255). `setBoostModeDuration` vise `0x0000`, accepte `1–7` (un octet). Ce sont des domaines de prototype, pas des prescriptions d’utilisation. Le choix de mode ne doit pas modifier la durée implicitement. Les réglages de référence confort, éco, hors-gel et `halted` sont distincts du choix via MP. Aucun arrêt global ni changement des consignes de référence n’est qualifié ici (`Catalogue:2323`, `:32796`, `:32820`, `:33079`, `:30555`, `:32866`, `:32904`, `:32919`).

## UART, radio et fin de transaction

**Code — enveloppe.** Le lien Linux–STM32 utilise `02 | groupe:u8 | commande:u8 | longueur:u16 BE | charge | CRC8(charge) | 03`. Le CRC-8 (polynôme `0x07`, initialisation et XOR final nuls, sans réflexion) couvre la charge seule. Le corpus répertorie 24 commandes entrantes et 52 callbacks déclarés. Il n’y a pas d’identifiant universel de transaction. Un code UART n’est ni un identifiant de paramètre ni un opcode RF (`continuation-radio/stm-real/RESULTAT.md:40`, `:46`, `:61`).

| Chemin | Charge et direction | ACK et limite |
|---|---|---|
| **READ MP — observé sur IC3 et CETHI** | `65537`, `READ=true`, Blob vide. UART TX `0x0100`, charge de 39 octets : sous-commande `ACTIVATE_STATUS_REQUEST=1`, champ conditionnel `legacySize`, `MAIN_INFO`, aucun FP demandé. | RX `0x010D` (`ACTIVATE_ACK`, charge de 28 octets sur ces captures), CRC valide. Fin `DONE` ; `0/5/0` signifie accepté / terminé / détail nul. Le couple `1/1` du callback Linux identifie `IoCommandNoError` : ce n’est pas le triplet TSD. `continuation-radio/stm-real/ADDENDUM-LECTURES-QUALIFIEES.md:11`, `:23` ; `client-autonome/RESULTAT.md:16` ; `live-interface/offline-stm32/LECTURES-APPAREILS.md:9`. |
| **WRITE MP / activation — code, non observé sur ces appareils** | Valeur MP `u16` BE ; masque des FP1–8 puis leurs mots sélectionnés ; masque des FP9–16 puis leurs mots sélectionnés, eux aussi `u16` BE. Le TSD complet comporte aussi l’origine et l’ACEI (priorité, service, type d’information). Le STM32 reconnaît la branche `ACTIVATE_FUNC=0` dans le chemin de mouvement. | Le schéma `ACTIVATE_ACK` prévoit l’information de base, le détail d’exécution et des données selon le contexte. Le Lua UART consulté ne décrit les données que pour la branche statut : ne pas reprendre `legacySize`, la taille ou `MAIN_INFO` de la READ. Aucun ACK WRITE CETHI n’est qualifié. `io-utils.module.lua:165` ; `lua/embedded/053ce0207326/AbstractActuator.lua:22` ; `lua/embedded/2a6a7fc7bc0b/TSDDefinitions.lua:104`, `:136`, `:936` ; `lua/embedded/4b808c3b915d/MovementOrderSubCommand.lua:5` ; `lua/embedded/ff02a5459c55/FrameDefinition.lua:330` ; `continuation-radio/stm-real/focused-existing-decompilation.c:1444`. |
| **Privé Atlantic — code et READ observé** | UART TX `0x0101`, sous-type privé, longueur legacy conditionnelle. `GenericV2` construit fabricant, code d’accès, indice `u16` BE et Blob. Le code d’accès est `0x61 − accès` : `READ=true` donne `0x60` et Blob vide ; `WRITE=false` donne `0x61` avec la valeur dans le Blob. Ne pas généraliser cette règle à toutes les variantes privées. | Les sondes ont reçu `0x040C` avec corrélation et CRC valide ; étiquette UART `LISTENER__PRIVATE_COMMAND_ACK`. Le TSD privé prévoit un champ fabricant et des données privées éventuelles. Ce callback ne prouve pas la forme ni l’effet d’une écriture sur `0x0006` ou sur IC3. `lua/embedded/ff02a5459c55/FrameDefinition.lua:468` ; `lua/embedded/2a6a7fc7bc0b/TSDDefinitions.lua:996` ; `lua/embedded/4a4bfad42f81/commandModel.lua:68` ; `live-interface/offline-stm32/atlantic-private.c:165` ; `continuation-radio/stm-real/interface-matrix.json:891` ; `service-local/RESULTAT.md:30`. |

**Ne pas confondre les sens ni les couches.** `0x0102` désigne `SET_BEACON` en entrée et `ACTIVATE_FUNC` dans la liste des callbacks : ce n’est pas un code TX d’activation (`continuation-radio/stm-real/interface-matrix.json:51`, `:251`). CRC valide, ACK UART/RF, statut final Linux et état relu ne prouvent pas la même chose. Le processeur OEM peut marquer une commande `DONE` à partir de `COMMAND_ACCEPTED` ; `DONE` seul ne prouve donc pas le changement d’état (`lua/embedded/4e3f45d67da7/EventProcessor.lua:48`, `continuation-radio/stm-real/RESULTAT.md:144`).

## Trois sondes Calypso

**Observé le 17 novembre.** Les réponses privées contiennent chacune un Blob de six octets. Le routeur vérifie l’indice BE aux offsets 2–3 du message privé (base zéro), retire les quatre octets de préfixe puis publie le Blob. Le mot candidat est donc aux offsets 4–5 du **message privé**, ou 0–1 du **Blob**, pas du paquet UART (`service-local/RESULTAT.md:30` ; `client-autonome/aqua/qualification/QUALIFICATION.md:35`, `:37`).

| Sonde | Indice | Premier mot brut | Conversion candidate |
|---|---|---:|---:|
| Air entrant | `0x001A` | 216 | 21,6 °C |
| Évaporateur bas | `0x001B` | 216 | 21,6 °C |
| Évaporateur haut | `0x001C` | 217 | 21,7 °C |

**Code pour la sonde d’eau `0x0017`, inférence forte pour les trois sondes ci-dessus.** Le catalogue relie la sonde d’eau au codec `i16 BE ÷ 10` : entier signé en complément à deux, 0,1 °C par unité, décalage nul. Ne pas appliquer le décalage de 273,15 de la consigne MP. Les trois modules déclarent `READ`, mais aucun lien avec le codec d’eau n’a été retrouvé. Les quatre octets suivants restent non interprétés. Une nouvelle valeur simplement plausible ne lèverait pas cette incertitude.

*Sources :* `Catalogue:2296`, `:18993` ; `rea/ByteArray-focused.c:289` ; `lua/embedded/bdf969ea2a23/SondeAirEntrant.lua:1`, `lua/embedded/b582f86f623b/SondeEvaporateurBas.lua:1`, `lua/embedded/1ae8fe9b6c52/SondeEvaporateurHaut.lua:1` ; `service-local/sondes-conversion/RESULTAT.md:7`, `:17`, `:24`.

## Garde-fous avant toute écriture

1. **Fermer par défaut.** Exiger une validation distincte de la cible, de l’opération, de la valeur et de la fenêtre. Autoriser uniquement les couples profil/opération qualifiés, sans commande brute ni valeur inconnue. Garder l’IC3 non inscriptible tant que la liaison manque. Exclure appairage, protections, anti-légionellose, programmation et écritures persistantes du hub.
2. **Vérifier avant d’agir.** Relire l’état et les bornes sur la cible exacte. Vérifier la fraîcheur, l’unité, l’ordre des bornes, le pas accepté et le mode actif. Refuser un état périmé ou une confusion entre cible, dérogation et consigne effective. Présenter l’effet attendu et l’état initial à la personne qui valide. Ne modifier aucune durée implicitement.
3. **Sérialiser et corréler.** Garder un seul propriétaire UART et une seule transaction en vol. Vérifier sens, groupe, type, taille, CRC et contexte ou indice. Isoler les notifications asynchrones et les réponses tardives. Journaliser les états et décisions, sans secrets ni trames privées.
4. **Éviter les ordres involontaires.** Utiliser une demande unique, non retenue dans MQTT, avec expiration et déduplication. Ne pas émettre si l’état demandé est déjà confirmé. Une relance répétée peut réarmer la durée : ne pas supposer l’idempotence. Ne rien rejouer automatiquement après délai dépassé, reconnexion ou redémarrage. Une perte d’ACK ne prouve pas une absence d’effet.
5. **Vérifier l’effet, puis arrêter en cas de doute.** Exiger une relecture indépendante du bon état, sans écho optimiste dans Home Assistant. Si le résultat est ambigu, fermer les écritures et revenir au diagnostic en lecture seule. Restaurer l’état initial si nécessaire constitue un nouvel ordre à valider, pas une annulation automatique.

Ces recommandations répondent aux limites de corrélation et de fin de commande (`continuation-radio/stm-real/RESULTAT.md:40`, `:138`, `:144`) et au risque de confondre les consignes (`direct-devices/IC3-CONSIGNE.md:7`).

## Vérifications à autoriser séparément

- **IC3 :** établir la commande OEM et le registre selon l’action et le mode ; vérifier la cible stockée et la consigne effective. Ne pas essayer d’indices candidats à l’aveugle (`direct-devices/IC3-CONSIGNE.md:23`).
- **CETHI :** relever les bornes, le pas et l’état initial en lecture. Si un essai est autorisé, corréler l’ordre OEM borné à sa réponse UART/RF, à la fin Linux et à une relecture indépendante. Qualifier séparément consigne MP, mode ECS et absence/relance (`continuation-radio/stm-real/ADDENDUM-LECTURES-QUALIFIEES.md:11` ; `Catalogue:33080`).
- **Sondes :** comparer en lecture seule les trois voies à un diagnostic indépendant sur plusieurs états thermiques. Contrôler l’association des voies, l’échelle, le signe et le décalage. Laisser les quatre octets suivants non interprétés faute de preuve (`service-local/sondes-conversion/RESULTAT.md:24`).
