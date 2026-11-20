# Revue indépendante de Cozytouch v5 — 20 novembre 2026

**Verdict pour `v-67ff1d7b2822` — OK après corrections.** Le nominal reproduit les 62,0 °C du relevé matériel. Deux écarts empêchent de valider l’isolation demandée. Le filtre change le traitement de vraies réponses régulières, même sur IC3. La phase peut aussi valider les bornes alors que l’UART a déjà commencé à recevoir un doublon.

Les références `service.lua`, `uart-session.lua` et `registers.lua` désignent les sources de `phase2/src`. `uart.lua` désigne le préfixe commun inclus dans le paquet. Les essais courts ci-dessous utilisent les modules extraits du paquet, LuaJIT ARM, un UART en mémoire et une horloge simulée. Les délais matériels proviennent du [diagnostic du 20 novembre](../diag-bornes/RESULTAT.md).

## Bloquants

**B1. Le filtre écarte des réponses MAIN_INFO avant toute demande de borne et sur IC3.** `uart-session.lua:216`, `uart-session.lua:220`, `uart.lua:85`, `uart.lua:92`, `service.lua:177`. Le premier prédicat teste toutes les réponses `0x010d` remises à une transaction active ordinaire ou privée. Il exige exactement 28 octets et `0x96` à l’octet 12. Il s’applique dès le démarrage, indépendamment de la cible et de l’émission d’une borne. Seul le second prédicat dépend de `limits_started`. Pendant une phase de bornes, c’est son propre décodeur qui reçoit les trames. Sans transaction active, elles sont ignorées.

| Réponse régulière injectée, sans autre réponse | v4 livrée | v5 |
|---|---|---|
| Refus IC3 de 16 ou 20 octets, avant les bornes | `DEVICE_ERROR` immédiat | `TIMEOUT` à 8 s |
| Succès IC3 de 28 octets, octet 12 = `0xd6`, avant les bornes | `DONE` | `TIMEOUT` à 8 s |
| Refus de 28 octets avec `0x96`, sur CETHI | `DEVICE_ERROR` | `DEVICE_ERROR` avant les bornes, `TIMEOUT` après leur première émission |
| Même refus de 28 octets, sur IC3 après les bornes | `DEVICE_ERROR` | `DEVICE_ERROR` |

Le cas `0xd6` démontre une différence entre décodeurs. La capture matérielle a fourni `0x96` pour les succès réguliers et aucun refus. Un succès conforme à la capture, aux bonnes adresses et dans les délais, passe aussi après les bornes.

Après la première émission, le second prédicat reste actif jusqu’à la fermeture de la session, même si la série échoue ou si MQTT se reconnecte. Pendant MAIN_INFO CETHI, il écarte toute réponse de 28 octets avec `0x96` dont les octets 15–16 diffèrent de `05 00` **ou** les octets 27–28 de `00 00`. Le critère porte sur la transaction active, avant vérification des adresses de la trame. Un véritable refus CETHI et un succès à FPI non nul sont donc aussi écartés. Si un succès conforme suit avant l’échéance initiale, la lecture aboutit. Sinon, le service sort avec le **code 32 après 8 s**. La v4 pouvait sortir immédiatement avec le code 33. Sur la première paire, l’échec empêche la validation de santé. Après la première émission de borne, `HEALTH_OK` a déjà eu lieu. Le service s’arrête tout de même, sans attendre le budget initial de 95 s. `service.lua:127`, `service.lua:216`, `service.lua:231`, `service.lua:256`.

**Correction.** Limiter le filtre au MAIN_INFO CETHI après une émission de borne. Rendre au décodeur v4 les lectures antérieures et toutes celles d’IC3. Pour CETHI après émission, la distinction entre deux refus identiques exige une garantie de protocole. Si le traitement v4 doit être préservé dans tous les cas, isoler ou désactiver la sonde dans la session régulière jusqu’à disposer de cette garantie. Reprendre la matrice ci-dessus, avec et sans succès ultérieur, dans les tests de session.

**B2. La garde peut valider une série pendant la réception d’un doublon.** `uart-session.lua:54`, `uart-session.lua:77`, `uart-session.lua:193`, `uart-session.lua:248`, `uart.lua:68`. Dans l’essai court, les douze premiers octets de l’enveloppe d’un doublon MAX arrivent 50 ms avant la fin de la garde. La phase termine avec trois bonnes valeurs et douze octets encore dans `parser.buf`. La suite du doublon arrive après la décision. `service.lua:146` accepte alors la série. Autre cas reproduit : le parseur compte un rejet CRC pendant la phase, puis trois réponses correctes suffisent à la faire accepter. Une trame UART complète d’un autre identifiant, par exemple un acquittement privé `0x040c` inattendu, est également ignorée pendant la garde. Les événements de reset conservent leur traitement fatal distinct. La règle effective vise les `0x010d` **complètes et décodées** pendant la phase.

**Correction.** Contrôler le tampon avant chaque émission et avant validation. Si une trame est en cours, attendre son décodage dans un délai borné ou invalider la série. Enregistrer les rejets du parseur pendant la phase et définir explicitement les événements asynchrones admis. Ajouter les cas « doublon à cheval sur la garde », « CRC rejeté » et « acquittement privé inattendu ».

## Importants

**I1. Une réponse au bon format peut être attribuée à la mauvaise demande.** `uart-session.lua:57`, `uart-session.lua:63`, `service.lua:145`, `uart.lua:94`. MIN et MAX portent le même marqueur et aucune référence à la demande. Dans un essai court, la réponse propre à MAX2 manque. Une copie tardive de MAX1 arrive pendant l’attente de MAX2. Les trois contrôles de valeur passent malgré l’absence de confirmation indépendante. Dans un second essai, une ancienne borne synthétique de 25 °C remplace le MIN silencieux de 20 °C. Avec deux MAX à 62 °C, le calcul donne **43,5 °C au lieu de 41,0 °C** à mi-échelle. Ce second cas suppose une ancienne valeur différente de la borne actuelle. La capture ne montre aucune telle substitution.

Pour MAIN_INFO, le succès de borne **observé** de 20 octets et les refus courts ou longs testés ne peuvent ni remplir l’état ni terminer directement la transaction CETHI après la sonde. En revanche, une réponse tardive qui coïnciderait entièrement avec un succès régulier serait acceptée. En simulation, un tel succès synthétique suivi dans la même lecture UART du vrai succès fait retenir le premier `target_raw` (33515 au lieu de 51200). Rien dans le relevé ne prouve qu’une borne produit cette forme de 28 octets. Rien n’établit non plus de durée de vie maximale des anciennes réponses. La garantie « jamais, quelle que soit la forme » dépasse donc les preuves disponibles.

**Correction.** Pour garantir une confirmation indépendante, exiger un identifiant renvoyé par l’appareil, une réponse distinguant MIN de MAX, ou une borne documentée sur la durée de vie des réponses et une séquence qui la respecte. En l’absence de cette preuve, laisser les degrés inconnus lorsque l’attribution certaine est requise. Une garde fixe plus longue déplace le cas limite.

## Mineur

**M1. Le test d’espacement laisse passer une émission anticipée.** `tests/test-qemu.py:270`, `tests/test-qemu.py:275`, `uart-session.lua:65`. Le code attend au moins 1 s depuis l’émission précédente et 500 ms depuis sa réponse. Le test exige seulement 450 ms depuis la réponse. Une régression qui supprimerait la condition de 1 s passerait avec les délais nominaux de 72 à 75 ms. **Correction.** Vérifier séparément les deux échéances avec l’horloge simulée, y compris juste avant et à chaque seuil.

## Vérifications sans écart supplémentaire

| Point | Résultat |
|---|---|
| Paquet et sources | Reconstruction indépendante sous WSL identique octet par octet. CTAPP1, 7 modules, 64 909 octets, SHA-256 `67ff1d7b28221f89c7ca4c4a61f968c7897638c2c096f1884659ae7157c9347a`. Le diff des quatre fichiers reproduit `CHANGEMENTS.diff`. Les copies Lua v3 et v4 correspondent à leurs archives. La v4 livrée est `v-1b3e4c30f96c`, postérieure aux deux candidates des anciennes revues. |
| Émissions et sérialisation | MAIN_INFO type 3 sur les deux cibles. Une seule **série** par session, sur CETHI : 7, 6, 7, soit deux émissions MAX prévues et une MIN, aucune relance après échec. Accès privé Atlantic fixé à `0x60`, registre autorisé par appareil. `uart.active` réserve l’UART pour toute la phase, garde comprise. `uart.lua:36`, `uart.lua:42`, `uart-session.lua:7`, `uart-session.lua:39`, `uart-session.lua:168`, `uart-session.lua:186`. |
| Acceptation des bornes | Échéance de 1 s, bonnes adresses, exactement 20 octets, octets 11–16 = `00 8e 00 04 05 00`, FPI nuls. Valeur u16 big-endian aux octets 17–18. Un autre `0x010d` complet dans la phase invalide la série s’il ne satisfait pas la demande en attente. Garde de 2 s après succès, de 10 s après échéance sans réponse exploitable. Publication seulement si MAX1 = MAX2 et 27315 ≤ MIN < MAX ≤ 37315. En cas d’échec, les trois clés sont absentes des états MQTT de la session. `uart-session.lua:49`, `uart-session.lua:57`, `uart-session.lua:69`, `service.lua:112`, `service.lua:146`. |
| Consigne | Sur les bornes mesurées 29315 et 33515, comparaison exhaustive sous LuaJIT avec l’interpolation et l’arrondi OEM : concordance des 51 201 bruts entiers de 0 à 51200. Exemples : 0 → 20,0 °C, 25600 → 41,0 °C, 51200 → 62,0 °C. Une cible absente ou hors plage laisse la consigne inconnue. Le service appelle la fonction seulement après validation des bornes. `registers.lua:198`, `service.lua:112`, `io-utils.module.lua:369`, `common_utils.module.lua:124`. |
| Santé, fraîcheur et anciennes revues | Préfixe UART de 9 461 octets identique en v3/v4/v5. Ordre CETHI puis IC3, échéance régulière de 8 s, deux états acquittés avant santé et budget initial de 95 s de session MQTT conservés. La priorité MAIN_INFO entre transactions et la reprise immédiate héritées de la v4 livrée sont présentes. Le journal v5 mesure une première paire fraîche après reconnexion à 0,213 s (intervalle 30 s) et 0,187 s (3 600 s). Avec 14 registres silencieux, l’écart maximal entre observations est de 35,277 s pour une expiration de 75 s. Le minimum manuel à deux octets reste exploitable indépendamment du maximum à quatre octets. L’inversion et l’égalité des bornes empêchent la publication. `service.lua:79`, `service.lua:133`, `service.lua:230`, `registers.lua:82`, journal v5 lignes 42, 134 et 155. |
| Découverte Home Assistant | Comparaison indépendante des JSON produits par les archives. Les 15/13 clés CETHI/IC3 de v3 et les 18/21 de v4 gardent leur identifiant unique. Les trois nouveaux capteurs CETHI sont `target_temp`, `setpoint_min`, `setpoint_max`. Sur IC3, seules les définitions de `env_presence`, `env_lux`, `env_humidity`, `env_temp` changent : diagnostic, désactivé par défaut. Au total, 21 composants par appareil. Avec l’identifiant maximal de 48 caractères et l’intervalle de 3 600 s : **5 708 et 5 661 octets**, sous 6 144. À 16 caractères et 30 s : 4 938 et 4 891. `service.lua:48`, `service.lua:63`, `registers.lua:147`, `tests/test-qemu.py:827`. |

**Couverture des tests.** Le journal v5 (non publié) consigne le nominal aux délais et aux octets observés, avec RSSI et adresses synthétiques. Il couvre les MAX divergents, MIN absent, doublon immédiat, doublon pendant la garde, FPI non nul suivi d’un bon ACK, bornes inversées et quatre formes tardives avant un vrai MAIN_INFO. Le cas tardif vérifie ensuite les deux nouvelles cibles et leurs séquences. Les cas `healthy`, `ota-fail`, `ota-trial`, `term` et `lwt` portent sur les applications de référence. La revue a relu ce journal sans relancer la suite longue. `tests/test-qemu.py:33`, `tests/test-qemu.py:245`, `tests/test-qemu.py:320`.

Outre B1, B2 et I1, la suite v5 gagnerait à couvrir un refus régulier seul jusqu’à l’arrêt avec vérification du code et de la santé, une coupure MQTT **pendant les bornes**, les bornes égales et les deux sorties de la plage 0–100 °C. Le test de coupure actuel intervient pendant la série privée qui suit. `tests/test-qemu.py:260`, `tests/test-qemu.py:333`, `tests/test-qemu.py:411`.

## Synthèse en cinq lignes

**OK après corrections** pour le paquet `v-67ff1d7b2822`, reconstruit à l’identique.  
Le filtre change le résultat de certaines lectures régulières, y compris avant les bornes et sur IC3.  
Un doublon fragmenté peut franchir la garde, et MAX2 peut accepter une copie tardive de MAX1.  
La formule OEM donne 62,0 °C pour 51200 avec les bornes mesurées de 20 et 62 °C.  
Les identifiants Home Assistant sont préservés et les deux configurations restent sous 6 144 octets.

> Les empreintes historiques des fichiers expurgés se rapportent aux originaux privés.
