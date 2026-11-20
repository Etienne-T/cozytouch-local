# 08 · Mettre à jour ou revenir en arrière

## Changer uniquement l’application

Le 20 novembre 2026, le dernier essai consigné en banque A a promu l’application v5 `v-a581179dd120` (`ct-20261120e.ctapp`). L’état relevé indiquait la v4 `v-1b3e4c30f96c` comme version précédente. [Rapport v5](../analyse-2026-11-20/maj-lan-5/RAPPORT.md)

1. Vérifiez la santé de A et notez la version avec `ct-update status` dans votre session SSH. Préparez l’archive .ctapp correspondant au service. Sous Windows, préparez une copie du lanceur de déploiement avec l’adresse `<IP_HUB>`, votre fichier de clé privée `<FICHIER_CLE>` et le fichier de clés d’hôte connues `<FICHIER_HOTES>`. Conservez la vérification stricte.
2. Utilisez cette copie avec `-Archive "<ARCHIVE_CTAPP>"` sans demander de redémarrage. Contrôlez UPDATE_STAGED et la version next. Si la version diffère, arrêtez.
3. Redémarrez pendant la fenêtre prévue. Le superviseur essaie next une fois. Attendez HEALTH_OK, deux publications acquittées et la promotion en current. Contrôlez les horodatages dans HA. Un courtier tardif a motivé la première mise à jour du 20 novembre.
4. Pour revenir à la version précédente, vérifiez d’abord son existence avec `ct-update status`. La procédure documente `ct-update rollback`, puis `ct-update reboot`. Vérifiez la version active après reconnexion. Ce retour ne change pas de banque.

## Revenir au système constructeur

Le retour à B sélectionne la paire rootB/appsB conservée sur le bridge. Il exige une paire B intacte, un pointeur lisible et un chargeur fonctionnel. Contrôlez la banque réellement montée après un démarrage à froid. Vérifiez séparément les services nécessaires. Le [scénario de récupération du pointeur](../analyse-2026-11-18/restauration-pointeur-jtag/PROCEDURE.md) décrit aussi les limites de sa simulation. Une simulation ne prouve pas la tenue après coupure.

## Restaurer toute la NAND

**Restauration physique intégrale non testée.** Il n’existe pas ici de commande de restauration qualifiée pour le lecteur. Conservez le brut avec OOB, les empreintes par lot, les journaux et la copie indépendante. Une image logique de 128 Mio seule perd les OOB. Avant toute tentative, il reste à qualifier sur une carte de réserve la géométrie, les blocs défectueux, l’ECC, la relecture indépendante et plusieurs démarrages à froid. N’utilisez pas une copie d’un autre bridge.

[Précédente](07-home-assistant.md) · [Sommaire](README.md#sommaire) · [Suivante](09-depannage.md)

> Les empreintes historiques des fichiers expurgés se rapportent aux originaux privés.
