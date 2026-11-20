# Linux alternatif : userland et autonomie du STM32

Analyse hors ligne du 17 novembre 2026. **La voie minimale est un Linux ARMv5 conservant le STM32 et son firmware, avec le client UART autonome déjà testé.** Le réemploi temporaire du daemon constructeur est possible à étudier comme référence de démarrage et de décodage, mais il impose une chaîne logicielle bien plus large. Aucun essai de nouveau rootfs, reboot, GPIO ou radio n’a été effectué pendant cet audit.

Le test réel antérieur établit quatre lectures principales réussies à chaud, dont deux sous blocage IP, sans le daemon OEM. **Un nouvel essai du coordinateur a aussi réussi après un reset normal du seul STM32, sous blocage IP, avec le client original et sans SET KEY/ADDRESS préalable.** CETHI termine en 93 ms, IC3 en 111 ms, sans CRC rejeté ; le daemon OEM a été restauré. Source : `../orchestration/cold02-result.txt`, code 0. Le Linux n’a pas redémarré. Cela ne valide ni un nouveau noyau, ni une coupure complète, ni toutes les fonctions. Le boot, la NAND et la restauration sont étudiés séparément dans `../linux-boot/`.

## 1. ABI établie sur les fichiers livrés

`audit_elf.py` lit les en-têtes, sections dynamiques, interpréteurs et versions GNU de **274 ELF** de `rootB/appsB`. Il ne lance ni `ldd`, ni chargeur, ni bibliothèque. Les résultats complets et SHA-256 sont dans `elf-audit.json`.

| Élément | Résultat vérifié |
|---|---|
| Machine | Tous les ELF sont ARM 32 bits little-endian, EABI5. |
| Convention flottante | 245 ELF portent `0x05000200` (soft-float) ; 29 portent `0x05000000`, sans drapeau explicite. Aucun ne porte le drapeau hard-float. Les composants retenus pour le service sont soft-float. |
| Jeu d’instructions | Les attributs des composants retenus indiquent CPU `5TEJ`, architecture ARMv5TEJ. Ne pas choisir des binaires ARMv7 ou hard-float pour cette carte. |
| Interpréteur | `/lib/ld-linux.so.3` pour les exécutables dynamiques examinés. |
| libc livrée | Chaîne interne `GNU C Library ... stable release version 2.35.` ; chargeur et libc à conserver ensemble. |
| LuaJIT | `/usr/bin/luajit-2.1.1707061634` et `/usr/lib/libluajit-5.1.so.2.1.1707061634`. L’exécutable requiert `GLIBC_2.34`, la chaîne livrée inclut des besoins `GLIBC_2.35` via libm/libstdc++. |
| C++ OEM | Modules retenus : `GLIBCXX_3.4.29`, `CXXABI_1.3.9`, `CXXABI_ARM_1.3.3`, `GCC_3.5`. OpenSSL : `OPENSSL_3.0.0`. |
| Chemins de bibliothèques OEM | `DT_RPATH=/apps/overkiz/lib` ou `/apps/overkiz/lib:/apps/overkiz/io-homecontrol/lib`. Pas de `RUNPATH` dans les composants retenus. |

Les trois ensembles calculés ont toutes leurs dépendances `DT_NEEDED` et tous les noms de versions requis disponibles dans la banque B. Ce contrôle ne vérifie pas les symboles réellement résolus à l’exécution, les modules Lua, les chargements `dlopen`, les permissions ni les périphériques.

**Un point essentiel : `io-homecontrold` n’est pas un ELF.** Le fichier de 1 510 302 octets commence par `1b 4c 4a 02` : c’est un conteneur de bytecode LuaJIT, avec modules embarqués. Le système stock utilise `binfmt_misc`, règle `/etc/binfmt.d/luajit.conf`, pour l’exécuter avec `/usr/bin/luajit`. Un rootfs neuf peut invoquer explicitement l’interpréteur et éviter de recréer ce mécanisme global. Les fichiers nommés `.lua` de l’arbre extrait peuvent également être du bytecode, pas du texte source.

## 2. Trois ensembles de réemploi

| Ensemble statique | ELF / taille non compressée | Ce qui reste hors de ce calcul |
|---|---:|---|
| Client autonome avec LuaJIT livré | **6 / 2 650 432 octets** | Client source, configuration privée, `/proc`, `/run`, UART, journaux et futur serveur/API. |
| LuaJIT + module OEM `ovk/iovp/Daemon.so` | **17 / 10 914 788 octets** | Conteneur `io-homecontrold` de 1,51 Mo, modules Overkiz/Luvit, configurations, D-Bus, stockage et scripts. C’est une borne basse, pas un paquet exécutable complet. |
| Réemploi du seul module OEM ByteArray | **13 / 7 969 876 octets** | Lua autour du module et autres modules dynamiques. Un petit module peut donc attirer une grande chaîne C++. |

Le premier ensemble contient exactement :

- `/lib/ld-linux.so.3`, `/lib/libc.so.6`, `/lib/libm.so.6`, `/lib/libgcc_s.so.1` ;
- `/usr/bin/luajit-2.1.1707061634`, `/usr/lib/libluajit-5.1.so.2.1.1707061634` et le lien SONAME `libluajit-5.1.so.2`.

Le second ajoute notamment `/apps/overkiz/lib/libCore.so.4.1.0`, `libLua.so.1.0.0`, `libBus.so.4.0.1`, `libIoHomecontrol.so.0.0.0`, `ovk/iovp/Daemon.so`, libstdc++, libatomic, libuv, libcbor, OpenSSL libcrypto et libdbus. `libIoHomecontrolOTL.so.0.0.0` existe aussi, mais n’appartient pas à cette fermeture `DT_NEEDED` ; ne l’ajouter que si un chemin conservé le charge.

Les liens symboliques et modes POSIX doivent être reconstruits à partir des métadonnées ou archives POSIX conservées, pas déduits de la seule copie Windows. Par exemple `daughterboard.sh`, absent comme fichier ordinaire, est un lien vers `/usr/share/actions/fw/bootmode` ; `stm32-utils/io` pointe vers `serial_rf`.

Pour un nouveau système utilisant musl, le réemploi le plus prévisible est un petit environnement séparé avec **chargeur et bibliothèques glibc livrés**, et chemins OEM préservés pour le daemon. Mélanger ces `.so` C++ avec un chargeur musl ou une libc ancienne n’est pas une compatibilité démontrée. Une autre option est de reconstruire LuaJIT pour le nouveau rootfs, mais le client doit alors être requalifié : ses structures FFI sont volontairement précises (`long=4`, `termios=36`, `cc` à 17, `dirent.name` à 11). Une variante de libc peut changer `dirent` et d’autres interfaces même si le noyau conserve l’UART.

## 3. Ce que le daemon OEM attend autour de lui

Le service `/etc/init.d/io-homecontrol` charge `kizosenv.sh`, `podserial.sh`, les variables de `etc/conf.d/io-homecontrol`, se place dans `/apps/overkiz/io-homecontrol`, puis lance le conteneur. Il crée le stockage et les PID sous `/data/io-homecontrol` et `/var/run/io-homecontrol`.

Le lanceur décompilé ajoute son `../lib` dans `package.path` et `package.cpath`, charge `Overkiz.Bus.Connection`, puis `Overkiz.LuaDaemon` et `ovk.iovp.main`. `LuaDaemon` lie les noms D-Bus `com.overkiz.Application.IoHomecontrol` et `com.overkiz.Application.Ovp`, initialise le poller, la configuration et l’identité. Il référence aussi le monitoring. D-Bus, les modules communs et les objets de stockage sont donc des dépendances fonctionnelles à établir au-delà de l’ELF.

Les variables importantes sont :

| Variable | Configuration livrée / rôle |
|---|---|
| `STORAGE_DIR` | `/data/io-homecontrol`, contenant les enregistrements nœuds/pile. Un test doit utiliser une copie de travail et préserver le stockage original. |
| `IO_DEVICE` | `/dev/io`, alias de `ttyS1` pour `minibox/miniio`. |
| `IO_SET_MODE_SCRIPT` | `daughterboard.sh`, chaîne de contrôle GPIO du STM32. |
| `IO_UPDATE_SCRIPT` | `fwupdate.sh`, chemin pouvant programmer le STM32 et appeler un repli de bas niveau. |
| `IO_SOFTWARE_REVISION` | Révision attendue ; défaut `v2.4.2`. Le Lua connaît aussi la sentinelle `DO-NOT-UPDATE`. |

Le client UART autonome supprime les besoins OEM/D-Bus/cloud pour le chemin déjà testé. Il conserve les contextes privés nécessaires, le codec, la corrélation et la fin de transaction. Cela permet d’exposer progressivement les fonctions utiles sans reconstruire l’ensemble du catalogue constructeur.

## 4. GPIO, initialisation et supervision

La chaîne livrée est `bootmode → stm32-utils/setmode → io → serial_rf`. `serial_rf` abaisse PA2, fixe PA3/PA5/PA6, attend **35 ms**, puis fixe PA2 selon PWR. Le mode normal `start/reset` demande BOOT0=0, BOOT1=0 et TEST_RADIO=1 ; `update` et `flash` sont des modes distincts. Ces noms et valeurs sont vérifiés dans les scripts, pas une nouvelle mesure électrique. Le rôle physique exact de PA2 ne doit pas être inventé à partir de son seul nom logiciel.

`ovk-gpio` résout les noms de lignes avec `gpiofind`, puis appelle `gpioset/gpioget`. Sur ce modèle, les noms recherchés sont de forme `pioA2`, pas une numérotation GPIO universelle. Un nouveau noyau doit conserver ou réadapter les noms, le pinctrl, l’UART, les polarités et les contraintes de maintien de ligne. Ne pas recopier une syntaxe libgpiod ancienne sans qualifier les outils retenus.

Le contrat d’initialisation UART (non publié) détaille les messages. Banque B : événement `STACK_START` (`0x0403`, valeur 4), lecture de version, puis `0x0502 SET KEY`, `0x0502 SET ADDRESS`, fin de chaque callback avant l’étape suivante. Le code lit ensuite calibration et numéro de série. Ces deux SET installent un contexte local SRAM ; ils ne constituent pas le transfert d’association `PAIRED` vers un appareil radio.

Le daemon n’est pas neutre au démarrage : il appelle le script normal de mise en route, peut faire des hard resets après erreur, et peut invoquer l’updater si la révision ne convient pas ou si le démarrage manque. Le script `fwupdate.sh` possède des commandes de programmation et un repli `stm32-upgrader`. Le choix d’une révision attendue ou d’un updater refusant l’opération doit être vérifié en environnement borné ; ce n’est pas une preuve de démarrage OEM sans écritures.

Deux supervisions sont distinctes : `busybox-watchdog` nourrit `/dev/watchdog0` toutes les 15 s avec timeout 60 s ; `autorestart` demande à `Internal.Modules` de relancer les applications. Les règles cron relancent aussi certains services. Un Linux alternatif doit avoir son propre propriétaire du watchdog et son propre superviseur. Il doit garantir **un seul propriétaire UART** ; conserver le daemon OEM en parallèle du client provoquerait des conflits.

## 5. OTA et persistance : limites précises

Sur le système livré, `/apps` est choisi en fonction du root actif : root→apps, rootB→appsB. `image-update` écrit la banque inactive puis change le repère de boot dans `/persistent/boot/boot_information_file`. Modifier une seule copie de `/etc/init.d` ou de `/apps` ne garantit donc pas la survie à une bascule A/B.

La partition `/persistent` porte des données de boot, des marqueurs et certains chemins ciblés. **Ce n’est pas une surcouche générale de tout le rootfs.** Le mécanisme post-install recherche ses scripts dans le root et apps courants, puis garde des marqueurs sous `/persistent/.../post-install/launched` ; déposer seulement un marqueur ne crée pas un service au prochain boot.

Un overlay persistant optionnel existe, sous volume UBI `overlayfs`, avec marqueur `/persistent/boot/mount-overlayfs`. Il couvre `bin etc lib root sbin usr www` et apps. Mais l’init appelle le chemin `remove` lorsque le marqueur n’est pas attendu ; ce chemin peut supprimer le volume overlayfs. Même avec le marqueur, une OTA peut changer les interfaces du système inférieur. Ce mécanisme n’est pas un point d’extension garanti et n’est pas activé par cet audit.

La sauvegarde OEM `persistent-spare` exclut explicitement `root/usr/share`, `apps/usr/share`, `factory/authorized_keys`, `factory/enable-dropbear` et `factory/enable-monitoring`. Ces chemins ne sont donc pas garantis après restauration de cette sauvegarde. De plus, `mount-persistent` possède un repli de formatage si le montage échoue. **Un essai RAM ne doit pas exécuter l’init constructeur complet**, ses scripts de migration, de montage-réparation ou de post-install.

L’essai en RAM perd normalement ses fichiers au reboot. Un rootfs alternatif ensuite installé aurait à définir son propre démarrage persistant, ses mises à jour et son retour arrière. Il ne suffit pas de désactiver une URL cloud. Cette installation reste une étape séparée ; aucune écriture de banque ou de marqueur n’est proposée ici.

## 6. Progression d’essai proposée

1. **Hors matériel, maintenant** : conserver les six blobs LuaJIT ou construire un runtime compatible, vérifier SONAME et versions, reconstruire les liens, puis tester le client avec fixtures synthétiques. Aucun périphérique réel exposé. Pour le daemon OEM, isoler les chargements Lua et D-Bus avant toute autorisation GPIO/UART.
2. **Qualification ABI en RAM sur le Linux actuel** : copie de travail sous tmpfs, chargeur cohérent et environnement explicite ; comparer les sorties de tests hors UART. Garder le stockage original en lecture seule. Ne pas charger automatiquement `kizosenv.sh` dans un shell sous `set -u`, incompatibilité déjà observée.
3. **Reprise après reset du seul STM32 — désormais réussie pour les deux lectures** : le coordinateur a obtenu les deux READ sous blocage IP sans `0x0502` préalable. Le contexte fourni par chaque `0x0100` suffit donc pour ce scénario. KEY puis ADDRESS restent une référence native et une possibilité de qualification pour d’autres fonctions ; leur nécessité n’est pas démontrée pour ces deux READ. Aucun nouvel updater, découverte ou appairage n’est nécessaire pour reproduire le scénario établi.
4. **Linux alternatif en RAM** : après le plan boot de l’autre axe, noyau/rootfs éphémères, init minimal propre, pas de montages NAND en écriture, ni de scripts stock de réparation. Vérifier watchdog, réseau d’administration, accès UART et contraintes FFI avant les lectures. Un chroot seul teste le userland mais ne démontre pas un nouveau noyau.
5. **Persistance future** : seulement après les résultats RAM et une restauration matérielle qualifiée, choisir un schéma d’installation et d’OTA explicite. Le simple succès du client à chaud n’autorise pas cette étape.

Le réemploi du daemon OEM est donc surtout un **outil de transition et une référence**. Le remplacement du client UART conserve le firmware radio et évite l’essentiel de la dette userland constructeur. Recréer aussi les sessions radio, le pilote RF et la cryptographie est un projet distinct, sans utilité démontrée pour les deux lectures locales déjà obtenues.

## Sources et méthode

Sources locales primaires : fichiers bankB extraits, métadonnées POSIX corrigées, bytecode banque B indexé dans `lua/embedded-index.json`, désassemblage `DaughterBoardManager-bankB.asm.txt`, schéma `FrameDefinition.lua` et corps STM32 déjà vérifiés identiques à la Flash réelle. Les preuves antérieures du client sont dans `../../client-autonome/RESULTAT.md`. Le manifeste de ce dossier référence les fichiers déterminants avec SHA-256.

Les pseudocodes Lua ne sont pas des sources originales et peuvent perdre des variables ; le point KEY→ADDRESS a été recoupé sur le bytecode. Le présent audit n’a ouvert aucune session REA globale, envoyé aucun nouveau corpus à Cursor, exécuté aucun code cible ou contacté aucun matériel. Aucun secret ni valeur privée de contexte n’est inclus.

> Les empreintes historiques des fichiers expurgés se rapportent aux originaux privés.
