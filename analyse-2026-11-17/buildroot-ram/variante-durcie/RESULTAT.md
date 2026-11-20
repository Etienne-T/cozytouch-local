# RAM4 allégé et durci — 18 novembre 2026

Variante publique de Linux 6.12.0-cozytouch-ram4 pour le SAM9G25. Le lot utilise Buildroot 2026.08, Linux 6.12 au commit `adc218676eef25575469234709c2d87185ca223a` et Bootlin ARMv5 EABI glibc stable 2025.08-1. Les trois archives correspondent aux sommes épinglées. La construction et l’émulation se déroulent sur le HP, dans `<CHEMIN_LOCAL>`. Le cache de téléchargements a été copié depuis le chantier RAM4. Les sorties de compilation sont propres à cette variante. Sommes des sources (non publié)

## Configuration et audit

- Le fragment Kconfig (non publié) retire CAN, Wi-Fi et cfg80211 avec sa base et ses certificats, NFS/SUNRPC, ALSA et le tunnel IPv6 SIT/6RD. Kconfig désactive aussi les dépendances devenues inutiles. 93 symboles intégrés disparaissent et 7 deviennent intégrés.
- NFSD, les tunnels SEG6 et IOAM6, et le HMAC SEG6 étaient déjà désactivés. Les objets IPv6 de base `seg6.o` et `ioam6.o` restent compilés avec le cœur IPv6 sous Linux 6.12. IPv6 et ip6tables legacy restent disponibles pour le pare-feu.
- `CONFIG_STRICT_KERNEL_RWX=y` et `CONFIG_ARM_DEBUG_WX=y` résolvent correctement. Dans `arch/arm/mm/init.c`, `arch_has_strict_perms()` exclut l’ARMv5. Sur ARM926, le noyau saute donc l’application des permissions de section RO/NX. Le contrôle W+X au démarrage est une vérification diagnostique. Les modules restent désactivés.
- `CONFIG_CRYPTO_JITTERENTROPY=y` sélectionne le générateur de l’API crypto et SHA3. Le code `crypto/jitterentropy-kcapi.c` enregistre le RNG. Le code `drivers/char/random.c` ne l’utilise pas pour initialiser le CRNG. Linux 6.12 ne fournit aucun raccordement Kconfig de ce générateur au pool d’entropie. Le seul changement de configuration ne permet donc pas d’attendre un gain CRNG attribuable à Jitterentropy.

L’audit de l’image publique contrôle les **43 fonctions requises** et les **29 fonctions interdites** de l’audit RAM4, la version locale, `PAGE_OFFSET=0xC0000000`, le plan de chargement, le timer TCB à `0xf8008000` et le pilote PIT désactivé. Le DTB est identique octet par octet à la référence hors bornes initrd. `/init` et `/lib/ramlab.sh` correspondent octet par octet à l’overlay partagé. Le CPIO ne contient ni l’overlay SSH privé ni le service UART/MQTT. Les 7 tests de construction et les 21 tests de l’audit passent. Audit A (non publié) · Audit B (non publié) · Tests de construction (non publié) · Tests d’audit (non publié)

| Mesure | RAM4 historique | Variante publique |
|---|---:|---:|
| Taille du `zImage` | 4 189 096 octets | **3 331 528 octets** |
| Fin de la réservation noyau et BSS | `0x20836c18` | `0x209552b8` |
| Budget RAM théorique de l’audit | 103,54 Mio | 103,24 Mio |

Le `zImage` perd 857 568 octets, soit 20,47 %. Kconfig sélectionne aussi `DEBUG_ALIGN_RODATA` avec les permissions strictes. Le budget RAM reste une estimation calculée avant les allocations au démarrage.

## QEMU et entropie

QEMU 10.2.1 en mode utilisateur ARM926 exécute les binaires BusyBox et Dropbear issus du CPIO. `readelf` confirme ELF32 ARM EABI5 soft-float dans les deux cas. Les contrôles confirment le shell BusyBox, l’analyse syntaxique de l’init, l’authentification SSH par clé et un vrai PTY `/dev/pts/0` via la boucle locale du HP. Des clés temporaires réservées au banc QEMU ont servi dans une copie distincte du rootfs. Preuve SSH (non publié) · Preuve PTY (non publié) · Sommes des binaires (non publié)

QEMU ne propose pas de machine SAM9G25. Aucun délai boot→CRNG de cette variante n’a pu être mesuré. Le journal RAM4 matériel du 17 novembre donne **27,949461 s** pour `random: crng init done`. Machines QEMU (non publié) · Journal RAM4 (non publié)

## Reproductibilité

Les deux sorties Buildroot `output/` et `output-repro/` utilisent `BR2_REPRODUCIBLE=y`, `SOURCE_DATE_EPOCH=1767225600`, UTC et les mêmes métadonnées Kbuild. Buildroot a compilé CMake hôte 4.4.0 pour A. B utilise le CMake Ubuntu 4.2.3, extrait dans le workspace sans installation système. La deuxième construction n’a réutilisé aucun produit compilé de la première. Recette (non publié) · Sommes des paquets CMake hôte (non publié)

La première collecte a détecté que le transfert Windows avait perdu le bit exécutable de `/init`. Le second passage de A a régénéré le CPIO après correction des modes de la copie HP. La recette applique ces modes dès le départ pour B. Kit transféré initialement (non publié)

**`zImage` est identique octet par octet. `rootfs.cpio.gz` diffère.** Sur le HP et Windows, les comparaisons donnent 3 168 210 octets pour A et 3 168 203 pour B. Le CPIO décompressé a les mêmes 529 entrées, dans le même ordre, et les mêmes métadonnées hors taille d’un fichier. La comparaison des contenus isole deux fichiers.

- `libstdc++.so.6.0.33-gdb.py` contient les chemins absolus du répertoire de sortie dans `pythondir` et `libdir`.
- `xtables-legacy-multi` reçoit au lien deux RPATH du répertoire de sortie. `output-repro` ajoute 12 octets au total dans la table de chaînes ELF `.dynstr` et décale la section `.text` d’autant. Le traitement final vide le RUNPATH et conserve la disposition ELF. Les deux binaires affichent `ip6tables v1.8.11 (legacy)` sous QEMU ARM926.

Comparaison binaire (non publié) · Comparaison HP (non publié) · Écarts CPIO (non publié) · Analyse ELF et preuve ip6tables (non publié)

## Disponibilité

Le manifeste (non publié) et SHA256SUMS (non publié) accompagnent les images, rapports et journaux sur Windows et dans `delivery/` sous le workspace HP. Le staging (non publié) décrit les contrôles futurs du lot privé et de son retour OEM.

**La revalidation sur le hub reste une étape séparée soumise à autorisation.**

> Les empreintes historiques des fichiers expurgés se rapportent aux originaux privés.
