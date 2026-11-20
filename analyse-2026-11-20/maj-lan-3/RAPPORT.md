# Troisième mise à jour LAN (v3) : corrections des registres privés — 20 novembre 2026

**Statut :** archive construite et testée sous QEMU, **non déployée**. Travail entièrement hors ligne : aucun accès au hub, au réseau, au courtier MQTT, ni aucune action radio.

| Élément | Valeur |
|---|---|
| Archive | `analyse-2026-11-18/persistance-banque-a/phase2/applications/ct-20261120c.ctapp` (7 modules, 55 432 octets) |
| SHA-256 | `5a15d3d38a81b85900c2804703d903886e1e1de54b97146d86b3319096c8c976` |
| Version | `v-5a15d3d38a81` |
| Version actuelle du hub (avant v3) | `v-466b96118501` (`ct-20261120b.ctapp`) |
| Journal de test | `phase2/preuves/private-reads-v3-20261120.log` |

Les chemins `phase2/…` ci-dessous désignent `analyse-2026-11-18/persistance-banque-a/phase2/…`.

## 1. Ce qui change

Fichier modifié : `phase2/src/registers.lua`. `service.lua` et `uart-session.lua` sont inchangés.

| Registre | Avant (v2) | Après (v3) | Clé d'état |
|---|---|---|---|
| CETHI `0x0031` | « Eau chaude disponible à 40 °C », `L`, `volume_storage` | « V40 eau chaude (index brut) », sans unité ni classe, diagnostic | `v40_litres` (conservée) |
| CETHI `0x0033` | « Consommation électrique (index brut) », `measurement` | « Énergie appoint électrique », `Wh`, `energy`, `total_increasing` | `elec_index` (conservée) |
| CETHI `0x0034` | « Consommation pompe à chaleur (index brut) », `measurement` | « Énergie pompe à chaleur », `Wh`, `energy`, `total_increasing` | `hp_index` (conservée) |
| IC3 `0x013a` | « Durée du boost » | « Durée restante du boost », min | `boost_minutes` (conservée) |
| IC3 `0x013b` | — | **nouveau** : « Durée du boost (réglage) » u8 @1 ; « Durée maximale du boost » u8 @2 (diagnostic), min | `boost_setting`, `boost_max` |
| IC3 `0x013c` | « Durée du séchage » | « Durée restante du séchage », min | `drying_minutes` (conservée) |

- **22 registres** sont lus au lieu de 21, pour 24 valeurs. La découverte publie 15 composants pour le chauffe-eau et 13 pour le sèche-serviettes, au lieu de 11.
- **Clés conservées :** l'`uniq_id` vaut `<client>_<appareil>_<clé>`, donc garder les clés garde les mêmes entités dans Home Assistant, avec leur historique. Le nom de la clé `v40_litres` est maintenant trompeur, mais il est interne et ne s'affiche pas.
- **Effet attendu dans HA pour `0x0033`/`0x0034` :** la classe et l'unité changent. HA peut signaler dans les statistiques un changement d'unité ou de classe d'état à corriger (Outils de développement → Statistiques). C'est sans conséquence sur les valeurs.
- **Lecture seule**, comme avant : `0x013b` reste lu en `GenericV2 READ` (accès `0x60`).

## 2. Preuves

### 2.1 V40 (`0x0031`) : aucune échelle dans le code OEM

- **Catalogue :** `core:V40WaterVolumeEstimationState`, raw id `201339137` = `0x0C003101`, convertisseur `slot0[584]`, soit `readUInt16(1)` sans facteur (`analyse-2026-11-17/lua/all/appsB/overkiz/io-homecontrol/lib/Overkiz/knowledge/io/devices.lua:22660-22667`). Sortie : `maj-lan-3/catalogue.txt`.
- **Module de paramètre OEM :** `ovk.io.Parameter.Private.Atlantic.ECS.V40ConsumEst`. Il déclare le même id en READ, rafraîchi toutes les heures, sans aucune conversion (`analyse-2026-11-17/lua/embedded/54bd2a70ecfb/V40ConsumEst.lua:1-4`).
- **Conditions OEM :** le paramètre n'est créé que pour la version Atlantic `VERSION_2_1` ou les logiciels `MURAL`, `CETHI_V4` et `CV4E` (`analyse-2026-11-17/lua/embedded/65b15020d2da/51.lua:681-694`).
- **Cache OEM du 17 novembre :** `core:V40WaterVolumeEstimationState` y est absent (`analyse-2026-11-17/live-interface/states-cache-01.txt:78`, `cached-state-results.csv:41`). Le 19 novembre, l'entité Overkiz correspondante était désactivée. **Aucune valeur de référence n'existe donc.**
- **Conclusion :** aucune échelle n'est prouvée. 11 000 est impossible en litres pour un ballon de 250 L : à 60 °C, un V40 plausible serait de l'ordre de 400 L. La valeur est publiée comme index brut. Hypothèses non vérifiées : une autre unité, par exemple des centilitres (110 L), une valeur sentinelle, ou un registre non pertinent pour ce modèle.

### 2.2 IC3 `0x013a`, `0x013b`, `0x013c`, `0x013d`

Correspondance entre raw id et indice : `0x0C<indice>01`, par exemple `201406977` = `0x0C013A01`.

| Indice | État du catalogue (convertisseur) | Module OEM, rafraîchissement | Référence |
|---|---|---|---|
| `0x013a` | `core:BoostModeDurationState`, `readUInt8(1)` | `SSV.TempoBoostSsv`, 10 min | `devices.lua:21668-21675` ; `lua/embedded/078184e73725/TempoBoostSsv.lua:1-6` |
| `0x013b` | `io:BoostDurationMaxState`, `readUInt8(2)` ; `io:BoostDurationUserParameterState`, `readUInt8(1)` | `SSV.ParametragesBoostSsv`, une fois par jour | `devices.lua:21790-21809` ; `lua/embedded/3d5b8085eafd/ParametragesBoostSsv.lua:1-6` |
| `0x013c` | `io:DryingDurationState`, `readUInt8(1)` | `SSV.TempoSechageSsv`, 10 min | `devices.lua:21826-21833` ; `lua/embedded/c0f594f4655f/TempoSechageSsv.lua:1-6` |
| `0x013d` | `io:DryingDurationMaxState` @2 ; `io:DryingDurationUserParameterState` @1 | `SSV.ParametragesSechageSsv`, une fois par jour | `devices.lua:21814-21845` ; `lua/embedded/3edfdc6feb93/ParametragesSechageSsv.lua:1-6` |

- **Sens :** « Tempo » désigne une temporisation, lue souvent. « Paramétrages » désigne un réglage, lu une fois par jour, qui contient la valeur utilisateur et le maximum. `0x013a` et `0x013c` sont donc les minuteries en cours, d'où les noms « Durée restante… ». Elles valent 0 hors boost ou séchage, ce qui est cohérent avec l'état observé (`climate off`, état temporaire `permanentHeating`).
- **Enregistrement natif GenericV2** (`maj-lan-3/reg.txt`, `scripts/reg.sh`), sur `analyse-2026-11-17/extracted/appsB/overkiz/io-homecontrol/lib/ovk/iovp/Daemon.so` :
  - `0x0C013A01` : littéral `0x1908d0`, chargé à `0x190650`, suivi de `bl 0x194bac` ;
  - `0x0C013B01` : littéral `0x1908d4`, chargé à `0x19078c`, suivi de `bl 0x194bac`, soit le wrapper GenericV2 ;
  - `0x0C013C01` : littéral `0x1908d8`, chargé à `0x190910`, suivi de `bl 0x194bac` ;
  - `0x0C013D01` : **introuvable**. Le pool de littéraux du constructeur contient, dans l'ordre, `0x0139`, `0x013a`, `0x013b`, `0x013c`, puis directement `0x013e`, `0x013f`, `0x0140`, `0x0150`… (`maj-lan-3/dis013.txt`, dump `0x1908c0-0x190910`).

  **`0x013d` n'est donc pas ajouté**, bien qu'un module Lua le déclare.
- **Écart avec Overkiz (boost 20, séchage 90, le 19 novembre ; `analyse-2026-11-19/ha-etat/ETAT-HA.md:35`) :** non résolu hors ligne. Deux hypothèses :
  - l'entité Overkiz affiche le réglage (`…UserParameterState`), pas la minuterie ;
  - l'état Overkiz garde la dernière durée lancée.

  **Test discriminant après déploiement :** si `boost_setting` vaut 20, la première hypothèse est confirmée pour le boost. Le séchage (90) ne peut pas être vérifié tant que `0x013d` n'est pas lisible.

### 2.3 CETHI `0x0034` (`io:PowerHeatPumpState`) : la valeur a simplement changé

- **Correspondance :** `0x0034` = `201339905` = `io:PowerHeatPumpState`, `readUInt16(1)` (`devices.lua:19056-19063`). `0x0033` = `io:PowerHeatElectricalState`, même convertisseur (`devices.lua:19044-19051`). Les deux sont bien enregistrés GenericV2 : littéraux `0x189c10` et `0x189c14`, `bl 0x194bac` (`reg.txt`). Le mapping v2 est donc correct.
- **Unité :** le compteur total du chauffe-eau, `core:ElectricEnergyConsumptionState`, est le registre `0x0004` (raw id `201327617`). Il est lu en `readUInt32(1)` (`devices.lua:19106-19113`). Le capteur OEM qui le porte déclare `core:MeasuredValueType = core:ElectricalEnergyInWh` (`analyse-2026-11-17/live-interface/definitions-cache-01.jsonl:2`). HA l'affichait à 4159,092, soit 4 159 092 Wh exprimés en kWh.
- **Identité de sommes** entre deux relevés indépendants :
  - le cache OEM du 17 novembre à 17 h 53 UTC (`analyse-2026-11-17/live-interface/states-cache-01.txt:2-4, 71-73, 93-95`) ;
  - les entités Overkiz du 19 novembre (`ETAT-HA.md:24`).

| Valeur | 17 nov. (cache OEM) | 19 nov. (Overkiz) | Écart |
|---|---|---|---|
| `0x0004` total (Wh) | 4 150 365 | 4 159 092 | **+8 727** |
| `0x0033` appoint | 24 097 | 26 542 | +2 445 |
| `0x0034` PAC | 63 036 | 3 782 | −59 254, soit **+6 282 modulo 65 536** |
| Somme des écarts `0x0033` et `0x0034` | | | **+8 727** |

  L'égalité est exacte. `0x0033` et `0x0034` sont donc des compteurs d'énergie en **Wh sur 16 bits**, qui repartent de zéro après 65 535. La PAC a dépassé 65 535 entre le 17 et le 19 novembre.
- **Du 19 au 20 novembre :**
  - PAC : 3 782 → 6 269, soit +2 487 Wh pendant +4 h de fonctionnement PAC (8 884 → 8 888 h), environ 620 W en moyenne ;
  - appoint : 26 542 → 26 542, soit 0 Wh pendant +0 h (87 → 87 h).

  C'est cohérent avec un ballon chauffé par la PAC seule : 60,2 °C lu par le hub, contre 54,1 °C la veille. Pour mémoire, du 17 au 19 novembre : +14 h de PAC pour +6 282 Wh, environ 450 W, et +1 h d'appoint pour +2 445 Wh.
- **Conclusion :** aucun autre état, raw id ou position n'est en cause. L'écart vient d'un changement réel de la valeur. Le code passe ces deux registres en énergie `Wh`, avec `total_increasing` : dans HA, une baisse de valeur ouvre un nouveau cycle de compteur. À chaque passage à zéro, l'énergie consommée entre la dernière lecture (300 s au plus) et 65 535 est perdue, soit quelques dizaines de Wh.
- **Piste non mise en œuvre :** le registre `0x0004` (u32, Wh, sans passage à zéro) est enregistré GenericV2 (littéral `0x185b8c`, chargé à `0x1869d8`, `bl 0x194bac` ; `reg.txt`). Il donnerait le compteur `ballon_eau_chaude_consommation` d'Overkiz. Il n'a pas été ajouté, car il n'est pas dans le périmètre demandé et ce serait une lecture radio de plus : décision à prendre par <PERSONNE>.

## 3. Tests

**Fichier :** `phase2/tests/test-qemu.py`.

- **`PRIVATE_FIXTURE`** (l. 105-111) : nouvel ordre sur 22 registres. Valeurs synthétiques :
  - `0x0031` = `2af8`, soit 11 000 ;
  - `0x013a` = `00` ;
  - `0x013b` = `1478`, soit 20 et 120 ;
  - `0x013c` = `5a`, soit 90.
- **`PRIVATE_EXPECTED`** : ajout de `boost_setting` (20) et `boost_max` (120). `v40_litres` vaut 11 000 et `boost_minutes` vaut 0.
- **Nouveaux contrôles de découverte** (l. 472-482, scénarios candidats) :
  - 15 et 13 composants ;
  - V40 sans unité ni classe, avec « brut » dans le nom ;
  - `0x0033` et `0x0034` en `Wh`, `energy`, `total_increasing` ;
  - « restante » dans le nom des deux minuteries ;
  - unité `min` pour le réglage et le maximum.

  Le contrôle de taille de 6 144 octets est conservé.
- **Avant QEMU** (`maj-lan-3/scripts/build-test.sh`) :
  - aucun CRLF dans les sources ;
  - empreinte de `root.ubifs` vérifiée ;
  - `loadfile` LuaJIT de chaque module sous `qemu-arm` ;
  - décodages : `0x013b` complet et trop court (nil) ; V40 ; refus de `0x013d`, absent de la liste autorisée.

**Résultats :** voir la section 5.

## 4. Fichiers produits (`analyse-2026-11-20/maj-lan-3/`)

- `RAPPORT.md` : ce rapport.
- `catalogue.txt`, `conv.txt` : états du catalogue et convertisseurs.
- `reg.txt`, `dis013.txt` : enregistrements GenericV2 et pool de littéraux IC3.
- `registers-v2.lua.orig`, `test-qemu-v2.py.orig` : copies des fichiers d'avant la v3.
- `scripts/` :
  - `catalog.py`, `reg.py` : copies des outils ;
  - `catalogue.sh`, `conv.sh`, `reg.sh`, `dis013.sh` : analyses hors ligne ;
  - `build-test.sh` : construction et tests.

## 5. Résultats des tests

**Commande** (WSL, base v4 déployée `<CHEMIN_LOCAL>`, images racine non reconstruites) : `CT_CANDIDATE_APP=…/ct-20261120c.ctapp python3 -u phase2/tests/test-qemu.py <CHEMIN_LOCAL> private late-broker healthy outage ota-fail`. Durée : 09:06:48 → 09:10:03 UTC. Code de sortie : **0**.

| Contrôle | Résultat (`phase2/preuves/private-reads-v3-20261120.log`) |
|---|---|
| Image racine | `root.ubifs: OK` (l. 1) |
| Archive | `CTAPP sha256=5a15d3d3… version=v-5a15d3d38a81 files=7 bytes=55432` (l. 2) |
| Modules Lua et décodages | `LOADFILE_OK`, `REGISTER_KEYS 24 REGISTERS 22`, `REGISTERS_OK` (l. 5-7) |
| `private` | `PRIVATE_READS 22 registers…` ; `MQTT_DEVICE_DISCOVERY components=15/13 max_bytes=3587` (l. 14-17) |
| `late-broker` | courtier absent 110 s, puis paire complète, `HEALTH_OK`, essai promu `v-5a15d3d38a81` (l. 21-27) |
| `healthy` | LED, mise à jour LAN (empreinte fausse refusée), pare-feu et SSH (l. 31-35) |
| `outage` | `MQTT_OUTAGE …` (l. 41) |
| `ota-fail` | `OTA_FAIL trial dropped before the single reboot; no counter ack` (l. 44) |

La plus grande configuration de découverte fait 3 587 octets, sous la limite de 6 144 octets. Elle faisait 3 552 octets en v2.

**Non vérifié :** le comportement sur les vrais appareils. Il reste à constater après déploiement : `0x013b` répond-il, et `boost_setting` vaut-il 20 ? Le déploiement n'a pas été fait et doit être autorisé par <PERSONNE>.

## 6. Déploiement (non fait)

La procédure est la même que pour `maj-lan-2/PROCEDURE.md`, avec `phase2/applications/ct-20261120c.ctapp`. Après redémarrage, attendre `current=v-5a15d3d38a81` et `previous=v-466b96118501`.

**Nouveauté radio :** une lecture privée de plus vers le sèche-serviettes (`0x013b`, en lecture seule), dans la même série de lectures espacées de 300 s.

## Déploiement, 20 novembre 2026 vers 10 h 26 (heure de Paris), autorisé par <PERSONNE> (« vas y pour les 2 »)

- **Installation :** `deployer-app.ps1 -Archive applications\ct-20261120c.ctapp` donne `UPDATE_STAGED version=v-5a15d3d38a81 files=7`. Le SHA-256 a été vérifié avant l'envoi.
- **Redémarrage et essai :** `ct-update reboot`, puis `HEALTHY=yes` à 21 secondes de fonctionnement. Ensuite : `current=v-5a15d3d38a81`, `previous=v-466b96118501`.
- **Contrôle par abonné MQTT en lecture seule** (`sub-states.ps1`) :
  - configurations : chauffe-eau, 15 composants et 3 517 octets ; sèche-serviettes, 13 composants et 2 973 octets ;
  - **`boost_setting` = 20**, ce qui correspond à la valeur Overkiz du 19 novembre. La première hypothèse est donc confirmée : Overkiz affichait le réglage, pas la minuterie. `boost_max` = 60 ;
  - les autres valeurs n'ont pas bougé : PAC 6 269 Wh, appoint 26 542 Wh, eau 60,1 °C.

> Les empreintes historiques des fichiers expurgés se rapportent aux originaux privés.
