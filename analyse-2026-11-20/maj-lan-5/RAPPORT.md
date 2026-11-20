# Cozytouch v5 — consigne du chauffe-eau en degrés Celsius

Version corrigée le 20 novembre 2026 pour le service local du hub. Le banc vérifie cette archive hors ligne. Le diagnostic matériel de référence concerne la v4 active lors du relevé.

| Élément | Valeur |
|---|---|
| Archive | [ct-20261120e.ctapp](../../analyse-2026-11-18/persistance-banque-a/phase2/applications/ct-20261120e.ctapp) |
| Identité du paquet | [Version et SHA-256](#paquet-et-découverte-home-assistant) |
| Candidat avant correction | [v-67ff1d7b2822](ct-20261120e-v-67ff1d7b2822.ctapp) · Journal initial (non publié) |
| Référence v4 | `v-1b3e4c30f96c`, SHA-256 `1b3e4c30f96c04ee338a1ebde1f4f7e53cb7dbfe0c8560b097e999a48734c426` |
| Journal d’essai | private-reads-v5-20261120.log (non publié) |

## Preuve matérielle et changements

Le diagnostic du 20 novembre a reçu une réponse `0x010d` par demande de borne. Les délais mesurés pour MAX, MIN et MAX sont de 73, 75 et 72 ms. Chaque réponse comporte 20 octets, avec `0x8e` à l’octet 12, `05 00` aux octets 15–16 et deux octets FPI nuls en fin de trame. Les octets 17–18 contiennent `82 eb`, `72 83`, puis `82 eb`, en centièmes de kelvin. Les réponses MAIN_INFO de 28 octets portent `0x96` à l’octet 12. La capture masque les adresses. [Résultat du diagnostic](../diag-bornes/RESULTAT.md) · Sortie UART expurgée (non publié)

1. Le service attend la première paire CETHI–IC3 acquittée par MQTT et la confirmation de santé. Il émet ensuite au plus trois lectures CETHI, dans l’ordre MAX (7), MIN (6), MAX (7), avant la première série privée. Chaque demande a une échéance de 1 s. La suivante part au moins 1 s après l’émission précédente et 500 ms après sa réponse.
2. La session accepte une réponse par demande, avec les adresses CETHI attendues, le format capturé, le statut DONE et les FPI nuls. Toute autre activité UART invalide la série. Le service abandonne les demandes restantes après une anomalie, un délai dépassé ou une perte de connexion MQTT détectée. Il ne réessaie qu’au démarrage d’un nouveau service.
3. La garde réserve l’UART jusqu’à ce que le parseur soit vide et que la ligne soit restée silencieuse pendant 2 s. Après une demande expirée, la garde exige 10 s de silence à partir de l’échéance ou du dernier octet reçu, selon le plus tardif. La session exige ensuite MAX1 = MAX2 et 0 °C ≤ MIN < MAX ≤ 100 °C. Si la série échoue, les trois champs de température restent absents des états MQTT de la session.
4. Après validation, le service publie `setpoint_min`, `setpoint_max` et `target_temp` sur l’état CETHI. Il conserve l’horodatage de la lecture qui fournit le premier `target_raw`. Il recalcule la consigne à chaque nouvelle paire et conserve les bornes après une reconnexion MQTT dans la même session radio. Le calcul OEM interpole le brut entre 0 et 51200 et arrondit la température au dixième. Le brut 51200 donne 62,0 °C et le brut 25600 donne 41,0 °C avec les bornes observées. Un brut hors plage laisse la consigne inconnue. Formule OEM (non publié)
5. Les quatre clés `env_presence`, `env_lux`, `env_humidity` et `env_temp` restent dans les lectures et états IC3 du registre `0x0140`. La découverte les classe comme diagnostics et les déclare désactivées par défaut. Le relevé communiqué pour le sèche-serviettes donne OFF, 0 lx, 100 % et 0 °C.

Les copies v4 ont été vérifiées par SHA-256 avant modification. Le diff du candidat initial (non publié) couvre les quatre fichiers de `v-67ff1d7b2822`. Les trois copies Lua correspondent aux modules de l’archive v4, après séparation du préfixe UART commun pour la session.

| Copie v4 | Changement dans le diff |
|---|---|
| service.lua-v4.orig (non publié) | Déclenchement après santé, validation et publication des bornes, trois composants CETHI |
| uart-session.lua-v4.orig (non publié) | Sérialisation MAX–MIN–MAX, garde, filtrage des réponses de statut |
| registers.lua-v4.orig (non publié) | Conversion de consigne et quatre diagnostics IC3 désactivés |
| test-qemu.py-v4.orig (non publié) | Rejeu des réponses capturées, des variantes et des valeurs MQTT |

## Corrections après revue Astra

| Constat | Correction | Vérification |
|---|---|---|
| B1 — Le filtre modifiait les lectures régulières, même sur IC3 avant la première borne. | Hors phase et garde, le répartiteur transmet chaque trame au décodeur v4. Pendant la phase, seule une trame CETHI de 20 octets portant `0x8e` peut correspondre à une borne. Les lectures régulières et privées attendent la fin de la garde. | `regular` et `regular-after` vérifient les refus courts, le succès IC3 avec `0xd6`, les refus longs et les FPI non nuls, avec et sans réponse ultérieure. Dans `regular-refusal`, le candidat initial attend 8 s et sort avec le code 32. Le correctif renvoie `DEVICE_ERROR` et sort avec le code 33 avant la validation de santé, comme v4. |
| B2 — La garde pouvait se terminer avec douze octets en tampon. Elle ignorait aussi un rejet CRC et un acquittement privé inattendu. | Avant une émission de borne ou la fin de la garde, la lecture UART doit confirmer que la file est vide, le tampon du parseur doit être vide et aucune trame partielle ne doit rester en cours. Chaque octet reçu prolonge la garde. Une trame supplémentaire, du bruit ou un rejet du parseur invalide la série. Un reset STM32 reste fatal. | `partial-guard` injecte les douze premiers octets du doublon 50 ms avant l’ancienne échéance, puis le reste 50 ms après. Le candidat initial termine avec douze octets en tampon. Le correctif rejette la série après deux secondes de silence. `crc`, `private-ack` et `timeout` vérifient le rejet CRC, l’acquittement inattendu et la prolongation après expiration. |
| I1 — Une réponse de borne ne désigne pas sa demande. MAX2 pouvait accepter une copie tardive de MAX1. | Chaque demande ouvre sa propre fenêtre de 1 s. Une réponse complète ou partielle entre deux demandes invalide la série. Une réponse de format inattendu invalide aussi la série. | Dans `late-max1`, la copie commence avant MAX2 et se termine 75 ms après l’instant où MAX2 aurait dû partir. Le candidat initial accepte 33515 / 29315 / 33515. Le correctif rejette la série après deux émissions. `identical-max` vérifie le cas d’une copie intégralement reçue dans la fenêtre de MAX2. |
| M1 — Le test ne vérifiait pas séparément les deux délais d’espacement. | Le banc QEMU vérifie les deux délais. Le test à horloge simulée vérifie leurs seuils exacts. | `spacing` vérifie qu’aucune demande ne part juste avant chacun des seuils et qu’elle part dès que les deux conditions sont satisfaites. |

Une copie de MAX1 reçue entièrement dans la fenêtre de MAX2 est indiscernable d’une réponse fraîche. Si MAX1 contient la vraie borne haute, la copie donne la même borne et la même consigne. Elle prive toutefois la série de sa confirmation indépendante. Dans le cas synthétique distinct décrit par Astra, une ancienne valeur de 25 °C reçue dans la fenêtre d’un MIN silencieux pourrait donner 43,5 °C au lieu de 41,0 °C à mi-échelle. Pour exclure ce cas, il faudrait un identifiant renvoyé par l’appareil, un format distinct selon la demande ou une durée de vie maximale établie pour les réponses. Le relevé matériel confirme le format de 20 octets et une réponse par demande, sans doublon observé.

Après la garde, le retour au traitement v4 s’applique aussi à une trame tardive. Une réponse synthétique de 28 octets qui imite entièrement MAIN_INFO peut donc être retenue si elle arrive pendant une lecture régulière. La capture matérielle montre uniquement des réponses de borne de 20 octets. Le préfixe UART commun de 9 461 octets, l’ordre CETHI puis IC3, le délai régulier de 8 s et le contrôle de santé de 95 s de temps connecté sont identiques à v4. [Revue Astra](REVUE-ASTRA.md) · [Tests de session UART](../../analyse-2026-11-18/persistance-banque-a/phase2/tests/test-uart-session.lua)

### Paquet et découverte Home Assistant

Le paquet corrigé `v-a581179dd120` a pour SHA-256 `a581179dd120b8f2d9027c0739e261fcfb1a910c8f844712652a01dc0d25a697`. Il contient sept modules au format CTAPP1 et mesure 65 333 octets. Une seconde construction a produit exactement les mêmes octets. Seuls `uart.lua`, `service.lua` et `registers.lua` diffèrent de la v4.

| Découverte MQTT | Chauffe-eau CETHI | Sèche-serviettes IC3 |
|---|---:|---:|
| Nombre de composants | 21 | 21 |
| Identifiant de 16 caractères et intervalle de 30 s | 4 938 octets | 4 891 octets |
| Identifiant de 48 caractères et intervalle de 3 600 s | 5 708 octets | 5 661 octets |
| Marge sous 6 144 octets à la taille maximale | 436 octets | 483 octets |

Les 18 clés CETHI et les 21 clés IC3 de la v4 conservent leurs identifiants uniques. Les quatre définitions `env_*` passent en diagnostics désactivés par défaut. La consigne s’ajoute comme capteur de température en °C avec `stat_cla: measurement`. Les deux bornes s’ajoutent comme diagnostics de température en °C. Journal QEMU (non publié)

## Trafic radio demandé par le service

Une session démarre au lancement du service. La v5 y ajoute jusqu’à trois demandes de statut étendu, toutes vers CETHI. Elle n’ajoute aucune demande récurrente de borne. Au nominal, l’ajout correspond à 138 octets UART émis et 81 reçus, enveloppes comprises. Ces nombres décrivent les échanges hôte–STM32. Le relevé ne mesure pas les retransmissions radio.

| Requêtes nominales | 300 s à 60 s par paire | 300 s à 30 s par paire |
|---|---:|---:|
| MAIN_INFO, type 3 | 10 | 20 |
| Registres privés, accès `0x60` | 28 | 28 |
| Bornes, première fenêtre de la session | 3 au plus | 3 au plus |
| **Total, première fenêtre** | **41 au plus** | **51 au plus** |
| **Total, fenêtres suivantes** | **38** | **48** |

Ces comptes supposent un courtier stable et des réponses aux cadences nominales. Une série privée se programme toutes les `ceil(300 / interval_seconds)` paires si la précédente est terminée. Une reconnexion remet le compteur des séries privées à zéro. Une fois la phase des bornes terminée, MAIN_INFO reprend la priorité à son échéance entre deux lectures privées.

## Banc QEMU

Le banc ARM926 utilise un UART et une NAND simulés. Son espace réseau hôte contient uniquement la boucle locale et ses services de test utilisent des identifiants synthétiques. La recette contrôle aussi le SHA-256 de chacun des sept modules de l’archive. verifier-v5.sh (non publié)

| Scénario | Contrôle |
|---|---|
| `private` | Réponses de borne conformes à la capture avec adresses et RSSI synthétiques. État CETHI à 62,0 °C pour le brut 51200. Les 28 registres privés restent lus, dont `0x0140`. |
| `limits-mismatch` | MAX1 et MAX2 diffèrent. Aucune publication de borne ni de consigne en °C. |
| `limits-missing` | MIN expire. La première lecture privée part 11,028 s après la demande silencieuse, soit 1 s de délai suivi d’au moins 10 s de garde. La paire régulière suivante se publie sans nouvelle tentative de borne. |
| `limits-duplicate`, `limits-guard` | Un doublon pendant la série ou pendant la garde invalide les trois champs. |
| `limits-unexpected` | Une réponse avec FPI non nul, suivie d’une réponse bien formée, invalide la série. |
| `limits-inverted`, `limits-equal`, `limits-low`, `limits-high` | Les deux bornes sont inversées, égales ou hors de la plage 0–100 °C. Les trois champs restent absents. |
| `limits-late` | Une réponse de borne de 20 octets arrive vers la fin de la garde et en prolonge la durée. La paire régulière suivante aboutit, sans bornes publiées. |
| `limits-outage` | Une coupure MQTT pendant MAX1 interrompt la série. Après reconnexion, le service publie une paire fraîche et ne relance pas les bornes. |
| `late-broker`, `outage` | Attente de 110 s sans courtier, puis validation de la santé et promotion de la v5 sur le banc. Après une coupure MQTT en série privée, le service abandonne la série et publie une paire fraîche avec la consigne recalculée, sans relire les bornes. |
| `private-slow` | 14 lectures privées sans réponse en 70,0 s. L’écart maximal entre observations MAIN_INFO est de 35,341 s pour une expiration MQTT de 75 s. |
| `regular-refusal` | Un refus court IC3 termine immédiatement la lecture. Le service sort avec le code 33, avant la validation de santé. |
| `healthy`, `ota-fail`, `ota-trial`, `term`, `lwt` | Le banc conserve ses applications de référence. Il vérifie la santé, la mise à jour locale de test, l’essai OTA réussi ou rejeté, l’arrêt propre et la publication MQTT d’indisponibilité après arrêt forcé. |

LuaJIT ARM confirme aussi le calcul aux bruts 0, 12 800, 25 600 et 51 200, qui donnent 20, 30,5, 41 et 62 °C. Une valeur brute absente ou hors de l’intervalle 0 à 51 200 laisse la consigne inconnue.

Les trois contre-essais reproduisent les écarts du candidat initial. Les neuf essais à horloge simulée, les 21 scénarios QEMU et les deux passages au format maximal réussissent sur le paquet corrigé ou sur l’application de référence prévue par le scénario. Le journal se termine par `EXIT_STATUS 0`. Les empreintes de l’archive v4, du candidat initial et de l’image racine du banc concordent avant et après les essais.

## Résumé

La v5 corrigée rétablit le traitement v4 des lectures régulières. Une série de bornes valide donne 62,0 °C pour le brut observé de 51200. Une anomalie dans la fenêtre surveillée laisse les trois températures inconnues pour la session. Le paquet est destiné à la validation hors ligne et n’a pas été déployé sur le hub.

## Déploiement, 20 novembre 2026 vers 14 h 12 (heure de Paris), autorisé par <PERSONNE> (« oui installe »)

- **Installation :** `UPDATE_STAGED version=v-a581179dd120 files=7`. SHA-256 `a581179dd120b8f2…`.
- **Redémarrage et essai :** `HEALTHY=yes` à 21 secondes de fonctionnement. Ensuite : `current=v-a581179dd120`, `previous=v-1b3e4c30f96c`.
- **Abonné MQTT en lecture seule** :
  - configurations : chauffe-eau, 21 composants et 4 843 octets ; sèche-serviettes, 21 composants et 4 792 octets ;
  - chauffe-eau : **`target_temp` = 62**, `setpoint_min` = 20, `setpoint_max` = 62, `target_raw` = 51200. Ces valeurs correspondent au diagnostic matériel et à Overkiz ;
  - sèche-serviettes : ambiante 17,75 °C, séchage 90 min, `index_conso_raw` `04af`.

> Les empreintes historiques des fichiers expurgés se rapportent aux originaux privés.
