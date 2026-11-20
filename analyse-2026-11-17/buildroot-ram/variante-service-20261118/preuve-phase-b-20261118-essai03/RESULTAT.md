# Cozytouch RAM4 UART/MQTT — résultat Phase A

**18 novembre 2026. Variante construite sur le HP, auditée et qualifiée sous QEMU ARM926. Phase B en attente d'une autorisation explicite.** Le Pi et le hub sont restés hors de l'essai. L'état OEM froid et les pinces débranchées sont rapportés par <PERSONNE> pour la session courante.

## Images privées

Les fichiers se trouvent sous images/ (non publié) dans ce dossier. La copie HP se trouve sous `<CHEMIN_LOCAL>`. Les 60 fichiers du manifeste de livraison (non publié) concordent par SHA-256 entre Windows et le HP.

| Fichier | Octets | SHA-256 |
|---|---:|---|
| `zImage` | 4 189 096 | `d0937f9b1cccf5874c66facc363dee3c49910475b16bb2b5348417886488bb2e` |
| `ram4-final.dtb` | 18 520 | `d600bf0caf4068a09a5da1c2b5c9b53a5c30596e7f8aaf9cf9e330449b8d1f08` |
| `rootfs.cpio.gz` | 3 514 997 | `6b42c4a7b6b36a3171f901cc8dee94fbfbbdf02fc3fd7ad9c544fa2389eb6bbe` |
| `audit-final.json` | — | `bab3b572960e2282e0dc730d4e9391a3c52fdbe6ac6950d38bd58eccb1b15fb4` |

- Buildroot 2026.08 et Bootlin ARMv5 EABI glibc 2025.08-1. Programme de contrôle i386 compilé, lié et exécuté avec `gcc -m32`. LuaJIT `707c12bf00dafdfd3899b1a6c36435dbbf6c7022` et lua-cjson 2.1.0.10-1 proviennent des recettes Buildroot épinglées. `BR2_SHARED_LIBS=y`, `BR2_PACKAGE_LUA` désactivé, et `/usr/bin/lua` pointe vers LuaJIT. Sources et empreintes (non publié), journal de compilation (non publié).
- Le noyau et le DTB compilé avant ajustement sont identiques par SHA-256 à la base RAM4. Le paquet retient le noyau déjà vérifié. Seules les bornes initrd du DTB final sont susceptibles de changer. La recette fixe `0x24000000–0x2435a275` avec borne haute exclusive et conserve la marge théorique de 102,46 Mio. Les images de référence restent conservées. Reconstruction (non publié), bornes DTB (non publié), audit final (non publié).
- Les sept modules installés dans `/usr/share/cozytouch/mqtt` concordent avec leur manifeste. L'archive embarque le modèle de configuration et le chemin `/run/ct/mqtt-lab/targets.private.conf`. Les cibles réelles sont absentes. Le PID1 et sa politique réseau sont identiques octet pour octet à RAM4. Le service se lance manuellement.
- Deux fichiers préexistants diffèrent dans le CPIO reconstruit. Les chemins de compilation changent dans le fichier auxiliaire GDB de libstdc++. Le rebâti `xtables-legacy-multi` présente des différences de disposition et de contenu ELF. Le test QEMU applique les règles et mesure le DROP avec ce binaire de la variante. Delta CPIO (non publié), sections ELF (non publié).

## Qualification ARM926

Le banc système Linux 6.12 VersatilePB exécute le contenu utilisateur du CPIO final. Il utilise un init de test, des clés SSH jetables et les fonctions réseau de l'image. Il n'émule pas le SAM9G25, son watchdog ni son USART0. Consoles et contrôles (non publié), journal système (non publié), recette de test (non publié).

| Contrôle | Résultat |
|---|---|
| Runtime dynamique | ELF32 ARMv5, EABI5 soft-float, chargeur `ld-linux.so.3`, lien SONAME `libluajit-5.1.so.2`, symboles `luaopen_cjson` et `luaopen_cjson_safe`. Imports `ffi`, `cjson` et `cjson.safe` réussis via les chemins Lua attendus. |
| ABI | `long=4`, termios noyau 36 octets, offset `cc=17`, offset `dirent.name=11`. Symboles libc résolus. `readdir` vérifié dans proc et `TCGETS` sur le PTY du test. |
| Selftests et fixtures | Codec, CRC, fragmentation, corrélation, délais, MQTT, reconnexion simulée, cadence et configuration validés. Deux fixtures synthétiques avec toutes les coupures possibles reconstituent les requêtes et terminent `DONE` avec statuts 0/5/0. Les captures privées restent à leur emplacement d'origine. |
| SSH et politique réseau | Authentification par clé, PTY `/dev/pts/0`, politiques DROP actives avant interface UP, pas de route par défaut, IPv6 absent dans le noyau du banc. Une sonde vers une adresse de documentation a incrémenté le compteur OUTPUT DROP. Le réseau du banc est isolé par QEMU. |
| Stockage | Absence MTD, UBI, bloc et devmem constatée dans le banc. Config, DTB et symboles de l'image SAM9G25 contrôlés dans l'audit. |
| MQTT sans UART | Deux PUBACK sur Mosquitto ARM en boucle locale. Le subscriber indépendant a reçu le test retained en QoS1 et `availability=offline` par LWT après fermeture abrupte du client. |

## Staging et reprises

- Charge Pi (non publié), SHA-256 `f07b27ea52ab71ea0ef60bbda9d558769cf074af26d5b02d970e25349c102f87`. La validation locale du lanceur v2 a vérifié les images, leurs bornes et les fichiers de secours avec un identifiant synthétique. Le manifeste archive fixe les empreintes. Reçu du staging (non publié), plan local (non publié).
- Courtier et subscriber Mosquitto ARM (non publié), SHA-256 `e042385141b1a5e7284824bfea41b953b9fefead238aaee66fac6de34642e159`. Les deux outils restent dans un kit séparé pour lancement manuel en RAM en boucle locale. Ce choix évite une nouvelle règle LAN et conserve les paramètres SSH de RAM4. Le client des deux READ (non publié) est copié du client qualifié.
- Le boot sur le SAM9G25, la stabilité watchdog, la correspondance de `ttyS1`, la disponibilité du STM32 après transition, les deux READ réels et le scénario MQTT de 95 s restent à mesurer. Le runbook Phase B (non publié) exige d'abord la confirmation du câblage, de la baseline OEM, de la quiescence et du retour indépendant. Il précise la différence entre la vérification de clé depuis l'image RAM4 et la preuve par ring OEM RAM03. Valider la méthode applicable à la RAM4 avant connexion.

**Feu vert requis pour la Phase B.** Confirmer le hub sain sur OEM 5.4.302, la baseline OEM, le câblage JTAG et les pinces DBGU rebranchées en réception seule (**CH1 = TX du bridge + GND commun**). Confirmer aussi la voie de vérification de la quiescence et le retour indépendant.


## Phase B ? 18 novembre 2026, arr?t avant d?marrage

<PERSONNE> a autoris? l?essai mat?riel et confirm? le c?blage de capture en r?ception seule, le c?blage JTAG et sa disponibilit?. Le lot service autoris? correspond au SHA-256 attendu sur Windows et sur le HP. Les quatre fichiers historiques de r?cup?ration OEM v?rifi?s sur le Pi correspondent ? leurs empreintes. Aucun processus OpenOCD n??tait actif au contr?le initial sur le Pi.

Le contr?le de disponibilit? sur le HP a ?chou? pour le p?riph?rique s?rie DBGU r?f?renc? par la capture du 17 novembre. Le contr?le `test -c` a renvoy? 1. La capture passive n?a donc pas ?t? lanc?e. L?essai s?est arr?t? avant le transfert du lot au Pi, le ping et la comparaison ARP de r?f?rence, ainsi que toute action JTAG. Re?u de pr?paration (non publié).

| Contr?le demand? | R?sultat |
|---|---|
| Boot RAM4, trois relectures et identit? SSH | Non ex?cut?s |
| Deux READ MainParameter CETHI et IC3 | Non ex?cut?s |
| Trois paires MQTT en 95 s, r?tention, LWT et reconnexion | Non ex?cut?s |
| Restauration de l?UART et retour OEM | Sans transition ? restaurer |
| ?tat du hub | OEM NAND 5.4.302 et SSH temporaire absent selon l??tat initial d?clar?. Aucun contr?le r?seau, SSH ou radio pendant cette reprise. |
| ?tat du JTAG | OpenOCD absent au contr?le initial. GPIO en entr?e non rev?rifi?s. |

La reprise requiert un port s?rie DBGU disponible sur le HP pour le dispositif de capture valid?. Le c?blage c?t? hub reste en r?ception seule, avec CH1 sur le TX du bridge et masse commune. La version du rapport couverte par le manifeste de phase A est conserv?e dans RESULTAT-phase-a.md (non publié).


## Phase B — 18 novembre 2026, essai matériel 01

**La variante service RAM4 a démarré sur le hub. La qualification UART/MQTT s’est arrêtée avant les essais applicatifs. Le retour OEM RAM03 et les deux lectures natives de santé ont réussi.** Les heures ci-dessous sont en CET.

| Contrôle | Résultat |
|---|---|
| Charge et baseline | Variante service seule. SHA-256 de la charge Pi `f07b27ea52ab71ea0ef60bbda9d558769cf074af26d5b02d970e25349c102f87`. Manifeste et `plan.sh` validés dans le dossier Pi neuf. Ping et identité ARP concordants avant le halt. |
| Boot RAM4 à 10 h 36 | Préflight électrique v2 et quiescence validés. Trois relectures intégrales concordantes pour le noyau, l’initrd et le DTB. Entrée noyau unique. SSH strict validé avec la clé d’hôte extraite en privé de l’initrd relu. PTY réel vérifié. |
| Santé RAM4 | Linux `6.12.0-cozytouch-ram4`, racine et `/run` en RAM. Watchdog actif. Filtre DROP établi avant le réseau, aucune route WAN ni IPv6 active. Absence de MTD, UBI, périphérique bloc, `/dev/mem` et pilote USB lié. `ttyS1` correspond à USART0 et l’examen des descripteurs confirme qu’il est libre. |
| READ RAM4 | 0 sur 2. Arrêt lors de la préparation du fichier privé en RAM. |
| MQTT RAM4 | 0 paire sur 3. Le courtier et le service sont restés arrêtés. Rétention, LWT, reconnexion du courtier et restauration de l’UART après ouverture restent à qualifier sur le hub. Le port était libre avant le retour. |
| Capture DBGU | Démarrée avant le halt. 8 619 octets lisibles, avec les marqueurs du noyau RAM4 et de disponibilité SSH. Zéro écriture série. Le premier segment a couvert les deux entrées noyau. Capture de retour OEM vide. Réouverture de la capture à sa limite de 30 min, avec un intervalle d’environ 36 ms entre les horodatages de fin et de démarrage des deux segments. |
| Retour OEM à 10 h 48 | Continuité USB établie avant le retour direct RAM03. Deux relectures intégrales concordantes pour le noyau OEM et le DTB. Nouvelle identité SSH vérifiée dans le journal noyau relu par JTAG, puis authentification stricte réussie. |
| Contrôles de santé OEM | Les READ natifs `MainParameter` (65537) de CETHI puis IC3 ont chacun terminé `DONE / IoCommandNoError`. Même processus radio propriétaire de `/dev/ttyS1`, sans traceur, au contrôle différé. |
| État final observé vers 10 h 54 | Noyau OEM `5.4.302` démarré avec le DTB RAM03. SSH temporaire joignable après libération du JTAG. OpenOCD absent et GPIO 8 à 11 du Pi vérifiés en entrée. |

La sonde de santé supposait un lien `of_node` directement sous le périphérique `ttyS1`. Le chemin réel dans sysfs et le journal noyau ont confirmé l’association attendue avec USART0. L’arrêt de l’essai est intervenu ensuite, à la vérification du fichier privé. Ma commande utilisait `stat`, absent de cette image. Le transfert était engagé en RAM et la vérification du mode `0600` et du propriétaire n’a pas abouti. J’ai appliqué le retour prévu sans relancer la préparation. Le passage à l’OEM a remplacé le système de fichiers RAM de la variante. La reprise exige une vérification des permissions avec un outil disponible dans l’image, à valider hors matériel avant un nouvel essai.

Aucune écriture de chauffe, aucun appairage, aucun updater lancé pour l’essai, aucun reset de secours du STM32, aucun flash, aucun effacement ni accès brut NAND/MTD effectué pendant l’essai. Le SSH OEM est temporaire et disparaît après un redémarrage ordinaire.

Preuves expurgées avec empreintes dans SHA256SUMS (non publié). Captures DBGU brutes conservées en privé sur le HP. Relectures, ring OEM et journaux de lancement bruts conservés en privé sur le Pi. Les reçus et le présent rapport sont copiés sur Windows et sur le HP.

## Phase B — 18 novembre 2026, essai matériel 02

**Arrêt avant la mise au repos OEM et le halt JTAG.** La variante service et le retour OEM RAM03 ont passé les contrôles de préparation. Sur le hub, `internald` détenait l’unique descripteur du watchdog. Le code OEM de ce service contient des chemins d’écriture sur `/persistent`, dont la mise à jour des données de fuseau horaire. Le relevé `/proc` ne montrait aucun descripteur UBIFS ouvert en écriture ni mapping partagé modifiable au moment du contrôle. Ce relevé ponctuel ne permet pas de prouver l’arrêt des écrivains. La procédure OEM revue ne prévoit pas de mise au repos des écritures d’`internald` avec maintien vérifié du watchdog. Les services et les montages sont restés dans leur état initial. Inventaire OEM (non publié), contrôle final (non publié), code constructeur (non publié), revue du préboot (non publié).

| Contrôle | Résultat |
|---|---|
| Permissions du fichier privé | Sous QEMU ARM926, `busybox ls -ldn` accepte `0600` et `0:0`. Le contrôle refuse `0644`, le bit sticky, un UID ou GID différent, un lien symbolique et un fichier absent. CPIO service inchangé, SHA-256 `6b42c4a7b6b36a3171f901cc8dee94fbfbbdf02fc3fd7ad9c544fa2389eb6bbe`, concordant sur Windows et le HP. Sonde (non publié), résultat QEMU (non publié). |
| Charges sur le Pi | Charge service SHA-256 `f07b27ea52ab71ea0ef60bbda9d558769cf074af26d5b02d970e25349c102f87`, vérifiée dans un dossier neuf. Le `plan.sh` livré pointait vers le dossier d’essai01. Un plan séparé a vérifié les fichiers dans le nouveau dossier et des chemins de preuves neufs. Le plan OEM RAM03 a aussi réussi. Plans essai02 (non publié). |
| Quiescence logicielle | Arrêt avant toute commande de mise au repos. `/` était `ro`, `/apps`, `/data` et `/persistent` étaient `rw` au dernier contrôle. |
| Préflight, capture DBGU et boot RAM4 | Non lancés. |
| SSH | Identité OEM vérifiée avec le `known_hosts` de l’essai01. Identité RAM4 sans objet pour cet essai. |
| READ RAM4 | 0 sur 2. |
| MQTT | 0 paire sur 3. Reconnexion du courtier, LWT et rétention non testés. |
| UART et retour OEM | Aucun transfert de propriétaire ni changement de noyau. Le daemon radio OEM détenait seul `ttyS1`, sans traceur. Les deux READ de santé sont réservés au retour après une transition matérielle. |
| État final | OEM `5.4.302`, identifiant de boot identique à celui vérifié au retour RAM03 de l’essai01, SSH strict disponible. Ping et identité ARP concordants. OpenOCD arrêté, GPIO 8 à 11 en entrée. Contrôles Pi (non publié). |

La reprise exige une procédure revue pour mettre au repos les écritures d’`internald` tout en conservant le watchdog. Empreintes des preuves (non publié).


## Phase B ? 18 novembre 2026, essai mat?riel 03

**Le lanceur s?est arr?t? pendant la relecture JTAG du noyau. RAM4 n?a pas d?marr?. Le retour constructeur par `return-to-nand` a r?tabli la pr?sence du hub sur le r?seau.** Les heures ci-dessous sont en CET.

| Contr?le | R?sultat |
|---|---|
| Charge et r?f?rence OEM | Variante service seule. SHA-256 de la charge Pi `f07b27ea52ab71ea0ef60bbda9d558769cf074af26d5b02d970e25349c102f87`. Manifeste et plans service et retour v?rifi?s dans le dossier Pi neuf. Avant le halt, l?OEM `5.4.302` tournait sur le m?me boot RAM03 qu?au retour de l?essai01. SSH strict, ping et identit? ARP v?rifi?s. Le daemon radio ?tait seul propri?taire de `ttyS1`, sans traceur. Plans (non publié). |
| Quiescence | ? quiescence ?lectrique + sync, risque accept? par <PERSONNE> le 18/11 ?. Un seul `sync` par SSH OEM v?rifi?, de 11 h 41 min 39 s ? 11 h 41 min 40 s, code retour 0. Halt confirm? ? 11 h 41 min 45 s. Le pr?flight v2 et la quiescence revue ont r?ussi. Aucun service OEM arr?t?, aucun remontage et aucune intervention sur le watchdog OEM avant le halt. Re?u sync (non publié), ?v?nements (non publié). |
| Boot RAM4 | Le transfert du noyau a fini ? 11 h 45 min 31 s. Le d?lai de 360 s que j?avais fix? pour la commande SSH Windows a expir? pendant `full_readback_kernel`. Le lanceur sur le Pi a ensuite signal? `BrokenPipeError` et `aborted_recovery_required`. Aucune des trois relectures n?a ?t? confirm?e. Aucune entr?e noyau RAM4 ni reprise de l?ancien Linux. Diagnostic (non publié), preuves du Pi (non publié). |
| Capture DBGU | R?ception seule continue de 11 h 41 min 03 s ? 11 h 51 min 57 s, z?ro ?criture s?rie. La capture contient 89 octets lisibles au moment du retour NAND, sans ligne de version Linux. Re?u (non publié). |
| Identit? et SSH RAM4 | Non atteints, faute d?initrd relu et d?entr?e noyau. |
| READ RAM4 | 0 sur 2. La v?rification des permissions reste acquise sous QEMU pour ce CPIO. |
| MQTT | 0 paire sur 3. Courtier, coupure planifi?e, reconnexion, LWT et r?tention non test?s. |
| Restauration UART | Aucun client UART d?essai lanc?. Le propri?taire UART apr?s retour reste non v?rifi?. |
| Retour | Cible confirm?e ? l?arr?t avec marqueur de quiescence engag?. Le sc?nario direct RAM4 ? OEM RAM03 exige un boot RAM4 v?rifi?. Retour SRAM `return-to-nand` ex?cut? ? 11 h 50 min 23 s selon la revue. ?tat avant retour (non publié), re?u du retour (non publié). |
| ?tat final ? 11 h 51 min 25 s | Ping et identit? ARP conformes apr?s retour. Le port SSH temporaire 2222 refuse la connexion. Version du noyau, propri?taire UART et sant? radio non attest?s. Deux READ OEM de sant? non effectu?s. OpenOCD arr?t?, GPIO 8 ? 11 v?rifi?s en entr?e. R?seau (non publié), lib?ration JTAG (non publié). |

Le d?lai de pilotage en amont ?tait trop court pour les transferts et relectures du lanceur. Une reprise devra d?coupler l?ex?cution sur le Pi de la dur?e de la session SSH Windows et utiliser le journal du lanceur pour d?terminer son ?tat. Le retour NAND a perdu le SSH RAM03. La qualification UART/MQTT reste ouverte et une nouvelle transition mat?rielle n?cessite une d?cision de <PERSONNE>.

Aucune consigne de chauffe, aucun appairage, aucun updater lanc? pour l?essai, aucun reset de secours du STM32, aucun flash, aucun effacement ni acc?s brut NAND/MTD effectu?. Le retour a demand? le reset pr?vu du SoC. Empreintes des preuves expurg?es (non publié).

> Les empreintes historiques des fichiers expurgés se rapportent aux originaux privés.
