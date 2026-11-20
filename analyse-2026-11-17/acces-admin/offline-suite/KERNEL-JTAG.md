# Noyau, JTAG et absence de SSH : audit hors ligne

> **ERRATUM visible — 17 novembre 2026 :** les adresses `saved_command_line` de la table historique ci-dessous sont erronées : **A PA `0x205e5014` ; B PA `0x205e7014`**. Le calcul antérieur confondait les littéraux de r6/r5. Les scripts et résultats historiques restent préservés. La correction indépendante par `/proc/cmdline` et l’analyse du ringbuffer de l’essai02 sont dans offline-kernel/README.md (non publié). Le mot `0x7` à l’ancienne adresse ne permettait aucune conclusion sur la banque.

17 novembre 2026. **Le transfert du candidat et la demande d’entrée sont prouvés ; son démarrage complet, sa commande active et l’exécution du wrapper ne le sont pas. Aucun accès SSH n’a été obtenu.** Les traces établissent ensuite un reset watchdog pendant l’intervalle de diagnostic. Elles ne permettent pas de l’attribuer au premier démarrage candidat.

Cette analyse n’a contacté ni le hub, ni le Pi, ni le HP. Aucun kit n’a été lancé. Le script exécuté et les preuves de `attempt-01/` sont préservés. REA n’était pas nécessaire : décompression locale, inspection Capstone ciblée déjà conservée et tests de RPC simulés suffisent.

## Faits et chronologie

| Étape | Preuve locale | Conclusion bornée |
|---|---|---|
| Quiescence et transition CPU | `attempt-01/events.jsonl`, `openocd-final.log` | Contrôles passés ; SCTLR `0x5217a` ; MMU/D-cache/I-cache désactivés avant chargement |
| Relecture noyau | Même dossier, `readback-kernel.bin` | 3 089 896 octets, SHA-256 `8c58bb4c0bbb294f9e2b017f245183f09541ae394c59356c41b342e030d7475a`, égalité binaire avec B confirmée à nouveau hors ligne |
| Relecture DTB | `readback-dtb.bin` | 22 060 octets, SHA-256 `68c873705b88c38636582f8362b7aa5a48835866553e393cb46172180db4e051`, égalité avec candidat confirmée |
| Service WDT et entrée | Événements du Pi, 16:28:55 UTC | WDT acquitté à 16:28:55.912 ; reprise acquittée à 16:28:55.929. Aucun jalon noyau ou init enregistré |
| Réseau | Résultats post-boot et `RESULTAT-ESSAI-RAM.md` | Hôte répondant avec identité attendue ; ports administratifs refusés. Cela ne désigne ni le noyau ni la racine active |
| Premier diagnostic | `post-boot-inspection.log` et fin `openocd-final.log` | CPU en mode utilisateur, MMU/caches actifs ; RSTC_SR `0x10000`. Pas de reset watchdog indiqué à cette lecture |
| Lecture virtuelle | Mêmes traces | Data abort sur `0xc05b4004`. Ce n’est pas une lecture réussie de la commande active ; ne pas interpréter l’échec comme preuve de banque |
| Arrêt ultérieur | `active-command-inspection.log`, 16:34:28 UTC ; OpenOCD | Timeout de halt ; réponse RPC de statut `-4`, mal classée par le client |
| Nouvelle session | `active-command-inspection-03.log`, 16:38:09 UTC | Mot physique supposé du pointeur B = `0x7`, rejeté ; RSTC_SR `0x10200`, soit type watchdog |
| Clôture | `runtime-session-02.log`, rapport de résultat | Routine SRAM relue et exécutée pour demander retour NAND ; réseau revenu ; arrêt OpenOCD/GPIO remis en entrée rapportés par le coordinateur |

La première trace de diagnostic n’horodate pas chaque lecture cible. Le reset watchdog se place entre les observations de statut différentes, dans une séquence qui comporte un data abort, une reprise et un timeout JTAG. Le lien causal précis n’est pas observable. Une prise en charge WDT tardive au premier boot reste une hypothèse générale ; **les traces présentes ne la démontrent pas**. Les accès du débogueur et leurs reprises constituent aussi des événements à distinguer dans une future capture. La pause debug qualifiée n’équivaut pas à une mesure de toutes ces transitions.

## Identifier le noyau avant de lire ses variables

Les deux noyaux livrés diffèrent. Les adresses B ne doivent pas être réutilisées pour A.

| Objet physique | A : 5.4.294 (`root`) | B : 5.4.302 (`rootB`) |
|---|---|---|
| Bannière `Linux version …` | `0x20486078` | `0x20487078` |
| Mot pointeur `saved_command_line` | `0x205bf014` | `0x205c1014` |
| Tampon initial `boot_command_line` | `0x205b3004` | `0x205b4004` |

Empreinte zImage A : `e4a88b2da888c6da60a95b0970e4c671a43ce53d5d6bbd9b58d298e7c3275d04`. Les signatures et dérivations sont reproduites par `prepare_offline.py` et conservées dans `offline-audit.json`. Le pointeur est établi par le registre d’ancrage des données chargé dans `start_kernel`, l’allocation stockée à son offset `0x14`, puis la copie de la commande.

**Une bannière présente en RAM peut être un vestige.** Elle ne suffit pas à identifier le noyau actif, encore moins la racine montée. Une reprise devra corroborer la version par le contexte d’exécution et des références de code cohérentes, ou par la bannière effectivement émise pendant ce démarrage. Les noyaux B NAND et candidat partagent aussi la même version et le même binaire : leur bannière ne les distingue pas.

Le mot `0x7` à l’adresse B n’est pas un pointeur direct plausible. Il peut correspondre à un autre objet si un autre noyau tourne, à une adresse inadaptée ou à un contenu non interprétable dans cet état. **Il ne prouve ni A, ni B, ni une corruption du noyau.** Aucun déréférencement n’a été effectué.

Après identification corroborée du noyau, la copie durable `saved_command_line` est préférable au tampon `boot_command_line`, normalement `__initdata` et réutilisable. Pour un pointeur direct valide, la correspondance observée est `PA = VA - 0xc0000000 + 0x20000000`, dans la DDR `[0x20000000,0x28000000)`. Une acquisition future doit vérifier sa plausibilité et la terminaison NUL sous 1 024 octets. Comparer en mémoire au candidat et conserver seulement longueur, égalité et marqueurs utiles. Ne pas afficher la commande complète : elle contient une clé publique du kit. Voir aussi `../COMMANDE-NOYAU-ACTIF.md`.

## Défaut du parseur RPC confirmé et corrigé séparément

Le lanceur exécuté, SHA-256 `8e9ee090fa6a61055584d3133edcfb94d6e1f4e03b0082e28d4bcb1409cd4fe5`, impose `[0-9]+` au statut de `catch`. OpenOCD renvoie réellement `__COZY_RAM_RPC_1__-4` après le timeout de halt. Le client transforme ce statut en `malformed Tcl RPC envelope` avant d’enregistrer son diagnostic. L’enveloppe est pourtant structurée ; c’est un échec cible.

La copie **non exécutée** `launch-ram-offline-candidate.py` accepte `-?[0-9]+`, traite toujours tout statut non nul comme un échec et conserve le nombre dans l’exception. Elle conserve le corps d’erreur dans le fichier privé prévu, même si ce corps est vide. Le script historique reste identique. Empreinte candidate : `10a90bbf83e44a426175ee90bb7593a3476522dc841083b5e7f2c64f73a1f319`.

`test_rpc_offline.py` extrait uniquement les définitions nécessaires par AST ; il n’importe pas le lanceur complet et n’appelle jamais son `main`. Les sockets sont simulées en mémoire. **12 cas passent** : succès, erreur positive, erreurs négatives dont `-4` avec texte et corps vide, statut mal formé, sur l’original et la copie. Résultats dans `rpc-test-results.json`.

Ce défaut explique la perte de précision du diagnostic ultérieur. **Il n’explique pas l’absence initiale de SSH** : les 29 commandes de l’entrée initiale se terminent avec un statut nul dans les preuves.

## Ce qu’une capture utile doit distinguer

Une nouvelle tentative n’est pas préparée pour exécution ici. Les prochaines étapes proposées sont :

1. **Capturer le démarrage série avant toute nouvelle entrée**, avec horodatage continu jusqu’à init et après tout reset. Le DTB source désigne `/ahb/apb/serial@fffff200` comme `stdout-path` (alias `serial0`), distinct de l’USART0 à `0xf801c000` dont le DMA a été arrêté. Cela n’établit pas les broches, le niveau électrique ou la vitesse à utiliser : vérifier le raccordement connu et une réception seule. La disponibilité du matériel de capture reste à confirmer.
2. **Rendre les jalons observables**, dans un futur candidat revu : entrée du wrapper, `/run` prêt, `/tmp/boot` présent, début/fin de génération de clé, bind réussi, lancement et sortie Dropbear. Messages courts sans clé ni commande complète. Le kit actuel ne journalise pas ces étapes sur console.
3. **Distinguer les attentes** : délai du marqueur d’init, génération RSA/entropie, erreur de montage et échec du serveur. Ces hypothèses restent ouvertes ; aucune trace de processus ne les départage. Le diagnostic natif Dropbear antérieur n’exige pas de déverrouiller shadow pour une clé publique.
4. **Corroborer noyau et commande active avant les variables internes**, en privilégiant capture série ou preuves runtime cohérentes. Une source DTB restée en RAM, une bannière isolée, un ping ou la MAC attendue ne démontrent pas l’exécution du candidat.
5. **Horodater les causes de reset et les transitions de diagnostic**, sans reprendre une ancienne DDR après takeover. Un log de cause avant/après chaque étape aide à séparer échec du démarrage et incident ultérieur de diagnostic.

Le DTB original ne contient pas d’option `console=` explicite ; son `stdout-path` peut être pris en charge selon le pilote compilé. Il contient `loglevel=2`, qui masque les messages nominaux de niveaux supérieurs sur console. Une absence de bannière UART ne suffirait donc pas à conclure à l’absence de boot sans vérifier cette configuration. Toute modification de verbosité ou instrumentation serait un futur changement revu, pas une action effectuée par cet audit.

Les fondements de durée de vie et de copie des commandes sont dans [Linux 5.4 init/main.c](https://raw.githubusercontent.com/torvalds/linux/v5.4/init/main.c) et [fs/proc/cmdline.c](https://raw.githubusercontent.com/torvalds/linux/v5.4/fs/proc/cmdline.c). Les exigences d’entrée sont décrites dans [Booting ARM Linux](https://docs.kernel.org/arch/arm/booting.html). Les conclusions de cet audit reposent sur les artefacts et traces locales ; aucune observation nouvelle du matériel n’a été ajoutée.

> Les empreintes historiques des fichiers expurgés se rapportent aux originaux privés.
