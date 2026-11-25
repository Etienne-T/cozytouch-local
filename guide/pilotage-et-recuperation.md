# Cozytouch sans cloud : piloter deux appareils et récupérer le bridge après une panne

Le 25 novembre 2026, un appui dans Home Assistant a lancé un séchage de 60 minutes sur un Sauter Asama. Le bridge Atlantic 500090 a relu la durée et l’état actif par radio, et le propriétaire a vu le cycle démarrer sur l’appareil. Quelques minutes plus tôt, ce même bridge avait redémarré après la réécriture de son système principal depuis sa banque de secours.

## Du bouton Home Assistant au sèche-serviettes

Le chauffage et le chauffe-eau Calypso étaient déjà associés au bridge. Le projet conserve leur liaison radio d’origine. Le nouveau système Linux de la banque A reçoit les commandes de Home Assistant via MQTT sur le réseau local. Il échange par liaison série avec le STM32 du bridge, qui assure la communication radio avec les appareils. Cette chaîne fonctionne avec l’accès Internet du hub bloqué.

Le premier service publiait uniquement les mesures. À partir de la v7, le pilotage s’active commande par commande. Pour chaque geste, le service envoie la demande et relit les registres concernés. Si une écriture est partie et que la confirmation reste incertaine, le service verrouille les nouvelles écritures vers cet appareil. Sur le banc QEMU, l’émulation du processeur Linux et du firmware STM32 d’origine a notamment permis de reproduire une réponse dupliquée et de corriger le traitement de ce cas.

Sur cette installation, les essais ont confirmé le réglage de la consigne et des modes du sèche-serviettes, le début et la fin d’absence, ainsi que les commandes Éco et automatique du chauffe-eau. Le séchage a montré pourquoi il faut distinguer l’accusé radio, la relecture d’état et l’effet visible.

| Durée demandée dans Home Assistant | Version essayée | Observation |
| --- | --- | --- |
| 30 min et 120 min, le 23 novembre | v8.7 | Pour chaque appui, le hub a relu la durée et l’état de séchage. Le propriétaire a confirmé le démarrage sur l’appareil puis arrêté le cycle à la main. |
| 60 min, le 25 novembre | v8.11 | La première relecture d’état, environ 7 s après l’écriture, indiquait encore le chauffage normal. Le hub a ensuite relu 60 min, puis le mode séchage environ 19 s après l’écriture. Le verdict final, `ACK_RELUE`, est arrivé 31 s après l’appui. Le propriétaire a confirmé le démarrage sur l’appareil. |

Le dernier essai qualifie le lancement du cycle et la durée acceptée par l’appareil. La fin automatique à l’issue des 60 minutes reste à vérifier. L’unité du registre de consommation du sèche-serviettes reste également à établir.

## Quand le secours constructeur a réécrit le système principal

Le 23 novembre, pendant un essai de mise à jour, le bridge a démarré KizOS en banque B. Le système constructeur a alors réécrit la racine et les applications de A. Les journaux volatils de A avaient disparu. La cause exacte de l’échec initial reste inconnue. La récupération a demandé un accès matériel par JTAG.

L’enquête a identifié deux conditions importantes. D’une part, le chargeur compte les démarrages de A avant que le système confirme sa santé. Redémarrer une nouvelle fois après l’échec d’un essai applicatif peut atteindre le seuil de bascule. D’autre part, la valeur laissée dans le registre de prochain démarrage pouvait ouvrir le chemin de migration du constructeur après un redémarrage logiciel.

La racine v4.2 prépare désormais le prochain démarrage et contrôle le compteur avant le redémarrage normal. Le chargeur modifié conserve le noyau de B, mais y lance une initialisation de secours qui permet de réparer A par le réseau local. Lors des premiers essais, la console est restée muette après le passage au noyau de B. Une lecture de la mémoire a établi que le noyau tournait déjà. Il fallait tenir compte de l’absence de console noyau et corriger le contrôle des volumes par l’initialisation.

## Ce que les trois essais de récupération ont établi

1. **Après une coupure d’alimentation**, le chargeur v3.11 a démarré A. Le bridge a confirmé sa santé 22 s après le début du démarrage.
2. **Après deux démarrages interrompus avant cette confirmation**, le compteur a atteint 2. Au démarrage suivant, le chargeur v3.11 a choisi B. Le secours a ouvert SSH et un redémarrage a ramené le bridge sur A.
3. **Depuis le secours v3.14 démarré en NAND**, la racine v4.2 a été réécrite puis relue à l’identique. A a ensuite démarré Linux 6.12 et l’application v8.11. Le compteur est revenu à zéro. Pour cet essai, le compteur avait été forcé et la racine contenait déjà la v4.2.

Entre les deuxième et troisième essais, une version intermédiaire du secours a effacé la table des blocs défectueux de la NAND. La [fiche de récupération](10-secours-du-bridge.md) explique comment cet incident a été détecté et ce qui a changé dans la v3.14. Il reste à éprouver la réparation depuis B avec une racine A réellement corrompue. La restauration physique de toute la NAND reste elle aussi non testée.

Les résultats portent sur un bridge Atlantic 500090 et ses deux appareils déjà associés. Le [guide de lecture des mesures](07-home-assistant.md) décrit les données disponibles. La [fiche de mise à jour](08-mises-a-jour-et-retour.md) distingue le retour applicatif en A, le démarrage du secours B et le retour au système constructeur.
