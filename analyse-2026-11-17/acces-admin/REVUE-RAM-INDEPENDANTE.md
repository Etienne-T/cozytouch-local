# Revue indépendante du candidat de démarrage RAM

Revue statique du 17 novembre 2026. **La modification DTB, le découpage de la ligne de commande et le montage SSH temporaire sont cohérents. Le démarrage à chaud ne doit pas encore être considéré comme validé : arrêt des DMA, comportement du watchdog et transition CPU restent des préconditions techniques ouvertes.** Aucun accès matériel, réseau ou REA n’a été effectué par le relecteur. Les états matériels cités proviennent des journaux fournis par le coordinateur.

## Résultats vérifiés

| Objet | Contrôle indépendant | Résultat |
|---|---|---|
| DTB | Parseur FDT indépendant du constructeur : propriétés, liste des nœuds, réservations et champs de version | Seule `/chosen/bootargs` diffère ; aucun autre nœud/propriété ni réservation modifié |
| Artefact | SHA-256 du DTB candidat | `68c873705b88c38636582f8362b7aa5a48835866553e393cb46172180db4e051` |
| Tailles | DTB source 21 168 octets ; candidat 22 060 | En-tête et taille totale cohérents |
| Commande noyau | Chaîne du DTB comparée à `bootargs.txt`, sans l’afficher | Identique ; **956 octets NUL compris**, sous 1024 |
| Arguments init | Séparation `--`, guillemets, affectations contenant `=` ; comparaison au script complet | Deux arguments utiles : `-c` puis script exact |
| Clé SSH | Lecture du format public uniquement, sans affichage | RSA2048, exposant65537, structure complète et même partie publique que celle embarquée |
| Permissions serveur | Métadonnées rootB et script | `/root` et `/root/.ssh` sont de vrais répertoires root0700 ; bind possible sans remplacer le lien persistant du fichier |
| Permissions client | ACL du fichier privé, sans lire sa valeur | Héritage coupé ; accès limités à <PERSONNE>, Administrateurs et Système |
| Options Dropbear | Chaînes d’aide du binaire livré | `-s`, `-j`, `-k`, `-p`, `-P`, `-r` présents ; liens `dropbear` et `dropbearkey` vers `dropbearmulti` conservés dans le root |

Le découpage a été confronté aux sources [Linux5.4 lib/cmdline.c](https://github.com/torvalds/linux/blob/v5.4/lib/cmdline.c) et [init/main.c](https://github.com/torvalds/linux/blob/v5.4/init/main.c) : `next_arg` puis `repair_env_string` restituent le `=` de l’affectation initiale du script. Le programme C du kit reproduit ces règles pour cet ensemble de caractères ; sa preuve existante et le contrôle indépendant concordent. La limite1024 est définie dans [setup.h ARMv5.4](https://github.com/torvalds/linux/blob/v5.4/arch/arm/include/uapi/asm/setup.h). L’absence d’IKCONFIG laisse inconnues les éventuelles options de ligne de commande compilée `CONFIG_CMDLINE_FORCE/EXTEND` : c’est une limite de preuve, pas une erreur démontrée du wrapper.

Le script attend `/run` monté en tmpfs et `/tmp/boot`. Le second marqueur est créé par `S00internal-boot`, après la séquence rcS qui monte les systèmes de fichiers et traite overlayfs. Le bind n’est donc pas installé avant ces montages initiaux. Le délai60s borne l’attente de ces conditions ; il ne borne pas la durée de génération de la clé d’hôte RSA sur cet ARM.

Le mot de passe root verrouillé ne suffit pas à conclure que le chemin par clé sera refusé. Le shell root est `/bin/sh`, autorisé dans `/etc/shells`. Le code officiel [Dropbear2020.81 svr-auth.c](https://github.com/mkj/dropbear/blob/DROPBEAR_2020.81/svr-auth.c) sépare la validation de l’utilisateur et l’authentification. Le résultat reste à confirmer avec le binaire livré. Celui-ci contient aussi `rsa-sha2-256` : **ne pas activer automatiquement une exception de signature SHA-1 `ssh-rsa` côté client** ; essayer la négociation normale d’abord, puis diagnostiquer un refus réel.

## Choix de carte : divergence résolue

La lecture initiale `0xfffffa3c = 00384023` ne visait pas PIOC et ne doit pas servir à choisir le DTB. Le nouveau journal `inspect-pioc-straps.log` utilise PIOC à `0xfffff800` et donne PDSR=`dfeff7ff`. Les bits PC25/PC27/PC29 valent **110**, ce qui sélectionne `miniio` et `at91-kizboxmini-base.dtb` dans `rootB/boot/at91-kizboxmini-bootscript-vars`. Le fichier historique `persistent/root/usr/share/model` indique aussi miniio. PSR/OSR montrent ces lignes comme GPIO d’entrée. L’hypothèse d’une inversion de `ovk-gpio` n’est pas nécessaire pour expliquer l’ancien écart d’adresse.

La sélection baseDTB est donc corroborée. La sélection `rootB` reste celle du fichier persistant sauvegardé ; elle ne doit pas être confondue avec une observation de `/proc/cmdline` du système courant.

## Correction critique : watchdog actif

**WDT_MR=`1fff2fff` ne signifie pas « watchdog désactivé ».** Le [registre défini par Linux5.4](https://github.com/torvalds/linux/blob/v5.4/drivers/watchdog/at91sam9_wdt.h) place :

- `WDDIS` au **bit15**, ici0 : désactivation non demandée ;
- `WDRSTEN` au **bit13**, ici1 : reset activé ;
- `WDDBGHLT` au **bit28**, ici1 : arrêt du compteur prévu pendant le debug halt ;
- `WDV` sur les12 bits faibles, ici4095 : environ16s au compteur256Hz décrit par le [pilote](https://github.com/torvalds/linux/blob/v5.4/drivers/watchdog/at91sam9_wdt.c).

Le pilote rappelle que le registre de mode n’est modifiable qu’une fois. Une écriture tardive ne doit pas être supposée désactiver le WDT. Le bit debug-halt rend plausible un arrêt du compteur pendant le halt JTAG, mais **la séquence de transfert choisie et chaque période de CPU repris doivent être couvertes explicitement**. Les microprogrammes RAM d’acquisition nourrissaient déjà le watchdog ; cela ne prouve pas que le nouveau chargement le fera.

## Blocages avant branchement sur le nouveau noyau

1. **Quiescence des DMA.** `inspect-boot-state.log` donne HDMAC0 CHSR=`00ff0002`, donc le canal1 reste actif dans les bits d’activation. Le complément `inspect-dma-usb.log` identifie sa source `0xf801c018` comme registre de réception UART, avec destinationDDR`0x278298c9` et chaîne`0x27a0cb64`. Il ne s’agit donc pas d’un DMA NAND dans ce relevé. Cela ne retire pas l’exigence de l’arrêter proprement avant le remplacement de l’OS ; ce maître peut encore écrire en DDR. Le statut après arrêt doit être relu. Le [pilote DMA Linux](https://github.com/torvalds/linux/blob/v5.4/drivers/dma/at_hdmac_regs.h) confirme les registres de statut et les blocs par canal. MACB NCR=`1c` montre aussi une interface encore active : le réseau ne doit pas continuer ses transferts pendant le remplacement mémoire.
2. **Ne pas oublier les DMA autonomes USB.** Le DTB base active OHCI à `0x00600000` et EHCI à `0x00700000` (`status=okay`). Leur présence n’est pas couverte par une lecture des seuls deux HDMAC. Le complément indique OHCIControl=`0x283` : étatOperational, même si ses listes périodiques/control/bulk sont désactivées. Cela ne démontre pas son innocuité : sa zone HCCA contient aussi le numéro de trame actualisé par le contrôleur, comme le montre [ohci.h Linux5.4](https://github.com/torvalds/linux/blob/v5.4/drivers/usb/host/ohci.h). Pour EHCI, CAPBASE=`0x01000010` donne CAPLENGTH=`0x10` : les registres opérationnels commencent àbase+0x10. Les valeurs jadis lues àbase+0x20 ne sont pas USBCMD/USBSTS ; elles ne démontrent pas l’arrêtEHCI. Identifier les maîtres actifs et leurs états, y compris USB, avant le chargement. Désactiver une propriété DTB future ne stopperait pas le contrôleur de l’ancien noyau.
3. **Transition CPU et caches.** Le dernier journal indique MMU et D-cache actifs. Le kit n’effectue aucune transition vers les conditions du chargeur ARM. Il faut une séquence explicite pour cohérence du cache, suppression des traductions/MMU, D-cache désactivé, IRQ/FIQ masquées, étatARM/SVC et r0/r1/r2 corrects, puis entrée physique du zImage. Désactiver le cache sans traiter ses lignes sales peut perdre les dernières écritures ou écraser ensuite le nouveau contenu. Une écriture JTAG physique seule ne prouve pas la cohérence de toutes les vues cache.
4. **Fenêtre watchdog.** Documenter le statut debug-halt effectivement applicable, les périodes où le CPU tourne, les alimentations WDT et la durée maximale de chaque transfert. Ne pas engager une séquence fondée sur l’interprétation erronée du bit13.
5. **Lecture de retour et marges mémoire.** Vérifier les octets réellement chargés en RAM avant l’entrée. Le plan des fichiers proposé ne suffit pas à établir la marge du noyau décompressé, du BSS et du travail du décompresseur. Les états DMA/CPU doivent rester maîtrisés entre cette vérification et le branchement.

Ces points sont des préconditions d’exécution à résoudre par le coordinateur matériel ; le présent rapport ne demande aucune nouvelle autorisation et n’exécute pas ces étapes. Les exigences de base proviennent de [Booting ARM Linux5.4](https://www.kernel.org/doc/html/v5.4/arm/booting.html), notamment l’arrêt de tous les DMA, les registres et la cohérence du mode CPU.

## Mémoire et portée du retour arrière

La DDR décrite couvre `[0x20000000, 0x28000000)`. Avec les adresses proposées, le zImage occupe `[0x22000000, 0x222f25e8)` et le DTB `[0x21000000, 0x2100562c)` : ces deux fichiers sont dans la DDR, alignés comme requis et distincts. `0x22000000` est exactement32Mio après le début deDDR, pas au-delà. Le flux décompressé mesuré fait6 155 420octets. L’emplacement exact de sortie et le BSS ne sont pas démontrés par cette seule mesure ; ne pas présenter les16Mio laissés avant le DTB comme une preuve complète.

Le wrapper conserve ses fichiers d’administration et sa clé d’hôte dans `/run`. Il remplace la vue de `/root/.ssh` par un bind et ne suit pas le lien persistant pour écrire `authorized_keys`. Aucun chemin d’administration persistant n’est modifié dans le script.

**Cela ne garantit pas zéro écriture NAND globale.** Le démarrage normal monte `/data` et `/persistent` en écriture, démarre les services et peut modifier sélection/compteurs/logs. Le saut à chaud abandonne aussi le contexte de l’ancien Linux : ce n’est pas une pause reprenable. La cohérence des écritures en vol et des caches de fichiers doit être traitée comme lors d’un arrêt non propre, pas comme une restauration exacte de l’état sauvegardé.

`rollback.sh` vérifie sommairement le PID et sa ligne de commande avant d’arrêter le listener, puis démonte le bind si le contenu correspond. Cela retire le chemin pour de nouvelles authentifications, **pas les sessions SSH déjà établies** ; le README le précise. Son message final n’est pas une preuve de fermeture du port ni de disparition du montage. Pour la recette de test, prévoir une vérification de2222, des processus temporaires et du bind, puis fermer les sessions. Le redémarrage électrique retire l’injection RAM, mais ne défait pas les écritures ordinaires que l’OS aurait déjà produites.

## Conclusion de revue

- **Acceptable statiquement :** choix miniio/base corroboré, DTB limité àbootargs, chaîne956octets, arguments init exacts, clés et cheminsSSH compatibles avec les observations.
- **À résoudre avant branchement :** canalDMA0#1 UART actif, MACB et contrôleursUSB, transition MMU/cache, couvertureWDT et preuve du chargement/marges.
- **À vérifier après un démarrage réussi :** identité hôte indépendante, authentification, UID0, montagesRAM, processus, absence de fichier admin persistant, et révocation complète. Aucune commande de chauffage ou d’eau chaude n’est nécessaire à cette validation.

Preuves supplémentaires : `ram-independent-checks.json` et `ram-independent-peripherals.json`. Les clés publiques et privées sont volontairement omises de ce rapport. Les fichiers du kit n’ont pas été modifiés par cette revue.

> Les empreintes historiques des fichiers expurgés se rapportent aux originaux privés.
