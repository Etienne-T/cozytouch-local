# Cozytouch local — projet indépendant

Ce projet documente le bridge Atlantic 500090 (Overkiz Kizbox Mini) et les travaux qui permettent de lire les équipements Atlantic depuis Home Assistant avec un service local. Il conserve les sources, les procédures et les preuves textuelles sélectionnées.

## Matériel et logiciel

Le bridge associe un AT91SAM9G25, une NAND MX30LF1G18AC et un STM32F101RCT6 exécutant MRIO v2.4.2. Le STM32 pilote la radio Si4461 en 868 MHz.

Le 19 novembre 2026, le système v4 a démarré en banque A sur Linux 6.12. La banque B conserve le KizOS d’origine. La sixième mise à jour par le réseau local, le 20 novembre 2026, a promu l’application v6 `v-f871bf800c8a`, alors active. La v5 était la version précédente. [Rapport v6](analyse-2026-11-20/maj-lan-6/RAPPORT.md) Le service publie les lectures via MQTT. [Reconnaissance matérielle](RECHERCHE-REVERSE-2026-11-17.md) · [Écriture et démarrage v4](analyse-2026-11-19/ecriture-v4/PROCEDURE.md)

Le 25 novembre 2026, le bridge exécutait la racine v4.2 et l’application v8.11. Le pilotage depuis Home Assistant et la réparation de A depuis le secours B ont été vérifiés sur ce matériel. [Article · Piloter deux appareils et récupérer le bridge après une panne](guide/pilotage-et-recuperation.md)

## Chronologie

- **6 avril 2026** · Première enquête documentaire. [Analyse historique](COZYTOUCH_ANALYSIS.md), en anglais
- **17 novembre 2026** · Acquisition et analyse NAND, analyse MRIO, lectures locales et essai de Linux en RAM. [Synthèse NAND](analyse-2026-11-17/SYNTHESE.md) · [Service local](analyse-2026-11-17/service-local/RESULTAT.md) · [Linux en RAM](analyse-2026-11-17/buildroot-ram/RESULTAT.md)
- **18 novembre 2026** · Préparation de la banque A et qualification sur banc QEMU. [Persistance banque A](analyse-2026-11-18/persistance-banque-a/RESULTAT.md) · [Sources et construction phase2](analyse-2026-11-18/persistance-banque-a/phase2/REPRODUIRE.md)
- **19 novembre 2026** · Essai de démarrage en banque A, diagnostic du démarrage radio, puis démarrage v4 autonome après débranchement. Premier essai dans le résultat local de démarrage en banque A · [Résultat v4](analyse-2026-11-19/ecriture-v4/PROCEDURE.md)
- **20 novembre 2026** · Mises à jour LAN pour attendre un courtier MQTT tardif, puis publier des mesures radio supplémentaires. [Premier déploiement](analyse-2026-11-20/maj-lan-1/PROCEDURE.md) · [Deuxième déploiement](analyse-2026-11-20/maj-lan-2/PROCEDURE.md) · [v3](analyse-2026-11-20/maj-lan-3/RAPPORT.md) · [v4](analyse-2026-11-20/maj-lan-4/RAPPORT.md) · [v5](analyse-2026-11-20/maj-lan-5/RAPPORT.md) · [v6](analyse-2026-11-20/maj-lan-6/RAPPORT.md)

## Suite

Les relevés laissent ouvertes l’échelle du V40, la comparaison simultanée de l’index PAC et l’interprétation du registre de consommation IC3. La [fiche Home Assistant](guide/07-home-assistant.md) détaille les mesures et leurs limites. [Périmètre de publication](PUBLICATION.md)



Le projet est indépendant et sans affiliation avec Atlantic, Overkiz ou Somfy. Le contenu est fourni sans garantie. Toute intervention se fait à vos risques.

[Guide](guide/README.md) · [Périmètre et marqueurs](PUBLICATION.md)

## Licence

- **Code** (Lua, Python, scripts shell, PowerShell et Tcl, sources C et assembleur, paquets `.ctapp`, fichiers Buildroot du projet) : [MIT](LICENSE).
- **Documentation** (fichiers Markdown) : [CC BY 4.0](LICENSE-DOCS.md).
- **Exceptions.** Les fichiers DTS et DTSI dérivés du noyau Linux restent sous GPL-2.0-or-later. Les fichiers `.config` de Linux, Buildroot et BusyBox sont des configurations de ces projets. Les courts extraits de firmwares Atlantic, Overkiz ou MRIO, cités à titre d’analyse, restent la propriété de leurs auteurs.
