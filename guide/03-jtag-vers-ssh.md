# 03 · Démarrer un Linux temporaire par JTAG et ouvrir SSH

Cette fiche décrit la séquence qui a ouvert un SSH root temporaire sur **notre** Kizbox Mini, le 17 novembre 2026 (essai RAM03). Le même jeu de fichiers a été relancé sur la même carte le 19 novembre 2026. Le lanceur historique épingle l’empreinte du DTB. Remplacer la clé publique d’administration du wrapper change cette empreinte et le lanceur refuse le DTB personnalisé. **Variante lecteur non qualifiée.** Elle exige aussi de réétablir l’identité du noyau, les adresses et les straps pour la carte concernée. Aucune durée et aucune autre révision ne sont promises.

Trois statuts sont utilisés ci-dessous.

- **Vérifié** : observé sur notre carte à la date indiquée, avec la source nommée.
- **Propre à notre matériel** : adresse, révision, noyau ou fichier de notre bridge. Le lecteur le recalcule pour le sien.
- **Transposition non testée** : généralisation vers une autre carte, un autre noyau ou un autre outil. Le texte le signale.

Le câblage est celui de [la fiche 01](01-materiel.md). La copie NAND de [la fiche 02](02-sauvegarde-nand.md) reste la référence avant de remplacer la SDRAM. Une adresse de chargement inadaptée peut bloquer le démarrage : elle peut recouvrir le noyau décompressé, le BSS ou le DTB. Les essais JTAG antérieurs de la même journée n’ont pas ouvert SSH.

~~~mermaid
flowchart TD
  A[Sonde et arrêt du CPU] --> B[Contrôles sans écriture]
  B --> C[Arrêt des DMA]
  C --> D[Chargement du zImage et du DTB]
  D --> E[Acquittement du watchdog et reprise]
  E --> F[Attente de la clé d’hôte]
  F --> G[SSH et contrôles en lecture]
  G --> H[Arrêt d’OpenOCD et GPIO en entrée]
~~~

L’ordre du schéma est celui de RAM03. Il ne montre pas le premier essai, resté sans SSH.

## Ce qui a été obtenu, et ce qui a échoué

**Vérifié le 17 novembre 2026.** `launch-ram.py` de `ram-kmsg-03` a chargé le noyau B en SDRAM, le journal noyau a montré les marqueurs du wrapper, puis une authentification par clé a réussi. Une seconde connexion a réussi après l’arrêt d’OpenOCD et la remise des GPIO BCM 8, 9, 10 et 11 en entrée. Source : [RESULTAT.md](../analyse-2026-11-17/acces-admin/ram-kmsg-03/RESULTAT.md) et `archive-verification.json` du même dossier.

**Vérifié le 19 novembre 2026, même carte, mêmes empreintes.** La relance depuis l’OEM démarré sur la NAND a de nouveau ouvert SSH, puis libéré la sonde. Source : [RESULTAT-20261119.md](../analyse-2026-11-17/acces-admin/ram-kmsg-03/RESULTAT-20261119.md).

**Vérifié : deux essais sans SSH.** Le candidat de 16:28:55 UTC a été relu en RAM, la reprise a été acquittée, et les ports administratifs sont restés fermés. Un reset watchdog a été observé plus tard, pendant le diagnostic. Son lien avec le lancement n’est pas établi. RAM02 a bien consommé la commande à l’adresse corrigée, sans que cet essai isole la cause de l’absence de serveur. Sources : [RESULTAT-ESSAI-RAM.md](../analyse-2026-11-17/acces-admin/RESULTAT-ESSAI-RAM.md) et le résultat RAM03.

L’accès vit en RAM. Un redémarrage retire le noyau chargé, le DTB, Dropbear ajouté et les clés temporaires. Après RAM03, cette disparition n’a pas été retestée : la session a été conservée. Le retour au démarrage NAND a été utilisé après le premier essai, celui qui n’avait pas ouvert SSH.

Le chargement JTAG n’envoie pas de commande d’effacement ni de programmation NAND. Le 17 novembre 2026, la racine `ubi0:rootB` était montée en lecture seule. Les fichiers SSH ajoutés étaient dans le tmpfs `/run`. Les volumes `/data` et `/persistent` étaient montés en lecture-écriture. Leurs écritures ordinaires n’ont pas été comparées. La banque B d’origine n’est pas réécrite par ce chargement. L’absence de toute écriture de l’OS sur la NAND n’est pas démontrée.

RAM03 utilise le noyau OEM B chargé en RAM. Plus loin, « banque A » désigne la destination de la v4 installée. Le Linux Buildroot 6.12 démarré plus tard le même soir est une autre image. Cette fiche ne le décrit pas. `run-ram4.py` et `stage-init.py` appartiennent à cette autre préparation.

## 1. Préparer la clé et le DTB

Le Dropbear livré dans rootB annonce `ssh-rsa`. L’inspection hors ligne de ce binaire n’a pas trouvé `ssh-ed25519`. **Vérifié le 17 novembre 2026** : la connexion a utilisé une clé RSA 2048 dédiée. Ed25519 n’est pas la clé de cet essai. **Transposition non testée** sur un autre binaire Dropbear.

Sur le poste, créez une paire neuve. Utilisez votre propre paire ; aucune clé privée n’est fournie dans le lot public.

~~~sh
ssh-keygen -t rsa -b 2048 -f "<FICHIER_CLE>"
~~~

Conservez le fichier de clé privée `<FICHIER_CLE>` sur le poste. Placez seulement la partie publique dans le wrapper.

`build-kit.py` part d’une copie de `rootB/boot/at91-kizboxmini-base.dtb` et ne change que `/chosen/bootargs`. Les autres propriétés sont comparées avant et après. Ce premier wrapper, sous `/run/cozytouch-admin`, est celui du candidat de 16:28 UTC. Il n’a pas ouvert SSH.

Le wrapper exécuté pour RAM03 est [wrapper.sh](../analyse-2026-11-17/acces-admin/ram-kmsg-03/wrapper.sh). Le brouillon de 1 023 octets du dossier `offline-suite` n’a pas été exécuté. Le DTB retenu mesure 22 100 octets, empreinte SHA-256 `f9dfe9677f8188bae1e03b5f34f178a9b783f262d65deed48680bac83591da3a`. Seule `/chosen/bootargs` change. La commande mesure 993 octets, NUL compris. **Propre à notre matériel.**

La commande active, lue dans le journal noyau de RAM03, commence par les paramètres `ubi.mtd=ubi`, `root=ubi0:rootB`, `rootfstype=ubifs`, `ro`, `loglevel=7` et `console=ttyS0,115200`, puis `init=/bin/sh -- -c` et le wrapper. La clé publique qui suit n’est pas reproduite ici. Le noyau B copie au plus 1 024 octets depuis `/chosen`. Un `bootargs` non vide est conservé par ce lecteur. Cette lecture est une inspection statique du binaire. Le journal RAM03 confirme que cette commande a été consommée.

Le wrapper est un sous-shell en arrière-plan, puis le parent exécute `/sbin/init`. Dans l’enfant, l’ordre est le suivant.

1. Attendre `/dev/kmsg`, au plus 60 tours d’une seconde. Le compteur est le même pour l’attente suivante.
2. Rediriger la sortie standard et l’erreur vers `/dev/kmsg`, puis écrire `K0`.
3. Attendre que `/run` soit un tmpfs et que `/tmp/boot` existe. Le même compteur borne cette seconde attente. À expiration, écrire `KT` et quitter.
4. Écrire `K1`. Créer `/run/ct` et `/run/ct/ssh` avec `umask 077`.
5. Y écrire la clé publique du lecteur, puis écrire `K2`.
6. Générer sur le bridge une clé d’hôte RSA 2048 avec `dropbearkey`, puis écrire `K3`.
7. Monter ce répertoire sur `/root/.ssh`, écrire `K4`, et lancer Dropbear au premier plan sur le port 2222, avec mot de passe et redirections désactivés (`-F -E -s -j -k`).

`sh -n` a accepté la syntaxe du premier kit sur le HP. Ce contrôle n’ouvre ni montage ni Dropbear. **Attendu pour le lecteur** : un DTB dont la seule propriété modifiée est `/chosen/bootargs`, un magic `d0 0d fe ed`, et une ligne qui reste sous 1 024 octets NUL compris. Remplacez la clé publique du wrapper du dépôt par la vôtre avant tout réemploi. La reconstruction avec une autre clé est une **transposition non testée**.

Le paramètre `console=ttyS0,115200` était présent. Le noyau a quand même signalé `Warning: unable to open an initial console.` Le DBGU est désactivé dans le DTB livré, et le pilote UART Atmel n’avait pas de console enregistrée. **Vérifié** : la capture UART des essais RAM a reçu 0 octet. Ce silence ne démontre pas un échec du wrapper.

## 2. Fixer le plan mémoire de ce noyau

Le lanceur refuse le chargement si les plages suivantes ne sont pas disjointes dans la DDR. Elles viennent du zImage B `5.4.302`, 3 089 896 octets, SHA-256 `8c58bb4c0bbb294f9e2b017f245183f09541ae394c59356c41b342e030d7475a`. Source statique : [NOYAU-B-MARGES-RAM.md](../analyse-2026-11-17/acces-admin/NOYAU-B-MARGES-RAM.md). Les bornes hautes sont exclues.

| Rôle | Adresse | Statut |
|---|---|---|
| Fenêtre DDR | `0x20000000` à `0x28000000` | Hypothèse du plan, 128 Mio. Contrôlée par le lanceur. |
| Début du noyau décompressé | `0x20008000` | Calculée dans ce zImage. |
| Fin du BSS | `0x205fe0bc` | Calculée dans ce zImage. |
| DTB | `0x21000000` | Utilisée les 17 et 19 novembre 2026. |
| zImage | `0x22000000` | Utilisée les 17 et 19 novembre 2026. |
| Fin conservative du décompresseur | `0x22307600` | Calculée dans ce zImage. |

**Propre à notre matériel.** Le noyau A `5.4.294` n’a pas ces adresses de symboles. Le pointeur utile pour relire la commande après le démarrage est `saved_command_line`. L’erratum du 17 novembre 2026 corrige les deux noyaux. Source : [KERNEL-JTAG.md](../analyse-2026-11-17/acces-admin/offline-suite/KERNEL-JTAG.md).

| Noyau | Adresse physique corrigée | Ancienne adresse, fausse |
|---|---|---|
| A `5.4.294` | `0x205e5014` | `0x205bf014` |
| B `5.4.302` | `0x205e7014` | `0x205c1014` |

**Vérifié** : RAM02 a été lu à `0x205e7014`. Le mot `0x7` lu à l’ancienne adresse B pendant le premier essai a été rejeté. Il n’identifie pas la banque. Une bannière laissée en RAM peut être un vestige. Recalculez le plan sur votre zImage et arrêtez s’il y a recouvrement. Réutiliser nos adresses sur un autre noyau est une **transposition non testée**.

## 3. Ouvrir la sonde et arrêter le CPU

Le script est [launch-ram.py](../analyse-2026-11-17/acces-admin/ram-kmsg-03/launch-ram.py). Sans `--execute`, il contrôle seulement les fichiers locaux. Avec `--execute`, il exige un système Linux. Il refuse de s’attacher si le port Tcl 6666 de `127.0.0.1` est déjà ouvert. Il ne tue pas une session existante.

~~~sh
python3 launch-ram.py \
  --kernel "<ZIMAGE>" \
  --dtb "<DTB>" \
  --preflight-tcl "<PREFLIGHT_TCL>" \
  --quiesce-tcl "<QUIESCENCE_TCL>" \
  --rollback-tcl "<RETOUR_TCL>" \
  --expected-mac-file "<FICHIER_MAC>" \
  --openocd-config "<CONFIG_OPENOCD>" \
  --run-dir "<DOSSIER_ESSAI>" \
  --execute
~~~

La copie du dépôt épingle les deux empreintes SHA-256 ci-dessus. Elle refuse un autre noyau ou un autre DTB. Changer ces constantes impose de revoir le plan mémoire. `<DOSSIER_ESSAI>` doit être un dossier neuf.

Le lanceur démarre `openocd -f "<CONFIG_OPENOCD>"`, attend le Tcl sur `127.0.0.1:6666`, sélectionne la cible `at91sam9g25.cpu`, règle la vitesse, puis exécute `halt`. Le délai de halt par défaut du script est 10 000 ms. Il désactive l’accès mémoire rapide et l’aire de travail.

**Propre à notre session.** L’état archivé de RAM03 nomme la configuration Pi `nand-session.cfg`, la cible, le préflight et la quiescence revus. Le scan JTAG du 17 novembre 2026 a lu l’IDCODE `0x0792603f` à 5 kHz. Le défaut `--adapter-khz` du lanceur est 1 000. L’état archivé de RAM03 ne conserve pas la vitesse réellement passée. **Non consigné.** Gardez la vitesse qui a déjà donné un scan stable sur votre câblage, et notez-la. Transposer 1 000 kHz est **non testé**.

**Attendu, vérifié sur notre carte** : le CPU est arrêté. Le lanceur compare d’abord l’adresse MAC, lue sur deux mots de 32 bits à partir de `0xf802c098`, à `<FICHIER_MAC>`, sans l’afficher. Un écart arrête la séquence avant le préflight et avant toute écriture de périphérique. Le préflight [preflight-reviewed.tcl](../analyse-2026-11-17/acces-admin/ram-boot/preflight-reviewed.tcl) reste en lecture. Il exige le mode watchdog `0x1fff2fff` à `0xfffffe44`, les straps `miniio` à `0xfffff83c`, et la MMU encore active de l’ancien Linux. Il affiche `READ_ONLY_PREFLIGHT_PASSED`. L’état RAM03 a poursuivi jusqu’à la demande d’entrée : ces contrôles ont donc abouti. La valeur initiale du PC archivée est `0xc001348c`. C’est le PC de notre Linux au moment de l’arrêt. Le lecteur ne la recopie pas comme cible.

## 4. Arrêter les DMA avant d’écrire la RAM

La quiescence est [quiesce-reviewed-candidate.tcl](../analyse-2026-11-17/acces-admin/ram-boot/quiesce-reviewed-candidate.tcl). Le CPU est déjà arrêté. Le lanceur pose `COZY_ALLOW_QUIESCE=reviewed`, puis source le fichier. Le script pose `COZY_QUIESCE_COMMITTED=1` avant la première écriture de périphérique.

Après ce drapeau, l’ordre écrit est le suivant.

1. EHCI : arrêter les listes, attendre l’arrêt, effacer le bit de marche.
2. OHCI : demander la remise à zéro, puis attendre 20 secondes sans évolution du compteur de trames.
3. MACB : couper la réception et l’émission sans modifier l’adresse de station, puis attendre la fin d’émission.
4. HDMAC0 et HDMAC1 : masquer les interruptions et attendre l’arrêt des huit canaux.

**Attendu** : le script atteint `COZY_QUIESCENCE_CHECKS_PASSED`. **Vérifié le 17 novembre 2026** sur le premier essai : les contrôles EHCI, OHCI, MACB et HDMAC sont passés. RAM03 a atteint l’étape suivante du lanceur, qui refuse de charger si le drapeau de quiescence n’est pas posé. Le compte rendu du 19 novembre 2026 nomme cette quiescence.

Après ce drapeau, un échec laisse OpenOCD actif. Le lanceur ne reprend pas l’ancien Linux. Il enregistre le script de retour et ne le source pas. Avant ce drapeau, le lanceur peut reprendre l’ancien Linux si le marqueur vaut encore zéro. RAM03 n’a pas emprunté cette branche d’abandon. Le compte rendu RAM03 n’en montre pas d’essai matériel.

Pendant toute la halte, la pause de watchdog contrôlée au préflight reste celle du mode déjà lu. Le réarmement du compteur est à l’étape 6, immédiatement avant `resume`.

## 5. Charger le zImage et le DTB, puis les relire

Le lanceur exécute `soft_reset_halt`, puis `wait_halt` avec un délai de 10 000 ms. Il exige ensuite que les bits 0, 2 et 12 de SCTLR soient à zéro : MMU, cache de données et cache d’instructions coupés. L’octet bas de CPSR doit valoir `0xD3` : état ARM, mode superviseur, IRQ et FIQ masquées.

**Vérifié le 17 novembre 2026 sur le premier essai** : SCTLR valait `0x5217a` à ce stade. L’état archivé de RAM03 ne conserve pas ce nombre. Le lanceur se serait arrêté si un seul des bits 0, 2 ou 12 était resté actif. **La valeur SCTLR de RAM03 n’est pas archivée.**

Le lanceur charge ensuite le zImage à `0x22000000` et le DTB à `0x21000000`, puis relit chaque image en entier et compare l’empreinte. Il relit aussi les quatre premiers octets du DTB et exige `d0 0d fe ed`.

**Attendu, vérifié le 17 novembre 2026 pour RAM03** : relecture noyau de 3 089 896 octets, SHA-256 `8c58bb4c0bbb294f9e2b017f245183f09541ae394c59356c41b342e030d7475a`. Relecture DTB de 22 100 octets, SHA-256 `f9dfe9677f8188bae1e03b5f34f178a9b783f262d65deed48680bac83591da3a`. Le 19 novembre 2026, les relectures des mêmes fichiers ont été déclarées conformes.

Le premier essai avait relu un autre DTB, de 22 060 octets, aux mêmes adresses, sans ouvrir SSH. Une relecture conforme ne prouve pas le serveur.

## 6. Acquitter le watchdog et reprendre le CPU

**Vérifié le 17 novembre 2026, avant les essais de démarrage.** Le mode watchdog à `0xfffffe44` valait `0x1fff2fff`, avec `WDDIS=0` et `WDDBGHLT=1` : le watchdog est actif, et la halte de debug le met en pause. Une halte de 22 secondes a laissé le PC inchangé. Cette mesure ne qualifie pas à elle seule toutes les durées de halte suivantes. La quiescence comprend déjà une attente OHCI de 20 secondes, CPU arrêté. Source : [QUALIFICATION-MATERIELLE.md](../analyse-2026-11-17/acces-admin/QUALIFICATION-MATERIELLE.md).

Le lanceur ne réécrit pas le registre de mode. Juste avant la reprise, il écrit `0xa5000001` en `0xfffffe40` pour réarmer le compteur.

Il prépare ensuite le contexte et le relit sans forcer une lecture matérielle. L’état RAM03 archive ces valeurs, avec le drapeau qui indique que ce contrôle n’est pas une relecture forcée du silicium.

| Registre | Valeur préparée |
|---|---|
| `cpsr` | `0xD3` |
| `r0` | `0` |
| `r1` | `0xFFFFFFFF` |
| `r2` | `0x21000000` |
| `pc` | `0x22000000` |

La commande suivante est `resume 0x22000000`. L’état devient `kernel_entry_requested_not_boot_confirmed`. OpenOCD reste lancé. **Vérifié** : RAM03 et le premier essai ont atteint cet état. Pour le premier essai, cela n’a pas produit de SSH. L’acquittement de `resume` ne démontre ni Linux ni le wrapper.

Le 19 novembre 2026, cette phase du lanceur s’est étendue d’environ 19:01 à 19:06:56 UTC. C’est une durée observée sur notre Pi, pas un délai à imposer.

## 7. Attendre la clé d’hôte

Laissez OpenOCD actif. La clé d’hôte est générée sur le bridge après `K2`, puis écrite dans le journal noyau parce que la sortie du wrapper est redirigée vers `/dev/kmsg`.

**Vérifié le 17 novembre 2026**, secondes depuis le démarrage du noyau : `K0` à 4,011 ; `K1` à 11,443 ; `K2` à 11,476 ; début RSA à 11,691 ; clé disponible à 114,544 ; `K3` à 114,545 ; `K4` à 114,561. La génération RSA 2048 a pris environ 103 secondes.

**Vérifié le 19 novembre 2026, même carte** : la clé d’hôte était prête à 55,5 secondes de temps noyau, avec `K0` à `K4`. La durée n’est pas stable. Attendez `K4` dans le journal. Un délai fixe de 103 secondes n’est pas un critère de succès.

`read-ring.py` réutilise la session OpenOCD. Il arrête le CPU, lit l’anneau, puis le reprend. **Vérifié le 17 novembre 2026** : l’anneau lu fait 16 384 octets, le pointeur virtuel est `0xc05eb930`, le statut de reset est `0x10000`, et le script a duré environ 1,28 seconde. Les adresses `0x205c8980` et `0x205e8c08` sont celles de ce script pour le noyau B. La lecture physique utilise le pointeur diminué de `0xa0000000`. **Propre à notre noyau.** Les réemployer ailleurs est **non testé**.

Extrayez de ce journal la clé publique d’hôte neuve. Écrivez une seule ligne dans `<FICHIER_HOTES>`. Pour un port autre que 22, la forme est `[<IP_HUB>]:<PORT_SSH>`, suivie du type et de la clé publique. Ne recopiez pas la clé dans un compte rendu. Ne réutilisez pas l’entrée d’un démarrage précédent : la clé d’hôte est régénérée à chaque lancement.

## 8. Ouvrir SSH et contrôler en lecture seule

Le wrapper exécuté écoutait sur le port 2222 et la session vérifiée était root. Ce sont les valeurs de notre essai. Une autre image utilise ses propres `<PORT_SSH>` et `<COMPTE>`.

~~~sh
ssh -p "<PORT_SSH>" -i "<FICHIER_CLE>" -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile="<FICHIER_HOTES>" "<COMPTE>@<IP_HUB>"
~~~

Dans cette session, exécutez [verify-admin-readonly.sh](../analyse-2026-11-17/acces-admin/ram-kmsg-03/verify-admin-readonly.sh). Il affiche l’identité, le noyau, certains montages, les modes, la comparaison des deux vues de `authorized_keys` et le processus Dropbear. Il n’affiche pas les clés.

**Attendu, vérifié le 17 novembre 2026** dans `admin-verification.txt` :

- `uid=0(root)`, noyau `5.4.302`, architecture `armv5tejl` ;
- `/` sur `ubi0:rootB`, type `ubifs`, option `ro` ;
- `/run` en tmpfs ;
- `/root/.ssh` en tmpfs, et les deux fichiers `authorized_keys` identiques ;
- `/run/ct` et `/run/ct/ssh` en mode 700, propriétaire root ;
- `authorized_keys` et `/run/ct/h` en mode 600 ;
- processus `dropbear`, uid 0, dernière ligne `READ_ONLY_ADMIN_CHECK_PASSED`.

Le pid Dropbear de ce démarrage était 49. Un autre pid, avec le nom `dropbear` et l’uid 0, n’est pas un échec. `io-homecontrold`, `internald`, `connmand` et `watchdogd` étaient présents. Leur présence ne prouve pas le cloud ni les appareils. Les contrôles du 17 novembre 2026 n’ont envoyé aucun ordre de chauffe, d’appairage ou de programmation de flash.

Arrêtez si le noyau, la racine ou l’option `ro` diffèrent de l’image chargée. Les chemins `/run/ct` sont ceux de ce wrapper. Si vous changez le répertoire, le script de contrôle doit suivre. Cette adaptation est **non testée**.

## 9. Libérer la sonde

Après ces contrôles, arrêtez l’OpenOCD de cet essai et remettez les GPIO BCM 8, 9, 10 et 11 en entrée. Ne redémarrez pas le bridge pour « terminer » : le redémarrage retire la session.

**Vérifié le 17 novembre 2026** : la seconde authentification a réussi après cette libération, vers 386 secondes d’uptime. Source : `stability-after-jtag-release.txt`.

Le texte de commande conservé dans le dépôt est celui de la relance du 19 novembre 2026, [release-ram03-20261119-pi.py](../analyse-2026-11-17/acces-admin/ram-kmsg-03/release-ram03-20261119-pi.py). Il envoie `shutdown` au Tcl `127.0.0.1:6666`, puis :

~~~sh
raspi-gpio set 8-11 ip
raspi-gpio get 8-11
pgrep -x openocd
~~~

**Attendu, vérifié le 19 novembre 2026** : quatre mentions `func=INPUT`, aucun processus `openocd`, puis une nouvelle connexion SSH avec le même `<FICHIER_HOTES>`. Le nom `raspi-gpio` est celui de notre Pi. Un autre outil GPIO est une **transposition non testée**.

Le lanceur ne fait pas cette libération. Il laisse OpenOCD actif après `resume`, y compris pour la lecture de l’anneau.

## Si un écart apparaît

Consultez [la fiche 09](09-depannage.md). Une relecture d’empreinte différente impose de ne pas reprendre le CPU. Un strap ou un mode watchdog différent arrête la quiescence. L’absence de `K4` signifie que le serveur de cet essai n’est pas établi.

Le retour NAND utilisé après le premier essai est décrit dans [RESULTAT-ESSAI-RAM.md](../analyse-2026-11-17/acces-admin/RESULTAT-ESSAI-RAM.md). Cette fiche n’en répète pas la routine. Le lanceur ne l’exécute pas seul.

Sources de la séquence : [launch-ram.py](../analyse-2026-11-17/acces-admin/ram-kmsg-03/launch-ram.py), [wrapper.sh](../analyse-2026-11-17/acces-admin/ram-kmsg-03/wrapper.sh), [read-ring.py](../analyse-2026-11-17/acces-admin/ram-kmsg-03/read-ring.py), [le kit](../analyse-2026-11-17/acces-admin/ram-boot/README.md), [le câblage](../jtag/README.md).

**Poursuivre vers la fiche 04.** Après la libération de la sonde et la vérification SSH, gardez la session RAM03 active, les alimentations et le câblage en place. Passez à la [sauvegarde du contrôleur radio](04-sauvegarde-stm32.md).

**Terminer l’intervention et retirer le câblage.** Coupez les deux alimentations avant de retirer les fils. La coupure du bridge met fin à la session RAM03.

[Précédente](02-sauvegarde-nand.md) · [Sommaire](README.md#sommaire) · [Suivante](04-sauvegarde-stm32.md)

> Les empreintes historiques des fichiers expurgés se rapportent aux originaux privés.
