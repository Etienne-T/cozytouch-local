# Interfaces locales, radio et mémoires — 17 novembre 2026

État vérifié en fin de cette série : SSH root RAM03 actif ; interfaces D-Bus du hub accessibles. Les lecteurs ajoutés résident dans `/run/ct/interface01`. Aucun service constructeur n'a été arrêté pour ces inspections.

## Résultats acquis

| Objet | Résultat | Limite |
|---|---|---|
| NAND Linux | Nouvelle acquisition complète brute 132 Mio avec OOB, puis 128 Mio corrigés ECC. Copies Windows et HP vérifiées. | Capture active non atomique ; conserver la référence JTAG initiale. |
| Chauffe-eau CETHI V4 | Modèle, firmware E722804, catalogue et valeurs de cache accessibles par D-Bus. Deux requêtes READ ciblées renvoient COMPLETED. | Ce statut accepte aussi DETAILED_ERROR dans le chemin étudié ; il ne prouve pas tous les états frais ni tous les résultats RF. |
| Liaison Linux–STM32 | `/dev/ttyS1` appartient à io-homecontrold. Le second READ produit 49 octets TX et 41 RX, entre deux témoins de deux secondes sans trafic. | Compteurs du pilote, sans octets de trame ni capture sur l'air. |
| Sèche-serviettes IC3 | Lecture native MainParameter réussie : DONE5 et IoCommandNoError. Cible et état courant correspondent au mode confort. Consigne effective 21 °C récupérée après un READ dédié. | Profil `localPairing=false` exclu du catalogue local. La consigne n'est pas la température ambiante ; heure physique de mesure non exposée. |
| Flash STM32 | Image distribuée et fonctions de lecture ciblée étudiées ; numéros de version et données personnalisées potentiellement lisibles par API applicative. | Aucun dump de la flash réelle. Helpers livrés non qualifiés pour maintenir le fonctionnement normal : ils changent le mode du STM32. |
| Mémoire des appareils | Catalogue de fonctions et d'états connu pour les profils présents. | Aucun service de lecture de firmware des appareils par radio démontré. Leur mémoire physique ne doit pas être appelée NAND sans identification. |

## Chemins de lecture vérifiés

`com.overkiz.Delegation.io.device.getDevices` reçoit une string RawSerializer, soit base64(bitser), et retourne un inventaire en cache. `getDeviceDefinition` fournit les définitions du composant passerelle, du chauffe-eau et de son capteur d'énergie. Trois objets logiques ne signifient pas trois appareils physiques. Aucun ordre radio n'est nécessaire pour ces deux appels.

`com.overkiz.Application.Trigger.HomeAutomation.Devices.get(sss)` lit le cache d'état de Trigger. La sortie est une chaîne : les valeurs complexes deviennent `table: 0x…`, sans sérialisation utile. Aucun horodatage de mesure n'est exposé. Les champs absents renvoient une erreur `namespace.isnil` ; ils ne déclenchent pas de rafraîchissement.

Exemples lus dans le cache du chauffe-eau : température 62 °C, consigne 62 °C, température intermédiaire 56,8 °C, capacité 250 L, mode `manualEcoInactive`, énergie cumulée 4 150 365 Wh. Ce sont les valeurs à l'instant de lecture du cache, sans garantie de fraîcheur de la mesure. Le fichier `cached-state-results.csv` conserve les 58 essais de champs : 19 valeurs scalaires, 5 valeurs complexes non sérialisées et 34 absences, chauffe-eau et IC3 réunis.

La minute d'écoute passive initiale ne reçoit aucun événement d'état. BusyBox timeout termine avec le code143 ; la capture est conservée et décodée ensuite, sans événement. Ce constat ne prouve pas que les appareils cessent de communiquer.

## Deux lectures ciblées du chauffe-eau

La revue du chemin READ (non publié) vérifie le profil51 et le regroupement MainParameter/FP10/FP15/FP16. La définition MainAndFunctionalParameter65554 fixe `access.READ=true` ; le même identifiant numérique peut servir à une activation en écriture, donc ce booléen est indispensable. Aucun setter, découverte, appairage, changement de `localPairing` ou appel direct au cloud n'est envoyé par les probes. Le traitement constructeur ordinaire peut continuer à communiquer avec le cloud.

Essai1 : un `refreshDeviceStates` ciblé renvoie la valeur sérialisée `COMPLETED` en environ0,3s. L'écoute D-Bus sur50s ne montre aucun événement d'état. Des valeurs inchangées et certains états de fin avec erreur détaillée peuvent expliquer cette absence ; ne pas conclure à une nouvelle mesure sur ce seul résultat.

Essai2 : témoin2s, même requête unique, puis témoin2s. Les compteurs UART passent de TX3981/RX2609 à TX4030/RX2650 pendant les0,38s encadrant l'appel. Les témoins sont stables. Le retour est à nouveau `COMPLETED`. Le dialogue sur la liaison détenue par le service radio est ainsi corroboré, sans attribuer à ces seuls compteurs le contenu précis d'une réponse RF.

## Sauvegarde et intégrité

Fiche NAND active (non publié) et comparaison (non publié). Les 68 corrections d'un bit sont corroborées par les parités BCH de l'OOB. La lecture ECC vérifie411 CRC UBI statiques et46093 nœuds UBIFS sans échec. Bootstrap identique ; contenus apps, appsB et persistent identiques aux références comparées. Neuf statuts internes et la date de secours changent. Les différences physiques et compteurs d'effacement ne sont pas assimilés à une modification de firmware.

L'archive privée sur le HP a le même SHA-256 que Windows. Aucun fichier brut, clé ou configuration privée n'est publié. Aucun effacement, programmation de flash ni ordre de chauffe envoyé. Les écritures ordinaires du Linux actif restent possibles.

## Lecture native avec retour détaillé

Le client LuaJIT FFI construit la signature native `(os)(s)a(utbuviiyisusuyy)` avec READ=true. Une première construction échoue sur une initialisation FFI de pointeur, avant connexion au bus. Le correctif est vérifié sur le hub avec `--build-only`. Client exécuté : SHA-256 `3edf4b7d426673dbf146884f908c9c2b5a2a5bfb9dd32f1911acdf262a9af85b`. Il reçoit et acquitte les callbacks `progress`, conserve les résultats dans un fichier RAM privé et n'envoie ni retry ni cancel.

- IC3 : une lecture de MainParameter65537 termine en 0,30 s. Statut DONE5 ; erreur structurée type1/id1, qui signifie précisément **IoCommandNoError** dans les constantes livrées. La réponse contient un MainInfo de dix octets. Cible et courant valent `0xfc05`, soit **comfort** selon le profil HeatingLevel ; remainingTime vaut0. Il s'agit d'un mode, pas d'une température. L'adresse du dernier maître reste privée. Compteurs UART : +46 TX et +35 RX.
- CETHI : même lecture native unique, même statut DONE5/IoCommandNoError, en 0,47 s ; +46 TX/+35 RX. Cible et courant bruts `0xc800`, remainingTime0. Ne pas les convertir en degrés sans le codec du profil51. Ces réponses détaillées sont une preuve plus forte que les deux COMPLETED de haut niveau.
- Consigne effective IC3 : une lecture READ du paramètre201406209, explicitement déclaré par `TemperatureConsigneEffectiveSsv.lua` et présent dans le profil IC3, termine en DONE5 sans erreur renseignée, en 0,40 s ; +47 TX/+27 RX. La valeur est absente du callback, mais le getter Trigger sur l'URL sans suffixe et `io:DataState/201406209` retourne `D2 00`. Le convertisseur livré lit un uint16 little-endian puis divise par10 : **21 °C de consigne effective**. Le nom `io:EffectiveTemperatureSetpointState` reste absent, ainsi que les formes avec #1. Le cache brut n'a pas été relevé avant cette requête : sa fraîcheur exacte n'est pas démontrée par comparaison avant/après. Client dérivé limité à ce paramètre et à cet IC3 : SHA-256 `2cc3c16bae6b48a648f7aff4c87b11bc8c5f8a83437e134c34125bc3a33f296d`.
- STM32 : GET logiciel0500 via OUTPUT_RAW42 sur le nœud stack. +8 TX/+14 RX ; deux callbacks PENDING mais aucun retour final pendant vingt secondes. La réponse applicative est normalement consommée par le tracker interne. La version n'est donc pas récupérée par ce client. Le getter passif Trigger `io:DataState/2146435073` est absent (`namespace.isnil`). Aucun passage au bootloader ou changement de protection.

Après ce GET, les cinq IDs raw de version, calibration, statut de calibration, série et cause de reset sont également absents du cache Trigger du stack. Aucun de ces champs n'est donc annoncé comme sauvegardé depuis la flash réelle. La piste d'observation des buffers via strace est documentée, mais aucun binaire ARMv5 compatible n'a été trouvé dans les emplacements vérifiés ; aucune instrumentation ptrace n'a été lancée.

Le service radio reste propriétaire de `/dev/ttyS1`. Aucun second lecteur du TTY n'est ouvert. Contrôle après les essais : SSH fonctionne, le FD radio reste ouvert, aucun client de probe ni moniteur D-Bus ne subsiste, racine rootB en lecture seule et `/run` en tmpfs. La journalisation debug n'a pas été activée : sa collecte HTTP et son backlog ne sont pas assez qualifiés pour garantir que les trames resteraient locales.

Contrôle final du 17 novembre à 18:34:48 UTC : `io-homecontrold` PID970 présent, état sleeping, TracerPid0, FD10 sur `/dev/ttyS1`, aucun processus de probe restant. Nouvelle connexion SSH réussie. Preuve : `runtime-health-final.txt`. La fiche PKM Home Assistant est mise à jour avec relecture vérifiée (`pkm-update-result.json`) ; la tâche Inbox reste ouverte.

Preuves : `native-probe-build-02.txt`, `native-ic3-read-01-result.txt`, `ic3-native-01.jsonl`, `native-cethi-read-01-result.txt`, `cethi-native-01.jsonl`, `ic3-setpoint-read-01-result.txt`, `ic3-setpoint-01.jsonl`, `ic3-setpoint-cache-after.txt`, `native-revision-read-01-result.txt`, `revision-native-01.jsonl`, `stack-cache-after.txt`, `runtime-health-01.txt`. Les payloads complets restent privés.

## Travail restant

Le chemin natif contourne désormais le filtre du catalogue pour une lecture IC3 vérifiée. Les suites utiles sont le décodage des paramètres supplémentaires, la récupération applicative des données STM32 et un test avec WAN isolé. Une capture passive de la liaison Linux–STM32 reste une alternative à l'instrumentation logicielle pour obtenir les réponses brutes.

La tâche de lecture locale sans cloud reste ouverte : le chemin local, le mode courant IC3 et la liaison STM32 sont testés, mais la fraîcheur complète des mesures et une expérimentation avec WAN coupé ne sont pas établies.

Preuves principales : `inventory.txt`, `definitions-cache-01.jsonl`, `states-cache-01.txt`, `ic3-states-cache-01.txt`, `radio-read-01-result.txt`, `radio-read-01-bus.txt` et `radio-read-02-counters.txt`. Les URLs privées d'appareils restent dans les captures locales.

> Les empreintes historiques des fichiers expurgés se rapportent aux originaux privés.
