# Sauvegarde NAND — 17 novembre 2026

État : sauvegarde terminée le 17 novembre 2026. Image brute complète vérifiée par relecture indépendante des 65536 pages ; les 64 SHA-256 de lots et les CRC32 concordent. Image de 138412032 octets ; SHA-256 `ce0be49873209b6d1565403c8292e376c466bc8d89fc000bd7afb5f452578d8e`. Copies Windows et HP vérifiées, archive complète conservée avec les preuves. <PERSONNE> a autorisé la poursuite autonome jusqu'à la sauvegarde de la NAND. Aucune commande d'effacement ni de programmation NAND.

## Méthode vérifiée

- Pi `<CHEMIN_LOCAL>`, SSH `<UTILISATEUR_ADMIN>@<IP_ADMIN>`, clé utilisateur existante `<CHEMIN_LOCAL>`. OpenOCD 0.12.0+dev-snapshot, JTAG natif GPIO. Configuration `nand-session.cfg`.
- ARM926EJ-S reconnu, IDCODE 0x0792603f. `soft_reset_halt` désactive MMU et caches sans réinitialiser les contrôleurs DDR et NAND. La mémoire vive est modifiée pour la lecture ; le système Linux ne doit pas être repris à son ancien contexte.
- NAND Macronix MX30LF1G18AC-TI identifiée sur photo ; géométrie détectée par OpenOCD : 128 Mio, 65536 pages, 2048 octets de données + 64 octets OOB, 1024 blocs de 64 pages.
- Routine ARM `nand-reader.s` chargée en SRAM à 0x00307000. Elle émet uniquement les commandes NAND 00h et 30h et transfère les pages physiques dans la RAM à 0x20000000. Elle alimente le watchdog. Point d'arrêt matériel à 0x003070bc. Chaque transfert vérifie PC, fin du tampon, index de page et compteur restant avant d'exporter la RAM.
- Le processeur calcule un CRC32 sur tous les octets et un indicateur par page (ET binaire de tous ses octets). Une page dont cet indicateur vaut FF est entièrement effacée ; le Pi la reconstitue en FF au lieu de la retransférer. Le CRC32 du bloc reconstitué doit être identique au CRC32 calculé par le processeur. Cela réduit le transfert sans sauter de lecture NAND. Indicateurs et plages réellement transférées sont conservés. Version initiale sans cette optimisation : `nand-reader-basic.s` et `backup-nand-basic.py`.
- Pages 0, 63, 4096 et 65535 identiques à une lecture OpenOCD lente, OOB compris. Premier bloc relu indépendamment et transferts RAM comparés à plusieurs vitesses JTAG : identiques sur cet essai initial. Les erreurs ultérieures ont imposé une réduction de vitesse. Réglage retenu : 1977 kHz annoncés, mode rapide désactivé ; les contrôles CRC restent indispensables.
- `backup-nand.py backup` a produit le passage A complet. Tous les blocs, y compris ceux éventuellement marqués défectueux, sont lus. Chaque lot contient 1024 pages. Aucun ECC n'est corrigé. L'ordre physique et les OOB sont conservés. Taille de l'image brute : 138412032 octets (132 Mio).
- La seconde passe utilise désormais `verify-nand-target.py verify` : nouvelle lecture NAND de chaque lot, CRC calculé sur le bridge, puis SHA-256 du tampon calculé sur le bridge et comparé au SHA-256 du lot A sauvegardé. Elle ne reconstruit pas artificiellement une image B. Ce choix évite de retransférer toute la NAND sur un JTAG lent et sujet aux erreurs, tout en relisant chaque octet et en vérifiant une empreinte cryptographique de chaque lot.
- SHA-256 en SRAM à 0x00300000, point d'arrêt 0x00300008, pile 0x00306f00, résultat à 0x20301000. Sources `sha256-target.c`, `sha256-start.s`, `sha256.ld`. Binaire de 1172 octets relu depuis le bridge à SHA-256 identique au binaire compilé ; le lecteur NAND de 224 octets est aussi relu identique. 14 tests sur le Pi passent, puis 11 tests sur le bridge, dont les messages NIST, les frontières de remplissage SHA et un lot NAND rempli de 2162688 octets déjà acquis. Preuves : `sha256-host-validation.json` et `sha256-target-validation.json`.

## Processus et preuves

Sur le Pi : `<CHEMIN_LOCAL>`.

- OpenOCD persistant, port Tcl 6666 lié à 127.0.0.1 ; journal `nand-20261117/openocd-02.log`.
- Acquisition optimisée : journal initial `nand-backup-20261117/backup-progress.jsonl`, puis `backup-progress-resumed.jsonl` et `backup-progress-resumed2.jsonl`. Processus de la seconde reprise : PID initial 15567. Première acquisition non optimisée arrêtée après quatre lots, conservée dans `nand-20261117/` ; ses quatre lots correspondent à l'acquisition optimisée. Le script reprend les lots validés après contrôle SHA-256 et taille. Sur écart CRC, il conserve les plages rejetées et relit le lot ; à la deuxième répétition il réduit à environ 1 MHz. Trois échecs arrêtent l'acquisition.
- Image complète dans `nand-backup-20261117/` : `nand-full-A-data-oob.raw`. Un éventuel fichier `nand-full-B-data-oob.raw` provient du début de l'ancienne méthode interrompue ; il n'est pas une image de référence.
- Lots bruts et manifeste SHA-256 dans `pass-A/`. Seconde lecture dans `verification-B.jsonl` et `verification-B/` : chaque empreinte est comparée au lot A correspondant. L'éventuel dossier `pass-B/` appartient au début interrompu de l'ancienne méthode. Un écart de vérification est signalé et doit être étudié avant de conclure.
- Validation : `nand-20261117/validation.log` et fichiers `validation-page*-slow.raw`, `validation-page*-custom.raw`.
- Première acquisition terminée, ancien pilote PID 15567 arrêté. Relecture SHA-256 : PID initial 23182, journal `nand-backup-20261117/verification-B-progress.jsonl`, manifeste `verification-B.jsonl`, empreintes binaires dans `verification-B/`. Copie compressée A préparée hors dossier source : `<CHEMIN_LOCAL>`.

Ne pas ouvrir de commande Tcl concurrente pendant un transfert ; consulter le journal par SSH. Ne pas couper les alimentations ou modifier les fils pendant l'acquisition. En cas d'erreur, conserver les lots, contrôler l'état réel avant toute reprise. Les scripts refusent d'écraser les images existantes.

## Incident OpenOCD contourné

La routine NAND accélérée intégrée (`arm_nandread`) ne termine pas correctement sur ce montage : délai dépassé, CPU non arrêté, puis retour trompeur « dumped ... bytes ». Les essais `page0-...` issus de cette routine ne constituent pas une sauvegarde. Seule `page0-slow-a.raw` et les lectures personnalisées comparées sont validées. Le code source `arm_io.c` explique pourquoi une erreur d'exécution peut être suivie d'une lecture de tampon et d'un succès apparent. Cause exacte du défaut d'exécution non établie.

Une erreur de transfert est aussi détectée par CRC sur le lot des pages 6144–7167 à 3646 kHz avec `fast_memory_access enable` : deux octets différents aux offsets 733080 et 737340 du tampon. Une relecture du même tampon sans nouvelle acquisition NAND, à 1977 kHz et `fast_memory_access disable`, donne le CRC attendu 98331b85. Les indicateurs de pages effacées sont corrects. Preuve conservée : `failed-buffer-reread.raw`, les plages du premier transfert et `inspect-buffer.py`. La sauvegarde reprend avec ces réglages réduits ; les lots précédents ont leur CRC valide. Il n'est pas établi si la vitesse, le mode rapide, ou leur combinaison explique l'erreur.

Un essai intermédiaire à 2991 kHz, mode rapide désactivé, échoue aussi au CRC sur un tampon de 2162688 octets : attendu c031538a, reçu b2f972b2. Essai conservé dans `buffer-speed3000.raw` et `transfer-speed3000.json`. Retour automatique à 1977 kHz. Ne pas retenir 3 MHz pour ce câblage ; le mode rapide n'est pas la seule condition d'échec observée.

Un autre écart de transfert est détecté à 1977 kHz sur le lot des pages 31744–32767 (62–64 Mio de données), attendu 49856d8b, reçu 9df76e1f. Une nouvelle lecture NAND calcule à nouveau 49856d8b et son transfert concorde. Ce lot validé est retenu ; le premier transfert rejeté reste conservé. La vitesse réduite ne dispense donc pas du contrôle CRC de chaque lot.

## Résultat et conservation

Vérification sur Windows terminée : 128 CRC de lots et 64 SHA-256 indépendants conformes. Images dérivées créées : 128 Mio de données et 4 Mio d'OOB. 26074 pages entièrement FF ; aucun premier octet OOB non-FF sur les deux premières pages de chaque bloc (ce contrôle ne garantit pas l'état électrique des blocs). 1019 en-têtes UBI aux frontières de blocs ; aucune reconstruction de volume UBI effectuée.

Les deux points d'arrêt ont été retirés, OpenOCD est arrêté et les GPIO 8/9/10/11 du Pi sont vérifiés en entrée. Aucun redémarrage du bridge n'a été envoyé : sa RAM a été utilisée pour la lecture et il faut un redémarrage électrique pour reprendre son fonctionnement normal. La NAND ne couvre pas la flash interne du STM32 radio ; aucune restauration sur matériel n'a été testée.

Windows : `donnees/nand-2026-11-17/`, rapport `verification.json`, contrôles des copies dans `copies-verifiees.json`. HP : `<CHEMIN_LOCAL>`. Les fichiers sont vérifiés par SHA-256 sur les deux machines. Source conservée sur le Pi ; aucun nettoyage effectué.

Archive finale `donnees/cozytouch-nand-20261117.tar.gz`, 319368713 octets, SHA-256 `b6057c380adf210d397d6f1a94bb9e2891e169c539c984f50228da1b89f2ac4d`, également copiée et vérifiée dans `<CHEMIN_LOCAL>`. Elle contient l'image brute de référence, les dérivés, manifestes, rapports et l'archive source. Cette dernière conserve 835 entrées, y compris les diagnostics rejetés ; son flux tar est vérifié entre Pi et Windows et les cinq membres critiques sont relus à empreintes conformes. La version de cette fiche dans l'archive source décrit l'état avant la vérification finale des copies ; la présente fiche et le dossier de sauvegarde donnent l'état final.

Sources techniques : [billet Lafois](https://www.lafois.com/2020/11/08/rooting-the-cozytouch-aka-kizbox-mini-part-2/), [OpenOCD NAND](https://openocd.org/doc-release/html/Flash-Commands.html#NAND-Flash-Commands), [adressage NAND OpenOCD](https://github.com/openocd-org/openocd/blob/master/src/flash/nand/core.c), [routine ARM native](https://github.com/openocd-org/openocd/blob/master/src/flash/nand/arm_io.c).

Vérification SHA-256 : [vecteurs NIST](https://www.nist.gov/itl/ai/ai-standards-and-guidelines-group/nsrl-test-data).

> Les empreintes historiques des fichiers expurgés se rapportent aux originaux privés.
