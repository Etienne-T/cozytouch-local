# Réponses des trois sondes : octets acquis, conversion partiellement étayée

Analyse hors ligne du 17 novembre 2026. Les captures matérielles ont été réalisées par le coordinateur. Cet agent ne s'est connecté ni au bridge ni aux appareils et n'a modifié aucun artefact figé.

**Le Calypso répond aux trois lectures nommées 001a/001b/001c.** Les contrôles du coordinateur corrèlent l'indice, la source et la destination, avec CRC valide. Les six octets de valeur sont donc acquis. Le callback D-Bus vide ne permettait pas, à lui seul, de constater cette réponse.

| Lecture | Valeur privée, après préfixe Atlantic | RSSI rapporté | Premier mot i16 big-endian | Si le codec natif de sonde d'eau s'applique |
|---|---|---|---|---|
| Air entrant001a | `00 d8 ff ec 01 7f` |−73 dBm |216 |21,6 °C |
| Évaporateur bas001b | `00 d8 ff 84 02 48` |−71 dBm |216 |21,6 °C |
| Évaporateur haut001c | `00 d9 ff 6e 02 71` |−72 dBm |217 |21,7 °C |

La dernière colonne est une **conversion fortement corroborée, mais son application exacte à ces trois registres reste inférée**. Elle ne vient pas du bus HMI ni d'AquaMQTT.

## Ce que démontre le logiciel natif

Dans le catalogue appsB, l'identifiant 201332481=`0x0c001701` de `SondeEauChaude1` alimente `io:MiddleWaterTemperatureState` via `slot0[302]`, lignes 18993–19001. Le convertisseur 302, lignes 2296–2302, retourne `readInt16(1) / 10`. Il ignore donc les quatre octets suivants pour cette température.

La décompilation `rea/ByteArray-focused.c`, fonction `ByteArray::read` Ghidra`0x20328`, établit deux points :

- Sans argument d'ordre des octets, le booléen d'ordre vaut true. La boucle place le premier octet dans la position haute : **big-endian par défaut**.
- La branche signée étend le bit de signe avant de convertir en nombre. Les mots négatifs suivent le complément à deux ; ce ne sont pas des u16 arbitrairement divisés par dix.

Le routeur `GenericV2::analyze` vérifie l'indice BE de la réponse, retire le préfixe de quatre octets et publie le Blob restant. Il ne convertit pas la température. Les trois modules `SondeAirEntrant`, `SondeEvaporateurBas` et `SondeEvaporateurHaut` déclarent READ, sans fonction de décodage ni unité.

La recherche des trois identifiants exacts dans le catalogue appsB ne trouve aucun lien vers un état de température ni vers le convertisseur 302. Leur enregistrement C++ est établi par l'étude précédente ; c'est leur **liaison à une conversion d'unité** qui manque. La proximité des registres, le nom des modules et le format de réponse soutiennent l'extension du codec d'eau, sans constituer une preuve exacte de cette liaison.

## Quatre octets encore non interprétés

Les deux autres mots, si on les lit en i16BE, valent :

| Lecture | Mot2 brut | Mot3 brut |
|---|---:|---:|
| Air |−20 |383 |
| Évaporateur bas |−124 |584 |
| Évaporateur haut |−146 |625 |

Ils pourraient représenter d'autres mesures, des limites ou des statistiques. Aucune structure native identifiée ne permet de choisir. **Les appeler minimum/maximum ou drapeaux serait prématuré.** Aucune conversion en degrés de ces deux mots n'est publiée comme fait.

La suite utile serait une définition constructeur du registre ou une corrélation indépendante avec un affichage de diagnostic déjà disponible. Un simple nouveau prélèvement montrant le même ordre de grandeur renforcerait l'hypothèse ; il ne démontrerait pas à lui seul la sémantique des quatre octets supplémentaires. Aucun balayage de registre, remise à zéro de statistiques ou ordre de fonctionnement n'est proposé pour résoudre ce point.

## Conservation

`decode_offline.py` lit seulement les deux résumés expurgés du coordinateur et les sources natives locales. Il vérifie le convertisseur 302, restitue les calculs BE/LE et produit `decodage.json`. `preuves-natives.txt` conserve les extraits numérotés. Le manifeste propre à ce dossier donne les SHA-256. Les captures brutes privées, les adresses uniques et les clés restent dans les preuves du coordinateur et ne sont pas reproduites ici.

> Les empreintes historiques des fichiers expurgés se rapportent aux originaux privés.
