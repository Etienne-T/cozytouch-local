# 05 · Préparer Linux v4

RAM03 avec noyau OEM B, Buildroot en RAM et v4 installée en banque A désignent trois états distincts. A désigne ici la banque de destination.

Les images compilées de la v4 et leur manifeste historique sont non publiés. Ce guide conserve la recette de construction et les paramètres du noyau.

**Recette historique de phase 2, documentée le 18 novembre 2026.** Utilisez Ubuntu 24.04 sous WSL2, GCC arm-linux-gnueabi 13, mkfs.ubifs 2.2.0, mtd-utils 2.2.1 et QEMU 8.2.2. La recette reprend les exécutables ARMv5 de Buildroot 2026.08 depuis le CPIO fusion. Elle reconstruit Linux 6.12. Un clone dépourvu de ce CPIO ne suffit pas.

1. Créez un répertoire Linux isolé pour les sorties. Placez les sources Linux et mtd-utils dans son sous-dossier sources. Vérifiez les deux archives avec les SHA-256 de [REPRODUIRE.md](../analyse-2026-11-18/persistance-banque-a/phase2/REPRODUIRE.md).
2. Depuis phase2, suivez les blocs de cette recette dans l’ordre : noyaux sam9 et qemu, DTB QEMU, compilation croisée statique des outils MTD, puis assemblage. Utilisez le même répertoire de construction dans chaque commande.
3. Exécutez l’audit des images puis le banc QEMU décrits dans la recette. Gardez le manifeste de votre lot. Les UUID UBIFS et les dates peuvent changer son empreinte. Un test QEMU valide le scénario émulé. Il ne qualifie pas l’écriture physique de votre NAND.

**Reconstruction de la v4 finale depuis un clone vierge : non démontrée.** La recette de phase 2 dépend d’un CPIO externe au clone. Son banc QEMU et le contrôle du manifeste v4 répondent à deux questions distinctes.

[Précédente](04-sauvegarde-stm32.md) · [Sommaire](README.md#sommaire) · [Suivante](06-installer-banque-a.md)

> Les empreintes historiques des fichiers expurgés se rapportent aux originaux privés.
