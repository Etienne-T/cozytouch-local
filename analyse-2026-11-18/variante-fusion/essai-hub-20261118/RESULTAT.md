# Cozytouch FUSION — préflight du 18 novembre 2026

**Essai arrêté avant transfert et avant mise au repos P1.** La fusion n’a pas démarré sur le hub. Le Linux constructeur `5.4.302` est resté en service ; aucun retour OEM n’a été nécessaire. Le DTB courant n’a pas été revérifié.

## Vérifications en lecture seule

| Point | Observation (CET) |
|---|---|
| SSH OEM temporaire | À 14 h 02 puis 14 h 05, authentification root par clé sur le port `2222`, avec vérification stricte de la clé d’hôte de l’essai 04. Code de sortie `0`. |
| Radio OEM | À 14 h 05, `io-homecontrold` actif (PID `972`), détenteur de `/dev/ttyS1`, sans traceur. Constat de santé du processus ; aucune lecture radio envoyée. |
| Montages OEM | Quatre montages UBIFS : `/` en lecture seule ; `/apps`, `/data` et `/persistent` en lecture-écriture, comme attendu. |
| Capture UART côté HP | FTDI `/dev/ttyUSB0` présent et accessible en lecture. Le relevé USB ne prouve pas le câblage RX seul. Port non ouvert, aucune capture ni écriture série. |

Relevé expurgé (non publié). Le SHA-256 de l’archive locale correspond au manifeste. Aucun transfert, aucune connexion au Pi, aucun halt JTAG, aucun redémarrage et aucun accès brut NAND/MTD. Les deux READ, les trois cycles MQTT et la reconnexion au courtier ne sont pas mesurés. Le PKM n’a pas été modifié.

## Motif de l’arrêt

P1 demande `sync` puis le remontage en lecture seule de trois volumes UBIFS. Dans Linux amont `v5.4.302`, `ubifs_sync_fs()` vide les tampons et peut valider le journal. `ubifs_remount_ro()` vide les tampons et appelle `ubifs_write_master()` pour écrire les métadonnées du volume. Le code amont ne prouve pas le comportement exact du fork constructeur ; il ne permet pas de garantir « aucune écriture NAND/MTD » pour P1.

Le [résultat de l’essai 04](../../../analyse-2026-11-17/buildroot-ram/variante-service-20261118/RESULTAT.md#phase-b--18-novembre-2026-essai-matériel-04) documente une quiescence électrique seule, sans `sync` ni arrêt de service OEM. La revue UBIFS (non publié) indique que le candidat de remontage n’a pas été exécuté sur le hub et qu’un montage en lecture seule ne prouve pas l’inactivité de la NAND. Aucun protocole n’a été substitué à P1.

Pour reprendre : préciser si la contrainte autorise les écritures normales d’UBIFS induites par P1, ou faire valider une autre procédure compatible avec l’interdiction absolue avant toute action matérielle.

Source technique : [Linux stable v5.4.302, `fs/ubifs/super.c`](https://raw.githubusercontent.com/gregkh/linux/refs/tags/v5.4.302/fs/ubifs/super.c).

## Reprise du 18 novembre 2026 — arrêt au préflight

<PERSONNE> a ensuite autorisé P1, y compris les vidages normaux du système de fichiers dus à `sync` et au remontage en lecture seule. L’autorisation lève le motif de l’arrêt précédent. Elle n’inclut ni accès brut ni programmation de la NAND ou du STM32.

| Étape | Résultat |
|---|---|
| SSH OEM et montages | À 14 h 25 CET, SSH temporaire strict confirmé, UID 0, noyau `5.4.302`. `/` en lecture seule ; `/apps`, `/data` et `/persistent` en lecture-écriture. Uptime : 6 485,59 s. DTB courant non revérifié. |
| Radio | La sonde n’a pas confirmé le propriétaire de `ttyS1`. `pidof` a renvoyé 1, puis la recherche par nom d’exécutable dans `/proc` a trouvé zéro correspondance. Cela ne démontre pas une panne radio. Aucune commande radio envoyée. |
| FTDI, transfert et P1 | FTDI observé au préflight précédent, non revérifié après l’arrêt de la sonde OEM. SHA-256 de l’archive locale conforme au manifeste. Aucun transfert au Pi, aucun `sync` ni remontage. Quiescence, `Dirty`, `Writeback` et watchdog non vérifiés. |
| Halt, mesures et retour | Aucun halt, aucune relecture RAM ni démarrage FUSION. Les deux READ, les trois cycles MQTT, les PUBACK et la reconnexion n’ont pas été mesurés. Le hub est resté sous OEM ; aucun retour ni redémarrage lancé. |

La santé radio n’étant pas confirmée, la reprise s’arrête avant toute action matérielle. Un essai avec changement de noyau doit disposer d’une voie de retour OEM qui ne recrée pas l’accès root par le démarrage OEM modifié. Ni le PKM ni le premier relevé n’ont été modifiés.

Relevé horodaté de la reprise (non publié).

## Reprise du 18 novembre 2026 à 15 h 28 CET — préflight conforme, essai non lancé

| Contrôle | Résultat |
|---|---|
| SSH et montages, 15 h 28 min 02 s | Clé d’hôte de l’essai 04 vérifiée strictement ; UID 0, noyau OEM `5.4.302`, uptime `10 236,08 s`. `/` en lecture seule ; `/apps`, `/data` et `/persistent` en lecture-écriture (UBIFS). DTB courant non vérifié. |
| Radio, même session | Le parcours des descripteurs de tous les PID trouve uniquement `/proc/972/fd/10` pour `/dev/ttyS1`. `fuser` renvoie uniquement `972` ; `comm` et `cmdline` confirment `io-homecontrold`. Contrôle passif uniquement ; aucune commande radio envoyée. Le diagnostic radio (non publié) explique le faux négatif précédent. |
| FTDI sur le HP, 15 h 28 min 03 s | `/dev/ttyUSB0` présent et lisible, pilote `ftdi_sio`. Port non ouvert ; câblage RX seul et capture non vérifiés. |
| Staging | SHA-256 local conforme au manifeste : `90679fdb6f9be408a0dca9cd26c1ffc248fd2be36e966d7fd46d5a7884da8d6a`. Aucun transfert au Pi ; aucune empreinte distante. |
| P1, halt et essai FUSION | Aucun arrêt de service, `sync` ou remontage. Quiescence, `Dirty`, `Writeback` et watchdog non vérifiés pour P1. Aucun halt, accès brut, relecture RAM, démarrage, READ CETHI/IC3, cycle MQTT, PUBACK ou test de reconnexion. |
| État final | Le hub est resté sous OEM pendant le contrôle. Aucun retour, redémarrage ou changement de montage demandé. Le PKM et le diagnostic radio précédent n’ont pas été modifiés. |

**Motif de l’arrêt :** le retour exigé cumule le retour au constructeur et la recréation d’un accès SSH root temporaire par un démarrage OEM modifié (DTB RAM03). Aucun retour répondant à ces deux critères par une voie d’administration prise en charge par le constructeur n’a été établi. L’essai n’a pas été engagé, afin de conserver la session OEM existante. Cette limite ne remet pas en cause l’autorisation donnée par <PERSONNE> pour les vidages normaux d’UBIFS pendant P1 et ne signale pas de panne du hub.

## Essai exécuté par <PERSONNE>, 18 novembre 2026 — fusion validée sur le hub

**Les sections précédentes décrivent des arrêts au préflight. Elles restent valables pour leur moment.** <PERSONNE> a ensuite exécuté lui-même les étapes matérielles avec RUNBOOK-<PERSONNE>.md (non publié), Claude contrôlant chaque barrière. L'image fusionnée a démarré en RAM sur le hub réel et a satisfait le critère de l'essai 04.

| Phase | Résultat |
|---|---|
| Clé d'hôte OEM | La clé vérifiée à l'essai 04 a été installée dans `known-hosts-oem-return` ; l'ancienne est conservée dans `known-hosts-oem-return.stale-spEZ4l.bak`. Vérification stricte maintenue. |
| P1 | Aucun écrivain sur `/apps`, `/data`, `/persistent` ; remontage en lecture seule ; `Dirty` et `Writeback` à 0. |
| Halt JTAG et boot | Lanceur `launch-ram4-v2.py`, dossier `attempt02` sur le Pi. Deux échecs avant toute action matérielle (chemin de lancement, dossier déjà existant), puis entrée noyau demandée sans erreur. |
| Santé | Noyau `6.12.0-cozytouch-ram4`. WAN bloqué, IPv6 désactivé, aucun accès MTD, UBI ou bloc, watchdog nourri, `ttyS1` libre. |
| Deux lectures | CETHI et IC3 : `DONE`, statuts 0/5/0. |
| Trois cycles MQTT | `SERVICE_STOP reads=6 cycles=3 mqtt_pubacks=12 mqtt_connections=2 uart_restored=true elapsed_ms=94036`. Courtier arrêté après la première paire puis relancé 5 s plus tard ; reconnexion du service ; états retenus et disponibilité `offline` (dernière volonté) reçus par un nouvel abonné ; `ttyS1` libre à la fin. |

Aucune commande de chauffe, aucun appairage. En dehors des vidages normaux de P1, aucune écriture NAND.

**État à la fin de l'essai :** la fusion tourne en RAM et OpenOCD reste actif sur le Pi. Le retour au Linux constructeur n'est pas fait. Méthode retenue avec <PERSONNE> : libérer OpenOCD avec `analyse-2026-11-17/buildroot-ram/orchestration/release-fusion-pi.py`, puis couper l'alimentation du hub pour démarrer depuis la NAND. Ce démarrage depuis la NAND n'est pas encore vérifié.

Sorties : `p4a.out` à `p4d2.out` dans `analyse-2026-11-17/buildroot-ram/orchestration/`.

> Les empreintes historiques des fichiers expurgés se rapportent aux originaux privés.
