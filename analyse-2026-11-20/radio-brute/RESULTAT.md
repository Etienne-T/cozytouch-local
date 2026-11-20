# Radio brute sur le STM32 d'origine : étude statique

Étude du 20 novembre 2026, hors ligne. Aucun accès au hub, aucun port série, aucune émission et aucune écriture matérielle. Le firmware n'a pas été exécuté. Les fichiers déjà présents n'ont pas été modifiés. Aucune valeur de calibration, de clé ou de numéro de série n'est reproduite.

**Verdict.** Ajouter une commande UART qui emprunte le Si4461 puis le rend à la pile io-homecontrol est faisable dans cette image, sans toucher au bootloader ni au secteur `0x08002000..0x080027ff`. La place en flash suffit. Le créneau `0x0400` est libre. La suspension propre et le retour io sont un ajout : aucune commande actuelle ne le fait. Le correctif doit recalculer le MD5, rester court devant le watchdog, et ne pas passer par le script de mise à jour constructeur tel qu'il est. Le fonctionnement radio, la broche de mode et le résultat réel de l'effacement large restent à vérifier sur le matériel, ce qui n'est pas fait ici.

## Périmètre et méthode

L'image lue est le fichier distribué `io-homecontrol-boot-stm32-MRIO_v1-v2.4.2.bin`, 262 144 octets, SHA-256 `c9346388a534b588438112f65692a166e89f51c7c8656f0b0ccd4a8adddb97f5`. Le script analyse_static.py (non publié) a revérifié que le fichier application en est le suffixe à l'offset `0x2800`, et que le MD5 de `[0x08003000, 0x0803fff0)` est égal au pied `0x0803fff0`. Le secteur `0x08002000..0x080027ff` de cette image distribuée est entièrement `FF`. Il n'a pas été affiché.

Le 17 novembre 2026, la comparaison au dump réel avait déjà montré que le bootloader `0x08000000..0x08001fff` et l'application `0x08002800..0x0803ffff` sont identiques à cette image, avec 48 octets différents seulement dans le secteur de carte. Cette identité est un fait de cette date. Elle n'a pas été remesurée le 20 novembre. Les décompilations de `analyse-2026-11-17/stm32/all-functions.c` s'appliquent donc au code, pas à la SRAM ni à l'exécution.

Les mesures brutes sont dans mesures.json (non publié). Les lectures ciblées (effacement, GPIO, modèle PA) viennent de complement.py (non publié). Le projet Ghidra n'a pas été rouvert.

## 1. Ressources libres

### Flash

Le STM32F101RCT6 a 256 Kio de flash, pages de 2 Kio. Dans l'image :

| Zone | Contenu vérifié |
|---|---|
| `0x08000000..0x08001fff` | Bootloader. À laisser intact. |
| `0x08002000..0x080027ff` | Secteur de carte. `FF` dans l'image distribuée. À laisser intact. |
| `0x08002800` | Vecteurs d'application. MSP initial `0x2000190c`, reset `0x080030a9`. |
| Dernier octet différent de `FF` avant le pied | `0x08035a5b` |
| `0x08036000..0x0803f7ff` | 19 pages entièrement `FF`, soit **38 912 octets** |
| `0x0803f800..0x0803ffff` | Une page dont 16 octets seulement diffèrent de `FF` : le pied MD5 |

La page des tables de commandes, `0x08034800`, contient 2 047 octets différents de `FF`. Une case nulle y vaut `0x00000000`. Programmer un pointeur à la place exige d'effacer cette page, puis de la réécrire. Les 19 pages vides, elles, sont déjà effacées : on peut y programmer le code ajouté en ne faisant passer des bits que de 1 à 0.

Le code ajouté tient largement dans ces 38 Kio. Une machine d'emprunt de quelques kilo-octets laisse de la marge. Il ne faut pas le placer dans la dernière page : un MD5 faux l'efface au démarrage, voir la section 4.

### SRAM et pile

Le reset applicatif `0x080030a8` utilise le pool `0x08003120` :

| Étape | Plage | Taille |
|---|---|---|
| Copie de `.data` depuis `0x080359c4` | `0x20000000..0x20000098` | 152 octets |
| Remplissage `0xDEADBEEF` | `0x20000098..0x2000190c` | 6 260 octets |
| Mise à zéro | `0x2000190c..0x20005e84` | 17 784 octets |

Le pointeur de pile initial est `0x2000190c`. La pile descend dans la zone empoisonnée, donc au plus environ **6,1 Kio** avant d'atteindre `.data`. La zone mise à zéro contient déjà l'objet radio à `0x2000486c`. Au-dessus de `0x20005e84`, le code référence encore la SRAM, jusqu'à des littéraux dont le plus haut est `0x20007be3` (23 adresses distinctes, certaines non alignées). La table de clés déjà située à `0x20005e8c` est dans cette zone haute. Aucun bloc libre de plusieurs kilo-octets n'est démontré au-delà de la BSS.

Fait établi : la pile d'environ 6 Kio peut porter un état court et un tampon de FIFO de 64 octets. Hypothèse : les adresses hautes éparses sont des bornes d'allocateur, pas du vide utilisable. Un correctif ne doit ni réinitialiser toute la SRAM, ni recouvrir la table de clés.

## 2. Point d'entrée UART

`0x08021c98` reçoit le groupe et l'octet de commande. Si `groupe - 1` est inférieur à 5, il lit le mot `table[groupe][commande]`. La racine des cinq tables est `0x0803485c`, lue via le littéral `0x08021cd0`. Chaque table occupe 21 mots, soit les index 0 à 20. Il n'y a pas de test de borne sur l'index : un octet supérieur à 20 lit la table voisine.

Les 24 commandes déjà décrites occupent exactement les cases non nulles. Le groupe 4, table `0x080349cc`, est entièrement nul. Si le groupe dépasse 5, le code journalise, met le registre de base à 0, puis charge le mot à l'adresse `commande << 2`. S'il n'est pas nul, il l'appelle. Comme l'adresse 0 miroir la flash au démarrage depuis le bootloader, cet index vise la table de vecteurs. Ce n'est pas un rejet. Une commande ajoutée reste donc dans les groupes 1 à 5 et dans les index 0 à 20.

Les réponses asynchrones du groupe 4 occupent déjà certains numéros, d'après `DaughterboardApiCallback.lua` : `0x0401`, `0x0403`, `0x0405`, `0x040a` à `0x0411`, `0x0414`. L'index `0x16` (`0x0416`) est hors de la table de 21 cases.

Cases du groupe 4 qui ne sont ni une commande entrante ni un de ces retours : **`0x0400`, `0x0402`, `0x0404`, `0x0406`, `0x0407`, `0x0408`, `0x0409`, `0x0412`, `0x0413`.**

Le meilleur accrochage est un seul mot : **`0x080349cc` = commande `0x0400`**, aujourd'hui nul, sans homonyme dans l'énumération des retours. Les sous-commandes tiennent dans la charge utile. Les 24 commandes actuelles restent à leurs adresses. Il faut réécrire la page `0x08034800` en conservant tous les autres mots, puis recalculer le MD5.

## 3. Suspendre la pile io, prêter la radio, la rendre

### Ce que la pile fait aujourd'hui

La tâche `0x08003280` tourne en boucle. Un bit d'événement appelle `0x08023188`, qui remet la trame au répartiteur. D'autres bits appellent les machines `0x08003c64` et suivantes, selon un état 0 à 11. Le bit périodique réarme le watchdog puis compte jusqu'à 60 avant d'appeler `0x08004624`, qui est vide.

L'objet radio est construit par `0x080284c0` à l'adresse SRAM `0x2000486c`. Si l'octet `+0x0d` vaut déjà 1, ce constructeur ne refait que la copie de 9 octets de fréquence et retourne. L'initialisation réelle est `0x08027620`, qui charge les trois fractions et appelle toujours `0x080272bc`.

`0x080272bc` pulse la broche SDN, attend, envoie `POWER_UP` (quartz 26 MHz, bloc `0x08035629`), puis une série de `SET_PROPERTY`, et termine par les appels de port logique 2 `0x0802cfd8` et `0x0802cf58`. `0x08026d64` attend CTS avec `READ_CMD_BUFF` (`0x44`). Le choix de canal `0x08026f10` n'accepte qu'un index 0, 1 ou 2 et écrit la fraction correspondante par `SET_PROPERTY` groupe `0x40`.

Les émissions et réceptions io passent par `START_TX` (`0x31`) dans `0x08027924` / `0x08027814` et `START_RX` (`0x32`) dans `0x080277d8` / `0x08027e10`. Les octets radio directs sortent sur USART3, port logique 2, via `0x08028d20`. SPI1 ne porte que les commandes.

### Commandes actuelles, et ce qu'elles ne font pas

| Commande | Handler | Fait établi |
|---|---|---|
| `FORCE_TRANSMISSION` `0x0507` | `0x08022ea8` | Écrit un demi-mot à l'offset `0x3d8` de l'objet de pile. `0x08003948` s'en sert pour compter certaines trames et émettre le retour `0x0508`. Ce n'est pas un accès SPI. |
| `RADIO_LOW_LEVEL_INFORMATION` `0x0509` | Aucun handler entrant | Nom de retour Linux. La case d'index 9 du groupe 5 est nulle. Aucun producteur direct n'a été retrouvé le 17 novembre. |
| `RADIO_CALIBRATION` `0x0506` | `0x08022dec` | La lecture renvoie le bloc de calibration. L'écriture passe par la routine de page `0x0802bed0`. À ne pas étendre. |
| `SEND_1W_FRAME` `0x0207` | `0x08022b20` | Trame de protocole 1W, pas un tampon PHY brut. |

Aucune de ces commandes ne met la machine RX en pause, ne coupe USART3, ni ne rend ensuite la configuration io.

### Séquence proposée

Fait établi pour les primitives à réutiliser : pulse SDN et `POWER_UP` dans `0x080272bc`, rechargement des canaux dans `0x08027620`, attente CTS dans `0x08026d64`, émission SPI dans `0x08027020`. Hypothèse de conception, non exécutée :

1. `ENTER` pose un drapeau SRAM et demande l'état radio READY (`CHANGE_STATE`, opcode `0x34`, déjà émis par `0x08027090`). Le même drapeau est testé au début de l'aiguillage radio de `0x08003280`, avant les cas 0 à 11. Sans ce test, une interruption ou un événement déjà posté peut relancer `START_RX`.
2. Le handler retourne tout de suite à la boucle. C'est elle qui réarme le watchdog. Une attente longue dans le handler reset le microcontrôleur.
3. Les sous-commandes SPI s'appuient sur `0x08027020` et `0x08026d64`. La liste blanche couvre la lecture d'état, le FIFO, `START_RX`, `START_TX`, `CHANGE_STATE`, et un `SET_PROPERTY` de fréquence borné à 863–870 MHz. Elle refuse l'écriture flash, l'augmentation de `PA_PWR_LVL`, `POWER_UP` vers un autre quartz, et tout index de canal hors 0..2 tant que la fréquence calculée sort de la bande.
4. `EXIT`, ou l'échéance d'un délai de 2 s sans ordre, efface le drapeau et appelle `0x08027620` sur l'objet existant. Cet appel refait SDN, `POWER_UP`, les propriétés et le port 2. Il ne passe pas par `0x080284c0`, qui sortirait trop tôt à cause de l'octet `+0x0d`.
5. Les clés à `0x20005e8c` ne sont pas dans le chemin de `0x08027620`. Un emprunt qui ne reset pas le STM32 les conserve. Un reset les perd jusqu'au prochain envoi par Linux.

Hypothèse restante : réinitialiser le circuit ne remet pas à lui seul la machine de session io (état dans l'objet de pile, transaction en cours, mode direct USART3 déjà armé par une IRQ). Le retour doit aussi replacer l'octet d'état de pile consommé par `0x08003c64` dans l'état de repos déjà utilisé après `0x08003aa0`. Cet enchaînement n'a pas été simulé.

```text
boucle 0x08003280
  réarmer le watchdog si l'événement périodique est levé
  si délai brut écoulé : EXIT
  si trame UART : répartiteur
     0x0400 : drapeau, ou SPI liste blanche, ou EXIT
  si drapeau brut : ne pas entrer dans les cas radio 0..11
  sinon : machine io actuelle
EXIT : 0x08027620(objet 0x2000486c) puis état de pile au repos
```

Le schéma est une proposition. Il n'a pas été exécuté.

## 4. Intégrité, mise à jour, watchdog

### MD5 applicatif

`0x0802b9e4`, appelée au démarrage par `0x08003004`, calcule le MD5 de `[0x08003000, 0x0803fff0)` et le compare au pied `0x0803fff0`. Le drapeau RAM est `0x20004b38` : 1 si égal, 0 sinon. Le démarrage continue dans les deux cas. Si le pied diffère et n'est pas déjà 16 octets `FF`, `0x0802bed0` réécrit le pied à `FF`. Cette réécriture efface la page de 2 Kio `0x0803f800`.

`0x0802bed0` n'accepte une écriture que si elle se termine au plus tard à `0x08002800`, ou si elle commence exactement au pied `0x0803fff0`. Le littéral de limite est `0x0802bf9c` = `0x08002800`, et `0x08002800 + 0x3d7f0 = 0x0803fff0`. Cette routine sert à la carte et au pied. Elle ne programme pas le code applicatif.

Conséquence pour un correctif : le MD5 du pied doit être celui de l'image modifiée. Un pied ancien déclenche l'effacement de la dernière page au premier boot. Le code ajouté reste dans `0x08036000..0x0803f7ff`.

### Bootloader et script constructeur

Le choix application ou maintenance est dans `0x0800087c`. Il lit GPIOB masque 4, donc **PB2**, via `0x08000700`. PB2 lu à 1 sélectionne la maintenance (`0x080003cc`). Une autre valeur saute à l'application (`0x080002b0`). Ce saut n'est pas un contrôle de MD5. `0x0800039e` (commande bootloader `0x16`) appelle le reset applicatif directement.

Commandes du bootloader, déjà reliées aux modèles de `fw-updater` :

| Opcode | Fonction | Portée lue dans le code |
|---|---|---|
| `0x12` | `0x08000628` | Efface depuis `0x08002800` par pages de `0x800`. La boucle vise `0x08100000`. Le succès n'est retourné que si le curseur dépasse `0x080ffffe`. |
| `0x14` | `0x080002c8` | Lecture à l'adresse demandée. |
| `0x16` | `0x0800039e` | Saute à l'application. |
| `0x17` | `0x08000378` | MD5 d'une plage adresse + longueur. |
| `0x18` | `0x080002d8` puis `0x0800065c` | Programme par pages. Chaque page touchée est effacée puis réécrite. Le contrôle haut est `fin < 0x08100000`. Il n'y a pas de plancher. |

`fwupdate.sh` calcule le MD5 de 249 840 octets à l'adresse décimale 134230016, soit `0x08003000`, et écrit le binaire application à 134227968, soit **`0x08002800`**. La taille du fichier application, 251 904 octets, couvre `0x08002800..0x0803ffff`. Cette écriture ne contient ni le bootloader ni le secteur `0x08002000`. Le même script, dans `-C write`, appelle d'abord `FUN_00011288` de `fw-updater`, qui envoie l'opcode `0x12`, puis le transfert `0x18`.

Fait établi : une image dont le MD5 de pied est juste, écrite par `0x18` à `0x08002800` avec cette longueur, remplace l'application et laisse le bootloader et le secteur de carte en dehors de la plage. Hypothèse non testée : sur le F101RC, l'effacement `0x12` échoue dès `0x08040000`, parce que la flash s'arrête à `0x0803ffff` alors que le succès exige d'aller jusqu'à `0x08100000`. Le délai du script est de 60 s. Environ 500 pages à 20–40 ms tiendraient dans ce délai si le contrôleur répondait succès hors flash. Ce comportement silicium n'est pas dans le firmware. Il ne faut pas le découvrir en lançant le script.

Le script constructeur compare ensuite ce MD5 au fichier officiel. Une application modifiée est donc, pour lui, une application à remplacer par l'image d'origine. En échec répété, `fwupdate.sh` appelle `stm32-upgrader`, dont le chemin audité le 17 novembre enchaîne une déprotection. Cette déprotection efface la flash principale, secteur de carte compris. Le script constructeur n'est pas un installeur de correctif.

### Retour à l'image d'origine

Si le bootloader est intact, un reset avec PB2 lu à 1 entre en maintenance avant tout saut applicatif. Une application qui plante après ce choix n'empêche pas la maintenance au reset suivant. La commande `0x18` à `0x08002800` peut alors réécrire l'image d'origine, et `0x16` ou un reset avec PB2 différent de 1 la redémarre. Le lien électrique entre `gpio_mode update` du script Linux et PB2 n'a pas été suivi sur la carte : le code STM32 établit PB2, le script ne fait que nommer un mode.

Le vecteur HardFault applicatif nul, relevé le 17 novembre dans l'image, reste une limite : une faute dans le code ajouté peut bloquer sans handler. Le watchdog ne sauve que s'il a déjà été armé.

### Watchdog

`0x0802d514`, appelée par `0x08003004`, écrit la clé `0x5555`, le préscaler **4**, le rechargement **`0xFFF`**, puis la clé de départ `0xCCCC`. `0x08031d54` écrit `0xAAAA` et la boucle `0x08003280` l'appelle sur l'événement périodique. Aucune référence à `0x40002C00` (WWDG) n'est présente. Le bootloader audité n'arme pas cet IWDG avant le choix d'application.

Calcul, pas une mesure : préscaler 4 = division par 64, compte 4 096. Avec l'oscillateur interne bas typique de 40 kHz (plage publique 30 à 60 kHz, RM0008), le délai vaut environ **6,6 s**, entre environ 4,4 s et 8,7 s. Un handler qui ne revient pas à la boucle pendant ce délai reset le STM32. Après ce reset, PB2 est relu : si le niveau maintenance n'est pas tenu, l'application repart.

## 5. Conception minimale

Une seule commande entrante, `0x0400`, avec un octet de sous-commande. Les réponses utilisent un identifiant de retour nouveau parmi les cases libres, par exemple `0x0402`, pour ne pas se superposer à `0x0401` et `0x0403` déjà émis par la pile.

| Sous-commande | Rôle | Garde |
|---|---|---|
| `ENTER_RAW` | Drapeau, `CHANGE_STATE` vers READY, pas d'entrée dans les cas io | Refus si une transaction io est encore dans l'état actif. Délai armé à 2 s. |
| `SPI` | Un opcode et son tampon, via `0x08027020` | Liste blanche. Longueur plafonnée par les 762 octets déjà admis, et par le FIFO 64 octets du Si446x pour les données. |
| `RX` | État modem, FIFO ou octet direct, RSSI déjà lu par `0x080285f0` (`0x22` sur le tampon de commande) | Lecture seule. Pas de changement de bande. |
| `TX` | Une trame, `START_TX` du chemin existant | Fréquence calculée dans 863–870 MHz. Compteur de temps d'émission. Refus au-dessus du plafond du sous-canal. |
| `EXIT_RAW` | `0x08027620` puis état de pile au repos | Aussi appelé par le délai, et si le watchdog va être le seul réarmement restant. |
| `STATUS` | Drapeau, temps restant, dernier CTS | Sert de signe de vie sans toucher au RF. |

Garde-fous proposés, à coder dans le handler :

- Bande unique 863–870 MHz. Les trois canaux d'origine restent les seuls réglages connus ; toute autre fraction est refusée tant que le diviseur de sortie n'est pas lu sur le composant.
- Puissance : ne pas écrire `PA_PWR_LVL` au-dessus de l'octet que l'init io vient de programmer. Le modèle `.data` à `0x08035a04` est le `SET_PROPERTY` groupe `0x22`, début `0x01`, octets `50 00 3d`. `0x080270f4` remplace le premier octet de donnée par une table. Les deux tables, `0x0803e056` et `0x0803f456`, sont `FF` dans l'image, y compris dans la zone de code identique au dump réel. L'octet réellement envoyé par cette fonction est donc `FF`. Ce n'est pas une puissance en dBm. Le correctif refuse toute écriture PA plutôt que d'inventer un plafond en dBm.
- Rapport cyclique : plafond par sous-bande, voir la section 6. Le compteur est dans le handler. À l'échéance, `TX` retourne une erreur et n'émet pas.
- Aucune écriture flash. `0x0802bed0` n'est pas appelée.
- Retour io sur `EXIT`, sur délai de 2 s, et avant qu'une attente ne mange le délai IWDG. Le retour ne reset pas le cœur.
- Le daemon Linux d'origine, s'il reste maître de l'UART, peut reset le STM32 sur silence ou lancer `fwupdate.sh` parce que le MD5 n'est plus celui du fichier officiel. L'emprunt suppose un seul propriétaire de l'UART, qui ne lance pas ce script.

## 6. Limites visibles dans le firmware

Le bloc `POWER_UP` à `0x08035629` annonce un quartz de **26 MHz**. `FREQ_CONTROL_INTE` vaut **65**. Les trois fractions `0x0e4ec4`, `0x0ebd0b` et `0x0f4ad4` sont à `0x08035640`. Avec la formule publique `(entier + fraction / 2^19) * 2 * 26 MHz / diviseur` et l'hypothèse diviseur 4, les fréquences sont 868,25 MHz, 868,95 MHz et 869,85 MHz. Le script retrouve les valeurs déjà consignées dans `radio-derived.json`. Aucun `SET_PROPERTY` extrait ne couvre `MODEM_CLKGEN_BAND` (`0x2051`). Le diviseur 4 reste une hypothèse : c'est celle qui place ces entiers dans la bande 850–1050 MHz du Si4460/61/63 (fiche Silicon Labs, tableau des diviseurs : 4 pour 850–1050 MHz, 8 pour 420–525 MHz). Le même entier avec un diviseur 8 tomberait vers 434 MHz. Le firmware ne programme pas ce diviseur et ne contient pas de constante 433.

`MODEM_MOD_TYPE` du modèle à `0x08035570` vaut `0xea` : 2FSK, source directe, émission asynchrone, comme déjà interprété le 17 novembre. Les trois octets de déviation au groupe `0x20` index `0x0a` valent `00 03 27`. La formule publique `(diviseur * quartz * registre) / 2^19` avec diviseur 4 donne environ 160 kHz. C'est un calcul, pas une mesure.

Le Si4461, d'après sa fiche, couvre 142–1050 MHz par bandes et monte à +16 dBm côté circuit. La fiche décrit des adaptations différentes selon la puissance et la bande. Le firmware ne décrit pas le réseau d'adaptation de la carte.

Broches STM32 utilisées par le pilote radio, d'après les littéraux de `0x0802ce1c` et `0x0802ce7c` :

| Accès | Port | Masque | Broche | Usage établi |
|---|---|---|---|---|
| Sortie, cas 1 | GPIOA `0x40010800` | `0x10` | PA4 | Sélection SPI autour de chaque commande. Cohérent avec NSS de SPI1. |
| Sortie, cas 3 | GPIOA | `0x08` | PA3 | Impulsion haute puis basse dans `0x080272bc`, et maintien haut dans `0x08027b80`. C'est la commande SDN. |
| Entrée, cas 2 | GPIOA | `0x04` | PA2 | Lecture disponible. Pas le choix de boot. |
| Entrée, bootloader | GPIOB `0x40010c00` | `0x04` | PB2 | Choix application ou maintenance. |
| Entrées, cas `0x18` `0x19` `0x1a` | GPIOB | `0x1000` `0x2000` `0x4000` | PB12, PB13, PB14 | `0x0802d374` choisit l'une des deux tables GPIO du Si446x. |
| Sortie, cas `0x1b` | GPIOB | `0x200` | PB9 | Commande de test `>` dans `0x080236a0`. Pas le chemin io. |
| Entrée, cas `0x16` | GPIOC `0x40011000` | `0x01` | PC0 | Lecture par la commande de test `0x08` de `0x080236a0`. |
| Entrée, cas `0x17` | GPIOC | `0x80` | PC7 | `0x08023598` : si la broche est lue à 1, le démarrage n'installe pas l'API UART normale. |
| Sortie, cas `0x10` | GPIOC | `0x200` | PC9 | Présente dans le sélecteur. Aucun appel direct avec la constante `0x10` n'a été retrouvé. |

Les deux tables copiées par `0x08027620` vers l'objet `+0x28`, puis envoyées par `0x080271a8` avec la commande `GPIO_PIN_CFG` (`0x13`), sont à `0x08035884` et `0x0803588c`. Six octets, dans l'ordre GPIO0, GPIO1, GPIO2, GPIO3, NIRQ, SDO :

- `04 14 21 20 18 00` : INPUT, RX_DATA, RX_STATE, TX_STATE, VALID_PREAMBLE, DONOTHING.
- `18 02 14 04 18 00` : VALID_PREAMBLE, DRIVE0, RX_DATA, INPUT, VALID_PREAMBLE, DONOTHING.

Les codes sont ceux du guide d'API public Si446x (`RX_DATA` = `0x14`, `ANTENNA_1_SW` = `0x16`, `TX_STATE` = `0x20`, `RX_STATE` = `0x21`). Aucun des deux tableaux ne contient `0x16`, `0x17` (commutateurs d'antenne) ni `0x0f` (`EN_PA`). Le code cherche aussi `0x07` et `0x1c` dans ces six octets : ils n'y sont pas, donc ces deux drapeaux restent à 0 avec les tables livrées.

USART3 a 9 littéraux de base `0x40004800`. Le chemin direct 2FSK est celui déjà décrit. SPI1 est `0x40013000`.

Pour le 433 MHz : le firmware ne le configure pas. Le composant saurait synthétiser 420–525 MHz avec le diviseur 8, d'après la fiche, mais ce diviseur n'est pas programmé ici, et rien dans le code ne décrit une adaptation 433. Le garde-fou à 863–870 MHz est aligné sur ce que le firmware sait faire. Il ne prouve pas, à lui seul, qu'un réseau HF 868 serait inoffensif si on forçait un autre diviseur : cette question est matérielle, et elle est hors de cette étude.

Sous-bandes publiques qui contiennent les trois canaux, d'après l'annexe ERC 70-03 et l'EN 300 220-2, à confirmer sur le texte en vigueur avant toute émission future :

| Canal du firmware | Sous-bande | Plafond public rappelé |
|---|---|---|
| 868,25 MHz | 868,0–868,6 | 25 mW, rapport 1 % ou accès poli |
| 868,95 MHz | 868,7–869,2 | 25 mW, rapport 0,1 % ou accès poli |
| 869,85 MHz | 869,7–870 | 25 mW et 1 %, ou 5 mW sans exigence de rapport |

La sous-bande 869,4–869,65 MHz, 500 mW et 10 %, ne contient aucun des trois canaux. Le +16 dBm du Si4461 peut dépasser 25 mW selon l'antenne. D'où le refus d'augmenter le PA au-delà du réglage déjà chargé par l'init io.

## 7. Verdict

| Question | Réponse |
|---|---|
| Place | Oui. 38 912 octets de flash déjà effacés. Pile d'environ 6,1 Kio. Pas de grosse SRAM libre démontrée au-dessus des objets existants. |
| Accroche | Oui. Un mot à `0x080349cc`, commande `0x0400`. Index borné à 0..20. Page `0x08034800` à réécrire. |
| Prêt et retour | Ajout nécessaire. Les primitives SDN, `POWER_UP`, propriétés et CTS existent et sont rappelables par `0x08027620`. Le drapeau dans `0x08003280` est indispensable. Le retour de la machine de session reste une hypothèse. |
| Installation | Le MD5 doit être recalculé, sinon la dernière page est effacée au boot. Le bootloader peut réécrire l'application d'origine à `0x08002800` si PB2 sélectionne la maintenance. Le script constructeur, lui, veut l'image officielle et peut tomber sur une déprotection. |
| Matériel | Quartz 26 MHz, trois canaux vers 868–870 MHz, PA3 = SDN, PA4 = sélection SPI, pas de commutateur d'antenne dans les tables GPIO. 433 MHz absent du code. |
| Effort | Un petit module et deux pages à réécrire : de l'ordre de quelques jours de préparation statique. L'essai réel est une étape séparée, plus lourde parce que la protection de lecture empêche le débogage flash. |
| Risques principaux | Retour io incomplet. Watchdog si le handler bloque. MD5 faux. Script constructeur. Effacement `0x12` dont la borne dépasse la flash. Index de commande sans borne. |

Points qu'un essai réel, non fait ici, peut seul trancher :

1. Le niveau électrique que `gpio_mode update` met sur PB2, et le retour en application.
2. Le code de retour réel de l'effacement `0x12` sur ce F101RC.
3. La fréquence, la déviation et le diviseur, mesurés, pour confirmer ou écarter l'hypothèse diviseur 4.
4. La puissance obtenue avec l'octet PA `FF` que le code programme, face au modèle `0x50`.
5. Une lecture io complète après `EXIT` : mêmes clés SRAM, même appareil, sans reset du STM32.
6. Le délai IWDG observé, l'oscillateur interne variant de 30 à 60 kHz.
7. Le délai exact avant qu'un propriétaire UART Linux ne reset le STM32 ou ne lance une mise à jour.
8. Le rôle de PC9 et de PC7 sur la carte, et l'état des straps PB12–PB14 qui choisissent la table GPIO.

## Sources

- Image : `analyse-2026-11-17/extracted/appsB/overkiz/share/io-homecontrol/bin/io-homecontrol-boot-stm32-MRIO_v1-v2.4.2.bin`
- Décompilation et tables : `analyse-2026-11-17/stm32/all-functions.c`, `uart-dispatch.json`, `radio-properties.json`, `radio-derived.json`
- Contrat UART et clés SRAM : `analyse-2026-11-17/continuation-radio/stm-real/RESULTAT.md`
- Bootloader et `fw-updater` : `analyse-2026-11-17/offline-next/boot-read-audit/RESULTAT.md`, `fw-updater.c`, `updater-literals.json`
- Script de mise à jour, lu et non exécuté : `analyse-2026-11-17/extracted/appsB/overkiz/share/io-homecontrol/scripts/fwupdate.sh`
- Énumérations : `analyse-2026-11-17/lua/embedded/23fc49b604cd/DaughterboardApiCommand.lua`, `analyse-2026-11-17/lua/embedded/39a18ee538e5/DaughterboardApiCallback.lua`
- Fiche Si4464/63/61/60, Silicon Labs, pour le diviseur, la bande et le PA. EN 300 220-2 et annexe ERC 70-03 pour les sous-bandes 863–870 MHz.
- Reproduction : `python analyse_static.py` puis `python complement.py` dans ce dossier. Les deux ne font que lire l'image distribuée.

> Les empreintes historiques des fichiers expurgés se rapportent aux originaux privés.
