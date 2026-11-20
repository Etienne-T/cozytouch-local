# Premier démarrage sur la banque A, 19 novembre 2026 vers 22 h 09 (heure de Paris)

<PERSONNE> a débranché puis rebranché le hub après la bascule du pointeur ([procédure](../provisionnement/PROCEDURE.md)). Capture UART de la console en réception seule : `~/cozytouch-captures/20261119-boot-banque-a-2` sur le HP. Les adresses MAC sont masquées dans les extraits.

## Ce qui fonctionne

- kboot charge la banque A. Le noyau `6.12.0-cozy-a` démarre avec le DTB « Overkiz Kizbox Mini durable A » et la cmdline `ubi.mtd=ubi rootfstype=ubifs ro ip=off root=ubi0:root`.
- UBI : 13 volumes, 0 PEB corrompu. root (ID 7) et apps (ID 12) sont montés en lecture seule.
- L'init met le pare-feu en refus par défaut avant le réseau (`FIREWALL_DEFAULT_DROP_INTERFACES_DOWN`), puis `CONFINED_LAN_UP`.
- MQTT : connexion au courtier HA à environ 9 s, PUBACK de la disponibilité et des deux configurations de découverte.
- SSH sur le port 2222 depuis <IP_ADMIN>, avec la clé d'hôte de `prive/known-hosts-banque-a` en vérification stricte. Le ping n'a pas de réponse, ce qui est attendu avec le pare-feu.

## Premier écart : la radio est restée muette

```
UART_CLEANUP restored=true
STM32_STACK_TIMEOUT
MQTT_PUBACK topic_suffix=availability ack_count=4
MQTT_DISCONNECT complete=true
SERVICE_EXIT status=35 pubacks=4
SUPERVISOR_HOLD no_automatic_reboot
```

- Le service ouvre `ttyS1` (USART0, liaison STM32) vers 5,3 s. Il attend `STACK_START` (0x0403/4) ou la cause de reset (0x050e) pendant 20 s, puis s'arrête (`uart-session.lua:109`).
- `/proc/tty/driver/atmel_serial` : port 1 (0xF801C000) `tx:0 rx:0`. Le STM32 n'a émis aucun octet pendant que le port était ouvert, et rien n'a été envoyé.
- Aucun reçu passif `/run/ct/stack-start-observed`.
- Le superviseur reste en attente, sans redémarrage automatique. Le compteur n'est pas remis à 0, ce qui est le comportement prévu en cas d'échec.

Deux explications restent possibles, et la capture actuelle ne permet pas de choisir :
1. Le STM32 a démarré à la mise sous tension et a émis `STACK_START` avant l'ouverture du port.
2. Le STM32 n'a pas démarré. L'OEM fait toujours la séquence `start` (PA2 bas, PA3=1, PA5=BOOT0=0, PA6=BOOT1=0, 35 ms, PA2 haut), et notre système ne touche pas ces lignes ([démarrage froid](../../analyse-2026-11-18/stm32-demarrage-froid/RAPPORT.md)).

C'est le risque prévu à l'étape 3 du plan (qualification sur banc du froid radio), qui n'a pas été faite avant l'installation.

## Autres constats

- `macb ... invalid hw address, using random` : le système A utilise une adresse MAC aléatoire à chaque démarrage. Le profil Freebox « Cozytouch sans internet » ne s'applique donc pas à lui. Le pare-feu A n'autorise de toute façon que MQTT vers <IP_COURTIER> et le SSH depuis <IP_ADMIN>.
- Le système ne contient que le strict nécessaire, sans `ps`, `id`, `uname` ni `tr`.

## Lecture des lignes radio, autorisée par <PERSONNE> (option 1)

Faite par SSH sur le système A, sans rien modifier :
- `debugfs` est monté en lecture seule, puis démonté.
- Le script `lire-lignes-radio.lua` utilise l'ABI GPIO v1. Il lit d'abord le sens des lignes, puis, comme elles sont toutes en entrée et libres, leurs niveaux en entrée sans option de biais.
- Après la lecture, la configuration `PULL_UP` est inchangée.

Sortie : `lignes-radio.out`.

| Ligne | Rôle OEM (`stm32-utils/serial_rf`, `setmode`) | État | Niveau |
|---|---|---|---|
| PA2 | `PWR` : 1 = radio alimentée/active, 0 = mode `stop` | entrée, pull-up, libre | **1** |
| PA3 | `TEST_RADIO`, 1 en mode `start` | entrée, pull-up, libre | 1 |
| PA5 | `BOOT0`, 0 = démarrage sur la Flash | entrée, pull-up, libre | **0**, donc tirée à la masse sur la carte |
| PA6 | `BOOT1`, 0 = démarrage sur la Flash | entrée, pull-up, libre | **0**, donc tirée à la masse sur la carte |

Sans intervention de l'hôte, les lignes sont déjà dans l'état final de la séquence `start` de l'OEM. La radio est donc alimentée et démarre sur sa Flash dès la mise sous tension. **L'explication la plus probable est la première :** `STACK_START` a été émis pendant le chargement de kboot et du noyau, avant que le service n'ouvre `ttyS1` vers 5,3 s. Le STM32 attend ensuite sans rien envoyer.

L'OEM ne se fie jamais à ce démarrage spontané. À chaque lancement, il refait `PA2=0`, 35 ms, `PA2=1`, ce qui redémarre la radio pendant que l'UART est ouvert.

## Test en direct de la remise en route radio, autorisé par <PERSONNE>, vers 22 h 17

Sur le système A en marche, sans réécriture. Sortie : `test-direct.out`.
1. Lancement du service à la main : `setsid luajit /usr/share/cozytouch/phase2/service.lua --run`, avec sa sortie dans `/run/ct/manual-run.log`. MQTT se connecte, et la disponibilité et les deux découvertes sont acquittées.
2. Deux secondes plus tard, `impulsion-pa2.lua` (SHA-256 `c6aafcc2…`, vérifié sur le hub) s'exécute :
   - il contrôle l'état passif `PA2..PA6=11100` ;
   - il passe PA2 en sortie à 0 pendant 35 ms, puis à 1, puis le remet en entrée ;
   - il relit `11100`.

   PA3, PA5 et PA6 ne sont pas touchés, car ils sont déjà aux niveaux de la séquence OEM `start`.
3. Résultat :
   ```
   STACK_START observed
   UART_READY revision=2.4.2
   READ_RESULT index=1 status=DONE
   READ_RESULT index=2 status=DONE
   MQTT_PUBACK topic_suffix=state ack_count=5
   MQTT_PUBACK topic_suffix=state ack_count=6
   HEALTH_OK counter_ack=verified
   ```
   Compteurs du port radio : `ttyS1 tx:100 rx:123`.
4. Relecture en lecture seule de `ubi0:persistent` : pointeur `ubi0:root`, **compteur 0**, `bootloaderid` 20180731.
5. Home Assistant :
   - appareils `Cozytouch`, `Cozytouch CETHI` et `Cozytouch IC3` ;
   - entités `sensor.cozytouch_cethi_valeur_brute` et `sensor.cozytouch_ic3_valeur_brute`, mises à jour à 21:17:29 UTC, puis toutes les 60 s.

**Cause confirmée.** La radio démarre seule à la mise sous tension, avant que Linux n'écoute. Une impulsion PA2, comme le fait l'OEM, la relance pendant que le port est ouvert.

## Reste à faire

- **Correction durable.** Le service doit faire lui-même l'impulsion PA2 après l'ouverture de `ttyS1`, avec les mêmes contrôles d'état passif. Il faut ensuite la tester sous QEMU, reconstruire root A et réécrire la banque A. Tant que ce n'est pas fait, chaque débranchement fait échouer le démarrage, et il faut refaire ce test à la main. Deux échecs de suite renvoient sur B.
- **Réécrire root A.** C'est impossible depuis A, car le volume est monté. Il faut passer par B puis RAM03, ou trouver une autre voie.
- **Adresse MAC aléatoire** au démarrage de A. Il faut décider s'il faut lire l'adresse d'usine.
- **Horloge.** Le système A est en 1970, sans NTP ni RTC : les dates de fichiers dans `/persistent` sont fausses.

## Correctif v2 construit et testé hors ligne, 19 novembre vers 22 h 25

- `phase2/src/radio-start.lua`, nouveau : même logique que `impulsion-pa2.lua`, validé sur le hub. Il refuse d'agir si PA2..PA6 ne sont pas libres, en entrée et à `11100`. Il ne sort avec le code 0 que si l'impulsion est faite et l'état passif retrouvé.
- `phase2/src/uart-session.lua` : le script est appelé une fois, juste après l'ouverture exclusive de `ttyS1`. En cas d'échec, le service affiche `STM32_PULSE_FAILED` (code 35) et se met en attente, sans lecture ni remise à 0 du compteur. Le délai de 20 s pour `STACK_START` court à partir de l'impulsion.
- `prepare-lua.py` copie le script.
- Banc QEMU (`tests/lab-init`, `tests/test-qemu.py`) : un faux script sert de marqueur, et le banc n'envoie les trames STM32 qu'après ce marqueur. Le nouveau scénario `pulse-refused` vérifie qu'en cas de refus, il n'y a ni attente STM32, ni lecture, ni remise à 0 du compteur.
- Résultat :
  - les 9 scénarios QEMU passent, ainsi que les contrôles du compteur, des fichiers privés, du superviseur et du secours. Journal : `phase2/preuves/build-v2.log` ;
  - par rapport à l'image déployée, l'arbre root ne diffère que par `uart.lua` (modifié) et `radio-start.lua` (ajouté) ;
  - nouvelle image `root.ubifs` : SHA-256 `46b89d1f83af26c1c3343c25cfe411ba24c8306bf8f42f02625090523d953215`, 68 LEB, 8634368 octets. `apps.ubifs` est inchangée : on garde l'image privée `apps-prive.ubifs` déjà écrite ;
  - la version v1 déployée (sources, images, preuves) est sauvegardée dans `phase2/historique/v1-deployee-20261119/`.

> Les empreintes historiques des fichiers expurgés se rapportent aux originaux privés.
