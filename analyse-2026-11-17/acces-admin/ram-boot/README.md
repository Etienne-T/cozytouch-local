# Candidat d’accès SSH temporaire par démarrage RAM

Kit local préparé le 17 novembre 2026. **Le coordinateur a signalé une tentative de démarrage RAM à 16:28:55 UTC. L’accès SSH n’est pas vérifié : les deux contrôles LAN suivants trouvent les ports fermés.** Voir `../RESEAU.md` et les preuves datées. Cet agent n’a commandé ni JTAG ni GPIO. Le kit ne contient aucune image NAND à écrire.

**État final de cette tentative : aucun accès SSH obtenu.** Après le retour au démarrage normal exécuté par le coordinateur, le contrôle LAN à 16:41:07 UTC retrouve la MAC attendue ; les ports 2222, 22, 443 et 8443 restent fermés. Le retour réseau après reset normal est vérifié. Le fonctionnement du cloud et des appareils reste non vérifié. Aucun nouvel essai ni activation n’a suivi. Preuve : `../after-normal-reset-20261117T164107Z.json`. Les procédures ci-dessous décrivent le kit conservé et ne constituent pas une instruction de le relancer.

`build-kit.py` modifie uniquement `/chosen/bootargs` d’une copie de `rootB/boot/at91-kizboxmini-base.dtb`. Les autres propriétés sont comparées avant/après. Le résultat suppose la carte `miniio` et la racine `ubi0:rootB` ; leur sélection effective doit être vérifiée avant usage. Le noyau correspondant est celui de `rootB/boot/zImage-5.4.302`. Les empreintes sont dans `manifest.json` et `../kernelB-boot-inspection.json`.

Le wrapper est transmis à `/bin/sh -c`, en arrière-plan, puis le PID1 exécute l’init normal. Pendant au plus 60 secondes, il attend le montage de `/run` en tmpfs et le marqueur natif `/tmp/boot`. Il crée sous `/run/cozytouch-admin` un répertoire SSH en mode 0700, un `authorized_keys` en mode 0600 et une clé d’hôte RSA 2048 générée sur le bridge. Il masque temporairement `/root/.ssh` par un bind et démarre Dropbear sur 2222 avec les mots de passe et redirections désactivés. Il ne passe pas par le script d’init Dropbear.

La clé publique Ed25519 existante demandée initialement a été écartée après inspection du binaire livré : celui-ci annonce `ssh-rsa`, sans chaîne `ssh-ed25519`, et contient une assertion limitée à `DROPBEAR_SIGNKEY_RSA`. Une clé RSA 2048 dédiée à cet essai a donc été créée avec l’accord du coordinateur. **Seule sa partie publique est incluse dans le DTB.** Le fichier privé `cozytouch-admin-rsa2048` reste dans ce dossier local ; ne pas le copier sur le hub, le Pi ou dans un rapport. Sa lecture sans mot de passe et la correspondance avec la partie publique sont vérifiées sans affichage de son contenu.

La revue native indépendante confirme que le verrouillage du mot de passe root ne bloque pas le chemin par clé publique dans ce binaire : ni `fill_passwd` ni les contrôles communs ne rejettent le champ shadow verrouillé. La chaîne de compte verrouillé concerne la vérification d’un mot de passe. **Aucune modification de `/etc/shadow` n’est nécessaire pour ce kit.** Voir le verdict natif (non publié). L’acceptation réelle de la clé reste à vérifier sur le serveur temporaire.

La ligne de commande mesure 956 octets avec son NUL final, sous la limite ARM Linux 5.4 de 1024. Le script de validation contrôle le découpage après `--`, et un programme C reproduit `next_arg` et la réparation de `set_init_arg` de Linux 5.4 : le noyau transmet exactement deux arguments, `-c` et le script complet. `sh -n` a accepté la syntaxe sur le HP. Ces contrôles n’exécutent ni montage ni Dropbear et ne prouvent pas le démarrage matériel.

## Préconditions à revérifier avant tout nouvel essai

1. Vérifier l’identité du hub et le choix réel du DTB, de la racine et du noyau.
2. Arrêter les DMA avant de remplacer la RAM. Valider les adresses, les marges de décompression/BSS, les registres ARM, les caches et la MMU.
3. Revalider la pause du watchdog pendant les transferts CPU arrêté, puis le réarmer juste avant la reprise. Ne pas modifier son mode sur une hypothèse. Les transferts SRAM/DDR doivent être vérifiés avant branchement au noyau.
4. Reconnaître que le redémarrage normal de l’OS peut écrire ses données habituelles et rétablir sa connexion cloud. La promesse du kit porte sur l’absence de fichier d’administration persistant, pas sur zéro écriture NAND de l’OS entier.
5. Après démarrage, vérifier le port 2222 depuis le LAN, sa nouvelle clé d’hôte et l’authentification dédiée. Les premières commandes doivent rester en lecture : identité, `id`, noyau, montages, processus, état des services.

Si le client exige les signatures `ssh-rsa` historiques, limiter l’exception éventuelle à la commande SSH de `<IP_HUB>:2222`, avec fichier `known_hosts` dédié et `IdentitiesOnly=yes`. Ne modifier aucune règle SSH globale. La clé d’hôte temporaire doit être vérifiée par le canal matériel ou une preuve indépendante avant de l’accepter comme identité forte ; une clé nouvelle seule ne suffit pas.

`rollback.sh` arrête uniquement le serveur temporaire identifié puis retire la vue autorisée temporaire. Il faut fermer les sessions déjà établies et vérifier la fermeture de 2222. Un redémarrage électrique retire également le noyau modifié en RAM, le wrapper, les montages et les fichiers du kit. Les fichiers persistants d’origine ne sont pas remplacés.

Voir `../REVUE-BOOT-RAM.md` pour les sources et limites de la proposition. Les contraintes du watchdog, des DMA et du choix matériel ne sont pas levées par la validation de syntaxe.

Le résultat matériel définitif de cette session est dans [RESULTAT-ESSAI-RAM.md](../RESULTAT-ESSAI-RAM.md). `manifest.json` décrit la construction initiale du candidat ; son champ `target_executed=false` ne constitue pas le statut des essais matériels ultérieurs, conservés séparément dans `attempt-01/` et le rapport de résultat. Les lectures de diagnostic n'ont pas identifié la commande du noyau actif.

> Les empreintes historiques des fichiers expurgés se rapportent aux originaux privés.
