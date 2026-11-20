# Phase 2 — construction et banc hors ligne

La recette ci-dessous décrit le banc historique. Elle suppose un CPIO de fusion vérifié et les configurations et répertoires de travail de ce banc. Le lot public fournit la recette, les sources et les tests de phase 2. Les binaires et les entrées privées nécessaires à une reproduction complète sont non publiés.

La tentative SSH vers l’alias <CHEMIN_LOCAL> a expiré. Le lot a été construit sous Ubuntu 24.04 WSL2, dans <CHEMIN_LOCAL> La recette conserve les Kconfig fusion et les binaires ARMv5 de Buildroot 2026.08. Elle reconstruit Linux et les composants de phase 2. Le script extract-runtime.py vérifie le SHA-256 du CPIO fusion puis copie 28 chemins ELF ou liens de bibliothèques exactement nommés. Il ignore les configurations historiques contenues dans ce CPIO.

Préparer dans sources/ du dossier de construction les deux archives vérifiées puis les extraire dans ce même sous-dossier.

| Archive | SHA-256 |
|---|---|
| linux-6.12.tar.xz | b1a2562be56e42afb3f8489d4c2a7ac472ac23098f1ef1c1e40da601f54625eb |
| mtd-utils-2.2.1.tar.bz2 | f7ae20b2eb79ee83441468f0b99d897024cd96ff853eea59106fb1952065c803 |

Outils principaux du lot livré. GCC arm-linux-gnueabi 13, mkfs.ubifs 2.2.0, mtd-utils de secours 2.2.1, QEMU 8.2.2 et Mosquitto 2.0.18. Les archives proviennent de kernel.org et infraroot.at. La recette utilise le CPIO, le DTS RAM4 et les Kconfig existants sous leurs chemins du projet.

Lancer depuis phase2 en remplaçant /chemin/build par un répertoire Linux isolé. Les scripts Buildroot historiques dotés d’overlays privés ne sont pas requis.

    bash build-kernels.sh /chemin/build sam9
    bash build-kernels.sh /chemin/build qemu
    make -C /chemin/build/sources/linux-6.12 O=/chemin/build/out/qemu \
      ARCH=arm CROSS_COMPILE=arm-linux-gnueabi- dtbs

    cd /chemin/build/sources/mtd-utils-2.2.1
    CC=arm-linux-gnueabi-gcc CFLAGS=-march=armv5te LDFLAGS=-static \
      ./configure --host=arm-linux-gnueabi --without-tests --without-lsmtd \
      --without-jffs --without-ubifs --without-zlib --without-xattr \
      --without-lzo --without-zstd --without-selinux --without-crypto --disable-ubihealthd
    make mtdinfo nanddump ubinfo ubiattach ubidetach ubiformat ubiupdatevol

Revenir dans phase2. Lancer l’assemblage avec des droits suffisants pour créer les nœuds du CPIO et les fixtures appartenant à root.

    bash build-images.sh /chemin/build
    python3 audit-images.py /chemin/build
    bash tests/run-evidence.sh /chemin/build

Le banc crée un courtier sur la boucle locale de l’hôte. Les données d’appareils, l’authentification et les clés SSH sont synthétiques et confinées à un dossier temporaire du banc. Les modifications du banc concernent uniquement la NAND émulée. Les journaux publics conservent des statuts et la géométrie. Les UUID générés par mkfs.ubifs et les métadonnées temporelles empêchent de déduire une reproduction octet à octet à partir des seules commandes. Le manifeste désigne le lot effectivement testé.

> Les empreintes historiques des fichiers expurgés se rapportent aux originaux privés.
