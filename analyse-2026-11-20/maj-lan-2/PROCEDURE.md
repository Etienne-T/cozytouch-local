# Deuxième mise à jour par le réseau local : capteurs Home Assistant — 20 novembre 2026

**But :** publier dans Home Assistant les valeurs utiles du chauffe-eau et du sèche-serviettes, au lieu d'une seule valeur brute par appareil. Le service les obtient par des lectures privées Atlantic, en **lecture seule**, sur une liste fermée de registres.

## Ce qui est établi hors ligne

- **Format de la demande.** Capture du 17 novembre (sonde air entrant `0x001a`) :
  - UART `0x0101`, avec le même contexte de 34 octets que la lecture principale ;
  - puis `07` (sous-commande PRIVATE), `04` (longueur), `0c` (fabricant Atlantic), `60` (accès READ) et l'indice sur 2 octets, gros-boutiste.

  L'accès `0x60` vaut `0x61 − 1` dans `GenericV2::create`, avec `READ=1`. Une écriture utiliserait `0x61` ; le code impose `0x60`.
- **Réponse.** UART `0x040c` :
  - en-tête : RSSI, adresses de l'appareil et du hub, type de trame 0, commande `0x21` ;
  - puis `0c 60` et l'indice ;
  - puis la valeur.

  Le service vérifie les adresses, le type de trame, la commande, le fabricant et l'indice. Il ignore toute autre trame.
- **Routage.** Dans `Daemon.so` (appsB), les 21 indices retenus sont tous enregistrés par le même constructeur `GenericV2`, à l'adresse ELF `0x194bac`. C'est le même que pour les sondes déjà lues le 17 novembre. Analyse : `scratchpad/reg.py`, sur les littéraux du constructeur `Atlantic::Gateway`.
- **Décodage.** Il reprend le convertisseur d'origine de chaque état, tiré du catalogue `io/devices.lua` (composant CETHI 604 et composant IC3), dans `phase2/src/registers.lua`. Le chauffe-eau est en gros-boutiste ; les températures de l'IC3 sont en petit-boutiste, lues avec `readUInt16(1, false)`.

## Registres lus

| Appareil | Indice | Valeur publiée | Décodage d'origine |
|---|---|---|---|
| CETHI | `0x0017` | température de l'eau, milieu du ballon | i16 / 10 °C |
| CETHI | `0x0003` | heures de fonctionnement pompe à chaleur et appoint | u16 @1, u16 @3 |
| CETHI | `0x0033`, `0x0034` | consommations appoint et pompe à chaleur | u16, **unité non établie** (index brut) |
| CETHI | `0x0006` | mode eau chaude | 0 autoMode, 1 manualEcoActive, 2 manualEcoInactive |
| CETHI | `0x0000`, `0x0005` | durées boost et absence | i8 ; u8 (255 = toujours) |
| CETHI | `0x0001`, `0x0031` | consommation d'eau, V40 | u16, litres |
| CETHI | `0x001a`, `0x001b`, `0x001c` | sondes air entrant, évaporateur bas et haut | i16 / 10 °C, **conversion déduite** (codec de la sonde d'eau) |
| IC3 | `0x0136` | mode | standby, auto, internal, external |
| IC3 | `0x0137`, `0x0138`, `0x011d` | consignes effective, confort et dérogation | u16 LE / 10 °C |
| IC3 | `0x0104` | abaissement éco | u16 LE / 10 °C |
| IC3 | `0x013a`, `0x013c` | durées boost et séchage | u8, minutes |
| IC3 | `0x013e` | état temporaire | permanentHeating, boost, drying |
| IC3 | `0x013f` | présence | u8 ≠ 0 |

**Hors du champ :**
- la consigne du chauffe-eau en °C, qui demande les bornes `65558`/`65559`, lues par un autre mécanisme ;
- les erreurs ;
- la température ambiante et la consommation du sèche-serviettes, qui viennent d'autres composants ;
- aucune écriture.

## Fonctionnement du service

- **Lectures principales :** inchangées. Elles suffisent toujours au contrôle de santé.
- **Lectures privées :**
  - elles ont lieu après une paire de lectures principales publiée, au plus une série toutes les 300 secondes, une lecture à la fois, avec 5 secondes d'attente au plus ;
  - elles ne partent que si le courtier est connecté.
- **En cas d'échec :** sans réponse ou en cas de refus, seule la valeur concernée passe à `null`, c'est-à-dire « inconnu » dans Home Assistant. Seule une réinitialisation du STM32 reste bloquante, comme pour les lectures principales.
- **Découverte Home Assistant :**
  - une configuration par appareil (`homeassistant/device/<id>_cethi/config` et `homeassistant/device/<id>_ic3/config`) : 15 composants pour le chauffe-eau, 11 pour le sèche-serviettes ;
  - le paramètre principal brut et le RSSI sont désactivés par défaut ;
  - les anciennes configurations par entité sont vidées à chaque démarrage, ce qui retire l'ancien capteur « Valeur brute ».
- **MQTT :**
  - un message peut maintenant atteindre 6 Kio, pour 3,5 Kio mesurés ;
  - un paquet peut atteindre 8 Kio, toujours un seul en vol ;
  - la file contient au plus 7 sujets.

## Archive

| Élément | Valeur |
|---|---|
| Fichier | `phase2/applications/ct-20261120b.ctapp` (7 modules, 53 755 octets) |
| SHA-256 | `466b96118501c0cd658604d94c6d56342e0b40733e327fe8eda584ab0dd2ced8` |
| Version sur le hub | `v-466b96118501` |

## Tests QEMU (`phase2/preuves/private-reads-20261120.log`)

- **Scénario `private`**, avec l'archive exacte en essai sur la base v4 :
  - 21 demandes `0x0101`, dans l'ordre et au format attendus, vers le bon appareil ;
  - une réponse dont l'indice ne correspond pas est ignorée ;
  - décodage vérifié, y compris une température négative et une valeur trop courte, qui donne `null` ;
  - une absence de réponse (`TIMEOUT`) et un accès refusé (`DEVICE_ERROR`) ne sont pas bloquants ;
  - deux configurations d'appareil de 3 552 octets au plus, sans aucun sujet de commande.
- **Non-régression :** `late-broker`, `healthy`, `outage`, `lwt`, `term`, `ota-trial` et `ota-fail` passent.

## Étapes sur le hub, à autoriser par <PERSONNE>

**Nouveauté radio :** ce sont les premières lectures privées envoyées par notre système aux appareils réels. Ce sont des lectures, que l'application d'origine fait elle aussi, avec un rafraîchissement de 10 minutes.

1. `.\phase2\deployer-app.ps1 -Archive phase2\applications\ct-20261120b.ctapp -Reboot`.
2. Environ 2 minutes plus tard, `-Status` doit indiquer `current=v-466b96118501` et `previous=v-bd5f7e61b4ea`.
3. Dans Home Assistant, les appareils « Cozytouch CETHI » et « Cozytouch IC3 » doivent afficher les nouvelles entités. Comparer leurs valeurs à celles d'Overkiz (`ETAT-HA.md`).

## Exécution, 20 novembre 2026 vers 9 h 48 (heure de Paris), autorisée par <PERSONNE> (« on y va »)

1. **Installation :** `deployer-app.ps1 -Archive …` (sans `-Reboot`) donne `UPDATE_STAGED version=v-466b96118501 files=7`, puis `next=v-466b96118501`. Le script corrigé lit maintenant bien le code de retour.
2. **Redémarrage :** `ct-update reboot` affiche `REBOOT_NOW`. Le SSH coupe au bout de 6 secondes grâce à `ServerAliveInterval`.
3. **Essai :** `HEALTHY=yes` à 12 secondes de fonctionnement, `current=v-466b96118501`, `previous=v-bd5f7e61b4ea`.
4. **Lecture des publications par un abonné MQTT en lecture seule** depuis le PC (`scratchpad/sub-states.ps1`, client PowerShell, car WSL n'atteint pas le courtier) :
   - configurations : chauffe-eau, 15 composants et 3 482 octets ; sèche-serviettes, 11 composants et 2 547 octets ;
   - comparaison avec le relevé Overkiz de la veille (`ETAT-HA.md`) :

| Valeur | Notre hub | Overkiz (19 nov.) | Verdict |
|---|---|---|---|
| Heures PAC / appoint | 8888 / 87 | 8884 / 87 | cohérent (+4 h) |
| Index conso électrique (`0x0033`) | 26542 | 26542 | identique |
| Index conso PAC (`0x0034`) | 6269 | 3782 | **écart à expliquer** |
| Température eau (milieu) | 60,2 °C | 54,1 °C | plausible (ballon en chauffe) |
| Durées boost / absence | 0 / 0 | 0 / 0 | identique |
| Consommation d'eau | null (pas de réponse) | inconnue | cohérent |
| V40 (`0x0031`) | 11000 | entité désactivée | **échelle inconnue**, impossible en litres |
| Sondes air / évap. bas / haut | 19,3 / 19,0 / 19,4 °C | — | plausibles |
| IC3 mode | standby | climate off | cohérent |
| IC3 consigne confort / abaissement éco | 17 / 3,5 | 17 / 3,5 | identique |
| IC3 boost / séchage (`0x013a` / `0x013c`) | 0 / 0 | 20 / 90 | autre grandeur : durée en cours, pas le réglage |

**Corrections à prévoir (v3) :**
- V40 en index brut, sans unité ;
- renommer `0x013a` et `0x013c` en durées restantes ;
- ajouter `0x013b`, le réglage de durée du boost, enregistré `GenericV2` (ELF `0x19078c`). `0x013d` n'est pas trouvé dans le constructeur, donc pas ajouté ;
- expliquer l'écart de `0x0034`.

**Retour arrière :** `ct-update rollback`, puis `ct-update reboot`, reprend `v-bd5f7e61b4ea`. Un essai sans `HEALTH_OK` est abandonné automatiquement.

> Les empreintes historiques des fichiers expurgés se rapportent aux originaux privés.
