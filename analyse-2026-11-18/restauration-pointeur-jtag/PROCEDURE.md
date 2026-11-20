# Rétablir le choix de la banque OEM par JTAG

**18 novembre 2026 — Référence et modèle validés à blanc. Restauration matérielle non qualifiée.** La procédure vise deux fichiers d’amorçage, pas la réinstallation de la banque OEM. Elle suppose que la banque, ses applications et la chaîne d’amorçage commune sont intactes. Aucun accès au hub, au Pi, au réseau ou au JTAG n’a été effectué pour ce travail. Aucune écriture matérielle, aucun script de programmation et aucune modification du PKM.

## 1. Ce qui choisit la banque

- Le K-Boot étudié lance `usr/sbin/boot-ubifs` depuis son initramfs (CPIO `0x402fdc`). Ce script lit `/persistent/boot/boot_information_file` et `/persistent/boot/boot_count_file` (lignes 52–60). Il calcule le nouvel essai avant de monter la racine. Au seuil `>= 3`, il choisit l’autre banque en mémoire **et remet le compteur à zéro** (lignes 63–75). Si le montage échoue, il essaie l’autre banque immédiatement (lignes 89–105). Aucun de ces replis ne réécrit un pointeur valide. La branche sous le seuil peut réécrire un pointeur absent ou invalide vers `ubi0:root` (lignes 76–86).
- Il n’y a pas de bit de confirmation A/B distinct dans ce chemin. L’état est le **couple pointeur + compteur**. Dans l’OEM, `etc/init.d/bootcount-reset:17` remet le compteur à zéro ; il ne vérifie pas la santé des services. `image-update-functions.sh:237` désigne la banque pour le prochain démarrage. Le registre `0xfffffe60` et `/sys/kboot/{mode,next}` désignent un mode K-Boot, pas une banque. Un retour temporaire en RAM ne prouve pas un retour durable.
- Sur la sauvegarde du 17 novembre, l’OEM sélectionné est `rootB` (volume UBI 9) et ses applications sont `appsB` (8). L’autre paire est `root` (7) et `apps` (12). `rootB/etc/init.d/mount-apps.sh:7–30` sélectionne les applications d’après la racine. Ces noms et identifiants décrivent la capture ; ils ne suffisent pas à identifier une banque OEM sur un état futur.
- Dans `/persistent/boot/update`, `bootloaderid` est vérifié et, si nécessaire, écrit **après** le choix de racine (`boot-ubifs:110–119`). `rootB.txt`, `appsB.txt` et `version-hash.txt` sont des témoins d’installation ou de version, pas des acquittements de démarrage. Ne pas les restaurer pour changer de banque. Le volume `persistent-spare` (10) est distinct ; son mécanisme OEM de restauration peut remettre un état persistant plus ancien si ses conditions sont remplies. Vérifier ce risque avant le démarrage, sans modifier ce volume dans cette procédure.

Sources : [analyse K-Boot, section 2](../kboot-bootloader-sol/RAPPORT.md), script du sélecteur (non publié), remise à zéro OEM (non publié), gestion de la copie persistante (non publié).

## 2. Repères dans la sauvegarde vérifiée

Source JTAG : `donnees/nand-2026-11-17/`. Données : `nand-data-128MiB.bin` (`0x8000000` octets) ; brut intercalé : `nand-full-A-data-oob.raw` (`0x8400000` octets). La zone bootstrap `mtd0` couvre `[0x0, 0x20000)` ; la zone UBI `mtd1` couvre `[0x20000, 0x8000000)`. Un bloc physique (PEB) contient 64 pages de `0x800` octets + `0x40` d’OOB chacune. Dans la zone UBI, l’en-tête EC commence au début du PEB, le VID à `+0x800`, et les données du bloc logique (LEB) à `+0x1000`. Un LEB fait `0x1f000` octets. Pour un offset absolu de données `A`, le brut correspondant est `(A // 0x800) × 0x840 + (A % 0x800)`.

L’UBIFS du volume `persistent` (6) est reconstruit dans `analyse-2026-11-17/extraction/volumes/nand-data-128MiB.bin/img-372254595_vol-persistent.ubifs`. Les offsets suivants sont hexadécimaux et pointent au **début des nœuds**, sauf les lignes « octets du fichier ». La colonne « NAND données » part du début de la puce, pas de `mtd1`.

| Structure | UBIFS reconstruit | NAND données | Brut JTAG avec OOB |
|---|---:|---:|---:|
| Pointeur, entrée du répertoire DENT → inode 70 | `0x137b10` | `0x1022b10` | `0x10a3c50` |
| Pointeur, INO | `0x15d000` | `0xde9000` | `0xe58480` |
| Pointeur, DATA ; LEB 23 + `0x16800`, PEB 112 ; nœud de `0x3b` octets | `0x2df800` | `0xe17800` | `0xe883c0` |
| Pointeur, octets du fichier (`DATA + 0x30`) | `0x2df830` | `0xe17830` | `0xe883f0` |
| Compteur, DENT → inode 71 | `0x137ca0` | `0x1022ca0` | `0x10a3de0` |
| Compteur, INO | `0x2fe000` | `0xd97000` | `0xe03b80` |
| Compteur, DATA ; LEB 22 + `0x9000`, PEB 109 ; nœud de `0x32` octets | `0x2b3000` | `0xdaa000` | `0xe17500` |
| Compteur, octets du fichier (`DATA + 0x30`) | `0x2b3030` | `0xdaa030` | `0xe17530` |
| Répertoire `/boot/update`, DENT → inode 66 | `0x136980` | `0x1021980` | `0x10a2a40` |
| `bootloaderid`, DATA | `0x1a3000` | `0x2131000` | `0x223a880` |
| `rootB.txt`, DATA | `0x2de800` | `0xe16800` | `0xe87340` |
| `appsB.txt`, DATA | `0x2df000` | `0xe17000` | `0xe87b80` |
| `version-hash.txt`, DATA | `0x2e6800` | `0xe1e800` | `0xe8f740` |

**Données de référence à restaurer, sous conditions :** `\n` désigne un seul octet LF, sans CR ni BOM. Les longueurs et SHA-256 portent sur les fichiers, pas sur les pages ni les nœuds.

| Fichier | Octets | Taille | SHA-256 |
|---|---|---:|---|
| `/persistent/boot/boot_information_file` | `ubi0:rootB\n` | 11 | `13be208104fa2d0572e01f277e0552f42e0164da69d3d26131182cf2670796ee` |
| `/persistent/boot/boot_count_file` | `0\n` | 2 | `9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa` |

**Structures sous les fichiers.** Dans `nand-data-128MiB.bin`, le superbloc UBIFS est à `0x2381000`. Les maîtres à `0x8a8000` et `0x8c8000` indiquent le commit 477 et les flags `0x3`, dont l’indicateur de journal non propre. La racine d’index est à `0x2fa1c40`. Le journal à `0x2f81000` comporte des références à `+0x20`, `+0x60` et `+0xa0` vers les LEB 19, 24 et 22. Parcourir l’index n’équivaut pas à rejouer ce journal. Les deux tables UBI ont un enregistrement `persistent` à `0xfa1408` et `0xfe1408`, avec `upd_marker=0` dans cette capture. Ce drapeau indique l’état d’une mise à jour de volume, pas une confirmation de banque.

**Ne jamais programmer ces adresses.** Dans la capture Linux ultérieure corrigée par ECC, non atomique, le compteur contient les mêmes octets mais son nœud réside en LEB 22 + `0xe800`, PEB 387, à `0x306f800` dans les données NAND. Cinq LEB de `persistent` ont changé de PEB et douze LEB ont changé de contenu, alors que les 35 fichiers réguliers indexés sont inchangés. Une recette qui modifie des pages fixes risquerait d’altérer le journal, des fichiers voisins ou les données de correction. Voir comparaison des deux captures (non publié) et métadonnées de l’extraction (non publié).

## 3. Procédure proposée — exécution interdite dans cette tâche

**Choix de conception : OpenOCD/JTAG sert à prendre la main et à charger un Linux de secours dédié en RAM.** Ce Linux, et non OpenOCD, réalise une éventuelle écriture logique via MTD/UBI/UBIFS. Le Buildroot déjà démarré par JTAG n’a ni MTD ni UBI ; il faut produire et qualifier une image dédiée. Pas d’écriture brute, de réinjection de l’OOB historique, d’effacement direct, de déprotection ni de formatage. Si `persistent` ne peut pas être monté sainement ou si la banque a disparu, cette procédure ne sait pas la restaurer.

1. **Prendre la main sans amorcer le système installé.** Sur matériel autorisé seulement : confirmer la carte, la tension de référence, la chaîne JTAG (`0x0792603f` observé historiquement), la puce et la géométrie. Disposer d’une alimentation stable, d’une console locale et d’une méthode testée pour empêcher un démarrage automatique ou un reset watchdog. Établir un état sans opération NAND en cours ; le `halt` seul ne prouve pas que le contrôleur et les autres maîtres du bus sont inactifs. Mettre le CPU en pause et confirmer l’état à deux lectures. Charger l’image de secours épinglée en RAM, vérifier sa taille et son SHA-256 par relecture avant de la lancer. Ne jamais reprendre le contexte de l’ancien Linux. Le CPU exécute **uniquement** le secours pendant l’opération logique ; il ne reste pas en pause pendant une écriture par Linux. Aucun réseau, automontage, script de mise à jour ou client radio dans le secours.
2. **Capturer l’état initial sans écriture de flash.** Avec une voie de lecture brute non mutante validée, capturer deux fois l’intégralité des données et des OOB, enregistrer tailles, empreintes par lot et empreinte globale. Conserver ces captures hors hub. Relever la carte EC/VID, l’état des blocs, des réserves et de l’ECC ; comparer avec une lecture corrigée ou un décodage hors ligne qualifié. Analyser une copie, y compris le rejeu du journal si requis. Ne pas assimiler montage UBIFS en lecture seule et absence d’écritures physiques : l’attache UBI et certaines initialisations MTD peuvent modifier le support. N’autoriser aucune attache sur la cible avant d’avoir qualifié les effets de cette phase et prévu son autorisation.
3. **Figer le périmètre avant la première écriture possible.** Vérifier l’identité du volume `persistent`, sa cohérence et son espace disponible ; relever les types, modes, propriétaires, attributs et SHA-256 des entrées, ou consigner leur absence. Refuser les liens, les types inattendus et les noms ambigus. Vérifier que le K-Boot courant utilise toujours le sélecteur décrit et que `rootB` **et** `appsB` correspondent à la référence OEM approuvée (inventaire et empreintes logiques, noyau et paramètres d’amorçage compris). Vérifier la chaîne commune et le mécanisme `persistent-spare`. Refuser la procédure si l’OEM attendu n’est plus `rootB` ou si une protection, une erreur non corrigée, un journal non résolu ou l’état d’un volume reste ambigu. Sceller le manifeste d’avant et conserver la copie à restaurer indépendamment du hub. Si la paire présente correspond déjà et que les preuves requises sont disponibles, ne rien écrire.
4. **Remplacer les deux fichiers seulement.** Après le feu vert séparé, utiliser le pilote NAND compatible et le système de fichiers du secours, avec `persistent` comme seul volume monté en écriture. Vérifier à nouveau l’état initial et l’exclusivité, puis créer deux fichiers temporaires dans le même répertoire, avec les octets de la référence vérifiée. Préserver les modes, propriétaires et attributs attendus ; pour une entrée absente, n’appliquer le mode de référence `0644`, UID/GID `0`, que si cette création fait partie du périmètre approuvé. Relire les temporaires, synchroniser les fichiers, renommer le compteur puis le pointeur, et synchroniser le répertoire après chaque renommage. Contrôler tous les retours et démonter proprement. Le changement des deux fichiers n’est pas atomique : garder le démarrage OEM interdit sur toute la fenêtre, y compris après une coupure. Ne pas toucher aux témoins ni aux autres volumes. UBI/UBIFS peut déplacer des blocs et mettre à jour ses métadonnées ; le périmètre logique de deux fichiers ne signifie pas deux écritures physiques.
5. **Vérifier avant de libérer le démarrage.** Relire les deux fichiers après démontage via une acquisition indépendante et un décodage qui tient compte d’UBI et du journal ; ne pas se limiter au cache du premier montage. Vérifier type, taille, SHA-256 et attributs attendus. Comparer l’inventaire logique avant/après de `persistent` (aucun autre fichier modifié, ajouté ou supprimé, aucun temporaire ; métadonnées de répertoire attendues) et les empreintes des autres volumes et du bootstrap. Documenter tout déplacement ou entretien physique ; ne pas exiger le SHA-256 de la NAND brute historique après une écriture logique. Vérifier les compteurs ECC, les journaux et l’absence d’erreur avant de décider d’un démarrage. Ne redémarrer qu’avec une autorisation distincte couvrant ce test.

### Arrêt et retour arrière

| Incident ou écart | Décision |
|---|---|
| Instabilité JTAG, mauvaise cible, CPU non maîtrisé, NAND occupée, tension ou watchdog incertains | Arrêt avant toute écriture. Ne pas relancer le Linux interrompu ni supposer la NAND au repos. |
| Mappage, banque, OOB/BBT, pilotes, CRC ou état de journal incompatibles ; réserve insuffisante ; erreur ECC non corrigeable | Arrêt. Ne pas réinjecter un PEB historique ni tenter un formatage. La puce utilise le PMECC matériel (4 bits par secteur de 512 octets) et une table de blocs défectueux en NAND. Deux captures brutes identiques ne prouvent pas l’absence d’erreurs stables. |
| Coupure, reset, échec de synchronisation ou SHA-256 divergent | Bloquer le démarrage installé. Conserver les preuves, reprendre en secours sans attache mutante et relire l’état réel. Ne pas répéter l’écriture à l’aveugle. |
| Divergence limitée aux fichiers cibles ; UBIFS sain et retour préautorisé | Reposer par la même voie logique les valeurs **fraîches d’avant l’intervention**, avec leurs attributs ; rétablir une absence seulement si elle a été enregistrée et autorisée. Démonter, refaire la lecture indépendante et comparer au manifeste initial. C’est un retour à l’état initial, pas la preuve que cet état démarre. |
| Corruption UBIFS/UBI, écart hors périmètre, nouvelle erreur ECC ou retour non vérifiable | Arrêt. Conserver les acquisitions et qualifier une récupération de volume ou de support à part. Ne pas laisser démarrer K-Boot en cas de doute : `etc/init.d/mount-partition:26–28` appelle un formatage de `persistent` si son montage échoue. |

**Preuves à conserver en local et en privé :** autorisations et identité du support ; versions et empreintes des binaires et configurations du secours ; journal du `halt`, des lectures RAM et du watchdog ; captures A/B et carte UBI/ECC/BBT ; manifestes logiques avant/après et résultat d’une éventuelle restauration inverse. Retirer les valeurs privées des comptes rendus. Les codes d’erreur et les résultats de contrôle doivent rester visibles.

## 4. Validation à blanc et limite de qualification

**Exécuté sur fichiers Windows :** `py -I -B -u analyse-2026-11-18/restauration-pointeur-jtag/verification_hors_ligne.py`, avec `ubi-reader` 0.8.16 déjà installé. Le [vérificateur](verification_hors_ligne.py) n’ouvre que des fichiers en lecture. Tous les membres listés par `SHA256SUMS` concordent entre l’archive et le dossier. Les 64 lots A/B concordent ; les 65 536 pages se décomposent exactement en données et OOB. L’index UBIFS, les longueurs, les CRC des deux nœuds, les bornes de page et leur correspondance avec le brut ont été contrôlés. Une seconde lecture locale des structures a confirmé les repères du tableau. Le modèle en mémoire accepte la paire exacte, rejette une mise à jour partielle dans les deux ordres et une altération voisine, et vérifie un retour à l’état initial, y compris avec un fichier initialement absent.

| Pièce de référence | SHA-256 vérifié |
|---|---|
| `donnees/cozytouch-nand-20261117.tar.gz` | `b6057c380adf210d397d6f1a94bb9e2891e169c539c984f50228da1b89f2ac4d` |
| `donnees/nand-2026-11-17/nand-full-A-data-oob.raw` | `ce0be49873209b6d1565403c8292e376c466bc8d89fc000bd7afb5f452578d8e` |
| `donnees/nand-2026-11-17/nand-data-128MiB.bin` | `91797af053f204d5fc5bf10ff664d3c47f458a7185d88f03573b7ab12c8c94c2` |
| `donnees/nand-2026-11-17/nand-oob-4MiB.bin` | `0f5d7159aa695095909749c970bd904814151714a3af4cad265755889096a5c8` |

**Restant hors ligne :** construire le secours RAM et revoir son pilote, son DTB et son plan mémoire. Vérifier le futur lanceur avec des cibles factices qui refusent tout accès à un adaptateur ou à un réseau : syntaxe et chemins des scripts, bornes et absence de recouvrement des segments RAM, tailles de transfert et empreintes, rejet d’une mauvaise géométrie ou d’un mauvais volume, arrêt à chaque erreur. Rejouer la séquence logique sur des copies jetables avec une pile UBI/UBIFS représentative et vérifier aussi le journal. Le dry-run actuel ne lance ni Tcl/OpenOCD ni un noyau de secours ; il ne valide pas l’ECC d’une écriture, la programmation, la synchronisation ni le rejeu réel.

**Sous autorisation séparée :** d’abord sur matériel de réserve équivalent, qualifier le contrôle du CPU, le secours RAM, l’innocuité de la prélecture, l’ECC et la procédure complète. Tester des interruptions contrôlées, notamment entre les deux renommages, puis la récupération et les relectures indépendantes. Vérifier ensuite sur ce banc des démarrages à froid répétés, la racine OEM réellement montée, la paire d’applications et la stabilité du pointeur après le passage OEM. Ne pas assimiler compteur à zéro et validation fonctionnelle des services. Un vrai essai est indispensable pour prouver la tenue après coupure, les effets du pilote et de la copie de secours, et le démarrage durable. Toute intervention sur le hub de <PERSONNE>, même une nouvelle capture JTAG, reste hors de cette tâche et exige son autorisation ; aucune écriture sur le hub avant réussite du banc et accord sur le périmètre exact, le retour arrière et le redémarrage.

> Les empreintes historiques des fichiers expurgés se rapportent aux originaux privés.
