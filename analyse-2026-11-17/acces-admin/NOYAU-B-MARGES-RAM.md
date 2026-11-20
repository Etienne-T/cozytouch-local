# Noyau B : décompression, BSS et arguments DT

Vérification statique du 17 novembre 2026. Aucun noyau exécuté, aucun accès matériel. **Les adresses proposées ne se chevauchent pas pendant la décompression et l’initialisation BSS de cette image**, sous l’hypothèse DDR `[0x20000000, 0x28000000)` (128 Mio). Cela ne valide pas à lui seul un démarrage RAM.

Source : `extracted/rootB/boot/zImage-5.4.302`, 3 089 896 octets, SHA-256 `8c58bb4c0bbb294f9e2b017f245183f09541ae394c59356c41b342e030d7475a`. Le script inspect-kernel-memory.py (non publié) reproduit les calculs et conserve les données JSON (non publié) et le désassemblage ciblé (non publié). Il complète `inspect-kernel.py` sans modifier l’image.

## Bornes établies dans le binaire

Les intervalles ci-dessous ont une borne supérieure exclue.

| Élément | Intervalle physique ou adresse | Preuve |
|---|---|---|
| zImage source | `0x22000000..0x222f25e8` | Taille fichier ; en-tête ARM : magic `0x016f2818` à `+0x24`, start `0`, end `0x2f25e8` |
| Destination décompressée | `0x20008000..0x205e6c9c` | Instructions zImage `+0x80..+0x88` : `(PC & 0xf8000000) + 0x8000` ; gzip décompressé de 6 155 420 octets |
| BSS du noyau | `0x205e6c9c..0x205fe0bc` | Initialisation à `0xc05932e0` ; table à `0xc0593324/28` = `0xc05e6c9c/0xc05fe0bc`, puis memset de 95 264 octets |
| FDT proposé | `0x21000000` | Adresse de la proposition ; taille à vérifier sur le DTB effectivement transféré |
| BSS du décompresseur | `0x222f25e8..0x222f2600` | Table zImage `+0x1dc/+0x1e0`, zéro par boucle `+0x190..+0x1a8` |
| Haut de pile décompresseur | `0x222f3600` | Littéral `+0x1f4`, chargé à `+0xb0`, ajusté à l’adresse de chargement |
| Espace allocation décompresseur | `0x222f3600..0x22303600` | Arguments de décompression `+0x1b8..+0x1c8` : début = SP, fin = SP + 64 Kio |
| Borne conservatrice du contrôle de chevauchement | `0x22307600` | `+0xe0/+0xe8` : SP + 64 Kio + 16 Kio |

Le gzip commence à `0x457c` et finit à `0x2f25ad` ; les octets suivants appartiennent encore au zImage. Son contenu décompressé a le SHA-256 `87b34210dc42d3d8f1daf2c680899a624ddc387f2b6bf0acf2681d1651141c16`.

La conversion virtuelle/physique utilisée ici est `VA - 0xc0000000 + 0x20000000`. Le début virtuel de l’image est `0xc0008000`. La fin du contenu décompressé correspond exactement au début BSS retrouvé. L’identification des champs comme `__bss_start` et `__bss_stop` concorde avec [head-common.S Linux 5.4](https://raw.githubusercontent.com/torvalds/linux/v5.4/arch/arm/kernel/head-common.S), notamment la séquence load/sub/memset. **Le nom de symbole `_end` n’a pas été récupéré** : la borne démontrée est celle de fin BSS, pas une table System.map reconstruite.

Il reste `0x00a01f44` octets (10 493 764, environ 10,008 Mio) entre la fin BSS et le début FDT. La source compressée est à 16 Mio au-dessus du FDT. La borne conservatrice de travail du décompresseur reste à plus de 92 Mio de la fin DDR. Au chargement proposé, la destination basse ne recouvre pas le décompresseur : son chemin de déplacement pour chevauchement n’est pas nécessaire.

## Arguments de démarrage

Le noyau ne contient pas de bloc `IKCFG_ST` : aucun `.config` embarqué n’a été récupéré. Toutefois, le code du chemin Device Tree est suffisamment explicite pour vérifier son comportement :

- La fonction identifiée par les chaînes `chosen`, `chosen@0`, `bootargs` lit la propriété à `0xc05a9bcc..0xc05a9bfc` et copie au plus `0x400` octets dans le tampon de commande.
- À `0xc05a9c00..0xc05a9c18`, elle teste le premier octet du tampon. Elle ne copie la valeur intégrée que si le tampon est vide.
- Cette séquence correspond à la branche de repli, et non à un remplacement forcé, dans [drivers/of/fdt.c Linux 5.4](https://raw.githubusercontent.com/torvalds/linux/v5.4/drivers/of/fdt.c) (`early_init_dt_scan_chosen`, lignes 994–1013). Elle permet de conclure que **ce chemin DT conserve les `bootargs` non vides**. Elle est compatible avec `CONFIG_CMDLINE_FORCE` et `CONFIG_CMDLINE_EXTEND` désactivés ; le fichier de configuration exact reste absent.

La valeur intégrée observée est générique : `panic=5 oops=panic rootfstype=ubifs ubi.mtd=ubi ro loglevel=2`. Le contrôle ne prouve pas qu’aucun autre code constructeur n’altère ensuite la commande ; il établit le comportement du lecteur `/chosen`.

## ABI et limites

L’[ABI ARM Linux](https://docs.kernel.org/arch/arm/booting.html) impose un FDT aligné sur 8 octets, accessible en RAM sans écrasement par le décompresseur, et son adresse dans `r2`. Elle recommande un zImage dans les 128 premiers Mio et un chargement au-dessus de 32 Mio pour éviter le déplacement. La source proposée est exactement à +32 Mio ; **la non-collision ici découle des bornes binaires calculées**, pas de cette recommandation seule.

La recommandation générique de placer un DTB au-dessus de +128 Mio ne s’applique pas telle quelle à une DDR totale de 128 Mio. Le FDT à +16 Mio est justifié ici par sa séparation avec les zones écrites, sous réserve que sa taille réelle reste inférieure à l’espace jusqu’à la source et qu’il soit réservé correctement par le noyau.

Cette inspection ne vérifie ni le contenu DDR réel au moment du branchement, ni les DMA, caches, MMU, registres, watchdog, le choix effectif du DTB/racine ou les allocations ultérieures du noyau. Elle ne constitue aucune autorisation d’exécuter le kit. Aucun contrôle matériel n’a été effectué dans ce complément.

> Les empreintes historiques des fichiers expurgés se rapportent aux originaux privés.
