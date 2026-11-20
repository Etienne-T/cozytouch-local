# Revue du démarrage RAM proposé — 17 novembre 2026

Revue préparatoire pour le coordinateur matériel. Aucune commande JTAG, GPIO, arrêt CPU ou démarrage de noyau n’est exécuté par cet agent.

## Artefacts établis

- `extracted/rootB/boot/zImage-5.4.302` : 3 089 896 octets, SHA-256 `8c58bb4c0bbb294f9e2b017f245183f09541ae394c59356c41b342e030d7475a`.
- Le flux gzip commence à l’offset 17 788 et produit 6 155 420 octets. L’inspection ne trouve pas d’IKCONFIG embarquée ; les options de compilation ne sont donc pas déduites du nom du noyau. Voir `kernelB-boot-inspection.json`.
- Le DTB sauvegardé décrit la DDR à `0x20000000`, taille `0x08000000` (128 Mio). Le choix `miniio` du bootscript utilise `at91-kizboxmini-base.dtb` ; le choix doit être recoupé avec l’identité de carte actuelle.
- La racine sauvegardée est `ubi0:rootB`. Les bootargs d’une nouvelle entrée doivent fournir explicitement cette racine, en plus de `ubi.mtd=ubi rootfstype=ubifs ro`.

## Préconditions du chargeur ARM

La documentation Linux 5.4 exige RAM initialisée, DMA arrêté, entrée ARM en mode SVC, IRQ/FIQ désactivées, MMU et cache de données désactivés. Elle indique `r0=0`, `r1=0xffffffff` pour une plateforme DT seule, `r2=adresse physique du DTB`, puis branchement vers la première instruction du zImage. Le DTB doit être aligné sur 64 bits et rester hors de la zone décompressée.

Une adresse de zImage à `0x22000000` est cohérente avec la recommandation de le placer au-delà de 32 Mio. Un DTB à `0x21000000` reste dans la DDR et à distance des 6,2 Mo de données décompressées observées. **Ces adresses sont des propositions, pas une preuve des marges du BSS, de la relocation ou des DMA en cours.** Leur validation et les registres relèvent du coordinateur matériel. `soft_reset_halt` détruit le contexte permettant de reprendre l’ancien Linux ; il ne constitue pas une simple pause réversible.

Le watchdog reste un point critique : pendant l’acquisition, la routine nourrit explicitement `0xfffffe40` avec `0xa5000001` (`jtag/nand-reader.s:17-18`). Un chargement lent de 3 Mo sous CPU arrêté doit conserver ce mécanisme, par transferts découpés et contrôles. Ne pas supposer qu’une écriture tardive du registre de mode peut désactiver un watchdog déjà configuré. Une réinitialisation pendant le transfert impose d’abandonner la séquence et de revérifier l’état.

Le DTB de base donne deux contrôleurs HDMAC à `0xffffec00` et `0xffffee00`, et le MACB Ethernet à `0xf802c000`. Le pilote Linux 5.4 définit HDMAC `EN` à l’offset `0x04`, `CHDR` à `0x2c` et `CHSR` à `0x30` ; MACB place `NCR` à `0x00`, avec RXEN bit2 et TXEN bit3. Ce sont des références pour une lecture et une revue des étapes d’arrêt, pas des commandes exécutées. Arrêter un transfert NAND en cours n’est pas équivalent à un flush propre des journaux UBIFS. L’absence momentanée de DMA ne prouve pas l’absence de données sales en cache.

Le driver watchdog confirme que son registre de mode n’accepte qu’une écriture et que le matériel ne peut pas être arrêté après activation. Sa fenêtre de réarmement doit être connue avant de fixer la cadence des écritures de service. Voir `dma-watchdog-dtb.json`, les sources [HDMAC](https://github.com/torvalds/linux/blob/v5.4/drivers/dma/at_hdmac_regs.h), [MACB](https://github.com/torvalds/linux/blob/v5.4/drivers/net/ethernet/cadence/macb.h) et [watchdog AT91](https://github.com/torvalds/linux/blob/v5.4/drivers/watchdog/at91sam9_wdt.c).

## Wrapper init et réversibilité

Linux 5.4 transmet tout ce qui suit `--` comme arguments à init. Le schéma `init=/bin/sh -- -c "…"` est donc cohérent pour exécuter un wrapper, puis `exec /sbin/init`. La limite ARM publiée est 1 024 octets pour la ligne de commande : vérifier la longueur UTF-8 réelle, la terminaison NUL et le découpage des arguments. Éviter les guillemets doubles internes non vérifiés ; leur traitement appartient au parseur du noyau avant celui du shell.

Le wrapper doit attendre que `/run` soit réellement monté en tmpfs avant de créer ses fichiers. Sinon le montage normal pourrait les masquer ou effacer leur visibilité. Les métadonnées rootB confirment `/root` et `/root/.ssh` comme répertoires réels ; seul `authorized_keys` pointe vers `/persistent/factory/authorized_keys`. Un bind de répertoire RAM sur `/root/.ssh` peut remplacer temporairement cette vue sans éditer sa cible persistante. Il faut refuser de créer un répertoire absent sur un stockage persistant.

La clé d’hôte du serveur temporaire, son PID et sa clé publique autorisée doivent rester sous `/run`. Lancer le serveur avec une clé dédiée et un port distinct, puis vérifier l’identité et `id` en lecture. La révocation logique consiste à arrêter ce PID et démonter le bind. Le redémarrage électrique retire le noyau, le wrapper, les montages et les fichiers RAM ajoutés.

**Limite de la promesse d’écriture :** le chemin qui poursuit le démarrage normal monte `/data` et `/persistent` en lecture-écriture (`rootB/etc/fstab:13-14`) et lance les services natifs. Il peut donc produire leurs écritures ordinaires. Il est possible de promettre l’absence d’écriture persistante des éléments d’administration ajoutés ; ce chemin ne démontre pas zéro écriture NAND globale. Une session de secours entièrement en initramfs, sans montage en écriture ni démarrage des services natifs, aurait une autre portée et interromprait leur fonctionnement.

Sources primaires : [Booting ARM Linux 5.4](https://www.kernel.org/doc/html/v5.4/arm/booting.html), [paramètres du noyau 5.4](https://www.kernel.org/doc/html/v5.4/admin-guide/kernel-parameters.html), [limite ARM dans setup.h v5.4](https://github.com/torvalds/linux/blob/v5.4/arch/arm/include/uapi/asm/setup.h), [transmission des arguments init](https://github.com/torvalds/linux/blob/v5.4/init/main.c), [configuration des cibles OpenOCD](https://openocd.org/doc-release/html/CPU-Configuration.html). Les exigences génériques ne prouvent pas une exécution réussie sur ce bridge.

> Les empreintes historiques des fichiers expurgés se rapportent aux originaux privés.
