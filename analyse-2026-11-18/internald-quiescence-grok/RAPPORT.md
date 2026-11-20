# Mise au repos des écritures d'internald, watchdog maintenu

Étude statique du 18 novembre 2026. Corpus : 201 modules Lua décompilés de `overkiz/internal/bin/internald`, dans `corpus/`. Aucun accès au hub, aucun essai sur le matériel.

Légende utilisée partout ci-dessous :

- **Démontré** : présent dans un module de ce corpus, avec fichier et ligne.
- **Identifié** : constante numérique du corpus, rapprochée d'un en-tête Linux public. Le nom n'est pas écrit dans le Lua.
- **Supposé** : lecture cohérente du décompilateur ou d'une bibliothèque absente du corpus.
- **À vérifier** : seulement sur le hub, plus tard, en lecture ou par observation.

Le décompilateur nomme les registres `slotN` et les upvalues `uvN`. Les upvalues sont numérotées par fonction, pas par fichier. Quand une correspondance `uvN` → symbole est nécessaire, elle est marquée supposée.

## 1. Watchdog

### Ce que le code fait au démarrage

`main.lua` construit un `Watchdog` et appelle `start()` avant le reste du service. L'instance n'est pas réutilisée dans la suite visible de `main.lua` : le champ `watchdog = slot6` référence un `slot6` jamais assigné dans ce fichier. C'est un artefact probable du décompilateur. Cela ne change pas le fait que `start()` est appelé.

```9:9:corpus/Overkiz/HomeAutomation/Protocol/Internal/main.lua
require("Overkiz.HomeAutomation.Protocol.Internal.Watchdog")():start()
```

```5:7:corpus/Overkiz/HomeAutomation/Protocol/Internal/main.lua
slot5 = {
	watchdog = slot6,
	dbusServer = require("Overkiz.DBusServer")("/com/overkiz/Application/Internal")
```

**Démontré.** Aucun autre module n'appelle `Watchdog`. Aucun module n'appelle `:stop()` sur cet objet : la seule définition de `stop` est dans `Watchdog.lua`, sans site d'appel dans le corpus.

### Paramètres

Défauts, remplaçables uniquement par l'environnement du processus, lus au chargement :

| Réglage | Variable | Défaut | Lieu |
|---|---|---|---|
| Périphérique | `INTERNAL_WATCHDOG_DEVICE` | `/dev/watchdog0` | `conf.lua` lignes 75 |
| Période de nourrissage | `INTERNAL_WATCHDOG_KEEPALIVE_INTERVAL` | `15` (secondes, voir plus bas) | `conf.lua` ligne 76 |
| Délai matériel | `INTERNAL_WATCHDOG_TIMEOUT` | `60` (secondes) | `conf.lua` ligne 77 |

```71:78:corpus/Overkiz/HomeAutomation/Protocol/Internal/conf.lua
	watchdog = {
		device = nil,
		keepAliveInterval = nil,
		timeout = nil,
		device = slot2("INTERNAL_WATCHDOG_DEVICE", "/dev/watchdog0"),
		keepAliveInterval = tonumber(slot2("INTERNAL_WATCHDOG_KEEPALIVE_INTERVAL", "15")),
		timeout = tonumber(slot2("INTERNAL_WATCHDOG_TIMEOUT", "60"))
	}
```

Le journal de démarrage affiche le chemin, la période et le délai réellement retenus (`Watchdog.lua` lignes 31-35). **À vérifier** : cette ligne de log sur le hub. Le contrôle du 18 novembre 2026 cite `/dev/watchdog` ; le défaut du code est `/dev/watchdog0`. Les deux peuvent être le même nœud si l'un est un lien. Ne pas les confondre tant que le lien n'est pas lu sur le hub.

### Séquence `start`

```38:61:corpus/Overkiz/HomeAutomation/Protocol/Internal/Watchdog.lua
function slot14.start(slot0)
	os.execute("killall -9 watchdog")

	slot1, slot2 = io.open(slot0.devicePath, "a+")
	...
	uv2(slot0.fd, uv3, uv4)
	uv7(slot0.fd, uv8, uv5.new("unsigned[1]", uv6))
	uv7(slot0.fd, uv9, uv5.new("unsigned[1]", slot0.watchdogTimeout))
	slot0:_touch()

	slot0.timer = uv10.Timeout(slot0.keepAliveInterval * 1000, function ()
		uv0:_touch()

		return true
	end)
end
```

**Démontré :**

1. `killall -9 watchdog` tue un éventuel démon utilisateur du même nom, puis `internald` ouvre le périphérique lui-même.
2. Ouverture en `"a+"`. L'ouverture arme le watchdog noyau. Le mode `a+` ne sert pas à journaliser : le descripteur sert aux `ioctl`.
3. Le descripteur Lua est converti par `fileno` (`Watchdog.lua` ligne 50).
4. Un `Timeout` rappelle `_touch` toutes les `keepAliveInterval * 1000` millisecondes. Avec le défaut, c'est 15 000 ms.
5. Le rappel retourne `true`.

**Supposé, fortement :** `return true` demande à `Overkiz.Timer.Timeout` de se reprogrammer. La bibliothèque n'est pas dans le corpus. Le même motif (`return true` dans un `Timeout`) est celui du serveur de métriques (`Monitoring/ObservabilityServer.lua` lignes 61-68). Un hub qui reste allumé plus d'une minute confirme déjà cette reprogrammation : sinon le délai matériel de 60 s aurait réinitialisé la carte.

**Identifié** à partir des littéraux de `Watchdog.lua` lignes 8, 9, 10 et 11, par la formule `_IOC` de Linux (`dir<<30 | size<<16 | type<<8 | nr`, type `'W'` = 87, `int` = 4 octets) :

| Littéral | Valeur | Ioctl |
|---|---|---|
| `slot8` | 2 | `F_SETFD` |
| `slot13` | 1 | `FD_CLOEXEC` |
| `slot9` | 2147768068 | `WDIOC_SETOPTIONS` (`_IOR('W', 4, int)`) |
| `slot12` | 2 | `WDIOS_ENABLECARD` |
| `slot10` | 2147768069 | `WDIOC_KEEPALIVE` (`_IOR('W', 5, int)`) |
| `slot11` | 3221509894 | `WDIOC_SETTIMEOUT` (`_IOWR('W', 6, int)`) |

Reconstruction de `start`, **supposée** sur l'ordre des upvalues, **cohérente** avec ces constantes : `fcntl(fd, F_SETFD, FD_CLOEXEC)`, puis `WDIOC_SETOPTIONS` avec `WDIOS_ENABLECARD` (2), puis `WDIOC_SETTIMEOUT` avec le délai configuré, puis un premier `WDIOC_KEEPALIVE`. L'autre lecture (passer 1, donc `WDIOS_DISABLECARD`, à `SETOPTIONS`) contredit le journal « Start watchdog » et le maintien en vie du hub. `FD_CLOEXEC` empêche un fils (`image-update`, scripts) d'hériter du descripteur.

`_touch` (`Watchdog.lua` lignes 64-68) envoie `WDIOC_KEEPALIVE` avec un pointeur `NULL` tant que `fd` est un entier positif. Ce n'est pas une écriture UBIFS.

### Arrêt prévu par le code, et pourquoi il ne sert pas ici

```70:78:corpus/Overkiz/HomeAutomation/Protocol/Internal/Watchdog.lua
function slot14.stop(slot0)
	if slot0.device then
		slot0.timer:cancel()
		slot0.device:write("V")
		slot0.device:close()
		...
	end
end
```

**Démontré :** `stop` annule le timer, écrit l'octet magique `"V"`, puis ferme le descripteur. **Démontré aussi :** aucun appelant dans les 201 modules.

Le caractère `V` est la fermeture magique documentée par le sous-système watchdog Linux. Elle ne désarme le compteur que si le pilote l'accepte. Le paramètre `nowayout` du pilote `at91sam9_wdt` n'apparaît nulle part dans ce Lua. **À vérifier** sur le hub (`/sys/module/at91sam9_wdt/parameters/nowayout`, ou la ligne de commande noyau). Le constat de mission (fermer `internald` réinitialise la carte) est compatible avec `nowayout` actif, et aussi avec une fermeture sans `V`. Ce rapport ne propose ni `stop()`, ni fermeture du descripteur, ni changement de `nowayout`.

### Signal, option, commande, mode maintenance

Recherche sur les 201 modules : aucun `posix.signal`, aucun `luv.signal`, aucun gestionnaire `SIGTERM` / `SIGUSR` enregistré par `internald`. Les `SIGUSR1` et `SIGUSR2` de `Admin/system.lua` lignes 40-49 sont envoyés à `http-logd`, pas reçus par `internald`.

Aucun mode nommé maintenance, mise à jour ou lecture seule ne suspend les autres activités tout en laissant tourner le timer de `Watchdog.lua`. Le timer est indépendant du reste : il vit tant que la boucle d'événements du processus vit et que `stop()` n'est pas appelé.

La seule commande qui arrête le processus est D-Bus `harakiri` (section 3). Elle termine le processus. Elle ne laisse pas un nourrisseur en place.

### Conséquence pour l'arrêt JTAG

Tant que le CPU exécute `internald`, le nourrissage a lieu toutes les 15 s (défaut) et chaque nourrissage reprogramme un délai matériel de 60 s (défaut). Juste après un nourrissage il reste environ 60 s ; juste avant le suivant, environ 45 s. **À vérifier** les deux valeurs dans le journal réel, car l'environnement peut les avoir changées.

Après l'arrêt du CPU par JTAG, ce Lua ne nourrit plus. Si le watchdog matériel n'est pas gelé par le halt de debug, la carte se réinitialise au plus tard à la fin du délai restant. Ce gel n'est pas déductible du Lua. **À vérifier** sur le matériel, sans désactiver le watchdog : un halt court, inférieur au délai restant, pendant qu'un observateur regarde si la carte repart. Le chargement de l'autre Linux doit tenir dans cette fenêtre, ou le nouvel environnement doit lui-même nourrir le même périphérique. Ce second point sort du corpus `internald`.

## 2. Inventaire des écritures vers `/apps`, `/data` et `/persistent`

Il n'existe aucun appel `sync`, `mount` ou `remount` dans le corpus. `internald` ne prépare pas lui-même le passage en lecture seule.

Les chemins ci-dessous sont les défauts de `conf.lua`. Chacun peut être déplacé par une variable d'environnement. **À vérifier** l'environnement réel du processus avant de conclure qu'un fichier est sur l'un des trois volumes.

### 2.1 Écritures dont le chemin est dans ce corpus

| Fichier ou répertoire | Volume par défaut | Déclencheur | Fréquence | Peut-on l'éviter sans tuer `internald` |
|---|---|---|---|---|
| `persistentSysConfDir .. "/tzdata"` puis `"timezone"` | `/persistent/root/etc/` | `setTimezone` | À la commande | Oui : ne pas envoyer la commande |
| `crlFile` | `/persistent/root/etc/ssl/local-apps-crl.pem` | cron automatique au chargement, et commande `updateLocalAppsCrl` | Période inconnue | Partiel, voir ci-dessous |
| `path.logFile` | `/apps/overkiz/http-log/etc/properties.xml` | `setLogConfig` | À la commande | Oui |
| `path.haveUserData` | `(STORAGE_DIR ou "") .. "/have_user_data"` | `hasRecovered` après acquittement cloud | Une fois, si recovery en cours | Oui si le fichier de recovery est déjà absent |
| `ENABLE_MONITORING_PATH` | Bibliothèque `Overkiz.conf`, chemin absent du corpus | Commande admin `monitoring` | À la commande | Oui |
| Destination de `image-update` | Arguments `root`, `apps`, parfois `bootloader`, `security`, `bootstrap` | Commande update/download, ou cron si `updateAuto` est actif | Horaire seulement si le cron est armé | Oui si le cron est inactif et qu'aucune commande n'est envoyée |
| `path.recoveredFile` | `/etc/recovered` (suppression) | `hasRecovered` | Une fois | Même condition que `haveUserData` |
| `path.bootFile` | `/tmp/boot` (suppression) | `hasBoot` | Une fois au boot cloud | Hors UBIFS si `/tmp` est un tmpfs. **À vérifier** |

Détail des chemins démontrés.

**Fuseau.** `setTimezone` (`Admin/system.lua` lignes 53-96) ne s'exécute que si `UPDATE_URL` est défini (lignes 64-67). Il télécharge vers `/persistent/root/etc/tzdata` via `FileUpdater`, puis `pl.file.write` écrit le nom de zone dans `/persistent/root/etc/timezone` (ligne 74). `timezoneHasChanged` (`bus/timezone.lua` lignes 5-12) émet seulement un signal D-Bus. `localtimeFile` (`/etc/localtime`) et `zoneinfoFile` (`/usr/share/zoneinfo`) sont définis (`conf.lua` lignes 65-66) et ne sont référencés nulle part ailleurs : ce corpus n'écrit pas le lien `localtime`.

**CRL.** Au chargement du module, si `/etc/security/app_ca.crt` existe, un `RandomCron` appelle `updateLocalAppsCrl` (`Admin/system.lua` lignes 97-102 et 387-391). L'instance du cron n'est pas conservée. Aucune fonction de ce module ne l'annule. `FileUpdater` n'écrit la destination qu'après HTTP 200, MD5 égal, contrôle OpenSSL et `mkdirp` (`Admin/FileUpdater.lua` lignes 101-151). Un échec réseau ou un MD5 identique ne déplace pas le fichier vers `/persistent`. Le téléchargement intermédiaire passe par `os.tmpname()` (ligne 100), en pratique sous `/tmp`. **À vérifier** que `/tmp` n'est pas sur UBIFS. La période du cron CRL n'est pas un nombre dans ce fichier : `RandomCron` est appelé avec le callback et un libellé seulement. **À vérifier** sur le hub la cadence réelle (journal « CRL successfully updated » ou « no newer version »).

**Journal HTTP.** `setLogConfig` ouvre `path.logFile` en `"w+"` (`Admin/common.lua` lignes 29-44, appelé par `Admin/system.lua` ligne 48). Déclencheur : méthode admin `log` avec `cmd == "put"` (`Transport/Admin/Objects/config.lua` lignes 25-28).

**Recovery.** `isRecovered` (`Admin/system.lua` lignes 252-259) est vrai si `haveUserData` et `/etc/recovered` sont tous deux absents, ou si `/etc/recovered` existe. Au démarrage du transport admin, un acquittement cloud positif appelle `hasRecovered` (`Transport/Admin/Objects/info.lua` lignes 145-151), qui supprime `/etc/recovered` et écrit l'horodatage dans `haveUserData` (`Admin/system.lua` lignes 262-265). Si cet acquittement n'a pas encore eu lieu, une écriture reste possible après la connexion cloud. `recovery.lua` ne fait que lire `/etc/recovered`.

**Monitoring.** `Transport/Admin/Objects/info.lua` lignes 78-85 crée ou supprime `ENABLE_MONITORING_PATH` sur la commande `monitoring`. Le chemin vient de `Overkiz.conf`, absent ici. **À vérifier** avec les descripteurs ouverts du processus.

**Mise à jour d'image.** Le Lua ne contient pas l'écriture flash. Il lance le binaire externe `image-update` :

- commande de nœud `update` : cibles `apps`, `root`, `bootloader`, `security`, `bootstrap` (`Node/Parameters/update.lua` lignes 9-31 et 68) ;
- commande `download` : `root`+`apps` ou `apps` (`Node/Parameters/download.lua` lignes 29-50) ;
- cron `updateAuto`, s'il est actif : `image-update -i <uuid> root apps upgrade` (`Node/Parameters/updateAuto.lua` lignes 39-45 et 60).

Le cron n'est armé que si la clé persistante `enabled` vaut `"true"` (`updateAuto.lua` lignes 98-101). Au premier `read`, si la clé est absente, le code écrit `enabled=false` (lignes 75-78) : une écriture de persistance, pas une écriture flash. Le troisième argument du cron est le littéral `3600` (`updateAuto.lua` ligne 11, passé ligne 99). L'unité n'est pas dans le corpus. **Supposé :** des secondes. **À vérifier.** À la fin d'une mise à jour automatique, le listener appelle `system.reboot` (`updateAuto.lua` lignes 16-24), qui programme `reboot.sh`.

`FileUpdater` sert uniquement au fuseau et à la CRL dans ce corpus. Son déplacement final est un `move` vers `localFile` (lignes 140-142).

### 2.2 Persistance dont le répertoire n'est pas dans ce corpus

`Overkiz.Persistence`, `Overkiz.Storage` et `Overkiz.TableStorage` ne font pas partie des 201 modules. Le type par défaut du service est `Persistence.Type.RESET` (`conf.lua` ligne 31). `countryCode` et `updateAuto` demandent `Type.UPDATE`. Aucun de ces types n'est défini ici : le répertoire (`/apps`, `/data`, `/persistent` ou ailleurs) est **à vérifier** par les fichiers ouverts du processus, pas par déduction.

Appels qui écrivent via ces bibliothèques (événement, pas une période) :

| Couche | Type | Écriture | Module |
|---|---|---|---|
| `"board"` | `RESET` | `:put` du nom de carte au premier démarrage, puis à chaque changement d'UI | `Boards/handler.lua` lignes 9-12 et 60 |
| `"modules"` | `RESET` | `:clear`, `:put`, `:del` | `modules.lua` lignes 249, 375, 492, 513 |
| `"module_options"` | `RESET` | `:put`, `:del` | `modules.lua` lignes 250, 496-499, 514 |
| `"region"` | `UPDATE` | `:put("countryCode")` | `Node/Parameters/countryCode.lua` ligne 18 |
| `"updateAuto"` | `UPDATE` | `:put` de `enabled`, `startAt`, `endAt`, `spanDays` | `Node/Parameters/updateAuto.lua` lignes 78 et 132-139 |
| `Storage("mode", …)` | module `…Internal.storage`, fichier absent | `:push` | `Mode/mode.lua` lignes 6, 155, 167 |
| `Storage("resyncModules", …)` | idem | `:push` | `bus/resync.lua` lignes 9, 20, 24 |
| `Storage` d'alarme et de LEDs | module `…Node.Parameters.storage`, fichier absent | `:push` sur `write` du paramètre | `activation.lua` 12, `alarmName.lua` 12, `currentMode.lua` 25, `delay.lua` 13, `intrusion.lua` 13, `lightingLedModemMode.lua` 13, `lightingLedPodMode.lua` 22, `mode.lua` 36, `siren.lua` 64 et 118 |

`NodeManager.saveAndReload` affecte une table issue de `TableStorage("nodes")` (`Node/NodeManager.lua` lignes 11 et 148). `update.lua` ligne 7 charge `TableStorage("status")` puis y recopie le fichier de statut (lignes 27-38). **Supposé :** une affectation peut persister si la bibliothèque a un métatable d'écriture. **Non démontré** par ce corpus. Le fichier de statut lui-même, `/persistent/boot/update/version-hash.txt` (`conf.lua` ligne 35), est ouvert en lecture (`update.lua` ligne 21), pas en écriture.

Les modules `Overkiz.HomeAutomation.Protocol.Internal.storage` et `…Node.Parameters.storage` sont nommés et absents du corpus. Leur nom est un nom de module Lua, pas un chemin disque.

### 2.3 Processus externes lancés par internald

Ces programmes ne sont pas dans le corpus. Leurs écritures sont **à vérifier** en lisant les scripts sur le hub, sans les exécuter pour cet objectif :

- `/scripts/reboot.sh` après l'échéance de `system.reboot` (`Admin/system.lua` lignes 304-332). Le timer n'est pas exposé pour annulation.
- `/scripts/bootloader-upgrade.sh start` (`Admin/system.lua` lignes 383-385), commande admin `upgrade`.
- `/scripts/coredump.sh` et `/scripts/ssh.sh` (`Admin/system.lua` lignes 192-217).
- `/scripts/enable-protocols.sh` (`modules.lua` ligne 294).
- `/etc/init.d/<service> start|stop|restart` (`Service.lua` lignes 19 et 149-198). `stopAllServices` n'est appelé que par `harakiri`.

`system.run` (`Admin/system.lua` lignes 335-340) exécute une chaîne shell bornée par `timeout 120`. La commande admin `run` peut donc lancer n'importe quel écrivain. Pendant la fenêtre de repos, aucune commande admin ne doit être envoyée. Le corpus ne fournit pas de verrou qui les refuserait.

`wifiAPConfigFile`, `connmanAutoConfigFile`, `wificountryFile` et les certificats Bluetooth sont lus ou seulement déclarés. `connmanAutoConfigFile` pointe par défaut vers `/var/volatile`, hors des trois volumes UBIFS. Aucune écriture de ces fichiers n'est présente dans le corpus.

Les définitions de carte, dont `at91-kizbox3-cozytouchV2.lua`, pilotent des LED dans `setFunction` (ligne 688 et suivantes). Elles n'ouvrent pas de fichier. Les noms `stm32StartUpgrade` / `stm32ApplyUpgrade` ne sont pas, dans ce fichier, une écriture NAND.

### 2.4 Ce qui continue même si personne n'envoie de commande

Sans action extérieure, les seuls écrivains spontanés démontrés sont :

1. le cron CRL, si le certificat d'autorité des applications locales existe et si `UPDATE_URL` est défini ;
2. le cron `image-update`, seulement si `updateAuto.enabled` vaut déjà `"true"` ;
3. un `reboot.sh` déjà programmé (journal « Update planned in ») ;
4. `hasRecovered`, si un acquittement de recovery est encore en attente ;
5. éventuellement la persistance cachée dans `TableStorage` / `Storage` / `Persistence` lors d'un événement (bouton, cloud, modem). Leur période propre n'est pas démontrée.

Le nourrissage du watchdog, le timer d'une seconde de `main.lua` (lignes 89-101) et l'envoi de métriques HTTP (`ObservabilityServer.lua`) ne sont pas des écritures UBIFS dans ce corpus. Le timer d'une seconde ne fait un travail modem que si le nom de carte contient `kizbox2`.

## 3. Mécanismes constructeur déjà présents

Ils préparent un redémarrage ou une mise à jour. Aucun ne réalise « écrivains arrêtés, `sync`, volumes en lecture seule, watchdog encore nourri ».

### `Watchdog.lua`

Nourrit le watchdog et, seulement via `stop()` jamais appelé, tente de le désarmer. Pas un mode de maintenance.

### `update.lua` et `harakiri`

Méthode D-Bus `harakiri` sur `com.overkiz.Application.Internal.Update`, signature `"s"` ou `""` (`update.lua` lignes 78-101).

- Signature `"s"` : rappelle `exitStatus` avec le code 0, arme `os.exit(0)` sur un délai de 1 000 ou 2 000 ms (`slot11` / `slot12`, lignes 11-12 ; l'upvalue exacte est supposée), et appelle `stopAllServices` sur l'autre délai.
- Signature `""` : `os.exit(0)` sur un de ces délais, et `stopAllServices()` tout de suite.

`stopAllServices` (`modules.lua` lignes 470-485) coupe l'auto-redémarrage, envoie `forceStop` à chaque service `init.d` géré, arrête le cloudlink, puis résout une promesse. Ensuite le processus se termine. La fermeture du descripteur watchdog se fait alors sans l'écriture `"V"` de `stop()`. Avec le comportement constaté en mission, cela réinitialise le hub. `harakiri` ne appelle ni `sync` ni `mount`.

`updateStatus` ne fait que notifier. `exitStatus` rappelle les callbacks d'un `image-update`. La lecture de `version-hash.txt` est une lecture.

### `recovery.lua`

Lecture unique de `/etc/recovered`. Pas de préparation flash.

### `reboot.lua` (paramètre de nœud)

Redémarre ofono / telit (`Node/Parameters/reboot.lua` lignes 5-8). Cela ne concerne pas UBIFS ni le watchdog. À ne pas confondre avec `Admin/system.lua` `reboot`, qui programme `/scripts/reboot.sh`.

### `Service.lua`

Cycle de vie des autres démons (`/etc/init.d/<nom> start|stop|restart`). Il ne détient pas le watchdog. `forceStop` est le moyen, déjà utilisé par `harakiri`, d'arrêter ces démons. L'appeler seul laisserait `internald` vivant ; le corpus ne l'expose que par `harakiri`, qui quitte ensuite.

### Scripts de boot

`bootMode`, `rebootMode` et `rebootReason` lisent des fichiers (`Admin/system.lua` lignes 275-285). Les défauts de `bootnextFile` et `bootmodeFile` sont des chaînes vides (`conf.lua` lignes 62-63) : le chemin réel est **à vérifier** dans l'environnement. `upgradeBootloader` lance un script externe. Ce n'est pas un modèle de mise au repos : c'est une écriture de bootloader possible.

## 4. Procédures candidates

Contrainte commune : ne pas modifier le firmware, ne pas écrire la NAND, ne pas fermer `/dev/watchdog`, ne pas envoyer `harakiri`, ne pas appeler `Watchdog:stop`. Le remontage en lecture seule est fait depuis un shell déjà ouvert sur le hub, pas en ajoutant un fichier sur les volumes.

Le corpus ne couvre pas les autres processus. La preuve d'absence d'écrivain est un relevé sur le hub (`fuser` ou descripteurs de `/proc` sur `/apps`, `/data` et `/persistent`), pas une conclusion de cette lecture.

### P1 — Laisser internald en vie, écarter les déclencheurs, sync, remount. Risque le plus bas. Procédure recommandée.

**Préconditions, toutes à vérifier, aucune à provoquer :**

- Le journal contient `Start watchdog` avec un délai connu. Noter `timeout` et `keepAliveInterval`.
- `ps` ne montre pas `image-update`, `reboot.sh` ni `bootloader-upgrade.sh`. Si `image-update` tourne, la fenêtre n'existe pas : attendre la fin du cycle, y compris le redémarrage qu'il peut avoir armé. Ne pas le tuer : une mise à jour flash interrompue est précisément le dégât à éviter.
- Le journal ne contient pas un « Update planned in » encore dans le futur. Ce timer n'a pas d'annulation exposée. S'il est armé, laisser le redémarrage se faire et reprendre sur le boot suivant, avant toute nouvelle commande de reboot.
- La persistance `updateAuto` / `enabled` n'est pas `true`. La lire sans appeler le `write` du paramètre, car le `write` réécrit la couche.
- Décider du cron CRL : `UPDATE_URL` vide, ou fichier CA absent, ou dernier cycle déjà passé et aucun transfert `FileUpdater` en cours. Sinon une publication de CRL peut encore écrire `/persistent` au prochain tir. Il n'y a pas d'arrêt de ce cron dans le Lua.
- `/etc/recovered` absent et `have_user_data` déjà présent, ou cloud non connecté, afin que `hasRecovered` ne parte pas pendant la fenêtre.
- Aucun client admin (fuseau, log, protocoles, monitoring, `run`, `upgrade`, download, update) pendant toute la fenêtre. Ne pas appuyer sur les boutons de la carte : ils changent le mode et peuvent pousser `Storage`.

**Étapes :**

1. Relever les écrivains des trois points de montage, `internald` inclus. Classer chaque descripteur ouvert en écriture : UBIFS, ou périphérique de type watchdog / socket / sysfs.
2. Arrêter depuis le shell, un par un, les processus autres qu'`internald` qui ont un descripteur en écriture sur ces volumes, en laissant leur arrêt init se terminer. Ne pas arrêter `internald`. Si un script d'arrêt écrit encore, le relevé de l'étape 1 le montrera au tour suivant.
3. Refaire le relevé. La condition de passage est : plus aucun descripteur en écriture sur les trois volumes, à l'exception éventuelle de fichiers que le relevé aura montrés comme seulement relus par `internald`. Un descripteur encore ouvert en écriture par `internald` sur `/persistent` ou `/apps` interdit le remontage.
4. `sync`.
5. Remonter `/apps`, `/data` et `/persistent` en lecture seule.
6. Vérifier. Si un remontage échoue, ne pas arrêter le CPU.

**Preuves à collecter avant l'arrêt JTAG :**

- `/proc/mounts` : les trois volumes ont l'option `ro`.
- Nouveau relevé de descripteurs : aucune ouverture en écriture sur ces volumes.
- Compteurs mémoire `Dirty` et `Writeback` revenus à zéro après le `sync` et restés à zéro après quelques secondes (le nourrissage watchdog, toutes les 15 s, ne doit pas les faire remonter).
- Le processus `internald` est toujours là, et son descripteur vers le watchdog vu au démarrage est toujours ouvert.
- Horodatage du dernier journal watchdog ou, à défaut, l'heure du `sync` : l'arrêt JTAG doit suivre dans le délai restant (défaut : 45 à 60 s après le dernier nourrissage, voir section 1).

**Échecs :**

- Remontage refusé parce qu'un descripteur tient le volume : rester en lecture-écriture, identifier le processus, ne pas halt.
- `Dirty` qui réaugmente : un écrivain tourne encore. Ne pas halt.
- `image-update` ou `reboot.sh` apparu entre-temps : ne pas halt.

**Retour arrière :** ne rien écrire de plus. Si le remontage a réussi et que l'arrêt JTAG est annulé, remonter les trois volumes en lecture-écriture depuis le shell. `internald` n'a pas été arrêté, le watchdog n'a pas été fermé. Aucun fichier de firmware n'a été modifié par cette procédure.

### P2 — Même séquence, en arrêtant d'abord tous les services init.d sauf internald. Risque moyen.

Intérêt : élargir P1 si le relevé montre beaucoup de démons. Le code de `Service.lua` montre que l'arrêt passe par `/etc/init.d/<nom> stop`, ce qui peut lui-même écrire un état. Faire l'arrêt, attendre la fin des scripts, puis seulement appliquer les étapes 3 à 6 de P1.

Ne pas passer par `harakiri` pour obtenir cet arrêt : `harakiri` enchaîne avec `os.exit(0)`.

**Échec propre à P2 :** un script `stop` tué ou interrompu au milieu d'une écriture UBIFS. Le retour arrière de P1 reste valable tant que `internald` vit. Si un volume a été corrompu par cet arrêt, ce n'est plus un retour arrière logiciel : c'est un incident flash, hors de ce que cette procédure doit provoquer. D'où l'ordre : P1 d'abord, P2 seulement pour les démons que le relevé désigne.

### P3 — Écartée. `harakiri`, `kill` d'internald, ou `Watchdog:stop`.

`harakiri` arrête les autres services puis termine `internald` en une à deux secondes (`update.lua` lignes 80-101). Le descripteur watchdog se ferme sans `"V"`. Le nourrissage cesse immédiatement. Il n'y a ni `sync` ni remontage. Le délai restant avant reset est alors quelconque entre zéro et `timeout`, pas la fenêtre stable de P1.

`Watchdog:stop` écrirait `"V"` et fermerait le périphérique (`Watchdog.lua` lignes 70-74). C'est une tentative de désarmement. Elle est exclue, qu'elle réussisse (`nowayout` inactif) ou qu'elle laisse le compteur courir (`nowayout` actif).

Tuer `internald` par un signal a le même effet qu'une sortie sans `stop()` : pas de gestionnaire dans le corpus, fermeture du descripteur, reset attendu.

## 5. Limites

- Bibliothèques absentes : `Overkiz.Persistence`, `Overkiz.Storage`, `Overkiz.TableStorage`, `Overkiz.Timer`, `Overkiz.RandomCron`, `Overkiz.conf`. Les chemins de persistance et la période du cron CRL ne sont pas démontrés.
- Les 201 modules ne décrivent pas les autres démons du hub. P1 exige le relevé de descripteurs pour cette raison.
- `nowayout`, le gel du watchdog pendant le halt JTAG, le point de montage de `/tmp` et de `STORAGE_DIR`, et les valeurs réelles d'environnement sont hors corpus.
- Une upvalue de `main.lua` (`slot6`) est incohérente. Elle ne crée pas de second watchdog dans le code visible.
- Cette étude ne dit pas que les volumes sont actuellement au repos. Elle décrit comment le code peut encore écrire, et la seule séquence qui laisse le nourrissage en place.
