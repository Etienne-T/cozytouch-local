# Sources et portée des preuves

Les rapports historiques décrivent le banc d’origine. Leurs valeurs réseau et leurs manifestes matériels ne servent pas de configuration pour un autre bridge.

- [Périmètre de publication](../PUBLICATION.md)
- [Identification de la carte](../RECHERCHE-REVERSE-2026-11-17.md) et [repères de câblage](../jtag/README.md)
- Vérification de la sauvegarde NAND (non publié) et [acquisition par lots](../jtag/ACQUISITION.md)
- [RAM03 avec noyau OEM B, accès SSH du 17 novembre](../analyse-2026-11-17/acces-admin/ram-kmsg-03/RESULTAT.md) et [relance du 19 novembre](../analyse-2026-11-17/acces-admin/ram-kmsg-03/RESULTAT-20261119.md)
- [Résultat Buildroot en RAM](../analyse-2026-11-17/buildroot-ram/RESULTAT.md) et reprise après l’essai (non publié)
- Sauvegarde du contrôleur radio (non publié) et validation des deux lectures (non publié)
- [Recette Linux et banc hors ligne](../analyse-2026-11-18/persistance-banque-a/phase2/REPRODUIRE.md) et manifeste v4 (non publié)
- [Provisionnement](../analyse-2026-11-19/provisionnement/PROCEDURE.md), [premier essai en banque A](../analyse-2026-11-19/boot-banque-a/RESULTAT.md) et [démarrage v4](../analyse-2026-11-19/ecriture-v4/PROCEDURE.md)
- [Service local](../analyse-2026-11-17/service-local/RESULTAT.md) et état Home Assistant (non publié)
- Conception des mises à jour (non publié), [premier déploiement](../analyse-2026-11-20/maj-lan-1/PROCEDURE.md) et [mesures supplémentaires](../analyse-2026-11-20/maj-lan-2/PROCEDURE.md)
- [Retour au pointeur B : simulation et limites de qualification matérielle](../analyse-2026-11-18/restauration-pointeur-jtag/PROCEDURE.md)

## Documentation publique

- [OpenOCD · NAND](https://openocd.org/doc-release/html/Flash-Commands.html#NAND-Flash-Commands)
- [Buildroot · Manuel](https://buildroot.org/downloads/manual/manual.html)
- [Home Assistant · MQTT et découverte](https://www.home-assistant.io/integrations/mqtt/)
