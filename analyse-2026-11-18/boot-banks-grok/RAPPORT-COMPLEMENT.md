# Complément : banques, activation et coupures

Scripts lus dans `complement/`, empreintes dans `complement-manifest.json`. `kboot.txt` et `kboot-spare.txt` ont la même empreinte. Les deux sont des fiches `version` / `checksum` / `datetime` datées `20180802` (`kboot.txt:1-3`, `kboot-spare.txt:1-3`). Ce ne sont pas des menus de boot.

Statuts : **démontré** si le texte le contient ; **supposé** si l'on relie un nom lu dans un fichier absent ; **à vérifier** si la réponse est dans le pilote `kboot`, le bootloader binaire, ou un script non fourni.

## Hors corpus

`image-update` charge `image-update-functions.sh`, qui charge `/usr/share/kizosenv.sh` (`image-update:5`, `image-update-functions.sh:5`). Ce fichier manque. Il fournit notamment `get_cmdline_root_vol`, `have_k_boot`, `have_u_boot`, `BOOT_INFORMATION_FILE`, `PERSISTENTDIR_BOOT`, et les noms de volumes `ROOT_*`, `APPS_*`, `BOOT_*`, `BOOTLOADER_*`, `DTB_*`, `SECURITY_*`.

Absents aussi, alors que le texte les appelle : `image-download`, `mtd-flash`, `ubi-md5`, `ubiupdatevol`, `mount_security`, `mount_security_spare`, `/etc/init.d/mount-security`, `/usr/share/post-install/post-install`, `/usr/share/bsp/manage-persistent-spare.sh`, `/usr/local/sbin/reboot`, `upload`, `debug_log`, `run_from_usb_loader`. Le pilote de `/sys/kboot/*` et le bootloader binaire ne sont pas dans le dossier. `setup_user_data` et `migration_first_boot_with_appsB` sont définies (`image-update-functions.sh:488`, `:619`) et ne sont appelées par aucun fichier du complément.

Ces scripts ne contiennent ni le mot watchdog, ni un compteur d'essais, ni une lecture de `/sys/kboot/mode`.

## 1. Banque cible, fichiers kboot, prochain démarrage

### Qui est la cible root et apps

**Démontré.** `set_root_volumes` prend le volume actif dans la sortie de `get_cmdline_root_vol`, second champ après `:` (`image-update-functions.sh:202`). Sous chargeur USB, il le relit dans `BOOT_INFORMATION_FILE`, sinon il force `ROOT_B_VOLUME_NAME` (`image-update-functions.sh:204-210`).

**Démontré.** Le `case` ne connaît que deux banques (`image-update-functions.sh:213-230`) :

- actif = `ROOT_VOLUME_NAME` : inactifs `ROOT_B`, `APPS_B`, `BOOT_B` ;
- actif = `ROOT_B_VOLUME_NAME` : inactifs `ROOT`, `APPS`, `BOOT`.

Tout autre nom termine en erreur 4, `Unknown Root volume used` (`image-update-functions.sh:228-229`).

**Supposé.** Ces variables valent `root` et `rootB`. Les littéraux du même fichier sont `root|rootB` (`image-update-functions.sh:673`), `appsB` (`image-update-functions.sh:598-600`) et l'expression `ubi0:rootB` (`image-update:142`). `kizosenv.sh` tranche.

**Démontré.** L'étape `root` n'appelle `update_volume` qu'avec `inactive_root_vol` (`image-update:573`). L'étape `apps` n'appelle `update_volume` qu'avec `inactive_apps_vol` (`image-update:617`). Le nom du volume actif n'est pas passé à `ubiupdatevol` dans ces deux étapes. `active_boot_vol` et `inactive_boot_vol` sont calculés (`image-update-functions.sh:215-225`) et ne sont plus lus : ce script ne bascule pas une paire de volumes `BOOT_*`.

**Démontré.** La décision « déjà à jour » compare des fiches texte, pas le contenu UBI. `check_update_needed` retourne « pas de mise à jour » si `TMPDIR/<nom>.txt` ou `PERSISTENT_UPDATE_DIR/<nom>.txt` est identique à la fiche téléchargée, ou si la fiche contient `action:bypass` (`image-update-functions.sh:166-196`). `-f` force la mise à jour (`image-update-functions.sh:166`). Le commentaire le dit : sans `-f`, un volume modifié dont la fiche est inchangée n'est pas réécrit (`image-update:560-561`).

Pour root, les trois cas sont (`image-update:562-591`) :

- la fiche du volume actif correspond déjà : aucun flash, aucun drapeau ;
- l'actif diffère et l'inactif diffère : flash de l'inactif, puis `touch` de `update_root_needed` ;
- l'actif diffère et l'inactif correspond déjà : pas de flash, le même `touch`, avec le journal `setting as next active volume` (`image-update:579`).

Le drapeau est un fichier vide. Il ne mémorise pas le nom du volume flashé.

Pour apps, le `touch` de `update_apps_needed` n'est fait qu'après un flash réussi (`image-update:620`). Si l'inactif est déjà à la bonne fiche, le journal `upgrade_apps_success` est émis et le drapeau n'est pas créé (`image-update:624-628`).

### Écriture de kboot et de kboot-spare

**Démontré.** L'étape `bootloader` ou `kboot`, et l'étape `all`, n'entrent dans ce bloc que si `have_k_boot` est vrai (`image-update:497`). La fonction est absente : **à vérifier**.

**Démontré.** Le composant comparé s'appelle le littéral `kboot` (`image-update:499-511`). Une seule comparaison a lieu, contre `PERSISTENT_UPDATE_DIR/kboot.txt` via le premier argument `kboot`. Le commentaire dit « if either is not up to date we update both » (`image-update:510`) ; le `if` ne teste pas la fiche spare ni la fiche dtb. Si `kboot.txt` correspond déjà, spare et dtb ne sont pas réécrits.

**Démontré.** Quand la comparaison demande une mise à jour et que l'on n'est pas en `--download-only`, l'ordre est (`image-update:517-533`) :

1. `update_volume` sur `BOOTLOADER_VOLUME_NAME` avec `zImage-initramfs-at91-kizboxmini-dtb.bin` (`image-update:17`, `:520`) ;
2. si `dtb_exists`, `update_volume` sur `DTB_VOLUME_NAME` avec `zImage-at91-kizboxmini.dtb` (`image-update:18`, `:522-524`) ;
3. `update_volume` sur `BOOTLOADER_SPARE_VOLUME_NAME` avec le même fichier bootloader (`image-update:527-528`) ;
4. si `dtb_exists`, le même dtb sur `DTB_SPARE_VOLUME_NAME` (`image-update:530-532`).

**Démontré.** `update_volume` redimensionne ou recrée le volume, appelle `ubiupdatevol`, puis `ubi-md5 --check` contre le champ `checksum:` de la fiche (`image-update-functions.sh:698-739`). Seulement si ce contrôle réussit, il copie la fiche vers `PERSISTENT_UPDATE_DIR/<nom-du-volume>.txt` (`image-update-functions.sh:748-749`). Un écart de md5 retourne 1 sans cette copie (`image-update-functions.sh:736-738`). `set -e` est actif (`image-update:3`) et l'appel kboot n'est pas dans un `if` : cet échec arrête le script avant la copie spare.

**Démontré.** Le post-install lit le volume par le littéral `kboot` : `ubi-md5 kboot > .../bootloaderid`, et seulement si `bootloaderid` est absent (`kboot-base.postinstall:13-15`). Le volume principal s'appelle donc `kboot`.

**Supposé.** Le volume spare s'appelle `kboot-spare`, parce que la fiche fournie porte ce nom et que `update_volume` nomme la fiche d'après le volume. Le nom exact est la variable `BOOTLOADER_SPARE_VOLUME_NAME`, absente. Les deux fiches du corpus sont identiques : au moment de leur écriture, les deux volumes avaient la même fiche `20180802`. Elles ne contiennent pas `root` ni `rootB`.

**Démontré.** `dtb_exists` traite un couple `DTB_VOLUME_NAME` / `DTB_SPARE_VOLUME_NAME`. Si un seul des deux volumes existe, l'autre est créé, vide, en volume statique de la taille du premier mtd dont le nom contient `dtb` (`image-update:191-230`).

### Marque du prochain démarrage

**Démontré.** La marque n'est pas écrite pendant le flash root. Elle l'est à l'étape `upgrade` ou `all`, et seulement si `update_root_needed` existe (`image-update:641-645`). `update_active_volume_on_persistent` écrit alors une seule ligne (`image-update-functions.sh:235-241`) :

`ubi0:<volume-root-inactif>`

dans `BOOT_INFORMATION_FILE`, car `UBI_DEVICE_NUMBER` vaut `0` (`image-update-functions.sh:11`, `:237`). Le commentaire dit que ce fichier sert au prochain reboot (`image-update-functions.sh:234`). Si `have_u_boot` est vrai, le même nom de volume est écrit dans `/sys/uboot/partition` (`image-update-functions.sh:239-241`). Cette fonction est absente. Le chemin de `BOOT_INFORMATION_FILE` est absent.

**Démontré.** Juste après, le script efface `update_root_needed` et `update_apps_needed`, appelle `post-install resetall`, et, avec `-f`, crée `$DATA_DIR/resetme` (`image-update:647-658`). Le consommateur de `resetme` dans ce dossier est `setup_user_data`, qui n'est pas appelée ici.

**Démontré.** L'aide dit que `upgrade` « set new active partitions », qu'une seule partition ne suffit pas, et que les suites reconnues sont `root apps upgrade`, ou `root apps` puis `upgrade`, ou `root` puis `apps upgrade` (`image-update:55-60`, `:81-88`). Le contrôle au début refuse `upgrade` sans étape root ni drapeau `update_root_needed`, et sans étape apps ni drapeau `update_apps_needed` (`image-update:360-374`). À l'intérieur de l'étape, seul le drapeau root est relu : le drapeau apps est seulement effacé (`image-update:641-647`).

**Démontré.** Avec `-r` et `update_done`, la fin appelle `/usr/local/sbin/reboot update` (`image-update:677-683`). Ce binaire manque. L'argument `update` n'est pas interprété ici. **À vérifier.**

**Démontré.** La seule écriture de `/sys/kboot/next` du complément est `echo 0 >/sys/kboot/next` (`kboot-base.initd:3`). Elle est inconditionnelle. Elle ne contient pas le nom `root` ou `rootB`. Elle ne lit pas `/sys/kboot/mode`. Ce n'est donc pas l'instruction qui choisit la banque root. Le même nœud est celui que `INTERNAL_BOOTNEXT_FILE` désigne (`corpus/etc/conf.d/internal:16`) et que le Lua rapporte sous le champ `bootmode` (`corpus/.../Admin/system.lua:275-277`, `corpus/.../Transport/Admin/Objects/info.lua:162`). Ce que le noyau fait de la valeur `0` est **à vérifier** dans le pilote.

Le commentaire du post-install, « force use the last available bootloader » (`kboot-base.postinstall:2`), ne correspond pas au corps : le corps crée le répertoire et, au plus, `bootloaderid`.

## 2. Confirmation, permanence, retour arrière

**Démontré.** Rien dans le complément n'arme un démarrage « à l'essai », n'incrémente un compteur, ne lit un échec de boot, ni ne parle du watchdog. Le rôle du watchdog dans un retour de banque reste celui du premier rapport : absent de ces scripts, **à vérifier** dans le pilote et le bootloader.

**Démontré.** Ce qui rend la bascule effective, dans ce texte, est l'écriture de `BOOT_INFORMATION_FILE` vers le volume root alors inactif (`image-update-functions.sh:237`). Avant cette ligne, le flash root ou apps ne change pas ce fichier. Après cette ligne, aucun chemin de ces scripts ne réécrit l'ancien nom. Il n'y a pas de retour automatique codé ici.

**Démontré.** `kboot-base.initd` écrit `0` à chaque passage de ce script d'init, pas seulement après une mise à jour (`kboot-base.initd:3`). Le corpus ne dit pas si ce script est activé dans un runlevel. **À vérifier.** Cette écriture ne distingue pas un essai réussi d'un boot ordinaire : la constante est la même.

**Démontré.** Le volume root laissé de côté n'est pas effacé par l'étape qui le désigne comme prochain. Il le devient plus tard, seulement si un `image-update` ultérieur tourne pendant que l'autre banque est l'active : il est alors l'inactif et peut être la cible de `update_volume`. Le drapeau `update_root_needed` ne stocke pas le nom ; `upgrade` recalcule l'inactif au moment où il écrit (`image-update:642-645`).

**Démontré.** Une coupure ou un `die` avant `upgrade` laisse le fichier d'activation non modifié par ce script. `update_volume` en échec de md5 sur root appelle `die 5` avant le `touch` (`image-update:573-575`, `:585`). Apps fait de même (`image-update:617-620`). L'étape `upgrade` est plus bas dans le même processus (`image-update:635`). Elle ne s'exécute pas après ces `die`.

**À vérifier.** Qui lit `BOOT_INFORMATION_FILE` au démarrage réel, et ce qui arrive si le nouveau volume ne va pas jusqu'à `kboot-base.initd`. Ce n'est pas dans ces scripts. L'initramfs, le bootloader et le pilote `kboot` manquent.

Le retour démontré par ce userspace est donc : ne pas exécuter l'écriture de `BOOT_INFORMATION_FILE`, le volume actif de root et d'apps n'ayant pas été la cible du flash. Le retour après cette écriture n'est pas démontré.

## 3. Ordre d'écriture et coupures

**Démontré.** Pour la cible `all`, bootstrap est exclu (`image-update:61-63`, `:391-392`). L'ordre du programme est :

1. `bootstrap` seulement si demandé, avant le reste (`image-update:397-429`) ;
2. `security` (`image-update:432`) ;
3. `kboot` puis dtb, chaque fois copie principale puis spare (`image-update:496-533`) ;
4. root inactif (`image-update:545-573`) ;
5. apps inactif (`image-update:597-617`) ;
6. écriture de `BOOT_INFORMATION_FILE` (`image-update:635-645`) ;
7. `cleanup all` (`image-update:664-666`) ;
8. si une mise à jour a eu lieu, sans `-r` et sans `--raw` : `manage-persistent-spare.sh backup` (`image-update:668-670`) ;
9. statut D-Bus `updated` ou `donothing`, puis `exitStatus` 0 (`image-update-functions.sh:73-76`, `image-update:672-673`) ;
10. reboot seulement si `-r` et `update_done` (`image-update:677-683`).

`set -e` et `die` arrêtent les étapes suivantes. Les numéros d'erreur utiles ici : 4 volume, 5 flash (`image-update-functions.sh:85-97`).

### Bootstrap

**Démontré.** Un seul `mtd-flash --partition bootstrap` (`image-update:415-416`). Pas de seconde copie dans ce script. La fiche est copiée vers `bootstrap.txt` après le flash (`image-update:419`). Une coupure pendant `mtd-flash` n'est pas rattrapée par la banque root restante : ce script ne le fait pas. Le choix du fichier dépend de `dtb_exists` : avec dtb, `bootstrap-at91-kizboxmini-dtb.bin`, sinon `bootstrap-at91-kizboxmini.bin` (`image-update:20-21`, `:398-404`).

### Security

**Démontré.** Volume partagé, pas un volume `root` / `rootB`. Séquence (`image-update:444-485`) : démontage de `/etc/security` si besoin ; sans `-f`, `mount_security_spare` est tenté et son échec est ignoré (`||:`) ; copie `dd` du volume courant vers `$TMPDIR/sectmp.ubi` ; `update_volume` du volume principal. Si le md5 échoue, `restore_security` réécrit cette copie temporaire puis termine en erreur (`image-update:173-178`, `:184-186`). La copie est sous `/tmp` (`image-update-functions.sh:15`) : un reset l'efface, et le script de restauration ne tourne plus.

**Démontré.** Avec `-f`, le spare est flashé dans la même exécution, puis sa fiche est copiée (`image-update:468-478`). Sans `-f`, le spare n'est pas flashé ici ; le script crée `security-has-been-updated` pour une reprise dans `mount-security` au boot (`image-update:480-484`). Ce script d'init manque. Le commentaire dit qu'un nom `securityupdate` serait traité par kboot, qui poserait une entrée security vide, d'où le nom actuel (`image-update:482-483`). Ce traitement kboot est **à vérifier**.

**Démontré.** `update_volume` ne copie pas la fiche du volume security principal : il retourne avant (`image-update-functions.sh:742-746`). L'appelant la copie lui-même après le flash (`image-update:466`), avant tout boot de vérification. Un prochain `check_update_needed` peut donc voir la nouvelle fiche alors que `mount-security` n'a pas encore confirmé le volume.

**Démontré.** La banque root opposée ne reçoit pas cette écriture. Si `-f` n'est pas passé, le volume spare n'est pas encore écrasé par ce script au moment où le principal l'est. Savoir si le boot monte ce spare : **à vérifier**.

### kboot et dtb

**Démontré.** Les deux copies reçoivent le même fichier, principale d'abord. Une coupure après le md5 du principal et avant le spare laisse la fiche `kboot.txt` déjà à jour (`image-update-functions.sh:748`) et le spare encore ancien. Au passage suivant, la comparaison ne regarde que `kboot.txt` (`image-update:511`) : elle peut sauter le spare. C'est le seul trou de reprise écrit dans ce script.

**Démontré.** Une fois les deux `update_volume` réussis, les deux volumes portent la nouvelle image. L'ancienne image bootloader n'est plus dans aucune des deux cibles de ce script. La banque root laissée intacte ne contient pas, dans ce schéma, une copie de l'ancien kboot : kboot n'est pas le volume root.

**À vérifier.** Un spare encore ancien ne sert de repli que si le bootloader le choisit. Le binaire manque.

### root et apps

**Démontré.** Seul l'inactif est passé à `ubiupdatevol`. L'actif, celui du cmdline, n'est pas l'argument. Avant `upgrade`, `BOOT_INFORMATION_FILE` n'est pas réécrit. Une coupure pendant le flash de l'inactif, ou un md5 faux, laisse donc la marque de boot telle qu'elle était, et ne désigne pas le volume à moitié écrit. Cela vaut pour la chaîne d'écriture de ce script. Le programme qui, au reset, relit encore l'ancienne marque, est **à vérifier**.

**Démontré.** L'écriture de la marque est un redirection `>` directe, sans fichier temporaire (`image-update-functions.sh:237`). Une coupure au milieu de cette ligne peut laisser un fichier tronqué. Aucune restauration de l'ancien contenu n'est codée.

**Démontré.** `backward_compatibility`, appelée avant le flash apps (`image-update:604`), ne s'active que si la version cible est inférieure à la version courante et inférieure à `2022.1.1-0` (`image-update-functions.sh:542-571`, `:574-584`). Dans ce cas elle supprime le volume `appsB`, efface sa fiche, force actif et inactif apps sur le même nom `APPS_VOLUME_NAME`, et supprime la ligne `appsB` de `/persistent/boot/update/version-hash.txt` (`image-update-functions.sh:597-611`). Il n'y a alors plus deux banques apps.

### Après la marque

**Démontré.** `manage-persistent-spare.sh backup` ne tourne pas sur le chemin `-r` (`image-update:668-670`). Il ne remplace pas la marque de banque. Son effet est **à vérifier**.

## 4. Conditions démontrées pour une installation dans une banque

Le code démontre les conditions suivantes. Il ne démontre pas un retour automatique après activation. Aucune écriture NAND n'est à lancer à partir de ce rapport.

**Démontré.** La banque root et apps conservée est celle que `get_cmdline_root_vol` présente comme active. Les étapes `root` et `apps` n'envoient à `update_volume` que l'autre nom (`image-update:573`, `:617`). Tant que l'étape `upgrade` n'atteint pas `update_active_volume_on_persistent`, ce script ne change pas `BOOT_INFORMATION_FILE` (`image-update:641-645`, `image-update-functions.sh:237`).

**Démontré.** L'activation est cette écriture `ubi0:<inactif>`, recalculée à ce moment-là, plus, si `have_u_boot`, `/sys/uboot/partition`. Elle est refusée si les drapeaux ou les étapes root et apps manquent (`image-update:360-374`). Le drapeau root vide ne vérifie pas que le volume inactif du moment est bien celui flashé plus tôt (`image-update:585`, `:642-645`).

**Démontré.** Après cette écriture, ces scripts n'ont pas de chemin de retour vers l'ancien nom. Le volume non choisi reste sur le média tant qu'une exécution ultérieure, démarrée depuis l'autre banque, ne le prend pas comme inactif.

**Démontré.** Les étapes `bootloader`, `security` et `bootstrap` ne protègent pas l'autre banque root. Bootstrap est une partition mtd unique (`image-update:415`). Security est un volume commun ; `-f` écrit aussi le spare (`image-update:477`). kboot écrit la même image dans les deux volumes (`image-update:520-528`). Une installation qui ne doit pas remplacer le bootloader ni security s'arrête, dans ce que le script permet de distinguer, aux cibles `root` et `apps` : les autres cibles ont d'autres volumes.

**Démontré.** `echo 0 >/sys/kboot/next` ne nomme pas la banque à garder (`kboot-base.initd:3`). Le garder ou le laisser s'exécuter ne choisit pas `root` plutôt que `rootB` dans ce texte.

**À vérifier**, et bloquant pour affirmer que le retour arrière fonctionne encore après une activation : le bootloader qui lit `BOOT_INFORMATION_FILE`, le pilote qui interprète `/sys/kboot/next` et `/sys/kboot/mode`, et le sort d'un boot qui n'atteint pas `kboot-base.initd`. Le watchdog n'est pas dans cette chaîne. Sans ces pièces, le code démontre la préservation du volume actif tant que la marque n'est pas réécrite, et non un repli matériel après un essai raté.

> Les empreintes historiques des fichiers expurgés se rapportent aux originaux privés.
