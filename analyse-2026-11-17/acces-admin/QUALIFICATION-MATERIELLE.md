# Qualification matérielle du candidat RAM

Contrôles du coordinateur, 17 novembre 2026. Les scripts `inspect-*.tcl` et `qualify-debug-halt.tcl` arrêtent brièvement le CPU, lisent des registres puis le reprennent. Ils ne chargent aucun noyau et ne programment aucune flash.

| Point | Observation vérifiée | Conséquence |
|---|---|---|
| Identité JTAG | TAP `0x0792603f`, ARM9 AT91SAM9G25 | Conforme à la carte étudiée |
| Straps carte | PIOC `PDSR=0xdfeff7ff`, PC25/27/29 = `110`, broches en entrée | Sélection `miniio`, DTB base |
| Watchdog | MR `0x1fff2fff`, WDDIS=0, WDDBGHLT=1 | Watchdog actif ; pause demandée pendant le debug |
| Pause debug | 22 secondes, PC relu `0xc0013424` avant/après, MR identique, aucune reprise/reset signalée | Pause supérieure à la période nominale de 16 secondes observée avec succès ; ne qualifie pas une routine CPU exécutée |
| Reprise | `TARGET_RESUMED`, OpenOCD terminé ; ping ultérieur reçu en 1,28 ms | Linux a repris après ce contrôle |
| HDMAC0 | CHSR `0x00ff0002`, canal 1, source `0xf801c018` | Réception USART0 active ; ce canal n'est pas une lecture NAND |
| HDMAC1 | CHSR `0x00ff0000` | Aucun canal activé lors de la lecture |
| Ethernet MACB | NCR `0x1c` | Réception/émission activées |
| OHCI | Control `0x283` | Contrôleur opérationnel ; listes désactivées, mais HCCA peut encore être écrite |
| EHCI | CAPBASE `0x01000010`, USBCMD `0x00010005`, USBSTS `0x00000008` | Registres opérationnels à base+0x10 ; contrôleur en marche |

Deux lectures préliminaires ont été corrigées : PIOC est à `0xfffff800` (et non PIOD à `0xfffffa00`) ; EHCI USBCMD est à `0x00700010` (et non `0x00700020`). Les anciens journaux sont conservés comme diagnostics, pas comme preuve des valeurs corrigées.

La pause debug ne suffit pas à autoriser un remplacement de DDR. Il reste à mettre les DMA dans un état arrêté vérifié, établir les conditions d'entrée ARM, contrôler les plages du noyau et du FDT, puis comparer intégralement les octets chargés. Un remplacement à chaud ne prouve pas que les volumes de l'ancien Linux ont été synchronisés. Le démarrage normal du nouvel OS peut écrire ses journaux et données habituels : le caractère temporaire concerne les fichiers d'administration.

Le journal d'une éventuelle tentative doit être distinct de ces contrôles. Tant qu'aucune preuve d'authentification et de révocation n'est enregistrée, l'accès administrateur reste non obtenu.
