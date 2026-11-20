# Contre-vérification de la réponse Cursor/Grok

Le 17 novembre 2026, Cursor CLI `2026.11.13-eacade1`, appelé avec `grok-4.7-high`, a terminé sa revue réelle du corpus expurgé après 7 min 49 s, code 0. La réponse originale reste dans `cursor-grok-result.json` et `RAPPORT-GROK.md`. Elle apporte des recoupements utiles, mais certaines phrases dépassent les preuves fournies.

## Conclusions retenues

Les offsets de la clé à 18 et de la sous-commande à 34 sont corrects. Le timestamp ignoré de deux octets doit conserver sa place dans le constructeur. Le passage du pointeur de clé dans `r1` corrige bien les prototypes Ghidra incomplets. Les blocs SRAM à `+2` et `+0x12` sont distincts, sans preuve d’identité sémantique automatique avec les champs Linux `key` et `oldKey`.

La priorité `node.oldSystemKey`, sinon `stackMaster.key`, est établie pour le constructeur Lua General Information réutilisé par la demande de statut. La découverte délègue à `getCurrentSystemKey`, dont le corps C++ reste absent du corpus. Les commentaires générés du désassembleur et le `slot10` incomplet de la reconstruction ne doivent pas être pris pour des définitions sources exactes.

La présence d’une copie conditionnelle de 16 octets par `0x0802b860` au démarrage est réelle, mais sa nature n’est pas identifiée. Elle ne permet ni d’affirmer que toutes les clés sont absentes de Flash, ni d’assimiler ces octets à la clé effective des appareils. Les chemins d’installation inspectés pour les demandes UART écrivent en SRAM.

**Contrôle supplémentaire du passage courant → secondaire :** le désassemblage Thumb local `current-to-secondary-thumb.txt`, produit après la réponse à partir de l’image constructeur déjà vérifiée identique au code réel, complète les extraits de Grok. `0x0800411c` garde le pointeur entrant dans `r5`, appelle `0x0800d0c0 → 0x0801ccf8 → 0x0800aaa4` pour obtenir le bloc courant `+2`, passe ce résultat dans `r1` avec `r2=0` vers `0x0800d084`, puis passe `r5` dans `r1` avec `r2=1`. Les wrappers déjà conservés montrent respectivement la copie en `+0x12` puis en `+2`. Pour ce chemin et un index valide, le second bloc reçoit donc la valeur courante avant l’installation de l’entrée. Ce résultat ne démontre pas que les noms Linux `oldKey` et `key` désignent systématiquement ces deux blocs.

## Corrections nécessaires

| Passage de Grok | Contre-vérification |
|---|---|
| `FUN_0801a844` « n’en recopie au plus que 6 » | Faux dans le corps générique : le plafond est 16 (`stm32-focused.c:1189–1193`). Les appels d’authentification examinés demandent six octets. |
| Les deux captures « correspondent au second terme », c’est-à-dire au repli `stackMaster.key` | Trop fort. L’égalité observée ne distingue pas un `oldSystemKey` absent d’un `oldSystemKey` contenant déjà les mêmes octets. Grok donne lui-même cette alternative plus haut. |
| « Prendre actuator.key ou stack.oldKey contredirait à la fois le schéma et ces captures » | Le schéma impose 16 octets, pas une politique de sélection. Une telle substitution ne reproduirait pas les demandes observées et pourrait échouer ; le corpus ne teste pas toutes les clés candidates ni toutes les opérations. |
| « Les lectures ont réussi parce que l’index maître, l’adresse et la session radio existaient déjà » | L’état initialisé est une condition du scénario observé. Sa nécessité complète et la causalité de chaque élément ne sont pas démontrées par ces captures. |
| « Corréler deux 0x0100 simultanés est impossible avec les octets de trame seuls » | L’absence d’identifiant universel justifie de sérialiser les demandes. Elle ne démontre pas une impossibilité générale : des champs source/cible et des contextes distincts peuvent aider à les distinguer selon le callback. Deux demandes identiques vers le même appareil resteraient ambiguës sans autre contexte. |
| Le STM32 ne suffirait plus si le client veut « interpréter un refus radio » | Interpréter les statuts et erreurs exposés sur UART peut rester une tâche hôte sans réimplémentation AES. Une pile RF native ou une vérification cryptographique indépendante serait un autre périmètre. |

Le schéma de séquence de Grok doit aussi être lu comme une simplification : `DONE/IoCommandNoError` est une terminaison logicielle Linux, pas un message UART émis textuellement par le STM32. La réponse `0x010d` décrit un callback, pas les octets RF.

## Preuve postérieure au corpus envoyé

La réponse de Grok indique qu’aucun autre client ni scénario sans WAN n’a été testé. Cette phrase est fidèle au corpus figé qu’il a reçu. Pendant son analyse, le coordinateur a terminé un essai supplémentaire, conservé dans `../orchestration/verified-results.json` :

- Client LuaJIT indépendant, daemon constructeur arrêté : CETHI `DONE` en 69 ms, IC3 `DONE` en 85 ms.
- Nouveau processus de ce client sous blocage IPv4/IPv6, hors loopback et pair SSH exact : CETHI `DONE` en 72 ms, IC3 `DONE` en 111 ms.
- Règles réseau restaurées exactement et contrôle de reprise du service réalisé par le coordinateur.

Ces résultats lèvent le blocage de clés pour **les deux lectures principales à chaud**, sans le daemon constructeur ni disponibilité IP des services externes pendant le scénario isolé. Ils ne prouvent pas le démarrage froid du STM32, la sélection générale de clé, les écritures, le transfert de clé ou l’association. Le corpus approuvé a été conservé inchangé ; ce complément n’a pas été envoyé à Grok.

La synthèse locale courante est `CONTRE-ANALYSE-LOCALE.md`. L’analyse de démarrage froid reste séparée d’une nouvelle opération active : la présente revue n’a envoyé aucune commande matérielle.
