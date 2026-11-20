# Cozytouch — installation de la banque A

État du 18 novembre 2026. Les images sont des candidates construites hors ligne. Ce plan prépare des interventions séparées. Arrêter au premier écart inexpliqué. Une validation sur QEMU ne vaut pas preuve de démarrage du SAM9G25, de sûreté de la lecture NAND ni de restauration d’un hub.

## 1. Revue hors ligne

Contrôler le manifeste du lot, le journal ARM926, le plan RAM et la correspondance avec la carte. Vérifier le type et la capacité des deux volumes A d’après la phase 1. Le candidat root contient /boot/zImage, /boot/dtb, /boot/cmdline et le témoin /boot/bootloaderid avec 20180731. Le wrapper kboot extrait consulte par défaut **/persistent/boot/update/bootloaderid**. Le témoin de root ne remplace pas ce prérequis d’activation. [Phase 1](../RESULTAT.md#1-chemin-de-démarrage) · Manifeste (non publié)

Préparer l’hébergement MQTT isolé, les accès SSH de gestion et le provisionnement privé de l’image dynamique apps A dans un espace séparé. Le lot public contient seulement le répertoire /ct vide. Le répertoire doit appartenir à root et être en 0700. Les quatre fichiers doivent être réguliers, à lien unique, appartenir à root et être en 0600.

- **broker.conf** contient broker_ipv4, broker_port, mqtt_username, mqtt_password, client_id, lan_ipv4, lan_prefix, admin_ipv4 et interval_seconds. Les trois adresses appartiennent au même sous-réseau IPv4 privé. Utiliser un identifiant MQTT stable et distinct des autres clients. Le courtier doit autoriser les publications de disponibilité, d’état et de découverte de ce client.
- **targets.conf** contient les deux lignes du format de contexte déjà qualifié, dans l’ordre CETHI, IC3. Les contextes existants sont fournis directement au provisionnement privé autorisé.
- **authorized_keys** et **ssh_host_key** contiennent respectivement les clés publiques d’administration autorisées et la clé d’hôte au format Dropbear. Vérifier la clé publique d’hôte par un canal indépendant.

Conserver l’empreinte de l’image apps provisionnée dans le procès-verbal privé. Le journal public conserve uniquement les statuts de contrôle. MQTT 3.1.1 utilise ici l’authentification utilisateur et mot de passe sur le LAN isolé. Le format MQTT choisi transmet ces valeurs sans chiffrement de transport.

## 2. Qualifier le secours en lecture sur banc — à autoriser par <PERSONNE>

1. Valider le point d’arrêt, la carte, la DDR, le watchdog, les périphériques actifs et les relectures RAM. Pour une prise de contrôle depuis l’OEM, appliquer la quiescence P1 seulement si son périmètre et ses écritures ordinaires sont autorisés. Pour un démarrage secteur, qualifier un arrêt avant l’entrée kboot. Employer le plan fusion pour les adresses et l’ABI de saut après revue de son préflight. Vérifier le DTB à 0x21000000, le zImage à 0x22000000 et l’initramfs à 0x24000000. Le DTB contient la borne finale exclusive calculée à partir du CPIO livré. Plan RAM4 (non publié) · [Préflight froid](../../stm32-demarrage-froid/RAPPORT.md)
2. Examiner la chaîne de lecture avant le chargement. Le DTB de secours rend les partitions non inscriptibles et omet nand-on-flash-bbt. Le pilote Atmel du lot accepte le mode de secours uniquement pour le contrôleur SMC. Il active NAND_ROM avant nand_scan et refuse les sorties de données et les commandes NAND hors liste de lecture et d’identification. Linux construit alors sa BBT en mémoire avec les marqueurs de blocs. Le test de la branche de secours doit couvrir une BBT absente, une seule copie et une copie dégradée sur un banc prévu pour ces configurations.
3. Au probe sur banc, enregistrer les marqueurs du pilote et une capture passive des cycles NAND. Vérifier qu’aucun opcode de programmation, d’effacement ou d’écriture OOB ne part vers la NAND. Le NAND RESET de la détection concerne la puce NAND. Les cycles WE# utilisés pour placer une commande de lecture ne démontrent pas une programmation. Confirmer les fenêtres observées par comparaison de deux acquisitions brutes, données et OOB, avant et après chaque essai. Comparer toutes les pages et les emplacements des copies de BBT.
4. Confirmer l’absence d’auto-attache UBI, le mode MTD en lecture seule et le chemin de lecture des blocs défectueux. Ne pas utiliser la carte du hub comme banc d’essai destructif. L’absence de BBT flash active dans ce profil peut modifier la liste de blocs réservés. Couvrir les blocs physiquement lus avec la méthode brute qualifiée. Une lecture via UBI seule ne couvre pas les OOB ni ces blocs. [Garde de commandes](patch-nand.py) · [DTB secours](src/rescue.dts)

## 3. Qualifier le froid radio et le retour OEM — à autoriser par <PERSONNE>

1. Qualifier sur banc un démarrage du service à froid sans action sur les lignes radio. Démarrer la capture passive à la mise sous tension. Exiger STACK_START, le GET local corrélé v2.4.2, les deux READ et leurs PUBACK. Si Linux ouvre l’UART après STACK_START, un opérateur autorisé peut déposer dans /run/ct/stack-start-observed un reçu root 0600 dont le contenu est STACK_START, un espace, l’identifiant du boot Linux lu localement, puis un saut de ligne. L’opérateur établit par capture que l’événement appartient à ce même cycle électrique. Le service lie le reçu au boot Linux et arrête l’essai si la pile ou le reset apparaissent à nouveau. Le reçu se perd au prochain redémarrage.
2. Si la pile reste muette ou si la révision diffère, arrêter. Qualifier le secours indépendant et le rétablissement du seul pointeur. Distinguer le repli temporaire de kboot et le retour durable sur B. Préparer la protection contre toute mise à jour STM32 par le daemon B, y compris à froid et hors WAN. Vérifier la sentinelle de blocage avant le lancement du daemon B, ainsi que l’absence d’une mise à jour déjà engagée. [Démarrage radio](../../stm32-demarrage-froid/RAPPORT.md#2-initialisation-minimale-du-service-alternatif) · [Restauration du pointeur](../../restauration-pointeur-jtag/PROCEDURE.md) · [Updaters](../../updater-stm32-sol/RAPPORT.md)

## 4. Constater le hub et sceller la copie récente — à autoriser par <PERSONNE>

Confirmer la paire OEM active rootB/appsB, l’état de l’updater et de ses tâches, les écrivains et le watchdog. Acquérir deux copies de la NAND avec la voie brute qualifiée. Vérifier tailles, SHA-256 par lots, PMECC et OOB, géométrie UBI, BBT et volumes. Décoder sur une copie les volumes, le compte, le pointeur et le marqueur partagé. Expliquer les écarts avec la sauvegarde du 17 novembre. Garder les originaux en lecture seule. Sceller aussi les empreintes des volumes communs et OEM et des fichiers partagés pertinents.

## 5. Écrire puis relire la banque A — à autoriser par <PERSONNE>

1. Le secours livré est **physiquement limité à la lecture**. Qualifier séparément un environnement d’écriture en RAM et l’attache UBI pour mettre à jour des volumes existants. Une attache UBI inscriptible peut écrire ses métadonnées et effectuer des opérations de récupération. Définir et approuver ce périmètre avant toute exécution. Comparer les données et les métadonnées pertinentes après l’attache.
2. Confirmer root A (ID 7, statique, 165 LEB) et apps A (ID 12, dynamique, 130 LEB), démontés. Appliquer les images au niveau des volumes UBI existants avec le mécanisme de mise à jour de volume. Utiliser l’image apps A provisionnée en privé si elle a été vérifiée. Exclure toute opération de formatage de la partition, de remplacement de table UBI ou d’écriture brute.
3. Relire intégralement la longueur utile des deux images. Comparer empreintes, géométrie, type, capacité et absence de marqueur de mise à jour. Monter A en lecture seule et vérifier les fichiers de boot, le répertoire privé et les droits. Confirmer les empreintes logiques de B, des volumes communs et de l’état partagé. Une écriture interrompue ou un écart fait arrêter avant activation.

## 6. Activer A par le seul pointeur — à autoriser par <PERSONNE>

Confirmer les relectures de A, le compteur à 0, la sélection actuelle ubi0:rootB et le marqueur **partagé** attendu. Vérifier l’absence d’une variable KBOOTIDFILE effective qui change le chemin de contrôle. Remplacer atomiquement le pointeur par ubi0:root suivi d’un saut de ligne, avec temporaire dans le même répertoire, synchronisation du fichier puis du répertoire et relecture indépendante. Vérifier les attributs et les autres fichiers de persistent avant tout redémarrage. Les anomalies des prérequis demandent une décision séparée.

## 7. Démarrer A, répéter puis éprouver le repli — à autoriser par <PERSONNE>

1. Définir une durée et le repli indépendant avant le premier boot. Confiner le réseau dès l’étage kboot et vérifier l’absence de daemon OEM, d’updater et de commande GPIO radio du profil A. Faire relever la version du noyau, le PMECC, les montages root/apps et le filtrage avant montée du lien. Vérifier le SSH par clé, la révision STM32, les deux READ, les publications et la relecture du compteur après santé.
2. Répéter sur au moins trois passages kboot. Autoriser séparément la coupure complète qui établit le froid et les redémarrages nécessaires à un essai d’échec contrôlé. Vérifier que le compteur reste à la valeur gérée par kboot en cas de santé absente. Le système A reste en attente après une erreur terminale. Le repli au seuil s’évalue aux passages suivants de kboot. Le seuil ne change pas le pointeur.
3. En cas d’écart, utiliser le secours qualifié dans le périmètre approuvé. Restaurer atomiquement le pointeur OEM et le relire. Vérifier le retour NAND sur B, le confinement, le blocage effectif de l’updater radio et l’état des appareils. Autoriser séparément tout traitement du compteur nécessaire à ce retour.

> Les empreintes historiques des fichiers expurgés se rapportent aux originaux privés.
