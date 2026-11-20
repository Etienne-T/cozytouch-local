# 02 · Sauvegarder les pages et leurs octets auxiliaires

**Vérifié le 17 novembre 2026.** La NAND comporte 65 536 pages de 2 048 octets, chacune suivie de 64 octets auxiliaires (OOB). Ces octets conservent notamment les informations de correction d’erreurs. L’archive de référence contient les pages physiques dans l’ordre, y compris les blocs marqués défectueux.

1. Depuis le Pi câblé selon la fiche 01, vérifiez le TAP avec la configuration de scan de la sonde. Le matériel essayé répondait avec l’IDCODE 0x0792603f à 5 kHz. Une erreur de capture IR impose de revoir tension, orientation et contacts.
2. Préparez un dossier de sortie vide sur un support fiable. Dans le dossier JTAG, contrôlez les chemins, la configuration OpenOCD et les fichiers attendus par les outils avant de reprendre la méthode d’acquisition. Le lecteur utilise la RAM et interrompt le système. Ne reprenez pas son ancien contexte CPU.
3. Effectuez le passage A avec le mode `backup` de `backup-nand.py`. Le lecteur conserve les OOB sans correction ECC. Attendez les 64 lots de 1 024 pages, avec leurs CRC concordants. Taille finale attendue : **138 412 032 octets**.
4. Utilisez le mode `verify` de `verify-nand-target.py`. Il relit toute la puce et calcule le SHA-256 de chaque lot sur la cible. Exigez **64 correspondances sur 64**. Recalculer deux fois le SHA-256 du fichier sur le poste ne vérifie pas la lecture matérielle.
5. Copiez le brut, les journaux et le manifeste sur un second support. Sous Linux, lancez `sha256sum "<IMAGE_BRUTE>"` sur chaque copie. Notez votre propre empreinte. Gardez le brut intact et faites les corrections éventuelles sur un dérivé.

Un lot absent ou discordant bloque la suite. Conservez le journal et les deux résultats pour identifier un transfert instable. La sauvegarde NAND exclut le STM32. [Méthode et incidents](../jtag/ACQUISITION.md)

**Entrée en fiche 03.** RAM03 part du système constructeur (OEM) déjà démarré sur la NAND. Après l’acquisition, ne reprenez pas l’ancien contexte CPU. Le passage de fin d’acquisition à un nouveau démarrage OEM n’est pas établi ici. Si vous ne pouvez pas confirmer ce nouvel état, **arrêt ici**.

[Précédente](01-materiel.md) · [Sommaire](README.md#sommaire) · [Suivante](03-jtag-vers-ssh.md)

> Les empreintes historiques des fichiers expurgés se rapportent aux originaux privés.
