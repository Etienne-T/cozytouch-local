# État du hub et copies NAND récentes — 19 novembre 2026

Étape 4 du [plan d'installation](../../analyse-2026-11-18/persistance-banque-a/phase2/PLAN-INSTALLATION.md), autorisée par <PERSONNE> (« go go »). Relevé en lecture seule par le SSH temporaire RAM03 ([relance](../../analyse-2026-11-17/acces-admin/ram-kmsg-03/RESULTAT-20261119.md)). Aucune écriture, aucun redémarrage, aucun ordre d'appareil. Sorties brutes : `inspect.out` et `inspect2.out`.

## Constat

| Point | État |
|---|---|
| Banque active | `ubi0:rootB` en lecture seule, `appsB` sur `/apps`, KizOS 2026.1.3-2. `version-hash.txt` indique rootB/appsB actives, root/apps inactives en 2025.4.4-3 |
| Démarrage | Le pointeur vaut `ubi0:rootB` et le compteur 0. Il réécrit le 19 novembre à 20 h 07, par le démarrage normal. `bootloaderid` vaut 20180731 |
| Mises à jour | `updateAuto` : enabled=false, fenêtre 03:00–06:00. Aucun processus image-update, image-download, fwupdate, stm32 ou curl. Aucun marqueur `update_*_needed`. Le crontab ne contient que des surveillances de services et logrotate |
| Radio | `io-homecontrold` PID 956. `IO_SOFTWARE_REVISION` est **absent** de son environnement : la sentinelle DO-NOT-UPDATE n'est pas active |
| Watchdog | `/dev/watchdog0` tenu par `internald` (PID 739) |
| Écrivains | Aucun descripteur ouvert sur `/data`, `/persistent` ou `/apps` au moment du relevé, qui est instantané |
| UBI | 13 volumes, aucun `upd_marker` ni `corrupted`. root ID 7 statique 165 LEB, apps ID 12 dynamique 130 LEB. bad_peb_count=4, ce qui correspond aux 4 blocs BBT ; mtd1 bad_blocks=0, ecc_failures=0 |
| Réseau | Connexion Cloudlink établie vers le port 803 (tcp+eap). **Le hub est joignable par le cloud** |

## Sauvegarde de la banque A comparée au manifeste constructeur

- `corrected-volumes/img-372254595_vol-root.ubifs` a pour MD5 `f5b5110849d8c5a4c5f1a936f6dc8d2b`. C'est exactement le `checksum` de `/persistent/boot/update/root.txt` (2025.4.4-3, 20951040 octets). **La copie corrigée de root A est identique à l'image écrite par le constructeur.** L'image non corrigée diffère, à cause de ses bits corrigés.
- rootB corrigée : `4e69584d…`, identique à `rootB.txt`.
- apps A : le MD5 diffère du manifeste. C'est attendu pour un volume dynamique monté en écriture quand A était active.

## Deux copies NAND brutes (données et OOB)

Méthode du 17 novembre : `nanddump --noecc --oob --bb=dumpbad` sur mtd0 puis mtd1, en O_RDONLY. Collecteur `../nand-live/collect_nand_live_20261119.py`. Ces copies sont prises sur un système actif, donc non atomiques.

| Copie | mtd0 SHA-256 | mtd1 SHA-256 |
|---|---|---|
| `donnees/nand-live-2026-11-19/20261119T193457.159755Z` | `59fa6000…82d4b7` | `142ab488…cd749f` |
| `donnees/nand-live-2026-11-19/20261119T193626.576117Z` | `59fa6000…82d4b7` (identique) | `7999c20b…6d98af` |

**Comparaison par bloc** (`../nand-live/compare_blocks.py`, `bitdiff.py`) :
- Copie 1 contre copie 2 : deux blocs diffèrent, d'**un seul bit** de données chacun. Ce sont kboot LEB 21 et root A LEB 1, deux volumes statiques jamais écrits. Il s'agit de cellules instables en lecture brute, que l'ECC corrige. Aucun autre bloc ne change.
- Copie 2 contre la NAND JTAG du 17 novembre : root A ne diffère que du même bit instable, apps A d'un seul bit au LEB 52. rootB, kboot, dtb et security sont identiques. appsB (4 blocs), data, persistent et des blocs libres ont changé : ce sont l'activité normale du système actif et de UBI. **La banque A n'a pas changé depuis le 17 novembre.**

## Coupure internet du hub sur la Freebox, 19 novembre 2026 vers 20 h 49

<PERSONNE> l'a demandée et a ouvert l'interface Freebox OS 4.13 (Freebox v8) dans le navigateur intégré. J'y ai créé le profil de contrôle parental **« Cozytouch sans internet »** (id 1), qui contient l'adresse matérielle du hub. Le hub y apparaît sous le nom `<ID_PASSERELLE>`, fabricant Overkiz. Le profil force le mode `denied` (`override`), et la Freebox indique `current_mode=denied`. L'adresse MAC a été lue dans le navigateur de réseau local de la Freebox, sans passer par la conversation.

Contrôle depuis le hub, 20 secondes après la règle :
- la connexion Cloudlink sur le port 803 a disparu, et il ne reste que deux connexions HTTPS en CLOSE_WAIT ;
- le ping vers internet est bloqué ;
- la passerelle et Home Assistant (<IP_COURTIER>) répondent ;
- le SSH local fonctionne toujours.

Pour annuler : dans Freebox OS → Profils, retirer le hub du profil ou supprimer le profil.

## À retenir pour la suite

1. Le hub est connecté au cloud et la sentinelle radio est absente. Un ordre `download`/`update` reçu du cloud peut écrire la banque A inactive. Il faut couper le WAN du hub avant d'écrire la banque A.
2. Les copies ne sont pas atomiques. La référence physique complète reste la NAND JTAG du 17 novembre. Les copies du 19 novembre servent de constat récent.

> Les empreintes historiques des fichiers expurgés se rapportent aux originaux privés.
