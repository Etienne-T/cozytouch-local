# Revue de robustesse du service UART/MQTT

Revue statique du 2026-11-18. Corpus : `<CHEMIN_LOCAL>` (sept modules Lua et annexes). Aucun essai LuaJIT, aucun accès réseau, aucun accès à un appareil. Les constats « démontrés » se lisent dans ce corpus. Les constats « supposés » dépendent du noyau, du démon constructeur ou d'un calendrier particulier.

Installation durable : pas dans l'état lu. Deux sujets d'abord : ne pas rendre `/dev/ttyS1` tant qu'un READ est armé ; ne pas traiter le scan de `/proc` comme une preuve de propriété exclusive. Le service ne contient pas de chemin vers une consigne de chauffage ni vers une initialisation à froid.

## Élevé

### 1. Le port est fermé alors qu'un READ peut encore être armé

Démontré. `service.lua` lignes 33-34 et 64. `uart.lua` lignes 159, 205 et 212-226. `cadence.lua` ligne 5.

La boucle de `service.lua` s'arrête dès que `Net.now() >= absolute - 1`, sans regarder `uart.active`. Sur TERM ou INT, elle fait `break` tout de suite (ligne 34). Dans les deux cas, la ligne 64 appelle `uart:close()` immédiatement.

`cadence.lua` autorise une paire tant qu'il reste 17 s. Le second READ part dès qu'il reste 8,5 s (`service.lua` ligne 54). `uart.lua` ligne 205 arme alors l'échéance à `min(now+8, absolute)`. Au plus tard, ce READ commence à `absolute - 8,5` et son échéance est `absolute - 0,5`. La boucle, elle, ne rappelle plus `step` à partir de `absolute - 1`. Si la réponse n'est pas arrivée, `active` est encore posé : le service restaure les termios, lève `TIOCEXCL` et ferme le descripteur pendant que le STM32 peut encore répondre.

`receive` refuse `now >= absolute` (`uart.lua` ligne 159) avant que `tick` puisse poser `TIMEOUT` si l'échéance vaut `absolute`. Prolonger la boucle jusqu'à `absolute` sans modifier `bounded` transformerait cette fin de lecture en erreur « UART whole-run deadline », avec la même fermeture.

Conséquence : le démon constructeur peut reprendre `/dev/ttyS1` au milieu de la transaction. Ce n'est pas un second ordre du service. C'est un port partagé après un READ déjà émis. `close` ne purge pas non plus le tampon d'entrée : les octets déjà reçus restent disponibles pour le prochain ouvreur.

Correction proposée, sans réécrire le service :

1. Dans `cadence.lua`, n'autoriser `can_start` que si `deadline - now >= 18` (17 s de paire plus 1 s de marge de boucle).
2. Dans `service.lua`, ne plus sortir de la boucle tant que `uart.active` est vrai, sauf échéance absolue. Sur TERM ou INT : ne plus appeler `start`, continuer `step` jusqu'à `active == nil` ou jusqu'à l'échéance de cette transaction.
3. Dans `uart.lua`, armer les 8 s après la dernière écriture réussie, avec une échéance au plus `absolute - 0,2`. Dans cette dernière attente, ne pas faire échouer `receive` par `bounded` : laisser `tick` conclure `TIMEOUT`.
4. Dans `close`, seulement une fois la transaction terminée ou expirée : purger l'entrée série (`TCFLSH` / `TCIOFLUSH`, numéro à confirmer dans les en-têtes du hub) puis restaurer les termios et fermer.

## Moyen

### 2. Le contrôle « seul propriétaire » peut manquer un processus

Démontré pour le critère lu dans le code. `uart.lua` lignes 161-170 et 184-187. Effet contre un processus root : supposé.

`noowners` ne signale un propriétaire que si `readlink` renvoie exactement la chaîne `/dev/ttyS1`. Un autre chemin vers le même périphérique (lien, `st_rdev` identique) ne compte pas. `readdir` qui renvoie `NULL` termine la liste : une erreur n'est pas distinguée de la fin, et le reste de `/proc` n'est pas vu. `readlink` négatif est ignoré (`n>0` seulement), donc un descripteur illisible n'empêche pas l'ouverture.

Le verrou `flock` de `/run/ct/autonomous-uart.lock` ne lie que les clients qui l'utilisent. `TIOCEXCL` (`uart.lua` ligne 187) n'empêche pas, d'après le contrat Linux habituel, un processus `CAP_SYS_ADMIN` d'ouvrir le port. Le démon constructeur est souvent root : c'est supposé ici, le corpus ne le prouve pas.

Le second scan après `TIOCEXCL` et l'échec fermé si `/proc/<pid>/fd` est illisible alors que le processus existe sont de vrais garde-fous. Ils ne couvrent pas les trous ci-dessus. L'intervalle entre le scan et `open` existe ; le second scan le referme pour un chemin canonique, pas pour un alias.

Correction proposée : avant d'accepter un descripteur, comparer `st_rdev` (après `fstat` du fd et `stat` de `/dev/ttyS1`), pas le texte du lien. Mettre `errno` à 0 avant `readdir` et traiter `NULL` avec `errno ~= 0` comme un échec. Si `readlink` échoue pour une raison autre que la disparition du lien, arrêter. Conserver le `flock` et `TIOCEXCL` comme compléments, pas comme seule preuve.

### 3. Une panne MQTT n'arrête pas les READ, et le processus peut quand même réussir

Démontré. `service.lua` lignes 35, 52-56 et 71. `mqtt.lua` lignes 61-121.

`mqtt:step` absorbe ses erreurs et se déconnecte. L'itération suivante appelle quand même `uart:start` si la cadence le permet. Aucun test de `mqtt.state == 'ready'`. Chaque `start` écrit la trame READ de 46 octets (`uart.lua` lignes 201-210). Ce n'est pas une consigne : l'allowlist des octets 40 à 44 reste `01 03 03 00 00`. C'est quand même un ordre radio, émis parce que la boucle continue alors que le courtier est en panne.

Le README du corpus décrit ce découplage. Le critère 6 de la mission ne le retient pas : un défaut du courtier ne doit pas entraîner d'action sur le matériel.

La ligne 71 ne conditionne le succès qu'à `interrupted` ou `reads >= 2`. `mqtt_pubacks` est journalisé, pas exigé. Deux lectures UART et zéro PUBACK donnent un processus qui se termine sans `error`. Une supervision qui ne lit que le code de sortie ne voit ni la panne du courtier, ni la différence entre `TIMEOUT`, `DEVICE_ERROR` et un reset `0x050e` (tous passent par `error` Lua).

Correction proposée : n'appeler `uart:start` que si `mqtt.state == 'ready'`. Ne pas fermer l'UART seulement parce que le courtier est absent. Si l'arrêt est demandé ou si la durée expire, finir la transaction déjà armée, puis fermer. En `--run`, refuser un succès sans le PUBACK de `online` et sans le PUBACK de chaque état publié. Réserver des codes de sortie distincts, par `os.exit`, pour courtier, appareil et STM32, et ne pas relancer la radio depuis ces codes.

### 4. Le DISCONNECT d'arrêt peut ne pas partir, et le LWT `offline` part alors

Démontré. `mqtt.lua` lignes 124-128. `net.lua` lignes 50-53. Le commentaire de `graceful_disconnect` dit qu'une écriture courte non bloquante ne suffit pas : sans paquet complet, le courtier publie le LWT. La ligne suivante fait exactement un `io:write` de deux octets, sans regarder le nombre écrit, puis `close_abrupt`. `t:write` a le droit de rendre `0` (`EAGAIN`) ou un compte partiel. `pcall` masque aussi une erreur dure de `send`.

`offline_acked` exige déjà le PUBACK de `offline` retenu. L'état retenu peut donc être `offline` et le LWT répéter le même `offline`. Ce n'est pas une valeur `online` fantôme sur cet arrêt-là. C'est un écart au contrat d'arrêt normal du README (publier `offline`, attendre l'ACK, fermer sans laisser le LWT repartir).

L'essai `--mqtt-test` ferme exprès sans DISCONNECT (`service.lua` lignes 21 et 24). Ce chemin-là est voulu.

Correction proposée : après `offline_acked`, écrire `0xe0 0x00` en boucle jusqu'à deux octets envoyés ou jusqu'à une échéance courte (200 ms sur l'horloge monotone). N'appeler `close` qu'ensuite. Si l'échéance est dépassée, fermeture abrupte : le LWT `offline` est alors assumé. Étendre le faux transport de `selftest.lua` (déjà capable d'une écriture d'un octet, lignes 55-56) à ce DISCONNECT. Le test actuel, ligne 47, utilise une écriture large et ne voit pas le défaut.

Le budget d'arrêt de 0,7 s (`service.lua` ligne 66) peut aussi expirer pendant un PUBACK encore en vol (délai de 5 s, `mqtt.lua` ligne 107). Même correction de repli : pas de second READ, fermeture abrupte, LWT `offline`.

### 5. Les droits et le type des fichiers de configuration ne sont pas vérifiés

Démontré pour l'absence de contrôle. `service.lua` lignes 4 et 11. `config.lua` lignes 19-20. `uart.lua` ligne 24. Effet d'un lien ou d'un tube : supposé, selon ce qui est déposé sous `/run/ct/`.

`io.open` suit les liens. Aucun `lstat`, aucun test de mode, aucun test « fichier régulier ». Le README demande `0600` pour le service et pour les cibles. Les cibles portent la clé de 16 octets (`uart.lua`, `field_sizes` et ligne 33). Un fichier `0644`, un lien hors de `/run/ct`, ou un tube nommé qui bloque le `read` sont acceptés par le texte du code. Le masque `..` et le préfixe `/run/ct/` limitent le chemin lexicale, pas le fichier pointé.

Les valeurs par défaut `interval_seconds = 30` et `duration_seconds = 95` (`config.lua` ligne 20) s'appliquent si la clé est absente. La durée minimale acceptée par `parse` est 1 s (ligne 22), alors que `--run` exige au moins 20 s (`service.lua` ligne 26). `--check-config` peut donc annoncer `CONFIG_OK` pour une durée que `--run` refusera. Le port `1883` reste autorisé (plancher 1024) : supposé qu'un courtier du LAN sans authentification recevrait alors des topics `cozytouch-lab-*`. Aucun identifiant MQTT n'est envoyé, le code ne sait pas en porter.

`read(..., 2048)` accepte 2048 octets (`service.lua` ligne 11) et `UART.config` rejette `#text >= 2048` (`uart.lua` ligne 24). Démontré, impact limité à un fichier limite refusé.

Correction proposée : `lstat` des deux fichiers, refuser lien, tube et tout mode hors `0600`, et exiger le propriétaire égal à l'uid du processus. Exiger la présence des clés `interval_seconds` et `duration_seconds`. Aligner le plancher de durée de `parse` sur 20 s pour un fichier destiné à `--run`, ou faire échouer `--check-config` avec le même critère que `--run`. Aligner la borne des cibles sur `<= 2047` aux deux endroits.

## Faible

### 6. Les 8 secondes démarrent avant la fin de l'écriture

Démontré. `uart.lua` lignes 205-209.

`M.transaction` est créé avant la boucle d'écriture, dont l'échéance propre est 0,5 s. Le temps d'écriture est pris sur les 8 s de réponse. La borne « il reste 8,5 s » côté service couvre ce 0,5 s seulement si l'écriture va au bout. Le critère « délai maximal de 8 s par lecture » est donc plus court côté réception dès que `write` est partiel ou répété.

Correction proposée : capturer `deadline` après `off == #packet`, valeur `min(now+8, absolute - 0,2)`.

### 7. L'UART et le verrou n'ont pas `O_CLOEXEC`

Démontré. `uart.lua` lignes 184-186. `net.lua` ligne 39 montre le flag déjà utilisé pour le socket : `SOCK_CLOEXEC` est dans `0x80801`.

L'ouverture série est `0x902` (`O_RDWR|O_NOCTTY|O_NONBLOCK`) et le verrou `0x42` (`O_RDWR|O_CREAT`). Aucun `fork` ni `exec` dans le corpus : un héritier n'existe que si une évolution en ajoute un. Sans `O_CLOEXEC`, cet héritier garderait le port après la fermeture du descripteur Lua.

Correction proposée : ouvrir l'UART avec `0x80902` et le verrou avec `O_CLOEXEC` en plus de `0x42`.

### 8. TERM et INT ne sont masqués que dans `--run`

Démontré. `service.lua` ligne 30, après les branches `--mqtt-test` (lignes 14-25). `--mqtt-test` ne prend pas l'UART. Un TERM pendant ces 8 s tue le processus sans `close` TCP. Le LWT peut quand même publier `offline` si le CONNECT avait abouti. Impact limité à l'essai.

Correction proposée : installer le même `stop_signals` pour `--mqtt-test`, et fermer le socket dans le chemin d'arrêt.

## Comportements conformes au critère de sûreté

Ces points ont été lus. Ils ne demandent pas de correctif pour la raison indiquée.

- Une seule trame en émission : `M.request` puis l'allowlist de `start` (`uart.lua` lignes 39-45 et 204). Pas de `SUBSCRIBE`, pas de topic de commande (`mqtt.lua` lignes 42-43, refus testé dans `selftest.lua` ligne 58). Un paquet courtier inattendu coupe MQTT dans le `pcall` de `step` (`mqtt.lua` lignes 101 et 121) et n'écrit pas sur l'UART.
- Un statut UART autre que `DONE` ne publie pas d'état et ne relance pas de READ (`service.lua` lignes 38-47). `0x050e` arrête par `assert` sans trame d'initialisation (`uart.lua` lignes 216 et 222).
- L'erreur de la boucle passe par `xpcall`. Si `open_session` échoue, il ferme lui-même avant de propager (`uart.lua` ligne 193) et `service.lua` ne voit pas d'objet `uart`. Si la session est ouverte, `close` est appelé avant l'arrêt MQTT (`service.lua` lignes 64-68).
- Reprise MQTT : backoff 1, 2, 4, 8 puis 16 s (`mqtt.lua` lignes 51-54), pas de boucle serrée. File bornée à quatre topics, dernière valeur seulement (lignes 41-46 et 53). Un PUBACK dont la charge ne correspond plus à `latest` laisse `dirty` en place (lignes 95-98). L'intervalle radio part de la fin de paire sur l'horloge monotone (`cadence.lua` ligne 7, `net.lua` ligne 21, `clock_gettime(1)`). Il ne se raccourcit pas.
- `online` n'est demandé qu'une fois `uart.ready` (`service.lua` ligne 51). Les champs publiés restent des bruts nommés, avec `value_semantics` fixe (lignes 41-46).

## Points à vérifier à l'exécution

À faire sur le hub, après correctif, avec le coordinateur. Cette revue ne les a pas exécutés.

1. TERM pendant un READ lent : aucun octet nouveau vers le STM32, `close` seulement après `DONE` ou `TIMEOUT`, termios d'origine relus par `TCGETS`, puis seulement le démon constructeur.
2. Second READ démarré vers `absolute - 8,5` s, réponse après 7,6 s : le service doit encore la lire, ou sortir en `TIMEOUT` sans rendre le port avant.
3. Courtier coupé après `online` : plus de ligne `TX_READ` dans le journal, UART encore détenu jusqu'à la fin de la transaction déjà partie, code de sortie distinct d'un `DEVICE_ERROR`.
4. Arrêt normal : un `offline` retenu acquitté, pas un second `offline` de LWT. Le contrôle se fait sur le courtier, pas seulement dans le journal du client (déjà dit dans le README).
5. Fichiers `0644`, lien symbolique et tube sous `/run/ct/` : refus avant toute ouverture UART.
6. Deuxième processus, et ouverture de l'inode `ttyS1` par un chemin autre que `/dev/ttyS1` : refus avant `TX_READ`.
7. SIGKILL : pas de restauration logicielle possible. Le coordinateur doit restaurer le port et ne pas relancer le service ni le démon sur un code d'erreur UART.
8. Horloge civile fausse : les topics doivent rester exploitables par `session_id`, `observed_monotonic_ms` et `read_sequence`, pas par `observed_epoch` seul. `online` ne signifie pas que la mesure est fraîche.

## Limites de cette revue

`selftest.lua` n'appelle pas `service.lua`, `net.lua` ni `open_session`. La cadence, les paquets MQTT et le codec UART y sont couverts. La propriété du port, les signaux, la boucle et l'arrêt ne le sont pas.

`corpus-manifest.json` et `corpus/MANIFEST-SHA256.json` donnent le même condensat pour les six autres modules qu'ils citent tous les deux, et deux condensats différents pour `selftest.lua`. Dans le selftest lu, les `gsub` d'adresse remplacent `<ip-redige>` par `<ip-redige>` (lignes 8-11 et 19). Ce sont des opérations nulles : les cas « loopback exact », « autre 127/8 » et « adresse publique » ne sont plus distincts. `config.lua`, lui, n'accepte qu'une IPv4 canonique privée ou `127.0.0.1`. Ne pas « corriger » `config.lua` pour accepter le jeton `<ip-redige>` : la mission dit que ce jeton remplace les adresses dans le corpus de revue. Ne pas prendre ce selftest comme preuve des contrôles d'adresse.

`uart-session.lua.inc` reprend le backend déjà présent dans `uart.lua` (ouverture, `noowners`, `close`, `start`, `step`). Pas d'écart de logique entre les deux textes sur ce backend.
