# Parité Home Assistant : consigne du chauffe-eau et capteurs du sèche-serviettes — 20 novembre 2026

Recherche **hors ligne**. Aucun accès réseau, SSH, MQTT ou hub. Aucune commande d'appareil ni émission radio. Aucune modification de `analyse-2026-11-18/persistance-banque-a/phase2/`. Aucun fichier privé n'a été lu. Seule exception : deux extraits masqués du cache d'états du 17 novembre (`analyse-2026-11-17/live-interface/states-cache-01.txt`), dont la valeur était déjà citée dans `live-interface/offline-api/README.md:26`. Les URL d'appareils y sont masquées.

Sources principales :
- catalogue OEM : `analyse-2026-11-17/lua/all/appsB/overkiz/io-homecontrol/lib/Overkiz/knowledge/io/devices.lua`, noté **`devices.lua`** ;
- démon natif : `analyse-2026-11-17/extracted/appsB/overkiz/io-homecontrol/lib/ovk/iovp/Daemon.so`, noté **`Daemon.so`** ;
- schémas Lua embarqués : `analyse-2026-11-17/lua/embedded/`, noté **`embedded/`**.

Les adresses `0x…` sans autre précision sont des adresses ELF de `Daemon.so`. Les scripts et extraits de ce dossier sont décrits à la fin.

---

## 1. Chauffe-eau CETHI V4 : consigne en °C

### 1.1 Ce que calcule l'OEM

Le composant `slot4[604]` (`devices.lua:35379-35478`) relie les états bruts aux états de haut niveau.

| État brut | Lien | État calculé | Convertisseur |
|---|---|---|---|
| `65537` (MP, valeur courante) | `slot4[237]`, `devices.lua:30518-30528` | `core:TemperatureState` (`slot2[71]`, `devices.lua:15127`) | `fromRawTemperatureValue(65537, 65558, 65559)`, `devices.lua:1030-1037` |
| `16830720` = `0x0100D100` (cible) | `slot4[381]`, `devices.lua:32500-32515` | `core:TargetTemperatureState` (`slot2[373]`, `devices.lua:18797-18836`) | alias éventuel, puis `fromRawTemperatureValue(cible, 65558, 65559)`, `devices.lua:2249-2258` |
| `65558`, `65559` | `slot4[368]`, `slot4[369]`, `devices.lua:32358-32387` | recalcul de tous les états de température ci-dessus | — |

Formule (`analyse-2026-11-17/lua/all/appsB/overkiz/lib/lua/Overkiz/knowledge/io-utils.module.lua:369-379`) :

```
T = round((raw × (max − min) / 51200 + min) / 100 − 273,15 ; 1)   si 0 ≤ raw ≤ 51200, sinon nil
```

`min` = état 65558 et `max` = état 65559, en centièmes de kelvin.

**Conséquence pour notre valeur.** Le hub lit `raw = 51200` pour la cible et pour la valeur courante (`analyse-2026-11-17/live-interface/offline-stm32/LECTURES-APPAREILS.md`). La formule donne alors `T = max/100 − 273,15`, **quel que soit `min`**. Pour obtenir 62,0 °C, il faut `max` entre 33510 et 33519, très probablement **33515 (`0x82EB`)**. Cette constante 29315/33515 (20–62 °C) est codée en dur dans un autre profil du catalogue (`slot2[643]`). Contrôle synthétique : check_formula.out (non publié).

**Corroboration :** le cache local du hub du 17 novembre contenait déjà `core:TemperatureState = 62` et `core:TargetTemperatureState = 62` pour le CETHI (`states-cache-01.txt`, extrait masqué ; `offline-api/README.md:26`). L'OEM disposait donc des bornes. Avec raw = 51200, ces bornes donnent 62.

**Ce qu'il manque :** `min` est inconnu. Il compte dès que la cible passe sous 51200.

### 1.2 Comment l'OEM lit 65558 et 65559 : une demande de statut séparée par borne

Ce ne sont **ni** des paramètres fonctionnels (FPI) de MAIN_INFO **ni** une lecture privée Atlantic. Chaque borne est lue par **son propre ACTIVATE_STATUS_REQUEST**, avec le type étendu `DEFAULT_MIN` ou `DEFAULT_MAX` à la place de `MAIN_INFO`.

Preuves, dans l'ordre de la chaîne :

1. **Définitions Lua.**
   - `embedded/31ce13eb47b6/DefaultValueMin.lua:1-3` : paramètre 65558, `READ`, `startup = true`.
   - `embedded/5d34cc4d077e/DefaultValueMax.lua:1-3` : paramètre 65559, mêmes options.
   - Il n'y a pas d'intervalle : l'OEM lit les bornes **une fois, au démarrage**. Ce sont des constantes de l'appareil.
2. **Enregistrement natif commun à tous les actionneurs io.**
   - `ParameterManager::initAllParameter` (`0x131528`) appelle `IoProfileActuatorCommon::createParameter` à `0x131564`.
   - Celle-ci construit deux `IoDefaultValue` (`0x145c98`, `0x145d74`). Leurs identifiants sont les littéraux `0x00010016` et `0x00010017` (`0x146a7c`, `0x146a80`).
   - Arguments octets (1, 1, 0) : le constructeur `Parameter` (`0x12e298`) les range à `+56`, `+57`, `+58` (`0x12e34c-0x12e378`). L'identifiant 64 bits est à `+40` (`Parameter::getId`, `0x12d4c0` : `ldrd r0, [r0, #40]`).
3. **Construction de la demande.**
   - `IoDefaultValue::create` (`0x139bdc`) vérifie l'accès, puis appelle `getDefaultValue` (`0x139a18`).
   - Celle-ci calcule `type = (octet bas de l'identifiant) & 7` (`0x139a24`, `0x139a44`). Pour 0x16 on obtient **6 = DEFAULT_MIN** ; pour 0x17, **7 = DEFAULT_MAX** (`embedded/6d09f61d4748/ExtendedInformationType.lua:29-30` ; `MAIN_INFO = 3` à la ligne 26).
   - Elle construit le vecteur `[3, type, 0, 0]` (`0x139a5c-0x139ae0`), puis appelle l'entrée de vtable `+20` avec `sous-commande = 1` et `longueur = 4` (`0x139af0-0x139b1c`).
   - Cette entrée est `Parameter::fillActuatorFoldable(Foldable&, Command, Node, u8, u16, const u8*, bool)` (relocation `0x259214` de la vtable `IoDefaultValue`).
   - Cette fonction (`0x12ee08`) pose l'en-tête `+57 = 1` et la commande `+58 = 0` (`0x12ef14-0x12ef28`), soit l'UART `0x0100`, `ACTUATOR_MANAGEMENT__MOVEMENT_ORDER = 256` (`embedded/23fc49b604cd/DaughterboardApiCommand.lua:27`). Elle pose ensuite la sous-commande 1 par `FoldableRemoteActuatorToSend::setCommand` (`0x12efd4-0x12efdc`).
4. **Schéma Linux identique à la lecture MAIN_INFO déjà qualifiée.**
   - `MovementOrderSubCommand.lua:6` : `ACTIVATE_STATUS_REQUEST = 1`.
   - `embedded/3c9a6ee11111/FrameDefinition.lua:330-356` : `subCommand`, puis `legacySize`, conditionnel à `ACTIVATE_STATUS_REQUEST`, puis les données TSD.
   - `embedded/2a6a7fc7bc0b/TSDDefinitions.lua:650-935` : `extendedInformationTypeMp` (u8, énuméré par `ExtendedInformationType`), puis `fpi1`, les types FP conditionnels, puis `fpi2`.
5. **Traitement de la réponse.** `IoMainAndFunctionalParameter::mpFpAck` (`0x140240`) traite le cas suivant :
   - si l'identifiant de la commande vaut `0x10016` ou `0x10017` (`0x140494-0x1404cc`), il lit `data[2] << 8 | data[3]` (u16 gros-boutiste) après basicInfo et detailedStatus (`0x1404d0-0x1404f8`) ;
   - il crée `State(nœud, identifiant, IoInt64(valeur))` (`0x140570`, `0x1405b0`), le transmet au gestionnaire d'états, puis passe la commande à `DONE = 5` (`0x140698-0x1406a4`).

   Extrait : mpFpAck.txt (non publié), lignes 148-200.

### 1.3 Octets UART exacts

**Demandes** (après les 34 octets de contexte, identiques à la lecture MAIN_INFO) :

| Lecture | Fin de charge utile | Charge utile | Trame |
|---|---|---|---|
| Borne basse 65558 | `01 03 06 00 00` | 39 octets | `02 01 00 00 27 <ctx 34> 01 03 06 00 00 <crc8> 03` |
| Borne haute 65559 | `01 03 07 00 00` | 39 octets | `02 01 00 00 27 <ctx 34> 01 03 07 00 00 <crc8> 03` |
| (référence) MAIN_INFO | `01 03 03 00 00` | 39 octets | inchangée |

`01` = ACTIVATE_STATUS_REQUEST, `03` = legacySize, `06`/`07` = type étendu, `00 00` = FPI1/FPI2. Le CRC8 (poly 0x07) se calcule sur la charge utile, comme aujourd'hui.

**Réponse attendue :** UART `0x010d` (`ACTUATOR_MANAGEMENT__ACTIVATE_ACK = 269`, `embedded/39a18ee538e5/DaughterboardApiCallback.lua:56`), **20 octets** au lieu de 28. En-tête générique `slot25` (`FrameDefinition.lua:19` et `:897`) ; TSD `ACTIVATE_ACK` (`TSDDefinitions.lua:936-950`, basicInformation `:102-126`) ; bloc dépendant du contexte : `ExtendedInformationDefinition.lua:77-88` (`DEFAULT_MIN`/`DEFAULT_MAX` = UINT_16) et `:265-589` (objet MP, puis `fpi1`, puis `fpi2`).

| Octets (base 1, comme `uart.lua`) | Champ | Contrôle |
|---|---|---|
| 1–4 | RSSI i32 BE | — |
| 5–7 | adresse de l'appareil | = cible |
| 8–10 | adresse du hub | = source |
| 11 | frameType | 0 (IO) |
| 12–13 | ctrl0, ctrl1 | bit 1W nul |
| 14 | commandId | 4 = ACTIVATE_ACK (`embedded/32747b462d47/Command.lua:44`) |
| 15 | basicInformation | commandStatus 0, executeStatus 5 |
| 16 | detailedExecuteStatus | 0 |
| **17–18** | **defaultMin ou defaultMax, u16 BE, centièmes de kelvin** | 33515 attendu pour la borne haute |
| 19–20 | FPI1, FPI2 | 0, 0 |

La réponse **ne rappelle pas le type demandé**. La corrélation repose donc sur une seule transaction en vol, comme aujourd'hui, et sur la longueur 20. Le parseur actuel rejette tout ce qui ne fait pas 28 octets (`UNSUPPORTED_ACK_SHAPE`, `analyse-2026-11-17/service-local/mqtt/uart.lua:95`). Il faudra une forme « borne » distincte.

**Décodage côté service :**
- `consigne = fromRaw(cible_MAIN_INFO, min, max)` ;
- `température = fromRaw(courant_MAIN_INFO, min, max)` ;
- les bornes sont mises en cache après une lecture au démarrage, puis relues après une perte de contexte STM32.

**La cible vient déjà de MAIN_INFO.** La branche MAIN_INFO de `mpFpAck` publie le champ `target` sous l'état `0x0100D100` = 16830720 (`0x140860-0x14097c`, littéral `0x141194`). La cible et la valeur courante sont donc déjà disponibles.

**Limite :** si la cible vaut un alias (`0xD80A`, `0xD80F`, `0xD812`, `0xD813`, `0xD816`), le convertisseur demande les états d'alias 16832522… (`devices.lua:2253`). Ces états se lisent par READ_ALIAS, que nous n'avons pas implémenté. Dans ce cas, publier « inconnu ».

### 1.4 Alternative : registre privé 0x0041

- Index `0x0041` = état 201343233 (`0x0c004101`).
- `core:MinimalTemperatureManualModeState` = `readUInt16(1) / 10` et `core:MaximalTemperatureManualModeState` = `readUInt16(3) / 10` : 2 × u16 BE, en °C×10 (`devices.lua:18737`, `:18761` ; convertisseurs `:2218-2238`).
- Enregistré `GenericV2` (`0x18a058` → `0x194bac`, gateway-ids-all.txt (non publié)). Il est donc lisible tout de suite par la trame `0x0101` déjà utilisée : `07 04 0c 60 00 41`.

**Ce n'est pas un substitut.** Ce sont les limites que l'utilisateur peut régler en mode manuel, pas les bornes de l'échelle 0..51200 du paramètre principal. Le catalogue ne les relie à aucun calcul de consigne. Ce registre peut servir :
- de contrôle de vraisemblance, si son maximum vaut aussi 62,0 ;
- d'entité supplémentaire.

Il ne remplace pas `min` quand la cible est inférieure à 51200. Le cache du 17 novembre ne contenait pas ces deux états.

### Verdict 1

| Point | Verdict | Confiance |
|---|---|---|
| Mécanisme (ACTIVATE_STATUS_REQUEST, type 6/7, réponse u16 BE) | Faisable avec la trame `0x0100` existante | **Fortement déduit** (code natif + schéma concordants ; jamais observé sur le fil) |
| Borne haute ≈ 33515 et consigne 62,0 °C | Cohérent avec le cache local et Overkiz | **Fortement déduit** |
| Borne basse | — | **Inconnu** |
| 0x0041 comme substitut | Non ; complément possible | **Prouvé** pour l'enregistrement et le décodage ; sémantique déduite |

---

## 2. Sèche-serviettes IC3 : température ambiante, consommation, présence

### 2.1 Les sous-appareils sont des sous-systèmes du même nœud io

Le type 4398049919244 (`devices.lua:71939-72073`) décrit **un seul produit** avec sept sous-systèmes :

| # | Composant | Lignes | États bruts |
|---|---|---|---|
| 1 | `io:AtlanticElectricalTowelDryer_IC3_IOComponent` (actionneur) | 71950-72066 | dont `201408257` = `0x013f` présence, `201406209` = `0x0137`… |
| 2 | `io:OccupancyIOSystemDeviceSensor` | 34874-34885 | `slot4[570]` : **201408513** + StatusState |
| 3 | `io:LightIOSystemDeviceSensor` | 34886-34897 | `slot4[570]` |
| 4 | `io:RelativeHumidityIOSystemDeviceSensor` | 34898-34909 | `slot4[570]` |
| 5 | `io:TemperatureInCelciusIOSystemDeviceSensor` | 34910-34921 | `slot4[570]` |
| 6 | `io:CumulatedElectricalEnergyConsumptionIOSystemDeviceSensor` | `slot4[459]` → `slot4[312]`, 33484-33487, 31666-31674 | **uniquement** `core:StatusState` (`slot4[311]`, 31662-31665) |
| 7 | `io:TemperatureInCelciusIOSystemDeviceSensor` | `slot4[454]`, 33426-33442 | **201397505** |

`slot4[570]` se trouve à `devices.lua:34868-34872`. Pour le chauffe-eau, la même structure (#1 composant, #2 capteur d'énergie du même appareil) est déjà établie (`offline-api/README.md:24`). **Ces capteurs ont donc la même adresse cible que l'actionneur IC3.** Les valeurs sont des registres privés Atlantic (fabricant `0x0c`) de ce nœud. Ce ne sont pas des nœuds séparés.

### 2.2 États bruts et décodage

| Valeur Overkiz | État brut → index privé | Décodage OEM | Définition Lua (lecture OEM) |
|---|---|---|---|
| Température ambiante (sous-appareil #7) | 201397505 = `0x0c011501` → **`0x0115`** | `readInt16(1, false) / 100` (LE, °C×100, −1 = absent) ; `slot2[441]`, `devices.lua:19707`, conv. `:2676-2682` | `ECL.TemperatureAmbianteLocale`, `embedded/5a3dacb7e218/…lua` : READ toutes les 10 min et après commande |
| Présence #2, luminance #3, humidité #4, température #5 | 201408513 = `0x0c014001` → **`0x0140`** | u8 @1 (0 = absent), `readUInt16(2, false)` lux, `readUInt16(4, false) / 10` %, `readInt16(6, false) / 10` °C ; `slot2[601-604]`, `devices.lua:21871-21918`, conv. `:3626-3641` | `SSV.EtatCapteurEnvironnementauxSsv`, `embedded/88a3deb59d6f/…lua` : READ toutes les 10 min |
| Second détecteur de présence (#1) | 201408257 → `0x013f` | déjà lu | — |
| Consommation (#6) | **aucun état dans ce catalogue** ; meilleur candidat : `ECL.IndexConso` 201397761 = `0x0c011601` → **`0x0116`** | **inconnu** : aucun convertisseur, 0 occurrence dans `devices.lua` apps et appsB | `embedded/88b1bd46df07/IndexConso.lua` : READ au démarrage, après commande, toutes les heures |

Les candidats proposés au départ **ne sont pas des capteurs** :
- 83935233 = `core:IdentifierState` (identifiant sur 4 octets) ;
- 84672516 = `io:AutoProgramState` (programme automatique) ;
- seul 201397505 est confirmé, comme température ambiante du #7.

**Création par l'OEM.**
- Le sous-profil `ElectricalHeaterSubProfile` (`embedded/5652f71b2561/1.lua:18-19, 50, 62-138`, code IC3 = `"260000"`) importe `TemperatureAmbianteLocale`, `IndexConso` et `EtatCapteurEnvironnementauxSsv`. Il les crée sur le nœud (`create(paramètre, nœud)`), avec une branche réservée à l'IC3.
- La décompilation brouille la correspondance des upvalues : l'appartenance exacte de chaque paramètre à chaque branche n'est donc que déduite. Elle reste cohérente avec le catalogue : l'anticipation `0x0114` est dans #1 et l'ambiante `0x0115` dans #7.

**Enregistrement natif.** Les trois index sont enregistrés par le même wrapper `GenericV2` (`0x194bac`) que les 21 registres déjà lus :

| Index | Site | Remarque |
|---|---|---|
| `0x0115` | `0x18d824` | Identifiant **calculé** : littéral `0x0D01` (`0x18dca8`) + `0x0c000000` + `0x10800`. `reg.py` le déclarait « NOT FOUND » à tort. |
| `0x0116` | `0x18d95c` | — |
| `0x0140` | `0x190e0c` | — |

**Mode de lecture OEM :** lectures privées Atlantic GenericV2 périodiques (10 min ou 1 h). Rien n'indique un passage par des événements capteur. Un argument négatif, seulement : l'écoute passive de 60 s n'en a vu aucun (`offline-api/README.md:32`). Les filtres `slot1[0]` = `never` et `slot1[1]` = `reportingInterval 6h` (`devices.lua:14148-14155`), portés par ces états, semblent régler la remontée vers le cloud. Leur sens exact n'est pas établi.

**Consommation 1098.** Le catalogue local ne produit pas l'état de consommation du #6. Overkiz le calcule donc probablement côté serveur, à partir d'un catalogue plus récent. `0x0116` est le candidat le plus solide, d'après son nom, son profil SSV/IC3 et sa lecture horaire. Son format et son unité restent **inconnus**.

**Température « actuelle » 18,5 de `climate.seche_serviette`.** Elle vient vraisemblablement du #7 (`0x0115`, /100). D'après le code de l'intégration Overkiz de HA, cité de mémoire et non vérifié hors ligne, l'entité climat du sèche-serviettes lit le capteur lié n° 7. Le #5 (`0x0140`, /10) en est une autre source plausible. Il faut lire les deux et comparer.

Les valeurs « météo min 10, max 17, statut 4 » n'ont aucune source trouvée dans ce catalogue. Aucune hypothèse n'est retenue.

### 2.3 Trames

Elles sont identiques aux 21 lectures privées en service (`0x0101`, même contexte de 34 octets que l'IC3) :

| Index | Fin de charge utile | Réponse `0x040c`, données attendues |
|---|---|---|
| `0x0115` | `07 04 0c 60 01 15` | 2 octets, i16 LE /100 |
| `0x0140` | `07 04 0c 60 01 40` | au moins 7 octets (présence, lux, humidité, température) |
| `0x0116` | `07 04 0c 60 01 16` | longueur inconnue ; publier en hexadécimal brut avant tout décodage |

### Verdict 2

| Point | Verdict | Confiance |
|---|---|---|
| Même nœud et même cible que l'actionneur IC3 | Oui | **Fortement déduit** (catalogue + analogie CETHI prouvée) |
| Température ambiante `0x0115` et capteurs `0x0140` : source, décodage, enregistrement GenericV2 | READ faisable avec la trame existante | **Prouvé** statiquement ; réponse réelle **inconnue** |
| Quelle température correspond au 18,5 de HA | #7 probable | **Déduit** (à confirmer par lecture) |
| Consommation 1098 via `0x0116` | Lecture faisable, décodage non | **Inconnu** |

---

## 3. Constats annexes, utiles à l'agent qui modifie phase2

1. **`0x013d` est enregistré GenericV2**, contrairement au commentaire de `phase2/src/registers.lua:93`.
   - Identifiant calculé `0x0D01 + 0x0c000000 + 0x13000` (`0x190a40-0x190a74`, appel `0x194bac`).
   - Décodage OEM : `io:DryingDurationUserParameterState` = u8 @1 et `io:DryingDurationMaxState` = u8 @2 (conv. `devices.lua:1676`, `:3620`).
   - C'est le réglage de durée de séchage, 90 côté Overkiz, comme `0x013b` pour le boost.
   - Plus généralement, `reg.py` manque les identifiants calculés. gateway-ids.py (non publié) en reconstitue 137 sur 139 appels du constructeur `Atlantic::Gateway`.
2. **Énergie du chauffe-eau.**
   - Le capteur #2 `io:DHWCumulatedElectricalEnergyConsumptionIOSystemDeviceSensor` (`devices.lua:33216-33240`) lit `0x0004` (201327617) : `core:ElectricEnergyConsumptionState` = `readUInt32(1)`, BE, en Wh (`devices.lua:19103-19112`, conv. `:1710-1712`).
   - Il est enregistré GenericV2 (`0x1869e0`).
   - Le cache du hub donnait 4 150 365 Wh le 17 novembre ; HA affiche 4 159,092 (kWh) le 19 novembre pour `ballon_eau_chaude_consommation`. C'est cohérent.
   - `registers.lua:32` cite déjà `0x0004`.

---

## 4. Prochaines étapes

### Hors ligne, sans autorisation

1. Ajouter au codec un type de demande « borne » : charge utile `ctx..01 03 06|07 00 00`, liste fermée {6, 7}.
2. Ajouter une forme de réponse `0x010d` de 20 octets, avec les contrôles du tableau 1.3.
3. Tester avec une fixture QEMU synthétique, sur le modèle de check_formula.py (non publié).
4. Mettre les bornes en cache. Publier la consigne et la température en °C seulement si la cible est dans 0..51200 et si les deux bornes sont connues.
5. Ajouter les index IC3 `0x0115` et `0x0140`, et éventuellement `0x013d`, et CETHI `0x0041`, à la liste fermée, avec les décodages du tableau 2.2.
6. Publier `0x0116` comme valeur brute de diagnostic, désactivée par défaut.

### Sur le matériel, à autoriser séparément par <PERSONNE>

Une seule session, **en lecture seule**, par l'archive de service mise à jour. Ce sont des lectures que l'application d'origine fait aussi :
- CETHI : deux demandes de statut `DEFAULT_MIN` et `DEFAULT_MAX` ;
- IC3 : trois lectures privées `0x0115`, `0x0140`, `0x0116`.

Critères de réussite :
- borne haute ≈ 33515, donc consigne = 62,0 °C ;
- l'une des deux températures IC3 ≈ 18,5 ;
- la valeur brute de `0x0116` se compare à 1098, en LE/BE et sur u16/u32.

Comparer avec les valeurs Overkiz relevées le jour même, et non avec celles du 19 novembre. En cas d'absence de réponse ou de refus, la valeur reste `null`, sans blocage, comme pour les lectures actuelles.

---

## 5. Fichiers de ce dossier

| Fichier | Rôle |
|---|---|
| `run.sh` | Lance un script Python de ce dossier dans WSL (`python3 -I`) |
| `catalog.py` | Copie de l'outil fourni : noms d'états et convertisseurs par identifiant |
| `component.py` | États réellement liés (`linkedHighLevelState`) d'un composant ; sorties `cethi-component.txt`, `ic3-component.txt` |
| `reg.py`, `reg.sh` | Copie de l'outil fourni (littéraux directs seulement) |
| `gateway-ids.py` | Identifiants GenericV2, y compris calculés ; sortie `gateway-ids-all.txt` |
| `lit.py` | Recherche d'un littéral 32 bits et de sa fonction englobante |
| `fulldis.sh`, `dis.sh`, `syms.sh`, `vt.sh`, `strings.sh` | Désassemblage, symboles, vtable, chaînes de `Daemon.so` (statique) ; motifs dans `motifs-*.txt` |
| `dis-iodefaultvalue.txt`, `fillActuator.txt`, `mpFpAck.txt` | Extraits de désassemblage cités |
| `cethi-catalog.txt`, `ic3-catalog.txt`, `*-ids.txt` | Sorties catalogue |
| `check_formula.py`, `check_formula.out` | Contrôle synthétique, sans donnée privée |
| `work/` | Désassemblage complet (20 Mo), régénérable par `fulldis.sh`, exclu par `.gitignore` |

---

## Synthèse des verdicts

- **Consigne CETHI en °C : faisable avec la trame existante, confiance « fortement déduit ».** Chaque borne (65558, 65559) se lit par un ACTIVATE_STATUS_REQUEST séparé sur l'UART `0x0100` : `01 03 06 00 00` pour la borne basse, `01 03 07 00 00` pour la borne haute. La réponse `0x010d` fait 20 octets, avec la borne en u16 BE aux octets 17–18, en centièmes de kelvin. Avec la cible actuelle 51200, consigne = max/100 − 273,15. Max ≈ 33515 d'après le cache local (62), et min est inconnu. Prochaine étape : codec et fixture hors ligne, puis deux lectures autorisées.
- **Registre privé 0x0041 : lisible tout de suite, mais pas un substitut** (limites du mode manuel). Il sert de contrôle ou d'entité supplémentaire.
- **Température ambiante IC3 (`0x0115`, /100) et capteurs présence, luminance, humidité et température (`0x0140`) : faisables par la lecture privée GenericV2 existante, même nœud.** Source et enregistrement prouvés statiquement ; réponse réelle inconnue. La correspondance avec le 18,5 de HA est à confirmer en lisant les deux.
- **Consommation IC3 1098 : inconnu.** Aucun état dans le catalogue local. Candidat `0x0116` (IndexConso), lisible mais au décodage non établi : il faut une lecture brute autorisée et une comparaison.
- **Annexe :** `0x013d` (réglage de séchage) est bien enregistré GenericV2, et `reg.py` sous-estime les registres.
