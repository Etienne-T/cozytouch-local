# Écriture de root A v4 — procédure préparée le 19 novembre 2026

**Contenu de la v4** : la relance radio par PA2, la LED d'état et la mise à jour par le réseau local (conception (non publié)). Ces trois ajouts sont construits et testés hors ligne :
- les 11 scénarios QEMU ;
- l'automate `ct-update` (8 cas) ;
- le compteur, les fichiers privés, le superviseur et le secours.

Journaux : `phase2/preuves/build-v4.log`, `phase2/preuves/evidence-v4.log`. Images : `phase2/images-v4/`. La v1 déployée est sauvegardée dans `phase2/historique/v1-deployee-20261119/`.

| Élément | Valeur |
|---|---|
| `root.ubifs` v4 | SHA-256 `42fa06254db031892e5e30aba6299ddaff5aebe6d0aa50db2b899e3391e81ddf`, 68 LEB, 8634368 octets |
| Noyau | identique à la v1 (`936560bf…`) |
| DTB `durable` | `1de62cab…`, avec `pwm0` et `pwm-leds` |
| apps A | **non réécrit**. L'image privée `6d2a1b95…` (13 LEB) est seulement relue sur la NAND |
| Différences de l'arbre root avec la v1 | `boot/dtb`, `init`, `supervise`, `service.lua`, `uart.lua` ; ajouts : `led.lua`, `radio-start.lua`, `ct-update`, `ct-update.lua`, `healthy`, les liens BusyBox `rm`, `reboot` et `flock`, et `/usr/bin/ct-update` |

## Étapes, chacune à autoriser par <PERSONNE>

État de départ : le hub tourne sur B. Le pointeur vaut `ubi0:rootB` et le compteur 0. Internet est coupé par la Freebox.

1. **SSH temporaire RAM03 par JTAG**, comme le 19 novembre à 19 h :
   - lancer `launch-ram.py --execute` sur le Pi, avec le dossier `ram03/attempt-20261119b` ;
   - lire le journal noyau par JTAG (`read-ring.py`, arrêt d'environ 1 s), puis la clé d'hôte vérifiée ;
   - libérer OpenOCD, avec le script de libération adapté au nouveau dossier.
2. **Copier `root.ubifs` v4** dans `/run/ct-install` sur le hub et vérifier son SHA-256.
3. **`root-a-v4-hub.sh check`**, en lecture seule :
   - pointeur rootB, `bootloaderid`, volumes 7 et 12 ;
   - absence d'updater et de connexion cloud ;
   - MD5 de rootB ;
   - SHA-256 de l'image v4 ;
   - **apps A sur la NAND identique à l'image privée**.
4. **`root-a-v4-hub.sh write`** : `ubiupdatevol /dev/ubi0_7` seul, puis `sync`.
5. **`root-a-v4-hub.sh verify`** :
   - relecture SHA-256 de root et de apps ;
   - montage en lecture seule de root, avec les fichiers v4 présents ;
   - banque B intacte.
6. **`bascule-pointeur.sh`**, déjà utilisé le 19 novembre : pointeur → `ubi0:root`.
7. **Débranchement et rebranchement par <PERSONNE>.** Résultats attendus :
   - LED orange, puis verte clignotante, puis verte fixe ;
   - `RADIO_PULSE`, `UART_READY revision=2.4.2`, les deux lectures et `HEALTH_OK`, sans intervention ;
   - compteur à 0 ;
   - `APP_SELECT mode=factory`.

## Ce qu'il restera à vérifier sur le hub

- Le sens réel de la LED (allumée = niveau haut) et le passage de l'orange de kboot au vert.
- Une première mise à jour par le réseau local, sans changement fonctionnel :
  - `bash phase2/construire-app.sh app.ctapp` sous WSL ;
  - puis `phase2/deployer-app.ps1 -Archive app.ctapp -Reboot` ;
  - attendus : `APP_SELECT mode=trial`, puis `APP_PROMOTED`, puis `mode=current` au démarrage suivant.

## Replis

- Avant l'étape 6, le pointeur reste sur B : une erreur d'écriture n'a aucun effet sur le démarrage. On peut réécrire la v1 (`historique/v1-deployee-20261119/images/root.ubifs`, `c02d22a1…`) avec la même commande.
- Après l'étape 6 : si A ne passe pas les contrôles de santé, kboot repasse sur B après deux tentatives. Le pointeur peut aussi être remis sur B par SSH depuis A (`boot-banque-a/pointeur-vers-b.sh`).

## Exécution, 19 novembre 2026 vers 23 h (heure de Paris) — autorisée par <PERSONNE> (« on fait l'install ce soir »)

1. **RAM03** (`attempt-20261119b`) :
   - entrées vérifiées sur le Pi : noyau `8c58bb4c…`, DTB `f9dfe967…` ;
   - préflight et identité MAC concordants, quiescence, relectures du noyau et du DTB conformes ;
   - entrée du noyau à 22:07:42 UTC.

   Journal noyau lu par JTAG à deux reprises. La première lecture est arrivée avant la génération de la clé, faite à +104 s. La clé d'hôte vient du message « Public key portion », qui donne `known-hosts-jtag-verified-20261119b` (empreinte `<EMPREINTE_CLE_HOTE>…`).

   Une première extraction avait pris la clé d'administration présente dans la ligne de commande du noyau. Le SSH l'a refusée en vérification stricte, puis l'extraction a été corrigée.

   Connexion : root, noyau 5.4.302, rootB, pointeur rootB, compteur 0, aucune connexion cloud. OpenOCD a ensuite été libéré (`release-ram03-20261119b-pi.py`, GPIO en entrée).
2. **Copie et contrôle.** `root.ubifs` v4 et le script ont été copiés, avec leur SHA-256 vérifié sur le hub. `check` : **CHECK_OK**, avec **apps A sur la NAND identique à l'image privée** (`check.out`).
3. **Écriture.** `write` : `ubiupdatevol /dev/ubi0_7` en 5 s, puis `sync` (`write.out`).
4. **Vérification.** `verify` : **VERIFY_OK** (`verify.out`) :
   - relecture SHA-256 de root v4 et de apps conforme ;
   - fichiers v4 présents, DTB `1de62cab…` ;
   - `/ct` en 0700, fichiers en 0600 ;
   - banque B intacte.
5. **Bascule.** `bascule-pointeur-v4.sh`, dont le contrôle d'octets utilise désormais `wc -c` et `od -c` : pointeur `ubi0:root`, 10 octets, compteur 0, `update/` inchangé (`bascule.out`).
6. **Débranchement par <PERSONNE>. Premier démarrage v4 réussi sans intervention.** Console UART (`~/cozytouch-captures/20261119-boot-banque-a-2`) :
   ```
   APP_SELECT mode=factory version=factory
   SERVICE_LAUNCH attempt=1
   LED state=working applied=true
   RADIO_PULSE low_ms=35 restored=true
   STACK_START observed
   UART_READY revision=2.4.2
   MQTT_CONNECTED clean_session=true
   READ_RESULT index=1 status=DONE
   READ_RESULT index=2 status=DONE
   MQTT_PUBACK topic_suffix=state ack_count=5
   HEALTH_OK counter_ack=verified
   LED state=ok applied=true
   ```
   - **LED : <PERSONNE> la voit verte fixe.** En sysfs, rouge vaut 0 et vert 255. La polarité « allumée = niveau haut » est donc confirmée.
   - SSH strict par clé avec `prive/known-hosts-banque-a` : pointeur `ubi0:root`, **compteur 0**, `ct-update status` en mode factory, sans version installée.
   - Le premier essai SSH a expiré, puis le second a réussi. Cause probable : l'adresse MAC aléatoire du système A, alors que le cache ARP du PC gardait celle de B.

**Reste à faire :** une première mise à jour réelle par le réseau local (`construire-app.sh`, puis `deployer-app.ps1 -Reboot`), pour valider l'essai et la promotion sur le hub.

> Les empreintes historiques des fichiers expurgés se rapportent aux originaux privés.
