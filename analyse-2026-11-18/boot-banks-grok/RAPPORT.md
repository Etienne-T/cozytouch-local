# Banques de démarrage : ce que le corpus userspace démontre

Étude statique du 18 novembre 2026, limitée au dossier `corpus/`. Les modules Lua sont décompilés. Un constat est **démontré** quand le texte le contient. Il est **supposé** quand il reconstruit l'intention au-delà d'un défaut de décompilation, ou quand il relie deux fichiers que le corpus ne montre pas chargés ensemble. Il est **à vérifier** quand la réponse dépend d'un module, d'un script ou d'un pilote absent.

Aucun fichier du corpus n'écrit dans une NAND, ne nomme une banque A ou B, et n'emploie les mots `bank` ou `nand`. Le mot `kboot` n'apparaît que dans `etc/conf.d/internal`.

## Synthèse

Le Linux applicatif de ce corpus ne choisit pas la banque du prochain démarrage. Il lit `/sys/kboot/next` et `/sys/kboot/mode` une fois, si un fichier volatile de boot existe, puis il transmet les deux nombres au canal d'administration. Il ne les écrit pas. Il ne confirme pas un démarrage d'essai. Il ne compte pas les échecs. Le watchdog userspace entretient `/dev/watchdog0` ; rien ne le relie à un changement de banque.

La mise à jour est déléguée à la commande externe `image-update`, absente du corpus. Les fichiers `version-hash.txt` et `bootloaderid` sont lus, jamais écrits ici. Le fichier `recovered` et `have_user_data` pilotent un signal de resynchronisation vers le cloud, puis le premier est effacé après un acquittement. Ce signal ne sélectionne pas une banque.

## 1. Chaîne des chemins `kboot`

Trois fichiers portent les chemins. Ils ne forment une chaîne que si le processus Lua reçoit les variables du fichier d'environnement.

| Rôle | Variable | Valeur dans `etc/conf.d/internal` | Défaut dans `conf.lua` si la variable est absente |
| --- | --- | --- | --- |
| Mode | `INTERNAL_BOOTMODE_FILE` | `/sys/kboot/mode` (ligne 15) | chaîne vide (ligne 63) |
| Prochain démarrage | `INTERNAL_BOOTNEXT_FILE` | `/sys/kboot/next` (ligne 16) | chaîne vide (ligne 62) |
| Raison de reset | `INTERNAL_RESETREASON_FILE` | `/sys/reset/reason` (ligne 7) | `/sys/reset/reason` (ligne 64) |
| Marqueur de boot | `INTERNAL_BOOT_FILE` | `/var/volatile/tmp/boot` (ligne 6) | `/tmp/boot` (ligne 61) |
| Identifiant recovery | `INTERNAL_RECOVERYID_FILE` | `"/persistent/boot/update/bootloaderid"` (ligne 17) | chaîne vide (ligne 59) |
| Statut de mise à jour | `INTERNAL_UPDATE_STATUS_PATH` | `/persistent/boot/update/version-hash.txt` (ligne 10) | le même chemin (ligne 35) |
| Fichier recovered | `INTERNAL_RECOVERED_FILE` | `/persistent/apps//etc/recovered` (ligne 5) | `/etc/recovered` (ligne 60) |
| Données utilisateur | `INTERNAL_HAVE_USER_DATA` | absente de ce fichier | `(STORAGE_DIR ou "") .. "/have_user_data"` (ligne 69) |
| Watchdog | `INTERNAL_WATCHDOG_DEVICE`, intervalle, timeout | `"/dev/watchdog0"`, `"15"`, `"60"` (lignes 24 à 26) | mêmes défauts (lignes 75 à 77) |

**Démontré.** `conf.lua` lit chaque chemin par `os.getenv`, avec le défaut en second argument (`conf.lua:1-3`, `59-69`, `75-77`).

**Démontré.** `STORAGE_DIR=/data/internal` (`etc/conf.d/internal:1`). `INTERNAL_HAVE_USER_DATA` n'y est pas définie. Si les deux fichiers alimentent le même processus, `have_user_data` vaut `/data/internal/have_user_data`. Ce chargement commun est **supposé** : le script d'init qui sourcerait `etc/conf.d/internal` est absent. Si `STORAGE_DIR` est vide dans le processus, le défaut devient `/have_user_data` (`conf.lua:69`).

**Démontré.** La valeur recovered contient deux barres obliques : `/persistent/apps//etc/recovered` (`etc/conf.d/internal:5`). L'équivalence POSIX avec `/persistent/apps/etc/recovered` est **supposée**.

**Supposé.** Les guillemets autour de `bootloaderid`, du watchdog et des URL CRL sont retirés par un shell qui source le fichier. Le corpus ne contient pas ce shell.

**Démontré.** L'identité configurée est `core-image-kizos-recovery-at91-kizboxmini`, version `2026.1.3-2` (`etc/conf.d/internal:2` et `:4`). Ce nom contient `recovery`. Il ne dit pas quelle banque NAND est active. **À vérifier** hors corpus.

## 2. Sélection de banque au démarrage

### Lectures

**Démontré.** Deux fonctions lisent les sysfs, et leurs noms sont croisés par rapport aux fichiers :

```275:281:corpus/lua/Overkiz/HomeAutomation/Protocol/Internal/Admin/system.lua
function slot26.bootMode()
	return tonumber(uv0.readInfoFile(uv1.path.bootnextFile)) or slot0
end

function slot26.rebootMode()
	return tonumber(uv0.readInfoFile(uv1.path.bootmodeFile)) or slot0
end
```

`bootMode` lit `bootnextFile`, donc `/sys/kboot/next` si l'environnement est appliqué (`conf.lua:62`, `etc/conf.d/internal:16`). `rebootMode` lit `bootmodeFile`, donc `/sys/kboot/mode` (`conf.lua:63`, `etc/conf.d/internal:15`). `rebootReason` lit `/sys/reset/reason` (`Admin/system.lua:283-285`).

**Démontré.** Le seul consommateur est le démarrage du transport d'administration. Si le fichier de boot existe, il envoie un message `boot` puis passe `hasBoot` en troisième argument :

```157:166:corpus/lua/Overkiz/HomeAutomation/Protocol/Internal/Transport/Admin/Objects/info.lua
	if uv2.isBoot() then
		uv3:pushUrg("boot", {
			bootmode = nil,
			reset = nil,
			rebootmode = nil,
			bootmode = uv2.bootMode(),
			rebootmode = uv2.rebootMode(),
			reset = uv2.rebootReason()
		}, uv2.hasBoot)
	end
```

Le champ transmis `bootmode` contient donc le nombre lu dans `/sys/kboot/next`. Le champ `rebootmode` contient le nombre lu dans `/sys/kboot/mode`.

**Démontré.** `isBoot` est vrai quand le fichier volatile existe (`Admin/system.lua:267-269`). Avec l'environnement du corpus, ce fichier est `/var/volatile/tmp/boot`. `hasBoot` le supprime (`Admin/system.lua:271-273`). Le module `dispatcher`, absent, décide du moment de cet appel. **À vérifier** : suppression immédiate, ou seulement après acquittement.

**Démontré.** `readInfoFile` vient de `Overkiz.utilities`, absent. Le corpus ne montre ni le retrait du saut de ligne, ni le comportement si le sysfs est illisible. `tonumber(...) or slot0` ne substitue aucun numéro de banque écrit dans la fonction : `slot0` n'y est pas affecté (`Admin/system.lua:276` et `:280`). La signification des entiers (banque, essai, mode recovery) est **à vérifier** dans le pilote `kboot`, absent.

### Écritures et confirmation

**Démontré.** Aucun fichier du corpus n'écrit `/sys/kboot/mode` ni `/sys/kboot/next`. Aucun ne parle d'un démarrage à l'essai, d'une confirmation après succès, ni d'un compteur d'essais.

**Démontré.** `getImageId`, `getVersion` et `getRevision` renvoient les chaînes d'environnement (`Admin/system.lua:232-250`). Le message `image` les republie avec le md5 et le nombre de paquets `opkg` non configurés (`Transport/Admin/Objects/info.lua:63-76`, `142-171`). Ce message ne contient pas de banque.

Les commandes qui pourraient fixer la banque suivante sont hors corpus : `image-update`, `reboot.sh`, `bootloader-upgrade.sh`, le pilote derrière `/sys/kboot`, le bootloader.

## 3. Retour arrière

**Démontré.** Le corpus ne contient pas de bascule vers une autre banque, ni en cas d'échec de démarrage, ni en cas d'absence de confirmation, ni après un nombre d'essais.

### Watchdog

**Démontré.** `Watchdog.lua` expose une classe. Aucun autre fichier du corpus ne la charge : le nom `Watchdog` n'y apparaît pas. On ne sait donc pas si ce processus arme le watchdog. **À vérifier.**

**Démontré.** `start` tue un processus nommé `watchdog`, ouvre le périphérique en `a+`, prend son descripteur, appelle `fcntl` puis deux `ioctl`, puis répète `_touch` (`Watchdog.lua:38-61`). Les littéraux présents sont `2`, `2147768068`, `2147768069`, `3221509894`, `2` et `1` (`Watchdog.lua:22-27`).

**Supposé**, par correspondance avec l'ABI Linux `watchdog.h`, et non par un en-tête du corpus :

- `2147768068` (`0x80045704`) est `WDIOC_SETOPTIONS` ;
- `2147768069` (`0x80045705`) est `WDIOC_KEEPALIVE` ;
- `3221509894` (`0xC0045706`) est `WDIOC_SETTIMEOUT` ;
- `1` est `WDIOS_DISABLECARD`, `2` est `WDIOS_ENABLECARD` ;
- `fcntl` avec la commande `2` est `F_SETFD`.

Le décompilateur a renommé les upvalues. Quel `ioctl` reçoit `1`, `2` ou le timeout de 60 secondes n'est pas fiable, sauf le timeout : un appel passe explicitement `slot0.watchdogTimeout` (`Watchdog.lua:54`). `_touch` appelle `ioctl` avec un troisième argument `NULL` (`Watchdog.lua:64-67`), ce qui correspond à un keepalive. Le délai de répétition est `keepAliveInterval * 1000`, donc 15 000 ms avec le défaut (`Watchdog.lua:57`, `conf.lua:76`).

**Démontré.** `stop` annule le timer, écrit le caractère `V`, puis ferme le périphérique (`Watchdog.lua:70-78`). L'écriture de `V` avant la fermeture correspond à la convention Linux dite magic close. Le fait que ce pilote la respecte est **à vérifier**.

**Démontré.** Ce module ne lit ni n'écrit `kboot`. Un reset matériel après absence de keepalive, et un éventuel changement de banque dans le bootloader à cette occasion, sont **à vérifier** hors corpus.

### Redémarrages présents dans le corpus

Trois chemins redémarrent quelque chose. Aucun ne reçoit de numéro de banque.

**Démontré.** `Admin.system.reboot` calcule une heure, arme un timer monotone, puis exécute `scriptDir .. "/reboot.sh"` (`Admin/system.lua:304-332`). Le script est absent. Avec l'environnement, le chemin serait `/apps/overkiz/share/internal/admin/scripts/reboot.sh` (`etc/conf.d/internal:8`). L'arithmétique des bornes est incomplète dans le texte décompilé : `slot5` n'est affecté que dans une branche (`Admin/system.lua:308-315`). Le détail du tirage aléatoire est **à vérifier** sur le bytecode. L'appel final à `reboot.sh` est littéral.

**Démontré.** Le paramètre de nœud `reboot.lua` relance ofono et envoie `#REBOOT` au modem (`Node/Parameters/reboot.lua:4-15`). Ce n'est pas un redémarrage du hub.

**Démontré.** `multiGatewayRestart.lua` appelle `MultiGatewayManager:restart()` (`Node/Parameters/multiGatewayRestart.lua:4-7`). Le gestionnaire est absent et le fichier ne cite pas `kboot`.

`Service.lua` gère des services `/etc/init.d` et un délai de relance. Il ne cite ni `kboot`, ni banque, ni watchdog.

## 4. Mise à jour et recovery

### `update.lua` : témoin lu, pas de préparation de banque

**Démontré.** Le module est un serveur de bus `/com/overkiz/Application/Internal/Update` (`update.lua:8`). Il ne lance pas `image-update` et n'écrit aucun fichier de boot.

**Démontré.** `slot13` ouvre `updateStatusPath` et découpe chaque ligne sur `:` en `id`, `status`, `version`, `hash` (`update.lua:14-43`). Le chemin configuré est `/persistent/boot/update/version-hash.txt`. Le fichier exemple est absent. Le comportement de `stringSimpleSplit` si un champ contient un `:` est **à vérifier** (`Overkiz.utilities` absent). Le test mêle `updateStatusPath` et une variable `slot0` non affectée (`update.lua:15`) : le texte décompilé est incohérent sur ce point. **Supposé** : les deux tests visaient le même chemin.

**Démontré.** La méthode `exitStatus` (`ssi` : deux chaînes et un entier) appelle le rappel enregistré sous l'identifiant. Code `0` : `onSuccess`. Autre code : `onError`. Puis `onExit`. Les rappels sont ensuite vidés (`update.lua:60-76`, `106-109`).

**Démontré.** La méthode `updateStatus` ne notifie `updateFinalStatusNotifier` que si la chaîne vaut `updated` (`update.lua:102-105`).

**Démontré.** `harakiri` déclenche le rappel de succès, demande l'arrêt des services à `modules.stopAllServices`, puis `os.exit(0)` (`update.lua:80-101`). Le module `modules` est absent. Les délais littéraux du fichier sont 1 000 et 2 000 (`update.lua:11-12`) ; lequel s'applique à l'arrêt et lequel à la sortie est **supposé**, à cause des upvalues.

### Préparation : la commande absente `image-update`

**Démontré.** Le paramètre `Node/Parameters/update.lua` construit et exécute `image-update`. La table des cibles est littérale (`Node/Parameters/update.lua:9-31`) :

| Cible demandée | Arguments ajoutés |
| --- | --- |
| `applications` | `upgrade`, `apps` |
| `system` | `root` |
| `bootloader` | `bootloader` |
| `security` | `security` |
| `bootstrap` | `bootstrap` |

Les arguments de tête visibles sont `-i` et un identifiant produit par `UUID.generate` (`Node/Parameters/update.lua:57-75`). `-f` est ajouté si `force` est vrai, `-r` si `reboot` est vrai (`Node/Parameters/update.lua:70-79`). L'environnement reçoit `TRIGGERED_BY=internal-update` (`Node/Parameters/update.lua:96-97`). L'option `detached` reçoit la valeur de `reboot` (`Node/Parameters/update.lua:91-94`). Un code de sortie non nul appelle le rappel d'erreur (`Node/Parameters/update.lua:103-111`). L'identifiant est aussi la clé du rappel sur `Internal.update` (`Node/Parameters/update.lua:58-67`), donc le lien avec `exitStatus` est dans ce fichier.

**Supposé.** Le constructeur de la table d'arguments est écrit dans le seul `if slot0.force` (`Node/Parameters/update.lua:70-75`), alors que la suite utilise `slot10` sans cette condition. Le texte d'origine construisait très probablement `{"-i", uuid}` dans tous les cas. Le bytecode trancherait.

**Démontré.** `updateAuto.lua` exécute la même commande avec les arguments littéraux `-i`, un identifiant, `root`, `apps`, `upgrade`, et `TRIGGERED_BY=internal-download` (`Node/Parameters/updateAuto.lua:39-56`). Il ne passe ni `-f` ni `-r`. Il n'agit que si `Boards.handler:getConnectionStatus()` vaut `connected` (`Node/Parameters/updateAuto.lua:33-37`). Le module `Boards.handler` est absent.

**Démontré.** `autoUpdate` enregistre un écouteur sur `updateFinalStatusNotifier` (`Node/Parameters/updateAuto.lua:58-68`). Une fonction du même fichier arrête un timer puis appelle `reboot(startAt, endAt, spanDays)` (`Node/Parameters/updateAuto.lua:16-24`). **Supposé** : cet écouteur est bien cette fonction, et il ne reçoit donc la notification que pour le statut `updated`. La persistance `updateAuto` (type `UPDATE`) mémorise `enabled`, `startAt`, `endAt`, `spanDays` (`Node/Parameters/updateAuto.lua:8-9`, `131-139`). Le module `Overkiz.Persistence` est absent : l'emplacement disque de ces clés est **à vérifier**. Si `enabled` est absent, le code le fixe à `false` (`Node/Parameters/updateAuto.lua:75-81`).

**Démontré.** Le test d'heure décompilé utilise `string.gmatch`, qui renvoie toujours un itérateur, donc une valeur vraie (`Node/Parameters/updateAuto.lua:119-122`). Ce test, tel qu'écrit, ne rejette pas une heure invalide. **Supposé** : l'original utilisait `string.match`.

**Démontré.** `upgradeBootloader` exécute `scriptDir .. "/bootloader-upgrade.sh start"` (`Admin/system.lua:383-385`). Le transport l'expose sous le nom `upgrade` (`Transport/Admin/Objects/system.lua:10-12`). Le script est absent.

**Démontré.** Rien dans ces fichiers n'écrit `version-hash.txt`, `bootloaderid`, ni un sysfs `kboot`. Le marquage de succès ou d'échec d'une banque, s'il existe, est dans `image-update` ou dans `bootloader-upgrade.sh`.

### `recovery.lua` et les témoins

**Démontré.** `recovery.lua` ne fait qu'ouvrir `path.recoveredFile`. S'il s'ouvre, `get` mémorise vrai et ferme le fichier (`recovery.lua:4-17`). Aucun autre fichier du corpus ne charge ce module. Le chemin effectif dépend de `conf.lua`, déjà décrit. Ce module n'écrit rien et ne choisit pas de banque.

Le chemin réellement utilisé au démarrage de l'administration est `Admin.system`, pas `recovery.lua`.

**Démontré.** `isRecovered` (`Admin/system.lua:252-260`) :

- si `have_user_data` et le fichier recovered sont tous deux absents, il journalise `we have lost the data partition, nodes synchronization request` et retourne vrai ;
- sinon, il retourne vrai seulement si le fichier recovered existe.

**Démontré.** Au démarrage, si `isRecovered` est vrai, le transport envoie un message urgent `recovery` avec `recovered = true` et `imageid = getRecoverId()`, via `pushUrgWithHighLevelAck` et l'argument `180000` (`Transport/Admin/Objects/info.lua:145-155`). Après succès, `hasRecovered` supprime le fichier recovered et écrit l'heure courante, en secondes, dans `have_user_data` (`Admin/system.lua:262-265`). Après échec, le journal dit que le serveur a répondu nack et que le fichier recovered n'a pas été effacé (`info.lua:152-154`). L'unité de `180000` est **supposée** être des millisecondes.

**Démontré.** `getRecoverId` lit `recoveryFile` seulement si le chemin est non vide, sinon il retourne `""` (`Admin/system.lua:236-242`). Avec l'environnement, ce chemin est `/persistent/boot/update/bootloaderid`. Le fichier n'est pas dans le corpus. La commande à la demande `getrecoveryinfo` republie cet identifiant avec `recovered = false` en littéral (`info.lua:93-100`). Ce `false` fixe ne reprend pas `isRecovered`.

**Démontré.** Personne dans le corpus n'écrit `bootloaderid` ni `version-hash.txt`. Les seules écritures de témoins sont :

- suppression du fichier recovered et création de `have_user_data` (`Admin/system.lua:263-264`) ;
- suppression du marqueur volatile de boot (`Admin/system.lua:272`).

Ces écritures changent le signal cloud et le fait d'avoir déjà notifié le boot. Elles ne sont suivies d'aucune écriture `kboot`.

## 5. Conditions qu'on peut déduire pour une installation durable

Le code ne démontre pas de condition qui rendrait une banque permanente, ni de condition qui rendrait l'autre banque le repli. Il démontre les limites suivantes.

1. **Démontré.** Tout choix de banque est hors de ce userspace. Une installation qui ne modifierait que ces modules Lua ne fixerait ni la banque courante, ni la suivante. Le point de lecture à conserver pour un constat ultérieur est la paire `/sys/kboot/next` (champ rapporté `bootmode`) et `/sys/kboot/mode` (champ rapporté `rebootmode`), lue seulement tant que le fichier volatile de boot existe.

2. **Démontré.** Le retour arrière fonctionnel n'est pas décidé ici. Le conserver dépend du pilote `kboot`, du bootloader, et des commandes `image-update` et `bootloader-upgrade.sh`, tous absents. Aucun compteur d'essais n'est visible pour le préserver ou le casser.

3. **Démontré.** Le fichier recovered, et l'absence simultanée de ce fichier et de `have_user_data`, déclenchent une demande de resynchronisation des nœuds. Un acquittement efface le premier et réécrit le second. Ce couple est un témoin de recovery applicative. Le laisser ou le retirer ne sélectionne pas la banque dans ce code. L'effacement n'a lieu qu'après la réponse positive du serveur.

4. **Démontré.** Le seul point d'entrée de mise à jour visible nomme les cibles `root`, `apps`, `upgrade`, `bootloader`, `security` et `bootstrap`, puis attend un code de sortie et, pour le statut `updated`, un `reboot.sh`. Sans le corps de `image-update`, on ne sait pas si une cible écrit une banque inactive, les deux, ou le bootloader commun. **À vérifier** avant toute conclusion sur l'intégrité de la banque laissée de côté.

5. **Démontré.** Le watchdog de ce fichier n'est pas un mécanisme de confirmation de banque. Son démarrage effectif est lui-même **à vérifier**, faute d'appelant.

Ce corpus ne fournit donc pas le mécanisme à garder intact pour garantir le retour au Linux d'origine. Aucune écriture NAND, aucun flash et aucune modification persistante ne sont proposés.

## 6. Modules, scripts et fichiers référencés mais absents

Présents et utilisés entre eux : `conf.lua`, `update.lua`, `Admin/system.lua`, `Transport/Admin/Objects/info.lua`, `Transport/Admin/Objects/system.lua`, les cinq paramètres de nœud, `recovery.lua` (isolé), `Watchdog.lua` (isolé), `Service.lua` (isolé), `scripts/pkg.sh`, `etc/conf.d/internal`.

`pkg.sh` calcule le md5 de `/var/lib/opkg/status`, compte les paquets `unpacked`, ou appelle `opkg` (`scripts/pkg.sh:3-49`). `Admin.system` l'invoque pour `md5` et `nbrunpacked` (`Admin/system.lua:220-229`). Il ne participe pas au choix de banque. La commande `install` qu'il contient lancerait `opkg update` si on l'exécutait ; cette étude ne l'exécute pas.

Absents, alors qu'un `require` ou une commande du corpus les nomme. Leur comportement n'est pas inventé.

Modules Lua : `Overkiz.utilities`, `Overkiz.Timer`, `Overkiz.HomeAutomation.Protocol.Internal.log`, `Overkiz.HomeAutomation.Protocol.Internal.modules`, `pl.path`, `Overkiz.TableStorage`, `Overkiz.Bus.Object`, `Overkiz.Subject`, `Overkiz.Time`, `Overkiz.asyncProcess`, `Overkiz.Promise`, `Overkiz.OOP.Class`, `ffi`, `Overkiz.Logger`, `Overkiz.Persistence`, `Overkiz.conf`, `Overkiz.HomeAutomation.Protocol.Internal.Admin.common`, `Admin.FileUpdater`, `Overkiz.RandomCron`, `Common.systemex`, `Overkiz.Type.ByteArray`, `bus.timezone`, `Overkiz.asyncFs`, `Overkiz.Network.ConnectivityCheck`, `Overkiz.FileWatcher`, `pl.file`, `pl.url`, `pl.stringx`, `luvit.fs`, `openssl`, `Overkiz.Date`, `Transport.Admin.dispatcher`, `Overkiz.Log`, `bus.resync`, `Overkiz.UUID`, `Boards.handler`, `modemHandler`, `MultiGateway.MultiGatewayManager`.

Commandes et scripts : `image-update` ; `reboot.sh`, `bootloader-upgrade.sh`, `coredump.sh`, `ssh.sh` sous `INTERNAL_SCRIPTSDIR` ; le binaire `watchdog` tué par `killall`. `scripts/pkg.sh` du corpus porte le même nom que `scriptDir .. "/pkg.sh"`, sans que le corpus prouve que c'est le fichier installé à `/apps/overkiz/share/internal/admin/scripts/pkg.sh`.

Interfaces citées sans implémentation : `/sys/kboot/mode`, `/sys/kboot/next`, `/sys/reset/reason`, `/dev/watchdog0`, `/dev/rtc`.

Témoins cités sans exemplaire dans le corpus : `/persistent/boot/update/version-hash.txt`, `/persistent/boot/update/bootloaderid`, `/persistent/apps//etc/recovered`, `have_user_data`, `/var/volatile/tmp/boot`.

## 7. Limites de lecture

Les upvalues `uvN` sont des noms du décompilateur. Les branchements signalés plus haut (`slot0`, `slot5`, `slot10`, `string.gmatch`, argument exact des `ioctl`) ne doivent pas être pris pour le bytecode. Les hachages de `corpus-manifest.json` identifient ces textes décompilés ; ils ne prouvent pas le comportement sur le hub.
