# Buildroot en RAM sur Cozytouch

Essai matériel du 17 novembre 2026. **Buildroot 2026.08 et Linux 6.12.0-cozytouch-ram4 ont démarré sur le vrai hub.** SSH par clé et terminal interactif fonctionnent. Le dernier contrôle avant retour indique 377 secondes de fonctionnement avec le même identifiant de démarrage, après arrêt d’OpenOCD et remise des GPIO JTAG en entrée.

## Résultat vérifié

| Contrôle | Résultat |
|---|---|
| Chargement RAM | Noyau, initrd et DTB relus intégralement par JTAG ; trois SHA-256 identiques aux fichiers préparés |
| Système | ARMv5, racine en RAM, PID1 autonome ; environ 102 Mio de mémoire disponible au contrôle initial |
| Accès | SSH avec clé d’hôte vérifiée depuis l’image, authentification par clé et vrai PTY |
| Réseau | Pare-feu installé avant activation réseau ; seuls SSH et ping avec les deux postes de test sont autorisés ; aucune route Internet ; IPv6 désactivé avant activation des interfaces |
| Stockage | Aucun MTD, UBI, stockage bloc ni accès devmem dans cette image ; aucun volume NAND monté |
| Watchdog | Keeper actif ; stabilité constatée pendant plus de six minutes, sans dépendance au JTAG |
| Radio | UART STM32 enregistré, sans processus propriétaire ni client radio lancé dans Buildroot |
| Capture | UART Linux en réception seule : 8 619 octets, aucune écriture série ; copie et SHA-256 vérifiés |

Le marqueur PID1 prêt apparaît vers cinq secondes. Cela ne signifie pas que SSH était déjà utilisable : l’entropie noyau a retardé sa première authentification. La preuve mesure un démarrage direct par JTAG avec accès Internet bloqué dès l’initialisation du réseau. Elle ne qualifie pas un démarrage par la ROM après coupure électrique.

## Images, recette et preuves

Les images utilisables sont dans **`images-verified/`**. Le dossier `images-final/` conserve une étape rejetée avant correction du timer ; ne pas l’utiliser pour démarrer.

- Audit final des images (non publié), réalisé avant le matériel : ses champs `hardware_access=false` et `kernel_entry_or_boot_verified=false` restent volontairement historiques.
- Recette de construction (non publié) et versions épinglées : Buildroot 2026.08, Bootlin ARMv5 EABI glibc 2025.08-1, Linux 6.12. Une seconde reconstruction identique octet par octet n’a pas été démontrée.
- Santé réelle (non publié), terminal SSH (non publié), dernier contrôle avant retour (non publié).
- Continuité du système et journal (non publié), copies des preuves vérifiées (non publié).
- Revue du retour constructeur (non publié). Le redémarrage natif reste une option analysée, non exécutée dans cet essai.

Les images privées contiennent la configuration du banc et une clé d’hôte SSH. Elles restent dans les espaces privés Windows, HP et Pi ; elles ne constituent pas un paquet à publier.

## Corrections qui conditionnent la reprise

L’audit a détecté un DTB sans enfant timer TCB malgré la correction de sa source. Une reconstruction réelle a corrigé l’artefact. Les permissions des clés sont imposées par la table fakeroot Buildroot, car les overlays seuls ne les garantissaient pas. Le premier préflight matériel a refusé un niveau CE NAND bas ; Linux a été repris avant toute modification matérielle, puis la variante V2 a été revue avec Ready/Busy et DMA au repos. Le second essai a passé tous les contrôles et démarré.

Le kit comprend les tests de construction, de lancement et de reprise, ainsi que les contrôles ARM par QEMU. Ces tests complètent les observations du vrai hub ; ils ne les remplacent pas.

## Périmètre restant

Cette étape fournit un Linux autonome administrable. Le service UART/MQTT testé précédemment sous Linux constructeur n’est pas encore porté dans cette image. La suite utile est d’y intégrer le runtime nécessaire, puis de reproduire les deux lectures autorisées et le test sans Internet. La fiche de portage préparée par l’agent (non publié) précise les dépendances et la validation réversible. Une intégration persistante, le choix des banques et les mises à jour avec retour arrière constituent une étape séparée. Aucun test OTA ni démarrage persistant n’est validé ici.

## État final après retour

Le retour direct par JTAG vers le noyau constructeur **5.4.302 et le DTB RAM03** a réussi. Les deux images ont été relues intégralement avec SHA-256 concordants. La nouvelle clé d’hôte SSH a été extraite indépendamment du journal noyau par JTAG, puis utilisée pour l’authentification.

Deux READ natifs du paramètre principal du Calypso CETHI et de l’ASAMA IC3 terminent **DONE / IoCommandNoError**. Le même processus radio possède `/dev/ttyS1`, sans traceur, au contrôle différé. OpenOCD est arrêté et les GPIO 8–11 du Pi sont en entrée ; une nouvelle connexion SSH réussit ensuite. Les volumes OEM habituels sont revenus. Les restrictions réseau de Buildroot ne s’appliquent plus au système constructeur.

La capture UART du retour est vide, ce qui concorde avec la console DBGU désactivée de ce DTB OEM. La preuve de reprise repose sur le journal noyau lu par JTAG, SSH et les réponses radio, pas sur cette capture vide.

Preuves : relectures OEM (non publié), clé vérifiée (non publié), lectures radio (non publié), santé différée (non publié), JTAG libéré (non publié). Les réponses détaillées restent privées dans `orchestration/oem-radio-private/`.

Pour reprendre SSH, utiliser `orchestration/run-oem-return.py` ou la clé d’hôte de `orchestration/known-hosts-oem-return` avec son alias `cozytouch-oem-return`, port 2222, et la clé d’authentification historique. Les anciens fichiers known_hosts ne correspondent plus à cette instance. **SSH reste ajouté en RAM et sera perdu après un redémarrage ordinaire.** Les anciens processus et fichiers sous `/run` ont disparu ; notamment, ne pas présumer que le blocage d’updater défini dans l’ancien environnement RAM est encore actif. Le service MQTT de laboratoire n’est pas installé ni lancé.

Aucune commande de programmation ou d’effacement NAND/STM32, d’association ou de réglage de chauffe n’a été envoyée. Les écritures ordinaires du Linux constructeur après reprise ne sont pas une comparaison NAND avant/après. Aucun original ni historique n’est supprimé.

## Conservation

Archive privée prévue : `<CHEMIN_LOCAL>`. Destination HP : `<CHEMIN_LOCAL>`. Le reçu de copie et restauration (non publié), produit après l’archive, porte le résultat de vérification de chaque fichier ; il est conservé séparément de cet instantané. Les sources téléchargées et l’arbre de compilation restent aussi sur le HP.
