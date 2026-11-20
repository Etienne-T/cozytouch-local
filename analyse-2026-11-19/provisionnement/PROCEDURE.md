# Banque A : image apps privée et procédure d'écriture, 19 novembre 2026

## Image apps A provisionnée

Construite sous WSL avec `build-apps-prive.sh`. Aucun secret n'est affiché ni journalisé. L'image et ses empreintes sont rangées dans `analyse-2026-11-18/persistance-banque-a/prive/`, un dossier réservé à l'utilisateur Windows.

| Fichier dans `/apps/ct` | Contenu |
|---|---|
| `broker.conf` | Courtier <IP_COURTIER>:1883, utilisateur HA `<UTILISATEUR_MQTT>` (ETAT-HA (non publié)), `client_id=cozytouch-hub`, hub en <IP_HUB>/24, poste d'administration <IP_ADMIN>, intervalle 60 s |
| `targets.conf` | Contexte qualifié, deux lignes dans l'ordre CETHI puis IC3, copiées de `client-autonome/client/targets.private.conf` |
| `authorized_keys` | Clé publique d'administration `cozytouch-admin-rsa2048.pub`, la même que pour RAM03 |
| `ssh_host_key` | Clé Dropbear ed25519 générée par le `dropbearkey` ARM de l'image (qemu-arm). La clé publique est dans `prive/known-hosts-banque-a` |

Contrôles : `/ct` est en 0700, root ; les quatre fichiers sont réguliers, en 0600, root, avec un seul lien. Ces valeurs sont relevées par ubi_reader sur l'image produite. Superbloc : UBIFS v4, LZO, LEB 126976, 13 LEB sur un maximum de 130. SHA-256 de l'image : `6d2a1b9527128240b1f06e290986191151f4e0fbd249cb4852cf9e4a9f5a19c5`.

**Points d'attention réseau.** Le système A n'utilise pas DHCP. Il se fixe en <IP_HUB> et n'accepte le SSH que depuis <IP_ADMIN>. Ces deux adresses viennent aujourd'hui du DHCP de la Freebox. Pour éviter un conflit ou une perte d'accès, il faut créer deux baux statiques dans la Freebox : le hub en <IP_HUB>, ce PC en <IP_ADMIN>.

## Procédure d'écriture (étape 5)

Le mécanisme est celui du constructeur. `image-update` écrit la banque inactive avec `ubiupdatevol` (`usr/share/image-update-functions.sh:690–731` de rootB). Le script `banque-a-hub.sh` s'exécute sur le hub, à travers le SSH RAM03 :

1. `check`, en lecture seule. Il vérifie :
   - le pointeur `ubi0:rootB` et `bootloaderid` ;
   - le nom, le type et la capacité des volumes 7 et 12, et qu'ils ne sont pas montés ;
   - l'absence d'updater et de connexion Cloudlink ;
   - le MD5 de rootB par rapport au manifeste ;
   - le SHA-256 des deux images copiées dans `/run/ct-install`.

   **Exécuté le 19 novembre à 21 h : CHECK_OK** (`check-20261119.out`).
2. `write`, à autoriser par <PERSONNE>. Il refait les contrôles, puis lance `ubiupdatevol /dev/ubi0_7 root.ubifs`, `ubiupdatevol /dev/ubi0_12 apps.ubifs` et `sync`. Le pointeur, le compteur, `/persistent/boot/update/*.txt` et la banque B ne sont pas touchés.
3. `verify`, en lecture seule. Il contrôle :
   - l'absence de marqueur de mise à jour et de corruption ;
   - la relecture SHA-256 des longueurs utiles (68 et 13 LEB) ;
   - un montage en lecture seule de root A, avec les fichiers `/boot`, `bootloaderid` et `cmdline` ;
   - un montage en lecture seule de apps A, avec les droits de `/ct` ;
   - de nouveau l'état de B et le pointeur.

Retour arrière de la banque A : la même commande avec les copies de `extraction/corrected-volumes/`. La copie de root A a pour MD5 `f5b51108…`, identique au manifeste constructeur. Tant que le pointeur reste sur `ubi0:rootB`, l'écriture de A n'a aucun effet sur le démarrage.

## Exécution, 19 novembre 2026 — autorisée par <PERSONNE>

**Banque A écrite et vérifiée.** Un premier lancement de `write` s'est arrêté avant toute écriture : `ubiupdatevol` était introuvable dans le PATH de la session Dropbear. Les volumes étaient inchangés (upd=0, data_bytes d'origine), et le script a été corrigé avec `export PATH`. Second lancement, avec le SHA-256 du script vérifié sur le hub :

- contrôles préalables OK ;
- `ubiupdatevol` sur root (ID 7) de 19:59:52 à 19:59:59 UTC, puis sur apps (ID 12) jusqu'à 19:59:59, suivi de `sync` ;
- `verify` : upd_marker et corrupted à 0 ; root data_bytes = 8634368 ; relecture SHA-256 de root et de apps conforme ;
- montage root A en lecture seule : `bootloaderid`, `cmdline`, `dtb` et `zImage` présents, cmdline `ubi.mtd=ubi rootfstype=ubifs ro ip=off` ;
- montage apps A en lecture seule : `/ct` en 0700 root, et les quatre fichiers en 0600, root, avec un seul lien. L'affichage du script omettait la première ligne ; un contrôle séparé confirme les quatre fichiers ;
- noyau OEM : UBIFS w4/r0 monté en lecture seule sans erreur ;
- pointeur `ubi0:rootB`, compteur 0, MD5 rootB conforme.

Journaux : `write-20261119.out`, `verify-20261119.out`.

**Baux DHCP fixes créés dans la Freebox** : <IP_HUB> pour le hub (`<ID_PASSERELLE>`, Overkiz), <IP_ADMIN> pour ce PC (`<CHEMIN_LOCAL>`). Les deux baux ont été relus dans la liste. Les adresses MAC ont été lues dans le navigateur réseau de la Freebox, sans passer par la conversation.

Prochaine étape : l'étape 6 du plan, la bascule du seul pointeur vers `ubi0:root`. Elle reste à autoriser séparément, avec la définition du repli.

## Bascule du pointeur, 19 novembre 2026 à 21 h 01 (heure de Paris) — autorisée par <PERSONNE>

`bascule-pointeur.sh` a fait les contrôles préalables :
- pointeur rootB, compteur 0, bootloaderid 20180731 ;
- volumes A sans marqueur, root A de 8634368 octets ;
- `/persistent` monté en `sync` ;
- aucune variable KBOOTIDFILE.

Il a ensuite écrit un fichier temporaire dans le même répertoire, appelé `sync`, puis renommé ce fichier sur le pointeur et rappelé `sync`. La relecture donne 10 octets, `ubi0:root\n`. Le contrôle d'octets du script a échoué à cause d'une option `od` absente de BusyBox, après la bascule. Il a été refait à la main : contenu exact, MD5 de `update/` inchangés, compteur 0. Journal : `bascule-20261119.out`.

Capture UART en réception seule lancée sur le HP pour le démarrage : `~/cozytouch-captures/20261119-boot-banque-a`, 2400 s.

La première capture s'est terminée à 21 h 42 avec 0 octet : le hub n'avait pas été redémarré. Une seconde capture, toujours en réception seule, est lancée à 22 h 08 pour 7200 s : `~/cozytouch-captures/20261119-boot-banque-a-2`.

> Les empreintes historiques des fichiers expurgés se rapportent aux originaux privés.
