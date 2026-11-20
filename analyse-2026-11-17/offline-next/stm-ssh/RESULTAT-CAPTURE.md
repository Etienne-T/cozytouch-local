# Lecture STM32 par SSH — 17 novembre 2026

La capture de cinq secondes a récupéré la requête de version et la réponse du STM32 actif : **v2.4.2**. Les deux trames ont un CRC valide, sans candidat rejeté ni octet restant dans le parseur. Cette lecture évite de retourner la carte ou de connecter le LA1010 pour cet échange.

Le coordinateur a revu le script, vérifié son SHA-256 après dépôt dans `/run/ct`, puis contrôlé sa syntaxe sans exécution. Le test préalable sur un processus enfant jetable avait validé read, write, readv, writev et le détachement ARM. La capture réelle a observé uniquement les buffers du FD10 de `io-homecontrold`, résolu vers `/dev/ttyS1`. La requête native était le GET de version déjà qualifié ; aucune écriture UART directe ni commande d'appareil n'a été ajoutée.

Résultat : 275 arrêts de traçage, deux enregistrements, 22 octets (8 TX et 14 RX). Le GET et la capture ont terminé avec le code 0. Le nettoyage vérifie le détachement, la même identité et le même démarrage du processus. Le contrôle final retrouve TracerPid0, un thread, l'état sleeping et FD10 sur ttyS1. Le traçage ajoute de brefs arrêts au processus ; ce n'est pas une mesure électrique passive des timings.

Preuves privées conservées :

- `run-radio-result-01.txt` et reçu JSON : coordination et état final.
- `capture-01-private.txt` : octets, SHA-256 `9b5914f58a6b23623072a7fefca730fd36a39e1756130513047d1cad50120085`, identique sur le hub et Windows.
- `capture-01-decoded.json` : résultat du décodeur, sans contenu radio privé.
- `capture-radio-fd10.lua` : SHA-256 `05c625d1fe94e3a0e22398c5ecd970317ef954847215131553c02d324b85e848`.

Cette preuve confirme la version exécutée, pas l'identité intégrale de la flash avec l'image livrée. Aucun dump complet de flash STM32, effacement, changement de protection ou passage en bootloader n'a été effectué. Les éventuelles lectures de production, calibration ou empreinte d'application restent à qualifier séparément.

Le SH-U09C5 ne sert qu'à recevoir la console de démarrage Linux. Ses fils RXD et GND peuvent être retirés sans couper SSH. Conserver l'alimentation du hub et Ethernet : un redémarrage ferait perdre l'accès ajouté en RAM. Le STM32 est au verso, côté antenne et NAND. Le LA1010 est préparé sur le HP ; aucune nouvelle acquisition matérielle n'a été lancée, car il était absent lors du dernier contrôle USB.

> Les empreintes historiques des fichiers expurgés se rapportent aux originaux privés.
