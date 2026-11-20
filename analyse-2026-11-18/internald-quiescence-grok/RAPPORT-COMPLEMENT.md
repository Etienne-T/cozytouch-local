# Complément au rapport du 18 novembre 2026

Contrôle statique du rapport `RAPPORT.md`. Le rapport initial n'est pas modifié.

Sources lues : `RAPPORT.md`, `MISSION.md`, `complement-manifest.json`, `complement/`, et les modules du corpus cités par le rapport lorsque le complément les éclaire. Désassemblage ARM hors ligne de `Timer.so` et lecture des symboles de `Persistence.so`, avec Capstone déjà installé. Aucun téléchargement, aucun accès au hub.

`Persistence.so` et `Timer.so` ne contiennent pas les chemins de couches. `libCore.so.4` et `libLua.so.1`, dont dépendent ces bibliothèques, ne sont pas dans le complément.

Légende : **démontré**, **supposé**, **à vérifier**, comme dans le rapport initial.

## Verdict sur le rapport initial

| Point du rapport | Verdict |
|---|---|
| `Watchdog:start` au démarrage, aucun `:stop` appelé, ioctl de nourrissage toutes les 15 s | Confirmé. Le fichier d'environnement retient les mêmes valeurs que les défauts Lua. |
| `return true` réarme le `Timeout` | Confirmé, et désormais démontré dans `Timer.so`. |
| Délai matériel de 60 s, fenêtre JTAG de 45 à 60 s | Corrigé. 60 s est le délai logiciel `next_heartbeat`. Le compteur du SAM9 dure 16 s au plus. |
| Gel du watchdog pendant le halt JTAG, non déductible du Lua | Précisé. Le minuteur noyau s'arrête avec le CPU. Le gel du compteur matériel dépend du bit `WDDBGHLT`, non démontré sur cette carte. |
| Chemins `Persistence`, `Storage`, `TableStorage` inconnus | Corrigé pour `Storage` et `TableStorage`. Les répertoires des couches `Persistence` restent non démontrés. |
| Modules `…Internal.storage` et `…Parameters.storage` absents, donc chargés on ne sait comment | Corrigé. Ces chaînes sont des suffixes de clé. Aucun `require`. |
| Période du cron CRL inconnue | Corrigé. Une fois par jour local, plus un passage au chargement. Nouvel essai 30 min après un échec. |
| Littéral `3600` d'`updateAuto`, supposé période en secondes | Corrigé. C'est le délai de nouvel essai, converti en 1 h. La période reste d'un jour. |
| `ENABLE_MONITORING_PATH` absent | Corrigé : `/persistent/factory/enable-monitoring`. |
| `have_user_data` sous un `STORAGE_DIR` inconnu | Corrigé : `/data/internal/have_user_data`. |
| Suppression de `/etc/recovered` | Corrigé : `/persistent/apps/etc/recovered`. |
| `/tmp/boot` peut-être hors UBIFS | Corrigé : `/var/volatile/tmp/boot`. |
| Écriture CRL seulement après HTTP 200, MD5 et contrôle | Confirmé. Un échec de déplacement est une promesse rejetée. |
| Procédure P1 | Confirmée pour la phase où le CPU tourne. Le budget de 45 à 60 s après l'arrêt JTAG est à retirer. |
| `nowayout`, autres démons, corps de `Overkiz.FileSystem` | Toujours non démontré. |

## 1. Chemins écrits par Persistence, Storage et TableStorage

### 1.1 Répertoire commun de Storage et TableStorage

`complement/etc/conf.d/internal` ligne 1 fixe `STORAGE_DIR=/data/internal`.

`complement/lua/Overkiz/TableStorage.lua` lignes 33-37 :

```lua
if os.getenv("STORAGE_DIR") then
	slot12 = require("pl.path").join(slot13, "lua-storage")
end
slot3.Directory.add(slot12, tonumber("0700", 8))
```

**Démontré** : le nom de répertoire ajouté est `lua-storage`, et le répertoire est créé en mode `0700`. **Supposé**, artefact du décompilateur : `slot13` est la valeur renvoyée par `os.getenv("STORAGE_DIR")`, utilisée dans le test puis dans `join`, sans que l'affectation ait été réémise. C'est la seule lecture qui fournit un chemin à `Directory.add`. Avec le fichier d'environnement, la racine est :

`/data/internal/lua-storage`

Chaque appel `TableStorage(nom)` crée `/data/internal/lua-storage/<nom>/` (ligne 44).

**Démontré** dans la branche de suppression, ligne 63, le fichier d'une clé :

`racine .. "/" .. nom .. "/" .. quote(clé)`

`quote` est `pl.url.quote` (ligne 19). La branche d'écriture, lignes 69-72, appelle la fonction d'écriture puis `sync` sur `slot3`, mais le décompilateur n'a pas réémis l'affectation de `slot3`. **Supposé**, lecture unique : `slot3` est le même chemin que celui de la suppression.

Le fichier est ouvert en `"w"`, reçoit `return ` suivi de la valeur sérialisée, puis est fermé (lignes 26-31). Aucun test du retour de `io.open`.

L'écriture a lieu dans `__newindex`, donc à chaque affectation. Si l'argument `batch` est faux, `sync` est appelé tout de suite (lignes 65-67 et 71-73). Les trois appels du corpus, `TableStorage("nodes")`, `TableStorage("status")` et `TableStorage("generic-storage")`, ne passent pas de second argument. `batch` est donc nil, et chaque écriture est suivie de `sync`. Le corps de `Overkiz.FileSystem.sync` n'est pas dans le complément : l'appel est démontré, son effet exact sur la NAND reste **supposé**.

Il n'y a pas de minuteur dans `TableStorage.lua`. Rien n'écrit à période fixe.

### 1.2 Storage : une couche, des clés suffixées

`complement/lua/Overkiz/Storage.lua` lignes 5-22. Le premier objet crée un seul `TableStorage("generic-storage")`. La clé est le premier argument. Si un troisième argument est présent, la clé devient `nom .. "." .. suffixe` (lignes 12-13). Si `get()` vaut nil, `push` écrit tout de suite la valeur par défaut (lignes 16-17). `push` (lignes 21-23) fait une affectation, donc l'écriture de la section 1.1.

Les fichiers sont sous :

`/data/internal/lua-storage/generic-storage/<quote(clé)>`

Clés démontrées par les appels du corpus :

| Clé | Déclencheur | Lieu |
|---|---|---|
| `mode.Overkiz.HomeAutomation.Protocol.Internal.storage` | Valeur par défaut au chargement si la clé manque, puis `:push` sur changement de mode UI | `Mode/mode.lua` lignes 6, 155 et 167 |
| `resyncModules.Overkiz.HomeAutomation.Protocol.Internal.storage` | `:push` sur méthode D-Bus `resyncModuleNeeded`, et `cleanup` | `bus/resync.lua` lignes 9, 20 et 24 |
| `activation…Parameters.storage`, et les clés sœur `alarmName`, `alarmCurrentMode`, `alarmDelay`, `intrusion`, `lightingLedModemMode`, `lightingLedPodMode`, `alarmTargetMode`, `siren` | `:push` dans le `write` du paramètre. `siren.lua` lignes 56-65 peut aussi `:push("off")` à la fin d'un cycle GPIO déjà armé | fichiers cités par le rapport, section 2.2 |

**Démontré** : ce sont des écritures sur événement, ou une fois au chargement du module si la clé est absente. Pas une période.

Le cycle sirène déjà lancé est le seul de ces `:push` qui peut encore partir sans commande nouvelle. **À vérifier** avant la fenêtre : aucun cycle `cyclic;…` en cours.

### 1.3 Les deux noms de modules « storage » ne sont pas chargés

`Mode/mode.lua` ligne 6 :

```lua
require("Overkiz.Storage")("mode", 247, "Overkiz.HomeAutomation.Protocol.Internal.storage")
```

Le `require` vise `Overkiz.Storage`. La chaîne longue est le troisième argument. `Storage.lua` lignes 12-13 la concatène à la clé. Elle n'est jamais passée à `require`. Le même schéma vaut pour `…Node.Parameters.storage` (`activation.lua` ligne 1 et les fichiers frères).

Recherche sur le corpus : ces deux chaînes n'apparaissent que dans ces appels. Pas de `require` conditionnel, pas de branche morte. Les modules n'existent pas dans le firmware extrait parce que le code ne les demande pas.

### 1.4 TableStorage « nodes » et « status »

`Node/NodeManager.lua` ligne 11 charge `TableStorage("nodes")`. `saveAndReload` ligne 148 affecte `uv0[id] = nœud`. `reload` (lignes 43-60), appelé chaque seconde par `main.lua` lignes 89-101, parcourt et met à jour des objets en mémoire. Il n'affecte pas la table. **Démontré** : le timer d'une seconde ne passe pas par `__newindex`. **Supposé**, comme dans le rapport, et maintenant avec effet connu si l'upvalue est bien le proxy : `saveAndReload` écrit `/data/internal/lua-storage/nodes/<quote(id)>` lors d'une création ou d'un changement de nœud.

`update.lua` ligne 7 charge `TableStorage("status")`. `getFile` (lignes 27-38 et 46-57) relit `/persistent/boot/update/version-hash.txt` en lecture, puis range les champs dans une table itérée avec `.pairs`. **Supposé** que cette table est le proxy `status`, car `.pairs` est la méthode de `TableStorage`. Si cette lecture est juste, chaque lecture du paramètre `updateStatus` (`Node/Parameters/updateStatus.lua` lignes 15-16, rafraîchissement au démarrage) réécrit `/data/internal/lua-storage/status/`. Ce n'est pas un cron. Le fichier de `/persistent` reste ouvert en lecture.

### 1.5 Persistence : répertoire toujours non démontré

`Persistence.strings.txt` contient les noms `REBOOT`, `UPDATE`, `RESET`, les méthodes `put`, `get`, `del`, `clear`, `keys`, `keyExists`, et l'erreur `Invalid persistence layer name`. Aucune chaîne `/data`, `/apps` ou `/persistent`. Le seul chemin est le RPATH `/apps/overkiz/lib`.

Le symbole `Overkiz::Persistence::Factory::compat_createLayer(char const*, PersistenceType, LayerType)` est importé (valeur nulle dans la table dynamique). L'implantation est dans `libCore.so.4`, absent du complément. Le constructeur Lua lit deux arguments, ce qui correspond à `Layer(nom, type)` dans le corpus (`handler.lua` ligne 9, `modules.lua` lignes 249-250, `countryCode.lua` ligne 2, `updateAuto.lua` ligne 9).

**Démontré** : `Persistence.so` ne choisit pas un chemin. **Toujours non démontré** : le répertoire réel des couches `board`, `modules`, `module_options`, `region`, `updateAuto`. Les déclencheurs restent ceux du rapport : événement ou premier `put` si la clé manque, pas une période visible dans le Lua.

`Put` convertit deux chaînes Lua et appelle une méthode virtuelle de la couche. La réaction à un système de fichiers en lecture seule est dans `libCore`, donc **non démontrée**. Le binding importe de quoi transformer une exception C++ en erreur Lua (`Engine::error`). Cela ne dit pas si le processus survit.

### 1.6 Chemins du rapport dont l'environnement est maintenant connu

Le Lua lit ces variables dans `corpus/.../conf.lua`. Le fichier `complement/etc/conf.d/internal` en donne la valeur de l'image. Un processus déjà lancé peut différer : **à vérifier** par une lecture de `/proc/<pid>/environ`.

| Variable | Ligne | Valeur dans l'image | Effet sur le rapport |
|---|---|---|---|
| `STORAGE_DIR` | 1 | `/data/internal` | `have_user_data` → `/data/internal/have_user_data` (`conf.lua` ligne 69). Écriture dans `hasRecovered`, `system.lua` ligne 264. |
| `INTERNAL_RECOVERED_FILE` | 5 | `/persistent/apps//etc/recovered` | La suppression (`system.lua` ligne 263) vise `/persistent/apps/etc/recovered`. Le `//` est équivalent à `/`. |
| `INTERNAL_BOOT_FILE` | 6 | `/var/volatile/tmp/boot` | Hors des trois volumes UBIFS, si `/var/volatile` est bien volatile. **À vérifier** le montage. |
| `INTERNAL_CRL_FILE` | 19 | `/persistent/root/etc/ssl/local-apps-crl.pem` | Identique au défaut Lua. |
| `INTERNAL_PERSISTENT_SYSCONFDIR` | 14 | `/persistent/root//etc` | Fuseau : `/persistent/root/etc/tzdata` et `timezone`. |
| `INTERNAL_WATCHDOG_*` | 24-26 | `/dev/watchdog0`, `15`, `60` | Identiques aux défauts. |
| `INTERNAL_CONNMAN_AUTO_CONFIG` | 18 | `/var/lib/connman/auto.config` | Le défaut Lua `/var/volatile/...` est remplacé. Aucune écriture de ce fichier dans le corpus. Le point de montage de `/var/lib` est **à vérifier**. |
| `INTERNAL_SCRIPTSDIR` | 8 | `/apps/overkiz/share/internal/admin/scripts` | Les scripts cités par le rapport sont sous `/apps`. Leur contenu n'est pas dans ce dossier. |

`complement/lua/Overkiz/conf.lua` ligne 2 : `ENABLE_MONITORING_PATH = "/persistent/factory/enable-monitoring"`. La commande admin `monitoring` crée ou supprime ce fichier (`info.lua` lignes 80-84). Déclencheur : la commande, pas un cron.

`HTTP_LOG_PROPERTIES_FILE` n'est pas dans `conf.d/internal`. Le journal HTTP reste au défaut `/apps/overkiz/http-log/etc/properties.xml` (`conf.lua` du corpus, ligne 67), sur commande `log`.

## 2. Cron CRL : période et écritures sur /persistent

`RandomCron.lua` :

- ligne 3 : `86400`
- ligne 4 : `1800000`
- lignes 7-11 : l'heure d'exécution est `math.random(...) - 1`, tirée une fois à la construction
- lignes 21-42 : délai jusqu'à cette seconde du jour local (`os.date("*t")`, `os.time`), puis avance d'un jour tant que l'échéance est passée ; le résultat est en millisecondes
- lignes 45-68 : succès → ce délai ; échec → `failureDelay`
- lignes 72-82 : `start(true)` appelle `run()` tout de suite ; sinon le minuteur attend la prochaine échéance du jour
- ligne 17 : le journal dit `will be executed every day at ` et formate la seconde tirée en `!%H:%M:%S`

**Démontré** par la seule lecture cohérente avec cette phrase et avec les deux constantes. Les upvalues ne sont pas nommées par le décompilateur.

- `math.random` porte sur `86400`. L'heure est une seconde du jour, de 0 à 86399, stable pour la vie du processus.
- La boucle ajoute `86400` secondes à un `os.time`. La période de succès est un jour local.
- Le délai d'échec par défaut est `1800000` ms, soit 30 minutes. L'argument optionnel du constructeur est en secondes et multiplié par 1000 (ligne 10).

`Admin/system.lua` lignes 387-388, seulement si le certificat d'autorité des applications locales existe :

```lua
uv0(uv1.updateLocalAppsCrl, "Automatic local apps CRL update"):start(true)
```

Pas de troisième argument : l'échec retente après 30 min. `start(true)` lance un passage au chargement du module, puis le rythme quotidien. L'instance n'est pas conservée. `stop` (lignes 85-88) ne fait que lever un drapeau : il ne stoppe pas le minuteur monotone. Ici, rien ne peut l'appeler.

`updateLocalAppsCrl` (`system.lua` lignes 115-118) rejette la promesse si `UPDATE_URL` est absent, avant tout téléchargement. Le cron reste armé et se réveille, sans écrire. L'écriture n'a lieu que dans `FileUpdater`, vers `INTERNAL_CRL_FILE`, après HTTP 200, MD5, contrôle et `move` (`FileUpdater.lua` lignes 101-151). Un `move` raté est un rejet (`MOVE`, lignes 144-149), pas une erreur Lua brute. `RandomCron` programme alors le nouvel essai à 30 min.

`RandomCron` lui-même n'ouvre aucun fichier de `/persistent`.

Conséquence pour `updateAuto.lua` : le littéral `3600` (ligne 11) est le troisième argument du constructeur (lignes 99 et 148). C'est un nouvel essai au bout d'une heure après échec. `start(false)` (lignes 101 et 150) attend l'échéance quotidienne. Le cron n'est armé que si `enabled` vaut déjà `"true"`. Ce point du rapport est corrigé ; le reste (pas d'écriture flash dans le Lua, `image-update` externe) tient.

## 3. Watchdog : compteur du SAM9 et délai logiciel

### 3.1 Ce que le pilote programme

`complement/linux-v5.4/at91sam9_wdt.c` :

- Lignes 45-60 : compteur de 12 bits à 256 Hz. `WDT_COUNTER_MAX_SECS = ticks_to_secs(0xFFF) = 16`. Le maximum matériel est 16 s, exactement.
- Ligne 63 : `WDT_HW_TIMEOUT` vaut 2. Cette constante nourrit la valeur de repli du registre de mode (lignes 337-338), uniquement si Linux écrit ce registre.
- Lignes 10-12 et 163-168 : le registre de mode ne peut être écrit qu'une fois. Linux n'écrit que s'il lit encore `WDT_MR_RESET` (`0x3FFF2FFF`). Sinon il garde la valeur du chargeur d'amorçage.
- Lignes 267-317 : avec un arbre de périphériques, la durée matérielle vient de `atmel,max-heartbeat-sec`, plafonnée à 16 s. L'arbre n'est pas dans le complément. La durée réelle est **à vérifier** en lisant le registre, plus tard, sur le hub.
- Lignes 192-202 : le minuteur noyau caresse le matériel plusieurs fois par période matérielle (`max/4`, sinon `max/2`, sinon le minimum).

### 3.2 Les 60 s sont next_heartbeat

`at91_wdt_set_timeout` (lignes 146-149) enregistre `wdd->timeout` et appelle `at91_wdt_start`. `at91_wdt_start` (lignes 132-137) fait une seule chose :

`next_heartbeat = jiffies + timeout * HZ`

Aucune de ces fonctions n'écrit le compteur matériel. `at91_wdt_reset` (lignes 112-115), l'écriture du registre de contrôle, n'est appelée que par `at91_ping` (lignes 120-130).

`at91_ping` caresse le matériel et se reprogramme si `jiffies` est encore avant `next_heartbeat`, ou si le watchdog n'est plus actif. Sinon il journalise `I will reset your machine !` et ne se reprogramme pas. Le compteur matériel, privé de caresse, arrive alors à échéance dans le délai programmé au registre de mode, donc en 16 s au plus.

Les opérations exposées (lignes 258-263) sont `start`, `stop` et `set_timeout`. Il n'y a pas de `ping`. `stop` (lignes 140-144) retourne 0 et ne touche ni le minuteur ni le matériel. Le commentaire dit que le matériel ne peut pas être arrêté.

Le cœur `watchdog_dev.c` n'est pas dans le complément. **Démontré** par ce pilote : seuls `start` et `set_timeout` avancent `next_heartbeat`. Le keepalive d'`internald` (`Watchdog.lua` lignes 64-68, `WDIOC_KEEPALIVE`) ne peut rafraîchir ce délai qu'en rappelant l'une de ces deux fonctions. Le hub qui reste allumé au-delà de 60 s, déjà utilisé par le rapport, confirme que le keepalive le fait. Le fichier d'environnement lignes 25-26 et `Watchdog.lua` lignes 31-35 retiennent 15 s entre les keepalives et 60 s pour `WDIOC_SETTIMEOUT`.

Donc :

- toutes les 15 s, `internald` repousse `next_heartbeat` de 60 s ;
- pendant ces 60 s, le minuteur noyau caresse le compteur matériel ;
- le compteur matériel n'est pas réglé à 60 s.

`return true` du keepalive est démontré. `Timeout::expired` dans `Timer.so`, adresse `0xe04c`, enchaîne `Context::launch`, construit un `Boolean` avec la valeur de retour, appelle `Boolean::operator bool`, et, si le résultat est vrai et que le minuteur monotone est encore valide, appelle `Monotonic::start`. S'il est faux, `start` n'est pas appelé. Le texte `you can't cancel a timer and want to start it again` est le chemin où le rappel veut redémarrer un minuteur déjà annulé. Le rappel de `Watchdog.lua` lignes 57-61 retourne `true` après l'ioctl. Le nourrissage se réarme tant que ce rappel s'exécute.

### 3.3 Si internald cesse de nourrir

Deux situations.

**Le noyau continue.** Le dernier keepalive ou `SETTIMEOUT` a placé `next_heartbeat` à cet instant plus 60 s. `at91_ping` caresse le matériel jusqu'à cette échéance, puis s'arrête. Le compteur du SAM9 finit en au plus 16 s. Le délai qui décide est le délai logiciel de 60 s, suivi du solde matériel. Juste après un keepalive il reste environ 60 s plus au plus 16 s. Juste avant le keepalive suivant, environ 45 s plus au plus 16 s. La durée matérielle réellement programmée peut être plus courte que 16 s. Elle est **à vérifier**.

**Le CPU est arrêté par JTAG.** `at91_ping` est un `timer_list` réarmé par `mod_timer` (lignes 126 et 222-231). Un CPU en pause debug n'exécute plus ce minuteur, ni `internald`. Le minuteur noyau ne caresse plus le matériel pendant la pause. Le délai de 60 s ne s'écoule plus en caresses. Le compteur matériel, cadencé par l'horloge lente que le pilote active (lignes 352-360), continue, sauf gel.

Le gel est le bit `AT91_WDT_WDDBGHLT`. Le pilote le demande dans le registre de repli (ligne 338), et, en présence d'un arbre de périphériques, seulement si la propriété `atmel,dbg-halt` est présente (lignes 314-315). L'écriture n'a lieu que si le registre vaut encore la valeur de reset (lignes 163-168). L'arbre et le registre vivant ne sont pas dans le complément. **À vérifier** sur le hub, sans désactiver le watchdog : lire le registre de mode, ou un halt plus court que la période matérielle.

`WDIDLEHLT` (ligne 338 et propriété `atmel,idle-halt`) concerne l'état idle du processeur. Une pause JTAG n'est pas cet état.

### 3.4 Ce qui reste confirmé

Aucun module n'appelle `Watchdog:stop`. La fermeture avec l'octet `V` n'est pas le chemin d'exécution. `nowayout` est un paramètre du module (lignes 75-78), valeur par défaut `WATCHDOG_NOWAYOUT`, qui dépend de la configuration compilée, absente d'ici. **Toujours à vérifier.** Si le watchdog est marqué inactif, `at91_ping` continue de caresser le matériel (lignes 123-126) : un `stop` réussi ne laisserait pas expirer le compteur tant que le noyau tourne. Le code d'`internald` n'emprunte pas ce chemin. Le constat de mission, fermer `internald` réinitialise la carte, correspond au watchdog qui reste actif et à l'échéance de `next_heartbeat`, puis au compteur matériel.

## 4. La procédure P1 tient-elle encore

Oui pour l'ordre des opérations, tant que le CPU exécute encore `internald` et le noyau : laisser `internald` vivant, écarter les déclencheurs, `sync`, remonter `/apps`, `/data` et `/persistent` en lecture seule, vérifier, puis seulement arrêter le CPU. Ne pas envoyer `harakiri`, ne pas fermer `/dev/watchdog`, ne pas appeler `Watchdog:stop`.

Deux corrections changent le calendrier et le critère d'échec.

**Le budget de halt.** Pendant que le CPU tourne et qu'`internald` vit, le keepalive repousse `next_heartbeat` sans limite de 60 s. Le `sync` et les remontages n'ont pas à tenir dans 45 s. À l'instant du halt, ce délai ne protège plus : le minuteur noyau s'arrête avec le CPU. Sans `WDDBGHLT` dans le registre réel, la carte se réinitialise dans le solde du compteur matériel, au plus 16 s, souvent moins. Le chiffre « 45 à 60 s après le dernier nourrissage » du rapport (section 4, preuves, et section 1) ne doit pas servir de durée de pause JTAG. Le halt court de vérification demandé par le rapport devient le préalable, pas un essai facultatif.

**Une écriture après le passage en lecture seule.**

- CRL et fuseau, via `FileUpdater` : le `move` raté est rejeté (`FileUpdater.lua` lignes 139-150). `RandomCron` retente plus tard. Le processus continue. Démontré.
- `TableStorage` / `Storage` : `io.open` en `"w"` sans test (`TableStorage.lua` lignes 26-31). Sur un volume en lecture seule, `io.open` renvoie nil, et l'appel `:write` lève une erreur Lua. Aucun `pcall` dans ce module. **Démontré** que la bibliothèque ne gère pas l'erreur. **Non démontré** que le processus en meurt : `Timeout::expired` passe par `Context::launch`, dont le corps est dans `libLua.so`, absent. Si l'hôte avale l'erreur, `internald` continue et le keepalive, qui ne touche pas ces volumes (`Watchdog.lua` lignes 64-68), suit son cours. Si l'erreur tue le processus, le descripteur se ferme sans `"V"`. Tant que le noyau tourne, `at91_ping` nourrit encore jusqu'à `next_heartbeat` (environ 45 à 60 s selon l'instant du dernier keepalive), puis le compteur matériel ajoute au plus 16 s, et la carte repart. Ce n'est pas un reset immédiat. C'est un reset différé, incompatible avec une pause JTAG longue.
- `Persistence` : même incertitude, et le répertoire est inconnu. Un descripteur gardé ouvert par `libCore` empêcherait le remontage. Le relevé de descripteurs de P1 reste le critère de passage.

P1 demande déjà de ne pas lancer de commande, de ne pas toucher les boutons, et de contrôler qu'`internald` est toujours là avant le halt. Ces conditions couvrent l'erreur Lua : si le processus a disparu, on ne halte pas. Il faut y ajouter : ne pas compter 45 à 60 s une fois le CPU arrêté ; confirmer `WDDBGHLT` avant une pause plus longue que la période matérielle ; traiter un cycle sirène déjà armé comme un `:push` encore possible vers `/data/internal/lua-storage/generic-storage/`.

Le retour arrière du rapport reste valable tant qu'`internald` vit : remonter les volumes en lecture-écriture depuis le shell déjà ouvert. Aucune modification de firmware, aucune écriture NAND, aucune désactivation du watchdog.

P2 et P3 ne changent pas de rang. P3 reste écartée.

## 5. Ce qui reste à vérifier sur le matériel

- Registre de mode du watchdog : durée `WDV` réelle, et présence de `WDDBGHLT`. Halt court, sans désactiver le watchdog.
- `nowayout` compilé.
- `/proc/<pid>/environ` du processus vivant, pour confirmer que `conf.d/internal` est bien celui qui a été lu.
- Répertoires des couches `Persistence` (`libCore`), par les descripteurs ouverts, en lecture.
- Montage de `/var/volatile` et de `/var/lib`.
- Scripts sous `/apps/overkiz/share/internal/admin/scripts`, lus, non exécutés pour cet objectif.
- Autres processus écrivains, par le relevé de P1.
