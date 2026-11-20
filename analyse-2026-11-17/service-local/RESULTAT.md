# Service MQTT local, sondes Calypso et Linux alternatif

État vérifié le 17 novembre 2026, contrôle final à 21 h 55 CET. **Le prototype MQTT a lu les deux appareils avec le daemon constructeur arrêté, après reset normal du STM32 et sous blocage Internet.** Il reste un programme d'essai borné en RAM, pas un service installé au démarrage. Le Linux n'a pas redémarré. La radio constructeur et son réseau sont rétablis ; SSH principal reste en RAM.

## Résultats et preuves

| Essai | Résultat | Limite |
|---|---|---|
| Tâche Inbox « Valider une lecture d’état locale des appareils Cozytouch sans cloud » | Cochée avec accord explicite, écriture serveur vérifiée | Ne clôt pas le développement du service durable |
| Reset normal du STM32 sous blocage IPv4/IPv6 | CETHI en 93 ms, IC3 en 111 ms, deux DONE ; aucun SET KEY/ADDRESS préalable dans cet essai | Linux et stockage sauvegardé conservés ; pas une coupure complète du hub |
| Service MQTT après un nouveau reset STM32 | 6 lectures, 3 cycles, 12 PUBACK, environ 94 s | Deux paramètres principaux bruts ; aucun ordre de chauffe |
| Broker arrêté pendant 5 s | Reconnexion, deux derniers états republiés avec leur date originale, puis lectures poursuivies | Test court ; pas une qualification de disponibilité longue durée |
| Réception et rétention | Subscriber indépendant : 8 états, dont 6 lectures et 2 republications ; nouveau subscriber : 3 topics retained, disponibilité finale offline | Réception Home Assistant non testée |
| Retour au fonctionnement OEM | Deux READ natifs réussis ; PID 12567, TracerPid 0, UART normal ; règles IPv4/IPv6 identiques | Updater neutralisé dans l'environnement RAM du processus ; ne persiste pas au reboot |

Preuves principales : MQTT vérifié (non publié), exécution complète (non publié), reset STM32 (non publié), santé après essai (non publié), fermeture du laboratoire (non publié), clôture Inbox (non publié).

Le blocage réseau autorisait seulement loopback et les connexions SSH administratives exactes. Le port direct du broker sur le HP n'était pas joignable depuis le hub, malgré le ping ; la cause n'est pas établie. Le test MQTT a donc utilisé deux tunnels SSH temporaires LAN et un port loopback. Cela valide le protocole et la reprise, mais pas encore le chemin direct hub→broker à déployer. Les tunnels, le serveur SSH supplémentaire et les processus MQTT de laboratoire sont arrêtés. Le SSH principal est conservé. Paquets et journaux HP sont conservés dans une archive privée locale, sans installation système.

## Prototype réalisé

Sources et procédure : mqtt/README.md (non publié). Les sept modules Lua ont été déployés avec vérification des empreintes. Selftests codec UART, MQTT, fragmentation, acquittements, file bornée, cadence et configuration exécutés sur LuaJIT du hub ; ABI contrôlée avant accès UART. Le coordinateur a effectué les tests réseau et radio, puis vérifié les publications côté broker. Une revue indépendante a examiné la durée, la cadence et les publications après reconnexion.

Le service possède seul l'UART. Il attend au moins 30 s après une paire de lectures avant la paire suivante et conserve une marge de 17 s avant de démarrer un cycle. Sa durée maximale reste 120 s. La reconnexion MQTT utilise des délais de 1 à 16 s et une file bornée contenant les derniers états. Les messages QoS1 conservés portent la date de lecture ; un état ancien n'est pas redaté lors d'une republication. Le LWT offline a été observé dans l'essai réseau préalable.

Les états MQTT du paramètre principal sont explicitement **bruts, pas des températures**. Aucun SUBSCRIBE, topic de commande, setter, découverte Home Assistant ou accès cloud n'a été ajouté. Le prototype s'arrête sur erreur/reset UART ; une reprise radio continue n'est pas encore implémentée. Le README de l'agent décrit le scénario initial STM32 déjà initialisé : la preuve matérielle supplémentaire de reset appartient à ce rapport et aux journaux du coordinateur.

## Trois sondes Calypso

Chaque lecture native GenericV2 a été accompagnée d'une observation UART logicielle bornée, via ptrace sur le descripteur série existant ; ce n'est pas une acquisition électrique LA1010. Le processus a été détaché et contrôlé après chaque capture. Chaque demande 0x0101 a reçu un 0x040c corrélé : index, adresses et CRC vérifiés.

| Sonde | Index | Charge utile brute | Température candidate |
|---|---|---|---|
| Air entrant | 0x001a | `00d8ffec017f` | 21,6 °C |
| Évaporateur bas | 0x001b | `00d8ff840248` | 21,6 °C |
| Évaporateur haut | 0x001c | `00d9ff6e0271` | 21,7 °C |

Le callback de fin vide avec codes 0/0 ne signifie pas un refus : GenericV2 transmet sa donnée séparément. Le convertisseur OEM d'une sonde d'eau voisine lit un entier signé big-endian sur deux octets, puis divise par dix. L'appliquer au premier mot donne les températures candidates ci-dessus. **Le catalogue ne lie pas explicitement ces trois registres à ce convertisseur.** Les quatre octets restants ne sont pas étiquetés minimum, maximum ou drapeaux. Les sondes ne sont pas encore intégrées au service MQTT autonome. [Analyse et preuves natives](sondes-conversion/RESULTAT.md).

## Reboot et OTA : ce qui manque pour un service durable

Sur Linux OEM, un lanceur de boot persistant devra charger la configuration privée, réserver l'UART, initialiser le STM32, démarrer le service, superviser ses délais et éviter toute concurrence avec le daemon OEM. La récupération après panne devra distinguer broker absent, appareil radio absent et STM32 arrêté. La fraîcheur des états et le watchdog devront participer au diagnostic. Le reset testé réduit le risque d'une dépendance au cloud, mais ne prouve pas ce chemin complet.

Une OTA OEM peut remplacer la banque système, les scripts ou les interfaces ; les chemins actuels d'accès développeur/authorized_keys ne sont pas couverts par une garantie générale de conservation. Une installation persistante sous OEM **ne pourra donc pas être promise robuste aux OTA sans essais et contrôle de compatibilité**. La neutralisation RAM actuelle d'un updater ne constitue pas une stratégie permanente.

Avec notre Linux, nous maîtriserions le démarrage et les mises à jour : configuration séparée, image vérifiée, validation de santé et retour à la version précédente. C'est une architecture proposée, non réalisée. **Une banque OEM + une banque personnalisée ne donne pas deux banques personnalisées A/B.** Elle conserve un secours OEM pour apprendre, mais ce secours n'offrira pas nécessairement notre API locale. Deux banques personnalisées ne viendraient qu'après qualification d'une récupération externe, ou après étude réelle d'un autre plan de volumes. Les 278 blocs issus d'un calcul de réservations ne prouvent pas un espace UBI disponible utilisable.

## Avis issu des analyses parallèles Linux

Trois agents ont travaillé séparément sur le boot/NAND et les sondes, le userland/dépendances/OTA, et le service MQTT. Le coordinateur a vérifié les résultats matériels et confronté les conclusions de persistance.

- [Boot, NAND et récupération](linux-boot/RESULTAT.md) : ARM926 ARMv5TEJ, 128 Mio RAM et NAND ; le boot réel passe par un Linux kboot puis kexec. La carte possède une description dans Linux amont. Les images corrigées ECC de kboot et sa copie concordent ; CRC UBI et gzip contrôlés. Les scripts OEM de stockage contiennent des chemins de formatage à ne pas réemployer aveuglément. La restauration physique de NAND n'est pas qualifiée.
- [Userland et blobs](linux-userland/RESULTAT.md) : audit de 274 ELF, EABI5 soft-float et glibc 2.35. La fermeture ELF de LuaJIT livré tient dans 6 fichiers, 2,65 Mo, hors client/configuration/modules additionnels. Reprendre le daemon exige au moins 17 ELF, 10,91 Mo, plus 1,51 Mo de bytecode et les dépendances Lua/D-Bus/stockage. Ce calcul statique ne prouve pas un rootfs exécutable.
- **Première voie conseillée : Buildroot minimal en initramfs, chargé en RAM via la voie JTAG connue, STM32 et firmware radio conservés.** Premier essai avec pilote MTD désactivé, PID1 maîtrisé, UART/GPIO et watchdog qualifiés, blocage réseau avant ouverture de l'interface. Réemployer temporairement le runtime livré facilite l'étape ; recompiler ensuite permet de réduire les dépendances.
- OpenWrt demande davantage d'adaptation : pas de profil exact retrouvé dans la version examinée, recettes boot et géométrie UBI à corriger. Le système utilise des LEB de 124 Kio. Aucune image alternative n'a été construite ou démarrée pendant cette première analyse.

Pour prouver une coupure complète sans Internet, il faut une barrière réseau indépendante du système OEM : ses premières étapes de boot précèdent nos règles RAM. Un futur essai RAM avec notre PID1 doit aussi prévoir récupération SSH/JTAG et budget mémoire. Ne pas redémarrer le hub actuel en supposant que SSH ou MQTT reviendront.

Décision utilisateur conservée : AquaMQTT, ESP32 et ESPHome écartés du chantier courant. Les pistes actives sont service local Linux+STM32 et apprentissage d'un Linux maîtrisé.

## Incidents, conservation et suite

Deux préparations du reset ont échoué avant toute action GPIO : fins de ligne CRLF dans un script encodé, puis PATH sans `/usr/sbin`. Elles ont été corrigées et la radio rétablie avant l'essai cold02 concluant. Une erreur de validation de configuration MQTT a été corrigée avant UART ; le port direct HP inaccessible a conduit aux tunnels documentés. Aucun de ces essais préparatoires n'est compté comme une réussite.

Le service de laboratoire est terminé, le constructeur a repris la radio et aucun ordre de chauffe, association, effacement ou programmation Flash n'a été envoyé. Les écritures ordinaires de l'OS ne sont pas assimilées à une image NAND figée. Les captures privées contiennent des identifiants et contextes de clé : ne pas publier leur archive.

Suite technique : construire et vérifier hors ligne l'initramfs minimal, intégrer la lecture GenericV2 sans inventer la sémantique des sondes, puis qualifier séparément le boot complet, la reprise durable et l'OTA. La tâche historique de lecture sans cloud est close ; ces suites restent distinctes. Archivage et copie HP : `manifest-final.json` et `hp-backup-receipt.json` une fois produits.

> Les empreintes historiques des fichiers expurgés se rapportent aux originaux privés.
