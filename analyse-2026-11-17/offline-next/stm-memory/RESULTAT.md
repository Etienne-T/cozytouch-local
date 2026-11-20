# Lectures applicatives STM32 et limites du transport natif

Analyse hors ligne du 17 novembre 2026. **Les commandes applicatives qualifiées lisent 43 octets personnalisés, mais aucune primitive de sauvegarde complète sans quitter l'application n'est établie.** Le firmware livré et le firmware exécuté annoncent v2.4.2. Cette annonce et le MD5 applicatif ne vérifient pas le bootloader installé ni toute sa flash.

**Le client D-Bus reste impropre à une collecte autonome.** Le coordinateur a observé des réponses UART valides, puis des délais internes et des redémarrages automatiques de la carte radio. La conservation du PID et de SSH ne prouve pas la santé de la pile radio. Ne pas relancer les GET avec ce client avant qualification de l'achèvement des commandes. Les branches STM32 GET évitent l'écriture directe de flash ; le transport Linux peut toutefois déclencher une récupération après expiration.

Cet agent a uniquement lu et créé des fichiers locaux. Aucun accès réseau, UART ou appareil. Les anciens scripts et preuves restent inchangés. Le coordinateur est seul opérateur matériel. Le présent dossier réutilise l'export Ghidra existant et ajoute des vérifications binaires indépendantes avec Capstone.

## Requêtes et sources exactes

Le blob OUTPUT_RAW natif a la forme `[groupe,commande,0,0,donnée]`. Son convertisseur `output-raw.c`, Ghidra `0x00142d98`, copie seulement les octets à partir de l'offset 4 vers la trame STM32. Les deux zéros centraux ne sont pas des octets de données STM32.

| Lecture | Requête STM32 / donnée | Blob OUTPUT_RAW | Réponse / octets | Source et preuve |
|---|---|---|---|---|
| Logiciel | `0500 / 00` | `05 00 00 00 00` | `0500 / 7` | `08022c04` : type 0 puis chaîne compilée `v2.4.2`. |
| Matériel | `0500 / 01` | `05 00 00 00 01` | `0500 / 4` | Même fonction : `01 00 00 02`, constante compilée. |
| Bloc de pile | `0500 / 02` | Non inclus dans le client | `0500 / 2` | Même fonction : `02 03`, constante compilée. Aucun identifiant MCU unique. |
| MD5 | `0504 / 00` | `05 04 00 00 00` | `0517 / 16` | `08022da0` → `0802ba50` : cache RAM `20004b39`, calculé au démarrage. Le handler ignore la donnée. |
| Production | `0505 / 01` | `05 05 00 00 01` | `0505 / 13` | `08022db8` → `0802b744`, flash `08002100..0800210c`. |
| Calibration | `0506 / 01` | `05 06 00 00 01` | `0506 / 20` | `08022dec` : 16 octets de `08002004..08002013`, puis 4 octets de `08002000..08002003`. |
| Série | `050c / 01` | `05 0c 00 00 01` | `050c / 10` | `08022e54` → `0802b95c`, flash `08002200..08002209`, copie via cache RAM. |

Pour production/calibration/série, le premier octet **01** saute les appels d'écriture. Le premier octet **00** déclenche respectivement `0802b734`, `0802b7b8` et `0802b988`. Ces écritures ne figurent pas dans l'allowlist du client. Toute valeur différente de 0/1 atteint `0802d4fc(0,...)` : journalisation, désactivation IRQ, `SYSRESETREQ`, puis boucle. Ce n'est pas un simple avertissement.

Le MD5 porte sur `[08003000,0803fff0)`, soit **249 840 octets**. Son résultat dans l'image vaut `438a7250b32c5dddc694b48ada6d08f8`, identique aux 16 octets du pied. SHA-256 de cette plage : `bb53929ddf5d0825062572d136e42aac59bca241ec9ed986372f17f9eff1dcb7`. Cette plage exclut le bootloader, le secteur personnalisé et les vecteurs applicatifs `08002800..08002fff`.

## Périmètre de la recherche de lecture arbitraire

Les cinq tables de distribution ont été relues dans les octets du binaire, entrées 0 à 20 : **24 handlers** non nuls, répartis 4/7/4/0/9. Ils concordent avec les enums Linux. La table du groupe 4 est vide. Les gestionnaires sont conservés dans `application-handlers.c`.

| Groupe | Routes examinées | Résultat utile pour une sauvegarde MCU |
|---|---|---|
| 1 | Mouvement, information générale, ajout/retrait de balise | Commandes io-homecontrol. Les services de lecture/écriture de données sont des opérations de protocole ; aucune traduction vers une adresse physique STM32 n'est qualifiée. |
| 2 | Découverte, RCM, transfert, effacement base, validation/envoi 1W | Aucun lecteur flash générique. Plusieurs opérations changent l'état radio ou d'association. |
| 3 | Souscription, requête, commun, liste capteurs | Les trois premières routent des services radio. La liste copie une liste interne d'adresses de capteurs de taille `nombre*3`, sans adresse mémoire fournie par l'hôte. |
| 5 | Révision, adresse/clé maître, polling, MD5, production, calibration, transmission forcée, redémarrage, série | Seuls les champs ciblés ci-dessus concernent directement les données de flash. MD5 est un cache. Les autres commandes ne fournissent pas une primitive adresse+longueur. |

Un balayage des demi-mots applicatifs ne trouve aucun candidat `BL`, `BLX` immédiat ou `B.W` vers le bootloader `08000000..08001fff`. Une recherche de constantes 32 bits, même non alignées, ne trouve aucun pointeur applicatif vers le lecteur bootloader `080002c8/080002c9` ou son dispatcher `080003cc/080003cd`. **Ce résultat borné ne couvre pas tous les appels indirects.** Il n'existe pas de route applicative vérifiée permettant d'appeler directement le lecteur du bootloader.

Le dispatcher `08021c98` ne borne pas visiblement l'index de commande. Un indice hors table pourrait appeler du code arbitraire ou provoquer une faute. Ce constat n'établit aucune commande de lecture utilisable et ne justifie aucun essai malformé. Aucun fuzzing ni détournement du flot n'a été préparé.

## Diagnostics et adresse synthétique

`0508` (compteur de transmissions forcées), `0509` (information bas niveau) et `050e` (cause reset) sont des **callbacks** des enums Linux. Les emplacements correspondants dans la table de commandes sont nuls. Aucun GET direct de ces diagnostics n'est établi.

- `08003948` produit `0508`, 4 octets, lors d'une transmission forcée.
- `08003aa0` produit `050e`, 1 octet, lors de l'initialisation de pile.
- Linux conserve la cause reset sous `STACK_HARD_RESET_CAUSE=2146435078`. `_numberOfHardReset` compte les reprises demandées par Linux dans `DaughterBoardManager` et apparaît dans ses journaux. Ce n'est pas un compteur matériel cumulatif.
- Les caches connus comprennent logiciel `2146435073`, série `1877999618`, calibration `1877999616`, état de calibration `1877999620`. Leur fraîcheur dépend de l'initialisation ou de la dernière réponse.

`GetStackDataProcessor` cherche une commande interne à `stackAddressRange.Low-1`, soit **65535**, tandis que les adresses de nœuds réels commencent à 65536. Il marque DONE seulement si le **tracker Lua** possède une commande en cours à cette adresse. Une commande ajoutée directement au gestionnaire natif par D-Bus ne crée pas forcément cette promesse Lua. **Changer seulement l'adresse vers 65535 ne qualifie donc pas le transport.** `MD5Processor` consomme `0517` sans marquer la commande native DONE. Production `0505` n'a pas d'entrée dans la table de processeurs Lua examinée. La réponse peut passer au C++ sans satisfaire l'attente de la commande brute.

Le coordinateur a rapporté des `InternalTimeout` dès la première lecture de version antérieure à cette collecte. Les GET matériel, MD5 et production ont répondu sur UART ; calibration n'a produit aucun échange pendant la capture bornée de 5 secondes. Les causes et la restauration opérationnelle doivent être établies dans le rapport du coordinateur. Ce dossier n'attribue pas à production seule un incident commencé auparavant.

## Annulation ciblée et reprise

Le membre D-Bus exact est **`cancel`**, même service/objet/interface que `add`, signature **`s`** : l'identifiant exact du groupe, sans struct. Le dispatcher `Manager::method` Ghidra `000f078c` et le littéral à `0021eb14` le prouvent. `cancelByGroupHandler`, `000ef708`, désérialise une chaîne ; `CommandManager::cancel`, `001129f4`, compare cette chaîne à `Group::getId()` par `strcmp`. Il traite uniquement les associations correspondantes et appelle aussi `cancelTimedCommands` pour ce groupe. Une commande interne née d'une récupération peut appartenir à un autre groupe.

`cancel-own-production.lua` n'accepte que l'unique groupe extrait des callbacks privés de notre requête production. `prepare_cancel.py` vérifie `READ=true`, paramètre 42 et blob `05 05 00 00 01` avant de générer l'allowlist. Aucun groupe privé n'est reproduit ici. Un acquittement de l'annulation ne prouve pas la réparation d'un tracker Lua déjà incohérent.

Une relance du daemon peut réinitialiser les files et trackers. Elle réexécute aussi l'initialisation normale du module : adresse/clé maître et lectures calibration/série. La configuration Lua lit directement `IO_UPDATE_SCRIPT` depuis l'environnement. Une récupération en RAM peut donc remplacer cette variable par `/bin/false`, **après** chargement de la configuration originale, pour bloquer la programmation automatique par ce chemin. Cette préparation n'a pas été exécutée par cet agent ; le coordinateur vérifie le script vivant et la reprise.

## Artefacts et limites

- `native-stm32-read.lua` est gelé, SHA-256 `b22b3d14add5a73221442b90f9c2c529f0835c39ea345ff5caa50df7dd4515fe`. Le transport et l'attente de 20 secondes sont hérités du client antérieur. **Qualification opérationnelle échouée**, malgré les payloads GET bornés.
- `client.diff` et `client-validation.json` documentent les seules différences avec le client source. Les gardes Python hors ligne passent. Le coordinateur a rapporté la compilation Lua sur le hub.
- `cancel-own-production.lua` : SHA-256 `9deae9563e2e725a7d6bd5ba2548ca77ce9512267156359bba67e775e040b9eb`. Aucun envoi par cet agent.
- `memory-evidence.json`, `memory-machine-evidence.asm`, `application-handlers.c`, `memory-functions.c` et `queue-functions.c` conservent les preuves. La décompilation Linux utilise la base Ghidra `VA ELF+0x10000`.

L'image distribuée complète possède le SHA-256 `c9346388a534b588438112f65692a166e89f51c7c8656f0b0ccd4a8adddb97f5`. Son secteur `08002000..080027ff` est entièrement FF. Les 43 octets personnalisés accessibles ne reconstituent pas les 2 Kio de ce secteur, encore moins les 256 Kio du composant. Le lecteur arbitraire appartient au bootloader fabricant ; ses conditions d'entrée et de protection font l'objet de l'analyse séparée du coordinateur. Les scripts Linux relient PWR/TEST/BOOT0/BOOT1. Aucun câblage SWD entre GPIO Linux et STM32 n'est établi par les fichiers examinés.

> Les empreintes historiques des fichiers expurgés se rapportent aux originaux privés.
