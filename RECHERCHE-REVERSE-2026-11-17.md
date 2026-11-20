# Cozytouch — pistes de rétro-ingénierie

État au 17 novembre 2026. Recherche documentaire publique et examen de treize photos fournies par <PERSONNE> : deux vues du boîtier, sept du recto et quatre du verso. Capture UART passive sur le HP à la demande de <PERSONNE> : sortie de démarrage confirmée sur CH1 à 115200 bauds, 8N1. Aucun accès Home Assistant ou au compte Atlantic, aucune écriture dans le bridge.

## Identification

L'étiquette photographiée indique Atlantic Cozytouch, référence **500090**, alimentation **5 V continu, 120 mA**, IP30 et logo io-homecontrol. Les identifiants correspondent à l'enquête du 6 avril 2026 ; ils ne sont pas reproduits ici. Les photos originales sont conservées dans `donnees/photos-2026-11-17/`, avec manifeste SHA-256. Elles contiennent des identifiants privés.

La comparaison des photos internes confirme visuellement le dessin de carte Overkiz Kizbox Mini présenté par Benjamin Lafois. La référence exacte de révision du circuit et la version actuelle du firmware restent inconnues.

### Comparaison matérielle sur photos

Les sept nouvelles photos sont conservées dans `donnees/photos-carte-2026-11-17/`, copies vérifiées par SHA-256. Elles montrent toutes la face processeur, sous différents angles. La photo 1 montre les câbles USB et Ethernet branchés et des voyants allumés ; elle ne démontre pas un état fonctionnel complet.

| Élément | Carte de <PERSONNE> | Référence publique et conclusion |
|---|---|---|
| Dessin de carte | Marquage OVERKIZ, mêmes découpes, fixations, emplacement USB/RJ45, zone d'antenne et groupes de pastilles | Concordance visuelle avec la face processeur du Cozytouch de Lafois. Même dessin visible ; identité de révision et de nomenclature complète non démontrée. |
| Processeur | `AT91SAM9G25`, suffixe `CU`, lisible sur photo 7 | Même référence `AT91SAM9G25-CU` que la photo de Lafois. Les codes de fabrication diffèrent. |
| RAM | Logo Micron et code `D9RZH`, photo 4 | Même fabricant et même code `D9RZH` lisibles sur la photo de Lafois. Son texte identifie la RAM comme `MT47H64M16NF-25E` ; cette référence longue est une attribution documentaire, non une inscription directement lue sur la carte de <PERSONNE>. |
| Interface Ethernet | `KSZ8081`, ligne suivante commençant par `RNB`, photo 5 | Même famille et variante RNB visibles sur la photo de Lafois. Le KSZ8081 est un PHY Ethernet 10/100 selon Microchip. |
| Groupe de 10 pastilles près de la LED | Photos 6 et 7 | Même emplacement et géométrie que le JTAG annoté par Lafois. Affectation électrique non mesurée sur cet exemplaire. |
| Groupe de 3 trous entre processeur et transformateur Ethernet | Photo 3 | Même emplacement et géométrie que l'UART annoté par Lafois. Affectation électrique non mesurée sur cet exemplaire. |
| NAND | `MX30LF1G18AC-TI`, verso photos 3 et 4 | Même référence que la photo de Lafois ; NAND Macronix de 1 Gbit, soit 128 Mio. |
| Microcontrôleur radio | `STM32F101 RCT6`, verso photo 2 | Même référence STM32F101RCT6 que la photo de Lafois. |
| Circuit radio | Marquage `44612A`, verso photo 1 | Correspond au Si4461 révision 2A selon le tableau de marquage Silicon Labs. Ne pas l'identifier comme Si4463. |

Les quatre vues du verso sont conservées dans `donnees/photos-verso-2026-11-17/`, copies vérifiées par SHA-256. La révision exacte du PCB et le firmware restent inconnus. Références constructeur : [Macronix MX30LF1G18AC](https://www.macronix.com/Lists/Datasheet/Attachments/8458/MX30LF1G18AC%2C%203V%2C%201Gb%2C%20v1.2.pdf), [STM32F101](https://www.st.com/resource/en/datasheet/cd00191174.pdf), [marquages Silicon Labs](https://www.silabs.com/documents/public/data-sheets/Si4463-61-60-C.pdf).

La carte Connexoon de Donny Maasland a une implantation apparentée et le même processeur, mais sa photo montre une RAM **SK hynix H5PS1G63KFR**, différente de la Micron de <PERSONNE>. Il ne faut donc pas déclarer toutes les puces identiques sur toutes les références trouvées.

Attention à une erreur d'unité dans le texte de Lafois : il indique « 1GB » pour les mémoires. Le catalogue Micron donne **1 Gbit**, soit **128 Mio**, pour la famille MT47H64M16NF ; ne pas reprendre 1 Go comme capacité de RAM.

Sources visuelles examinées, copies conservées dans `donnees/references-cartes-2026-11-17/` avec URLs et SHA-256 dans le manifeste :

- [Lafois : face processeur](https://www.lafois.com/wp-content/uploads/2020/10/image-1-768x1024.png), [verso NAND/radio](https://www.lafois.com/wp-content/uploads/2020/10/image-2-768x1024.png), [repères JTAG/UART](https://www.lafois.com/wp-content/uploads/2020/10/jtag_usb-1-917x1024.png).
- [Maasland : face processeur du Connexoon](https://blog.unauthorizedaccess.nl/assets/img/somfy/995baae1-1476-44dc-aa3d-dc1ffcbcc7fe.jpg).
- [Microchip : KSZ8081](https://www.microchip.com/en-us/product/ksz8081), [Micron : catalogue DDR2](https://in.micron.com/products/memory/dram-components/ddr2-sdram/part-catalog).

## Travaux utiles

1. **Benjamin Lafois, Cozytouch/Kizbox Mini (2020–2021).** Analyse de carte, processeur AT91SAM9G25, NAND, points UART/JTAG, extraction et modification du firmware, puis accès root SSH. Sur son firmware, la console série initiale ne donne pas de shell. La partie 4 rapporte la perte ultérieure du root ; l'explication par un contrôle d'intégrité reste une hypothèse de l'auteur. [Partie 1](https://www.lafois.com/2020/11/07/rooting-the-cozytouch-aka-kizbox-mini-part-1/) · [Partie 4](https://www.lafois.com/2020/12/12/rooting-the-cozytouch-aka-kizbox-mini-part-4/).
2. **Services internes Cozytouch.** La partie 5 décrit D-Bus, LuaJIT et une API REST locale désactivée. L'auteur modifie le bytecode d'authentification. Dans une réponse du 20 mai 2024, il indique ne plus utiliser cette installation et fournit un client D-Bus vers MQTT, avec décodage de températures pour son AquaCozy. Ce résultat ne valide pas les commandes des appareils de <PERSONNE>. [Partie 5 et commentaires](https://www.lafois.com/2020/12/20/rooting-the-cozytouch-aka-kizbox-mini-part-5/).
3. **Donny Maasland, Connexoon (2021, compléments 2022).** Sur une plateforme apparentée, accès au mode de récupération SAM-BA, extraction NAND, modification du système et activation de l'API locale. Un jeton peut être généré via D-Bus. Cette approche d'authentification est à étudier avant tout contournement. Sa transposition au Cozytouch reste non vérifiée. [Article](https://blog.unauthorizedaccess.nl/2021/04/07/no-clouds-just-sunshine.html).
4. **Aldohrs/tahoma-jailbreak.** Documentation de l'architecture, du démarrage, des partitions et des services ; cible principale TaHoma v2, similitudes Cozytouch explicitement annoncées. [Dépôt](https://github.com/Aldohrs/tahoma-jailbreak).
5. **Radio io-homecontrol.** [Velocet/iown-homecontrol](https://github.com/Velocet/iown-homecontrol) documente le protocole et des travaux firmware. Les bibliothèques 1W/2W restent indiquées en développement. [rspaargaren/iohomecontrol](https://github.com/rspaargaren/iohomecontrol) fournit une implémentation ESP32/SX1276 orientée stores ; son auteur avertit que ses modifications ont rendu la partie 2W instable. Ces projets ne prouvent pas la compatibilité avec le chauffe-eau et le sèche-serviettes concernés.

## Orientation proposée

Le dessin de carte et les composants principaux des deux faces étant identifiés, examiner la sortie UART, puis étudier l'extraction et la sauvegarde du firmware avant toute écriture. L'objectif de recherche serait de réutiliser les services et la radio existants. La reconstruction d'une passerelle radio est une autre piste, plus éloignée du besoin immédiat. La ressemblance matérielle ne prouve ni l'accès JTAG/UART effectif, ni la compatibilité des commandes et images de firmware publiées.

## Essai UART — résultat vérifié

<PERSONNE> déclare le câblage suivant : GND LA1010 vers GND du bridge, CH0 vers RX du bridge, CH1 vers TX du bridge. Selon le repérage Lafois, face processeur avec LED en haut et antenne en bas, les trois trous entre CPU et transformateur Ethernet sont, de gauche à droite : TX, RX, GND carré. Ce repérage reste documentaire ; aucune mesure de continuité ou de tension n'a été rapportée.

HP `<CHEMIN_LOCAL>` joint par SSH ; LA1010 détecté et acquisition passive réussie avec l'installation existante `<CHEMIN_LOCAL>` (sigrok-cli 0.8.0-git-f44dd91). Une capture de contrôle de 100 ms voit les deux lignes basses. Une tentative de capture déclenchée révèle que ce modèle sans mémoire n'offre pas de déclenchement matériel dans ce pilote. Une capture continue de cinq minutes est donc lancée à 2 MHz, seuil numérique 1,4 V, deux canaux. Le seuil n'est pas une mesure de tension. Premier décodage prévu : CH1, 115200 bauds, 8N1 ; paramètres à confirmer par les données.

Preuves HP : `<CHEMIN_LOCAL>`. `idle.sr` = contrôle ; `boot-01.sr` = essai de déclenchement non validé ; `boot-02.sr` = fenêtre continue pour le démarrage manuel demandé à <PERSONNE>. Aucun générateur PWM ni émission UART utilisés. Les résultats de cette capture sont consignés ci-dessous.

Résultat après l'allumage signalé par <PERSONNE> : capture terminée proprement, **300,429312 s** à 2 MHz. Allumage vers **173,052 s** de l'enregistrement. CH0 présente une seule transition vers l'état haut et y reste ; CH1 présente **575 transitions**. Décodage **115200 bauds, 8N1**, non inversé, sur CH1 : **89 octets** lisibles.

```text
RomBOOT
Test DDRAM,BAAD=OK,DQSDM=OK:[passed]
Version NandFlash,SV=5065599B01:[passed]
```

La sortie UART est donc démontrée sur CH1. Aucune invite de commande n'a été reçue dans cette capture ; aucune émission vers RX n'a été tentée. Les mentions `[passed]` sont les messages du démarrage, pas une validation exhaustive des mémoires ou du fonctionnement applicatif. La chaîne `SV=5065599B01` ne suffit pas à identifier la version complète du firmware.

Copie locale : `donnees/uart-2026-11-17/`, capture `.sr`, statistiques, journal et texte décodé. SHA-256 de `boot-02.sr` identique sur HP et Windows : `c7d7c01eb0762d688323c9c3b7775d19dfa2de390c796a8476f4ad1fe3f7ccb4`. Suite possible : étudier une lecture JTAG et une sauvegarde adaptée ; cet essai n'autorise ni ne réalise de flash.

La documentation actuelle [Home Assistant Overkiz](https://www.home-assistant.io/integrations/overkiz/) ne liste pas Atlantic Cozytouch parmi les passerelles à API locale prise en charge. Cela ne démontre pas l'absence de composants locaux cachés dans le firmware.

La lecture autorisée d'Inbox et de la fiche PKM Home Assistant n'a révélé aucune tâche correspondant aux termes Cozytouch, Atlantic, chauffe-eau ou serviette. La fiche conserve l'étude du 6 avril comme historique, sans réalisation démontrée. Suite proposée, non ajoutée à Inbox : identifier la carte et établir une méthode de sauvegarde adaptée.

## Sauvegarde NAND — résultat vérifié le 17 novembre 2026

<PERSONNE> a ensuite autorisé le JTAG avec le Raspberry Pi Model B `<CHEMIN_LOCAL>`, puis la poursuite autonome jusqu'à la sauvegarde. VTREF mesuré à 3,3 V ; TMS sur la broche physique 24 du Pi. Le second scan identifie le TAP 0x0792603f. La NAND est acquise intégralement : **65536 pages, 128 Mio de données et 4 Mio d'OOB**, sans saut de blocs.

Chaque lot transféré est contrôlé par CRC calculé sur le bridge. Les transferts incorrects sont rejetés et relus. Une seconde lecture complète recalcule un SHA-256 sur le bridge pour chacun des 64 lots : toutes les empreintes concordent avec l'image sauvegardée. Aucun second fichier brut n'est synthétisé. SHA-256 de l'image brute de référence : `ce0be49873209b6d1565403c8292e376c466bc8d89fc000bd7afb5f452578d8e`.

Fichiers et vérifications (non publié), archive complète (non publié), [méthode et incidents](jtag/ACQUISITION.md). Copies Windows et HP vérifiées ; HP : `<CHEMIN_LOCAL>`. Sources conservées sur le Pi. Aucune commande d'effacement ou de programmation NAND. OpenOCD arrêté, GPIO JTAG en entrée ; la RAM du bridge ayant servi à l'acquisition, un redémarrage électrique est nécessaire pour reprendre son fonctionnement normal. La flash interne STM32 et une restauration sur matériel ne sont pas couvertes par cette sauvegarde.

> Les empreintes historiques des fichiers expurgés se rapportent aux originaux privés.
