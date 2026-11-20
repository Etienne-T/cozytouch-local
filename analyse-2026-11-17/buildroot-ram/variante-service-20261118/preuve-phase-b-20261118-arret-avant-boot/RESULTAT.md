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

> Les empreintes historiques des fichiers expurgés se rapportent aux originaux privés.
