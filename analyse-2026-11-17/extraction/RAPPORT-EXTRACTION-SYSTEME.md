# Extraction NAND et services — 17 novembre 2026

Analyse hors ligne. Aucun fichier du firmware n’a été exécuté. Aucun accès au bridge ou au cloud fabricant. Les images sources sont conservées sans modification.

## Résultat et qualité

Source données : `donnees/nand-2026-11-17/nand-data-128MiB.bin`, SHA-256 `91797af053f204d5fc5bf10ff664d3c47f458a7185d88f03573b7ab12c8c94c2`. Outils déjà installés : Python 3.13, ubi-reader 0.8.16, PySquashfsImage 0.9.0. Les scripts utilisés sont conservés dans ce dossier.

Treize volumes ont été extraits dans `volumes/nand-data-128MiB.bin/`. L’extension `.ubifs` donnée par ubi-reader ne garantit pas le format : `dtb` et `dtb-spare` sont des FDT ; `kboot` et `kboot-spare` commencent par du code ARM ; `security`, `security-spare` et `persistent-spare` sont des SquashFS. Les six autres volumes sont des UBIFS.

| Volume UBIFS | Fichiers réguliers | Liens symboliques | Dossiers | Spéciaux |
|---|---:|---:|---:|---:|
| root | 586 | 445 | 168 | 0 |
| rootB | 586 | 443 | 168 | 0 |
| apps | 660 | 14 | 377 | 0 |
| appsB | 679 | 16 | 380 | 0 |
| data | 28 | 0 | 24 | 0 |
| persistent | 35 | 0 | 19 | 0 |

Les trois SquashFS ajoutent 23 fichiers réguliers : total **2 597 fichiers réguliers**, 918 liens symboliques. Aucun fichier spécial n’a été trouvé dans ces systèmes de fichiers. Les manifestes `metadata-*.json` conservent les chemins, modes, UID/GID, tailles, dates et SHA-256. Aucun LEB manquant n’est signalé par le parcours des index.

Les dossiers `../extracted/` servent à lire les fichiers réguliers sous Windows. Ils ne représentent pas une restauration POSIX : Windows a refusé la création des liens symboliques et deux liens physiques `vt220`. Les binaires `apps{,B}/overkiz/internal/bin/internald`, initialement créés, ne sont ensuite plus présents ; aucun agent ne les a déplacés ou supprimés. La cause n’est pas établie. Les archives `*-posix.tar` et `*-corrected-posix.tar` conservent leur contenu, les liens symboliques, modes et propriétaires.

## Anomalies et dérivés corrigés

Le scan des six volumes trouve **14 nœuds UBIFS avec CRC32 invalide** : root 3, rootB 5, apps 2, appsB 3, persistent 1. Le dernier n’est pas relié à un chemin dans l’index actuel. Les 46 282 autres nœuds trouvés par scan physique dans les PEB UBI ont un CRC valide. Aucun PEB ancien portant un autre exemplaire de volume n’a été trouvé : 634 PEB sélectionnés pour les volumes, 2 PEB de table et 383 autres PEB sans nœud UBIFS additionnel intact détecté.

Chaque nœud invalide admet **un seul retournement de bit** qui restaure son CRC32 après énumération exhaustive de tous ses bits, hors champ magique. Les copies dans `corrected-volumes/` appliquent ces 14 retournements. Les sources et volumes initiaux restent inchangés. Pour les huit nœuds des volumes statiques root/rootB, la même correction restaure aussi le CRC32 UBI de tout le bloc : contrôle indépendant conservé dans `static-crc-recovery-validation.json`.

Les 14 corrections ont ensuite été **vérifiées indépendamment contre les codes PMECC/BCH enregistrés dans les OOB**. Le DTB spécifie PMECC matériel, correction de 4 bits par secteur de 512 octets, NAND sur 8 bits et BBT en flash. Il décrit une partition bootstrap de 0x00000 à 0x20000, puis UBI de 0x20000 à 0x8000000. Voir `dtb-interesting-properties.json`. Le SHA identique de deux acquisitions ne garantit pas que les données NAND soient exemptes d’erreurs de lecture stables.

Le contrôle BCH utilise une implémentation Python locale de l’encodage polynomial, sans bibliothèque ajoutée : GF(2^13), polynôme primitif `0x201b`, racines 1 à 8, générateur `0x14523043ab86ab`. Une recherche sur les orientations des bits/octets, le décalage du bourrage et les positions OOB trouve une seule configuration concordante sur 20 secteurs de référence : bits de données et de parité LSB-first dans chaque octet, 52 bits de parité dans 7 octets, zone OOB `36 + 7 × secteur`. Sur 1 123 secteurs additionnels avec contenu non trivial, les 1 123 parités recalculées correspondent aux 7 octets stockés.

Pour chacune des 14 anomalies, la parité du secteur original diffère de l’OOB ; après le retournement du bit indiqué par le CRC, la parité recalculée correspond exactement à l’OOB. Les trois autres secteurs de chacune des 14 pages correspondent déjà (42/42). Le contrôle compare la totalité des sept octets, y compris le bourrage. Cela corrobore les corrections avec une preuve ECC indépendante du CRC. Un second contrôle construit les 4 148 syndromes distincts correspondant aux 4 096 bits de données et aux 52 bits ECC du secteur. À partir des données originales et des OOB seuls, cette table localise le bit fautif indépendamment du CRC : les 14 positions concordent exactement. Ce contrôle ne constitue pas un examen exhaustif des 262 144 secteurs de toute la NAND. Preuves : `bch-oob-layout-discovery.json`, `bch-independent-validation.json`, `bch-independent-error-location.json` ; code : `validate_bch_pure.py`, `check_bch_pages.py`, `locate_bch_single_errors.py`.

`single-bit-recovery.json` décrit les offsets dans les volumes, les offsets données NAND, les pages, les offsets dans l’image avec OOB et le bit modifié. `anomalous-pages-oob-private.json` conserve les OOB utiles sans les afficher. Les 12 fichiers visibles concernés et leurs nouveaux SHA-256 figurent dans `corrected-files.json` ; leurs copies lisibles sont dans `../extracted-corrected/`. `*-corrected-posix.tar` contient une extraction complète recalculée depuis chaque volume corrigé. Aucun avertissement de décompression n’est apparu pendant cette extraction.

Sans correction, ubi-reader échoue à décompresser un nœud de `rootB/usr/lib/libssl.so.3` et un de `apps/overkiz/io-homecontrol/lib/ovk/iovp/Daemon.so`. Il écrit ensuite des fichiers de la bonne taille avec des zéros ajoutés : **la taille seule ne prouve pas l’intégrité**. Les autres erreurs CRC ne provoquent pas nécessairement d’échec LZO. Les fichiers dérivés corrigés sont donc les références d’analyse pour les chemins signalés.

Deux archives privées conservent 74 candidats historiques non indexés : `data-unindexed-recovered-private.tar` (8) et `persistent-unindexed-recovered-private.tar` (66). Les rapports `*-unindexed-recovery.json` indiquent l’inode, un ancien chemin supposé et le hash. La reconstruction assemble les derniers blocs visibles par numéro de séquence ; leur cohérence entre versions n’est pas garantie. Ce sont des pistes, pas des fichiers actuels validés. Les blocs NAND hors UBI, dont bootstrap, restent dans l’image source ; leur extraction détaillée relève de l’analyse boot.

## Système et accès administratif

Le fichier persistant `../extracted/persistent/boot/boot_information_file:1` contient `ubi0:rootB`. Il indique la sélection enregistrée, sans prouver le système effectivement exécuté au moment d’une future remise sous tension. `rootB` porte KizOS 2026.1.3-2 ; `root` porte 2025.4.4-3. Les reçus de mise à jour confirment les dates de construction 2026-01-27 et 2025-07-22 (`persistent/boot/update/rootB.txt` et `root.txt`). Le script `rootB/etc/init.d/mount-apps.sh:11` associe root à apps et rootB à appsB.

`rootB/etc/inittab:5` sélectionne le niveau 5 ; `:9` appelle rcS ; `:27` appelle rc 5. Aucune ligne getty n’est présente. Le mode mono-utilisateur appelle sulogin. Les comptes root des deux volumes sont verrouillés pour le mot de passe ; aucun hash n’est affiché ici.

Les métadonnées prouvent `rc5.d/S10dropbear-persistent -> ../init.d/dropbear-persistent`. Ce script ne démarre Dropbear que si `/persistent/factory/enable-dropbear` existe (`rootB/etc/init.d/dropbear-persistent:5`), marqueur absent de la capture. Le service utilise le port 22 (`init.d/dropbear:22`) et l’option `-s`, qui désactive l’authentification par mot de passe (`etc/default/dropbear:4`). La clef hôte vient de la zone security. Le binaire est fourni par `/usr/sbin/dropbearmulti` via des liens symboliques.

Différence utile entre générations : root lie `/root/.ssh/authorized_keys` à `/etc/security/authorized_keys`, tandis que rootB le lie à `/persistent/factory/authorized_keys`. Le second fichier existe dans la capture. Les clés ne sont pas reproduites. `rootB/usr/sbin/ssh-keys-handler:3` définit ce chemin persistant. `appsB/overkiz/share/internal/admin/scripts/ssh.sh:12` fournit déjà les actions enable/disable/add-key ; enable démarre le service et pose le marqueur persistant. Ces mécanismes constituent une piste native, à étudier avant un patch du mot de passe ou du binaire. Leur invocation sur l’appareil et la connexion SSH restent non testées.

Le client BusyBox `/usr/bin/telnet` figure dans `etc/busybox.links.nosuid:155`. Aucun serveur telnetd, script inetd ou démarrage telnet n’a été identifié. La présence du client n’établit pas une console réseau.

## HTTPS et pare-feu

Les métadonnées rc5 contiennent `K10lighttpd`, donc aucun démarrage automatique direct de Lighttpd dans cette liste. Un composant applicatif peut le démarrer ensuite ; l’état d’écoute réel n’est pas établi par la NAND.

`rootB/etc/init.d/lighttpd:35` fixe `OVK_LISTENING_PORTS=443` si la variable est absente. `etc/lighttpd/lighttpd.conf:19` inclut les fragments communs puis ceux des ports demandés. `etc/lighttpd.d/local.conf:4` route `/enduser-mobile-web/` vers le socket FastCGI `/var/run/luaUserAPI`. Les deux configurations de socket existent :

- `443/localsocket.conf:2` et `:21` écoutent toutes les adresses IPv4 et IPv6. Le certificat client est obligatoire (`:5-6`, `:24-25`) et le scope ajouté est `local` (`:17`, `:36`).
- `8443/devmodesocket.conf:2` et `:13` écoutent IPv4/IPv6 avec le scope `devmode` (`:5`, `:16`). Aucun certificat client n’est exigé dans ce fragment. L’authentification applicative doit être étudiée séparément ; cela ne prouve pas un accès anonyme.

Le script `etc/init.d/iptables-load` ne modifie que **IPv6** : INPUT/FORWARD DROP, OUTPUT ACCEPT (`:14-16`), réponses établies autorisées (`:19`), loopback (`:22`), ULA fc00::/7 (`:24`) et link-local fe80::/10 (`:26`) autorisés. L’exception SSH explicite est commentée. Les fichiers `etc/iptables/iptables.rules` et `ip6tables.rules` sont vides. Aucun filtre IPv4 actif ne peut être déduit de ces seuls fichiers. Les autres composants peuvent modifier les règles à l’exécution.

## Contraintes avant toute modification de firmware

Les fonctions `have_trusted`, `have_encryption`, `have_authentication` et `have_apps_ro` retournent false dans `rootB/usr/share/kizosenv.sh:69-96` ; `have_k_boot` retourne true. C’est une observation des scripts de cette image, pas une preuve qu’aucun contrôle d’intégrité n’existe dans kboot ou le kernel.

Le root est monté en lecture seule (`etc/fstab:3`). Apps est UBIFS, avec `chk_data_crc,relatime`; sa sélection suit le root actif. Un mécanisme overlayfs est fourni (`usr/sbin/mount-overlayfs.sh`) avec mode volatile ou volume persistant dédié ; la capture ne contient ni volume overlayfs ni marqueur d’automontage. L’activation ajouterait un volume et écrirait la NAND : elle n’a pas été réalisée.

Un futur repacking devra préserver la géométrie (page 2048, OOB 64, PEB 131072, LEB 126976), IDs et types de volumes, tailles réservées, métadonnées POSIX, liens, doublons de secours, sélection root/apps et mécanismes de contrôle. Les extensions génériques de ubi-reader et les dossiers Windows ne doivent pas être utilisés comme recette de restauration. Aucune image à flasher, écriture NAND, commande de chauffage ou de chauffe-eau n’a été produite ou exécutée.

> Les empreintes historiques des fichiers expurgés se rapportent aux originaux privés.
