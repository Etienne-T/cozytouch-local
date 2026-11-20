# Essai RAM du 17 novembre 2026 : accès non obtenu, retour effectué

**Une tentative a été exécutée. Aucun accès SSH administrateur n'a été obtenu.** Le chargement en RAM et ses contrôles ont réussi ; la raison de l'absence du serveur temporaire n'est pas établie. Le coordinateur a terminé l'essai par le retour SRAM au démarrage NAND, puis arrêté OpenOCD et remis les quatre GPIO JTAG en entrée. Le hub répond de nouveau sur son adresse habituelle.

## Ce qui est prouvé

1. L'identité MAC matérielle concorde avec la sauvegarde. Les straps correspondent à `miniio`. Les contrôles de quiescence EHCI, OHCI, MACB et HDMAC passent sur le matériel.
2. Après `soft_reset_halt`, SCTLR vaut `0x5217a` : MMU, cache de données et cache d'instructions désactivés. Le contexte d'entrée ARM/SVC et les registres préparés sont contrôlés.
3. Le noyau chargé à `0x22000000` est relu intégralement : **3 089 896 octets**, SHA-256 `8c58bb4c0bbb294f9e2b017f245183f09541ae394c59356c41b342e030d7475a`. Le DTB à `0x21000000` est également relu : **22 060 octets**, SHA-256 `68c873705b88c38636582f8362b7aa5a48835866553e393cb46172180db4e051`.
4. Le compteur watchdog est réarmé juste avant la commande de reprise à l'entrée du zImage. Cette reprise est acquittée par OpenOCD à 16:28:55 UTC, selon l'horloge du Pi. Elle ne prouve pas à elle seule le passage complet jusqu'au wrapper.
5. Le hub répond avec la MAC attendue, mais les ports 2222, 22, 443 et 8443 refusent les connexions à environ 23 s, 80 s et plus de six minutes. Aucune clé d'hôte n'est récupérée ; aucune authentification n'est tentée.

## Diagnostic limité

Le premier arrêt de diagnostic observe un CPU en mode utilisateur et `RSTC_SR=0x00010000`, donc aucun reset watchdog indiqué à ce moment. La tentative de lecture virtuelle du tampon initial de commande provoque un data abort du débogueur. Le CPU est repris, puis une demande d'arrêt ultérieure expire alors que le réseau répond encore. La nouvelle session OpenOCD rétablit les lectures ciblées.

Ces lectures physiques observent ensuite `RSTC_SR=0x00010200`, soit un reset watchdog, et `0x00000007` à l'emplacement supposé du pointeur `saved_command_line`. Ce pointeur est rejeté sans déréférencement. **La commande du noyau actif et sa banque n'ont donc pas été identifiées.** Le reset est survenu dans l'intervalle de diagnostic ; son lien avec le démarrage candidat ou avec l'inspection n'est pas établi. Il serait incorrect d'affirmer que le noyau candidat a immédiatement échoué, ou que le wrapper s'est exécuté.

Les chemins des exécutables, le montage tmpfs attendu et la création de `/tmp/boot` sont cohérents avec les scripts livrés. Une attente d'entropie pendant la génération RSA est possible selon le code Dropbear, mais aucun processus ni message d'exécution ne la confirme ici. Cette hypothèse ne constitue pas le diagnostic.

## Fin de l'essai et réversibilité observée

La séquence de quiescence est passée de nouveau. La routine de retour de 48 octets a été chargée en SRAM puis comparée mot par mot avant exécution. Elle arrête les accès DDR et demande le reset processeur/périphériques selon le chemin Linux étudié. Le hub répond ensuite au ping. OpenOCD est arrêté ; GPIO 8, 9, 10 et 11 sont vérifiés en `INPUT`.

Cette procédure **n'envoie aucune commande d'effacement ou de programmation d'image NAND/STM32**. Elle ne modifie pas le fichier shadow ni les clés autorisées persistantes. Le système fabricant peut néanmoins écrire ses données ordinaires pendant son fonctionnement et ses démarrages. L'absence de modification de toutes ses données et le fonctionnement du cloud ou des appareils n'ont pas été vérifiés. Aucun ordre radio ou changement de consigne n'a été envoyé par les outils de test.

La clé privée d'administration reste uniquement dans le dossier Windows du kit. Elle n'a pas servi à une authentification. Les deux acquisitions NAND originales ont été rehachées pendant cette session ; leurs empreintes sont inchangées.

## Reprise utile

Avant une seconde tentative, enregistrer le démarrage et instrumenter les étapes du wrapper afin de distinguer entrée noyau, init, attente du marqueur, génération de clé, montage et lancement Dropbear. Le LA1010 n'était plus présent sur l'USB du HP lors du contrôle de cette session. Identifier aussi la version du noyau réellement actif avant de réutiliser des adresses de symboles. Aucun nouvel essai n'est lancé automatiquement.

Preuves : `ram-boot/attempt-01/` (événements, état, journal et deux relectures RAM), `attempt-01-console.log`, `post-boot-inspection.log`, `active-command-inspection*.log`, `runtime-session-02.log`, `normal-boot-return.log`, `final-pi-and-network.log` et [rapport réseau](RESEAU.md). Le serveur de diagnostic écoute uniquement sur le loopback du Pi lorsqu'il est lancé ; il est arrêté à la clôture.

> Les empreintes historiques des fichiers expurgés se rapportent aux originaux privés.
