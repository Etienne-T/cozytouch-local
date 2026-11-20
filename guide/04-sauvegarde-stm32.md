# 04 · Sauvegarder le contrôleur radio

**Vérifié le 17 novembre 2026.** Deux acquisitions distinctes des 256 Kio de flash interne du STM32F101RCT6 ont donné le même fichier. Le contrôleur radio garde son micrologiciel lors du passage de Linux en banque A.

1. Confirmez le modèle et la disponibilité de la liaison série dans votre environnement de maintenance. Réservez la liaison à un seul lecteur.
2. Utilisez uniquement le parcours de lecture de la ROM décrit dans l’[audit du lecteur](../analyse-2026-11-17/offline-next/boot-read-audit/RESULTAT.md). Arrêtez au premier identifiant inattendu, refus ou dépassement de délai. **Ne lancez jamais de déprotection ni le script constructeur fwupdate.sh**. La déprotection peut effacer la flash.
3. Faites deux lectures indépendantes de 0x08000000 à 0x0803FFFF inclus. Gardez deux fichiers distincts.
4. Vérifiez chaque taille avec `wc -c "<LECTURE_A>" "<LECTURE_B>"`. Attendez 262 144 octets par fichier. Calculez les deux SHA-256 avec `sha256sum "<LECTURE_A>" "<LECTURE_B>"`. Comparez ensuite avec `cmp "<LECTURE_A>" "<LECTURE_B>"`. Attendez le code 0.
5. Archivez les lectures et le journal en accès restreint. Contrôlez la copie sur un second support. Une lecture réussie ne qualifie pas la reprogrammation du STM32.

[Précédente](03-jtag-vers-ssh.md) · [Sommaire](README.md#sommaire) · [Suivante](05-construire-v4.md)

> Les empreintes historiques des fichiers expurgés se rapportent aux originaux privés.
