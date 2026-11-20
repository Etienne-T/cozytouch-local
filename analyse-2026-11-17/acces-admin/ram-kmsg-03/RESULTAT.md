# SSH root temporaire obtenu — 17 novembre 2026

Le troisième essai RAM donne un accès SSH root sur `<IP_HUB>:2222`. L'authentification par la clé dédiée est vérifiée, ainsi que la clé du serveur obtenue indépendamment dans le journal noyau lu par JTAG. Une seconde connexion réussit après arrêt d'OpenOCD et remise des GPIO 8/9/10/11 du Pi en entrée. Le hub reste allumé avec cet accès temporaire.

## État vérifié

- UID/GID 0, noyau 5.4.302, architecture armv5tejl.
- Racine `ubi0:rootB` montée en lecture seule ; `/run` est un tmpfs.
- `/run/ct` et `/run/ct/ssh` : propriétaire root, mode 700. Clé d'hôte et authorized_keys : mode 600.
- `/root/.ssh` est un montage temporaire du répertoire RAM ; son authorized_keys est identique à celui de `/run/ct/ssh`.
- Dropbear PID 49, authentification par clé, port 2222. Les processus `io-homecontrold`, `internald`, `connmand` et `watchdogd` sont présents. Leur présence ne prouve pas le bon fonctionnement complet du cloud ou des appareils.
- Capture SH-U09C5 terminée : 0 octet pendant les deux essais RAM, aucune émission série. Le démarrage normal capturé auparavant produisait bien 89 octets lisibles.
- Aucun ordre de chauffage, de chauffe-eau, d'appairage ou de programmation de flash envoyé. Les écritures ordinaires de l'OS sur ses volumes persistants n'ont pas été comparées.

## Diagnostic et différence entre les essais

RAM02 a bien consommé notre commande : la lecture correcte de `saved_command_line` le démontre. Son adresse physique dans le noyau B est **0x205e7014**, et non 0x205c1014 employée auparavant. Les documents d'analyse portent un erratum ; les preuves d'exécution originales sont conservées.

Le noyau signale `Warning: unable to open an initial console.` Le pilote UART Atmel n'a pas de console enregistrée et le DBGU est désactivé dans le DTB livré. Le silence sur cette broche UART ne permettait donc pas de conclure que Linux ou le lancement du shell échouaient. La liaison interne ttyS1 n'a pas été utilisée pour envoyer des commandes.

RAM03 attend `/dev/kmsg`, puis y redirige ses sorties avant les messages de progression. Il attend ensuite le tmpfs `/run` et le marqueur de démarrage, crée les fichiers privés avec `umask 077`, génère la clé d'hôte, monte le répertoire SSH RAM et lance Dropbear au premier plan dans le processus de fond. Il remplace également certains appels chmod redondants par ce umask. Plusieurs différences existent : aucun essai isolé ne prouve que les messages echo de RAM02 étaient l'unique cause de son échec. Une sortie standard fermée pouvait toutefois interrompre sa chaîne `&&`.

Chronologie du journal RAM03, secondes depuis le démarrage noyau : K0 à 4,011 ; K1 à 11,443 ; K2 à 11,476 ; génération RSA à 11,691 ; clé disponible à 114,544 ; K3 à 114,545 ; K4 à 114,561. **La génération RSA prend environ 103 secondes.** Une erreur grep transitoire avant montage de `/proc` est suivie d'une attente réussie ; ce n'est pas un blocage.

## Reprise et réversibilité

Ne pas redémarrer le hub si l'on veut conserver cette session de travail. Un redémarrage perd le noyau/DTB chargés en RAM, le service ajouté, les clés temporaires et le montage `/root/.ssh`. Le retour au démarrage NAND a déjà été utilisé lors de RAM01, mais **la disparition de cet accès RAM03 après redémarrage n'a pas été retestée**, afin de le garder disponible.

Depuis le dossier du projet, connexion avec vérification de la clé d'hôte :

```powershell
ssh -p 2222 -i analyse-2026-11-17/acces-admin/ram-boot/cozytouch-admin-rsa2048 -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile=analyse-2026-11-17/acces-admin/ram-kmsg-03/known-hosts-jtag-verified root@<IP_HUB>
```

Le compte rendu ne contient aucune clé privée ni jeton. Le dossier et l'archive restent privés. La clé d'hôte est propre à ce démarrage ; ne pas réutiliser aveuglément sa vérification après un nouvel essai.

Prochaine piste : inspecter les interfaces locales et la liaison avec `io-homecontrold` depuis ce shell, puis obtenir une lecture d'état des appareils sans cloud. Cette dernière tâche reste ouverte dans Inbox ; l'accès SSH seul ne l'accomplit pas.

## Preuves

- `admin-verification.txt` : contrôle root, montages, droits et processus.
- `stability-after-jtag-release.txt` : seconde authentification après libération du JTAG, à environ 386 secondes d'uptime.
- `ring-01/` : journal binaire, indices, décodage ; inclut des informations privées, à ne pas publier brut.
- `candidate.dtb` : SHA-256 `f9dfe9677f8188bae1e03b5f34f178a9b783f262d65deed48680bac83591da3a`, 22 100 octets, commande de 993 octets NUL compris ; seule la propriété `/chosen/bootargs` change.
- `wrapper.sh` : version réellement exécutée de 993 octets avec la commande complète. Le brouillon ultérieur de 1023 octets dans `offline-suite` n'a pas été exécuté.
- `build.json` décrit la construction avant exécution ; son champ `hardware_executed:false` est historique. L'exécution est prouvée par `ram03/attempt/` dans l'archive et les vérifications SSH.
- `../ram02-03-evidence.tar.gz` : preuves Pi et relectures complètes, SHA-256 Pi/Windows concordant `788c3b99be204bd92492d4b1e54d7f643f95e21d927eb1c5ff3c3c06a9819b32`.
- `../../../donnees/<CHEMIN_LOCAL>-2026-11-17/20261117-ram02/` : capture HP de 17:13:50 à 17:41:34 UTC, finalisée et copiée ; fichier vide SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.

> Les empreintes historiques des fichiers expurgés se rapportent aux originaux privés.
