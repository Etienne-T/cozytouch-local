# 06 · Préparer la banque inactive et vérifier le premier démarrage

Avant de préparer le volume applicatif, configurez côté Home Assistant un courtier MQTT accessible depuis `<IP_HUB>`. Le projet utilisait Mosquitto sous Home Assistant OS. Créez un compte dédié au bridge et gardez ses identifiants pour le provisionnement.

1. Réservez `<IP_HUB>` et `<IP_POSTE>` sur votre LAN. Le système A emploie une adresse statique. Son pare-feu limite SSH au poste prévu, sur le port 2222.
2. Préparez votre propre volume apps. Dans /apps/ct, broker.conf porte `<IP_HUB>`, le préfixe, `<IP_POSTE>`, `<IP_COURTIER>`, son port, les identifiants MQTT, l’identité du client et l’intervalle. targets.conf porte vos propres cibles CETHI puis IC3 dans le format accepté. La découverte et l’appairage automatiques de nouveaux appareils restent à qualifier. Si vos contextes manquent, arrêtez ici.
3. Installez votre clé publique d’administration `<CLE_SSH_PUB>` dans authorized_keys. Générez votre propre clé hôte Dropbear. Gardez sa partie publique dans le fichier de clés d’hôte connues `<FICHIER_HOTES>` sur le poste pour la vérification stricte. Après assemblage, contrôlez le propriétaire root, le mode 0700 du répertoire et le mode 0600 des quatre fichiers réguliers. Calculez le SHA-256 de votre image apps.
4. Depuis votre environnement de maintenance autorisé, vérifiez le pointeur sur B, le chargeur, la paire B, les noms, types et capacités des volumes A, leur absence de montage et l’absence de mise à jour en cours. Vérifiez sur la cible les empreintes des images à écrire. Le script historique de provisionnement attend une **ancienne image root**. Le lot v4 possède son propre manifeste.
5. Laissez le pointeur sur B pendant l’écriture des seuls volumes root et apps de A. Relisez chacun sur la longueur exacte de son image et comparez les empreintes. Le 19 novembre, apps était déjà provisionnée et concordante lors du passage à v4. Une première installation doit préparer les deux volumes. Ne transposez aucun numéro UBI sans sa correspondance vérifiée.

**Point d’arrêt avant la sélection de A.** Exigez deux relectures conformes et une récupération matérielle qualifiée pour votre carte. Le [retour au pointeur B](../analyse-2026-11-18/restauration-pointeur-jtag/PROCEDURE.md) est documenté en simulation. Sans preuve matérielle, laissez le pointeur sur B. Un retour applicatif change la version en A. La sélection de B utilise les volumes constructeur existants. Une restauration intégrale réécrit la NAND et reste non testée. Chaque opération exige sa propre preuve.

**Vérifié le 19 novembre 2026 sur notre bridge.** Le volume applicatif était déjà provisionné. Le démarrage à froid a donné une LED verte fixe, deux publications acquittées et un compteur de démarrage revenu à zéro.

**Transposition non testée.** La première installation complète sur un second bridge reste à qualifier. Contrôlez aussi la racine active, la connexion SSH stricte et les mesures côté Home Assistant. La couleur seule ne valide pas la radio.

[Plan d’installation](../analyse-2026-11-18/persistance-banque-a/phase2/PLAN-INSTALLATION.md) · [Séquence v4 et observations](../analyse-2026-11-19/ecriture-v4/PROCEDURE.md)

[Précédente](05-construire-v4.md) · [Sommaire](README.md#sommaire) · [Suivante](07-home-assistant.md)

> Les empreintes historiques des fichiers expurgés se rapportent aux originaux privés.
