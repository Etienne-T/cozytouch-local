# Seconde revue de Cozytouch v5 · 20 novembre 2026

**Verdict — OK pour déployer `v-a581179dd120` pour la lecture d’état.** Les deux défauts bloquants de la première revue sont corrigés. Le risque résiduel porte sur la valeur affichée dans Home Assistant. Il exige une ancienne réponse d’une autre valeur qui arrive dans la fenêtre exacte d’un MIN manquant. Le relevé matériel n’en montre aucun exemple. [Première revue](REVUE-ASTRA.md) · [Rapport du candidat](RAPPORT.md) · [Diagnostic matériel](../diag-bornes/RESULTAT.md)

## Statut des quatre constats

| Constat | Statut | Vérification sur le paquet final |
|---|---|---|
| **B1 · Filtrage de MAIN_INFO** | **Corrigé** | Avant et après les bornes, les refus IC3 de 16 et 20 octets et les refus longs des deux appareils donnent immédiatement `DEVICE_ERROR`. Le succès IC3 marqué `0xd6` donne `DONE`. Un succès CETHI à FPI non nul donne `UNSUPPORTED_ACK_SHAPE`. Un succès ultérieur dans la même lecture UART ne change aucun de ces résultats. Pour le refus court IC3, le service sort avant santé avec le code 33 en v4 et en v5 finale. Le candidat précédent sort avec le code 32 après expiration. `uart-session.lua:227`, `service.lua:176`. |
| **B2 · Fin de garde avec une trame incomplète** | **Corrigé** | Le candidat précédent termine avec 12 octets en tampon. La v5 attend le reste du doublon, invalide la série et attend deux secondes de silence depuis le dernier fragment. Un rejet CRC suivi d’une réponse correcte invalide aussi la série. Un acquittement privé inattendu pendant la garde l’invalide. `uart-session.lua:69`, `:193`, `:203`, `:251`. |
| **I1 · Attribution d’une réponse à la mauvaise demande** | **Partiellement corrigé, risque résiduel accepté pour cet usage** | Une copie de MAX1 commencée avant l’émission de MAX2 arrête désormais la série après deux demandes. Le candidat précédent en émettait trois et acceptait la copie. Une copie reçue entièrement dans la fenêtre de MAX2 reste indiscernable et peut remplacer sa confirmation. Si elle répète le bon maximum, la valeur publiée reste exacte. `uart-session.lua:56`, `service.lua:145`. |
| **M1 · Test de l’espacement** | **Corrigé** | Avec l’horloge simulée, aucune émission à 0,999 s, puis MIN à 1,000 s. Pour un MIN reçu à 1,750 s, aucune émission à 2,249 s, puis MAX2 à 2,250 s. Ces essais isolent les seuils de 1 s depuis l’émission et de 500 ms depuis la réponse. Le banc système contrôle aussi les deux intervalles avec tolérance. `tests/test-uart-session.lua:148`, `tests/test-qemu.py:281`. |

## Ce que la phase accepte et ce que la garde écarte

L’UART appartient à une seule transaction. Pendant toute la série MAX–MIN–MAX et sa garde, le service ne démarre aucune lecture régulière ou privée. Chaque émission ouvre une fenêtre de 1 s. Seule la première réponse complète avant l’échéance peut fournir une valeur. Elle doit porter l’identifiant `0x010d`, les adresses CETHI et hub attendues, 20 octets de charge utile, les octets 11–16 `00 8e 00 04 05 00` et deux FPI nuls. Une réponse reçue exactement à l’échéance a été rejetée en essai. Le service exige ensuite MAX1 = MAX2 et 27315 ≤ MIN < MAX ≤ 37315 en centièmes de kelvin. La session ne relance jamais la série, même après une reconnexion MQTT. `uart-session.lua:39`, `:58`, `:189`, `service.lua:145`, `:231`.

**Précision sur « seules les trames CETHI sont écartées ».** Seules les réponses CETHI conformes peuvent alimenter les bornes. En revanche, la phase consomme aussi les autres trames. Une vraie réponse MAIN_INFO d’IC3 présentée pendant la garde a donné `UNEXPECTED_ACK` et invalidé la série. Elle n’est ni livrée ultérieurement ni perdue pour une requête en cours, puisque le service n’en a lancé aucune. Un reset STM32 conserve son traitement fatal. Hors phase et garde, toutes les trames suivent le chemin v4 pour les deux appareils. `uart-session.lua:56`, `:210`, `:227`.

**Disponibilité.** La garde exige une lecture UART vide ou `EAGAIN`, un tampon de parseur vide, aucune trame partielle et 2 s sans nouvel octet. Après expiration d’une demande, elle exige 10 s depuis l’échéance ou le dernier octet reçu, selon le plus tardif. Une ligne qui reste active peut donc différer la prochaine paire sans durée maximale. Après la garde, un doublon au format matériel de 20 octets reçu pendant un MAIN_INFO CETHI produit `UNSUPPORTED_ACK_SHAPE`, même si le vrai succès suit dans la même lecture. Le chemin régulier v4 conduit alors au code 33. Un succès synthétique de 28 octets imitant entièrement MAIN_INFO peut au contraire fournir le premier brut reçu (33515 au lieu de 51200 en essai). Le diagnostic n’a observé aucun de ces retards. `uart-session.lua:70`, `:81`, `:205`, `:251`, `uart.lua:94`, `service.lua:178`.

## Une ancienne valeur peut-elle fausser la consigne ?

Dans cette session, **MAX1 est la seule demande de borne qui précède MIN**. Si une copie de MAX1 remplace MIN, l’exigence MIN < MAX1 échoue. Le service simulé a bien omis les trois températures. Pour obtenir une erreur numérique, il faut une autre valeur plausible, à la bonne adresse, entièrement reçue dans la fenêtre de MIN, sans vraie réponse MIN ni autre anomalie détectée avant la fin de la garde.

| Réponses attribuées à MAX1 / MIN / MAX2 | État CETHI produit par le service pour `target_raw = 25600` |
|---|---|
| 62 / 20 / 62 °C | Bornes 20 et 62 °C, consigne **41,0 °C** |
| 62 / 62 / 62 °C | Les trois champs sont absents |
| 62 / 25 / 62 °C, ancienne valeur simulée à la place du MIN réel de 20 °C | Bornes 25 et 62 °C, consigne **43,5 °C** |

Les contrôles d’ordre et de plage acceptent 25 °C. Au brut 51200 du relevé, la consigne reste à 62 °C dans les deux séries acceptées, mais la borne basse affichée serait fausse. Le service demande une relance radio à l’ouverture et n’interroge les bornes qu’une fois, après la première paire acquittée et la santé. Ce dernier événement peut être tardif si le courtier est indisponible. Les trois délais matériels mesurés sont 73, 75 et 72 ms, sans doublon. **La substitution est possible dans le logiciel et peu plausible dans le fonctionnement observé.** Le relevé ne fixe ni durée de vie maximale d’une réponse ni garantie de purge de bout en bout. Capture expurgée (non publié) · `uart-session.lua:149`, `service.lua:112`, `:217`, `:232`, `registers.lua:203`.

## Intégrité, santé et découverte

- **Paquet.** Reconstruction temporaire sous WSL Ubuntu-24.04 identique octet par octet. CTAPP1, 7 modules vérifiés, 65 333 octets, SHA-256 `a581179dd120b8f2d9027c0739e261fcfb1a910c8f844712652a01dc0d25a697`. Les trois copies sources Lua v4 concordent avec la v4 livrée, après normalisation des fins de ligne. Le préfixe UART commun de 9 461 octets est identique. Seuls `uart.lua`, `registers.lua` et `service.lua` diffèrent de la v4.
- **Lectures et santé.** MAIN_INFO reste de type 3, dans l’ordre CETHI puis IC3, avec une échéance de 8 s. Les registres privés restent sur liste autorisée et en lecture `0x60`. Le service exige toujours les acquittements de la première paire avant santé, avec un budget de 95 s de session MQTT. Le journal consigne 28 registres lus, 14 lectures privées silencieuses non fatales et une paire fraîche après coupure pendant les bornes, sans relance. Une borne absente ou incohérente laisse les trois températures inconnues. `uart-session.lua:7`, `:171`, `service.lua:87`, `:155`, `:217`. Journal système (non publié)
- **Home Assistant.** Comparaison des JSON émis par les services v4 et v5 simulés. Les 18 identifiants CETHI et les 21 IC3 de la v4 sont conservés. CETHI ajoute `target_temp`, `setpoint_min` et `setpoint_max`. Sur IC3, seuls les quatre `env_*` deviennent des diagnostics désactivés par défaut. La v5 a 21 composants par appareil. Tailles CETHI/IC3 vérifiées pour les configurations 16 caractères / 30 s et 48 caractères / 3 600 s respectivement — 4 938 / 4 891 et 5 708 / 5 661 octets, sous la limite de 6 144. Le calcul concorde avec la formule OEM pour les 51 201 bruts entiers des bornes mesurées.
- **Portée des essais.** Les neuf scénarios courts du dépôt et les contre-essais ci-dessus ont été exécutés sur les modules des archives avec LuaJIT ARM sous `qemu-arm`, UART et horloge simulés. Pour les valeurs publiées, le service complet a remis ses JSON à un courtier simulé en mémoire. La suite QEMU longue est documentée par son journal existant, terminé par `EXIT_STATUS 0`. Cette seconde revue est entièrement hors ligne.

## Synthèse en cinq lignes

**OK pour déployer le paquet de lecture d’état `v-a581179dd120`, reconstruit à l’identique.**  
B1, B2 et M1 sont corrigés. Hors phase et garde, CETHI et IC3 retrouvent le comportement v4.  
La garde réserve l’UART jusqu’au silence et au vidage du parseur. Une trame inattendue invalide les bornes.  
I1 reste partiel. Un ancien MIN plausible peut fausser la consigne affichée de 41,0 à 43,5 °C dans l’essai à mi-échelle.  
Le relevé matériel donne 62 °C en haut d’échelle. Les identifiants Home Assistant et les tailles MQTT sont vérifiés.

> Les empreintes historiques des fichiers expurgés se rapportent aux originaux privés.
