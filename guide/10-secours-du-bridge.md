# 10 · Récupérer la banque A depuis le secours B

Le 23 novembre 2026, le bridge a démarré le système constructeur KizOS en banque B après un essai applicatif. KizOS a réécrit la racine et les applications de A. La récupération a demandé le JTAG. Pour pouvoir réparer A depuis le réseau local, nous avons changé ce qui démarre quand le chargeur choisit B.

Le chargeur modifié garde le noyau constructeur de B et lance une initialisation de secours qui ouvre SSH. Deux démarrages consécutifs de A sans acquittement de santé font basculer vers B au démarrage suivant. En fonctionnement normal, A acquitte sa santé et remet le compteur à zéro. Un reset par le watchdog suit une autre branche et arrête le démarrage.

## Trois essais sur l’Atlantic 500090

| Essai du 25 novembre | Version du chargeur | Ce que le bridge a montré |
| --- | --- | --- |
| Coupure puis remise sous tension | v3.11 | La banque A a atteint `HEALTH_OK` en 22 s. |
| Deux coupures avant l’acquittement de A | v3.11 | Le compteur est passé de 0 à 1 puis à 2. Au démarrage suivant, B a annoncé `RESCUE_READY`. La connexion SSH a abouti. |
| Réécriture de la racine A depuis B | v3.14 | Après sélection de B par compteur forcé, le secours a écrit la racine v4.2 et l’a relue. A a ensuite atteint `HEALTH_OK`. L’application v8.11 a redémarré et le compteur est revenu à zéro. |

Pour le troisième essai, A contenait déjà la racine v4.2. L’essai établit que B sait écrire puis relire la racine et que A redémarre. Le cas d’une racine réellement corrompue et la restauration complète de la NAND restent ouverts.

## Ce que la v3.14 change

Pendant un essai de la v3.13 en RAM, le noyau du secours a attaché la partition UBI en écriture sans réserver les blocs de la table des blocs défectueux (BBT). UBI a effacé cette table. Au démarrage suivant, le chargeur s’est arrêté. La récupération par JTAG a permis de recréer la table et de la comparer octet par octet à la sauvegarde du 17 novembre.

La v3.14 conserve la propriété `nand-on-flash-bbt` dans l’arbre matériel du secours. Sur cette carte, le secours a retrouvé les deux copies de la table et UBI a compté quatre blocs défectueux. Ces observations sont propres à la NAND essayée.

## Écriture et retour au chargeur constructeur

Sur le bridge essayé, le script v3.14 `ecrire-kboot.sh` travaille depuis A. L’action `check` vérifie l’identité des volumes, la copie constructeur dans `kboot-spare` et les empreintes des fichiers. L’action `write` écrit le volume 2. L’action `verify` le relit et compare son empreinte. Ces trois opérations ont abouti lors du passage v3.11 → v3.14. Le volume 3 contient la copie de secours du chargeur constructeur.

Depuis A, l’action `restore-oem` est prévue pour réécrire le volume 2 à partir de la copie d’origine et en vérifier l’empreinte. Le troisième essai a porté sur la racine A. Il ne qualifie pas un retour complet à KizOS ni la commande de restauration du chargeur depuis B.

[Mises à jour de l’application](08-mises-a-jour-et-retour.md) · [Sommaire](README.md#sommaire)
